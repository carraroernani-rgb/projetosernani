"""
Varredura de blogs concorrentes.

Estratégia em até três camadas por concorrente:
1. Tenta ler o feed RSS (mais estável e barato).
2. Se o concorrente tiver `sitemap_url` + `url_pattern` configurados (útil
   para sites que renderizam a listagem via JavaScript, ex.: PartnerStack em
   Webflow, onde o HTML estático não lista os posts), busca as URLs de posts
   diretamente no sitemap.xml.
3. Por fim, faz fallback para scraping da página de listagem de posts (com
   paginação) usando BeautifulSoup + os seletores em app/config.py.

O conteúdo completo de cada post é extraído com `readability-lxml`, que
remove menus/rodapés e mantém apenas o corpo do artigo.

Observação sobre bloqueios: alguns sites (ex.: Impartner, Allbound) usam
proteção anti-bot (Cloudflare) que pode retornar 403 mesmo com headers de
navegador legítimos. Isso está fora do escopo de contorno automático deste
projeto — se um concorrente específico começar a bloquear
consistentemente, ajuste o `listing_url`/seletor em app/config.py ou avalie
usar uma fonte alternativa (ex.: página de sitemap.xml do site).
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("scraper")

# Headers de um navegador real — reduz bloqueios básicos de bots (não contorna
# proteção anti-bot avançada como Cloudflare, que exige JS/desafios).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}
TIMEOUT = 20

# Quantas páginas de listagem HTML tentar percorrer ao fazer o backfill
# histórico (cada página costuma trazer ~10-20 posts).
MAX_LISTING_PAGES = 25


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retries = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


_session = _build_session()


@dataclass
class DiscoveredPost:
    url: str
    title: str
    published_at: Optional[datetime]


def discover_posts(competitor: dict, max_pages: int = 1) -> list[DiscoveredPost]:
    """Retorna os posts encontrados para um concorrente (RSS -> fallback HTML).

    `max_pages` controla quantas páginas de listagem HTML percorrer quando o
    RSS não estiver disponível (usado no backfill histórico para achar posts
    mais antigos). Para o RSS, o feed inteiro (todos os itens disponíveis) é
    sempre considerado — o corte por data acontece depois, no pipeline.
    """
    posts = _discover_via_rss(competitor)
    if posts:
        return posts

    if competitor.get("sitemap_url"):
        logger.info("RSS vazio/indisponível para %s, tentando sitemap.xml", competitor["name"])
        posts = _discover_via_sitemap(competitor)
        if posts:
            return posts

    logger.info("Tentando scraping HTML da listagem para %s", competitor["name"])
    return _discover_via_html(competitor, max_pages=max_pages)


def _discover_via_sitemap(competitor: dict) -> list[DiscoveredPost]:
    sitemap_url = competitor["sitemap_url"]
    url_pattern = competitor.get("url_pattern", "")
    try:
        resp = _session.get(sitemap_url, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Falha ao acessar sitemap %s: %s", sitemap_url, exc)
        return []

    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
    matched = [u for u in urls if url_pattern in u] if url_pattern else urls

    posts = []
    for url in matched:
        title = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
        posts.append(DiscoveredPost(url=url, title=title, published_at=None))
    return posts


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


def _discover_via_html(competitor: dict, max_pages: int = 1) -> list[DiscoveredPost]:
    listing_url = competitor["listing_url"]
    seen: set[str] = set()
    posts: list[DiscoveredPost] = []

    for page in range(1, max(1, max_pages) + 1):
        page_url = listing_url if page == 1 else _paginated_url(listing_url, page)
        try:
            resp = _session.get(page_url, timeout=TIMEOUT)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Falha ao acessar %s: %s", page_url, exc)
            break

        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select(competitor["link_selector"])
        if not links:
            break

        new_on_page = 0
        for a in links:
            href = a.get("href")
            if not href:
                continue
            full_url = urljoin(page_url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            title = a.get_text(strip=True) or full_url
            posts.append(DiscoveredPost(url=full_url, title=title, published_at=None))
            new_on_page += 1

        # Se a página não trouxe nenhum link novo, paramos (fim da paginação
        # ou padrão de URL de paginação não suportado pelo site).
        if new_on_page == 0:
            break

    return posts


def _paginated_url(listing_url: str, page: int) -> str:
    """Gera a URL da página N seguindo o padrão comum do WordPress (/page/N/)."""
    base = listing_url.rstrip("/")
    return f"{base}/page/{page}/"


def fetch_full_article(url: str) -> tuple[str, str]:
    """Baixa a página e retorna (titulo, texto_limpo_em_html_simplificado)."""
    resp = _session.get(url, timeout=TIMEOUT)
    resp.raise_for_status()

    doc = Document(resp.text)
    title = doc.short_title()
    content_html = doc.summary()

    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text("\n", strip=True)
    return title, text
