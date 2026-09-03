"""
Varredura de blogs concorrentes.

Estratégia em duas camadas por concorrente:
1. Tenta ler o feed RSS (mais estável e barato).
2. Se o RSS falhar ou vier vazio, faz fallback para scraping da página de
   listagem de posts usando BeautifulSoup + os seletores em app/config.py.

O conteúdo completo de cada post é extraído com `readability-lxml`, que
remove menus/rodapés e mantém apenas o corpo do artigo.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PartnerContentRadar/1.0; "
        "+https://github.com/) content-monitoring-bot"
    )
}
TIMEOUT = 20


@dataclass
class DiscoveredPost:
    url: str
    title: str
    published_at: Optional[datetime]


def discover_posts(competitor: dict) -> list[DiscoveredPost]:
    """Retorna os posts encontrados para um concorrente (RSS -> fallback HTML)."""
    posts = _discover_via_rss(competitor)
    if posts:
        return posts
    logger.info("RSS vazio/indisponível para %s, tentando scraping HTML", competitor["name"])
    return _discover_via_html(competitor)


def _discover_via_rss(competitor: dict) -> list[DiscoveredPost]:
    rss_url = competitor.get("rss")
    if not rss_url:
        return []
    try:
        feed = feedparser.parse(rss_url)
    except Exception as exc:  # feeds instáveis não podem derrubar a varredura inteira
        logger.warning("Falha ao ler RSS de %s: %s", competitor["name"], exc)
        return []

    posts = []
    for entry in feed.entries:
        published = None
        if getattr(entry, "published_parsed", None):
            published = datetime(*entry.published_parsed[:6])
        posts.append(
            DiscoveredPost(url=entry.link, title=entry.title, published_at=published)
        )
    return posts


def _discover_via_html(competitor: dict) -> list[DiscoveredPost]:
    listing_url = competitor["listing_url"]
    try:
        resp = requests.get(listing_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Falha ao acessar %s: %s", listing_url, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    links = soup.select(competitor["link_selector"])

    seen = set()
    posts = []
    for a in links:
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin(listing_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        title = a.get_text(strip=True) or full_url
        posts.append(DiscoveredPost(url=full_url, title=title, published_at=None))
    return posts


def fetch_full_article(url: str) -> tuple[str, str]:
    """Baixa a página e retorna (titulo, texto_limpo_em_html_simplificado)."""
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    doc = Document(resp.text)
    title = doc.short_title()
    content_html = doc.summary()

    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text("\n", strip=True)
    return title, text
