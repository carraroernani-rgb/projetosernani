"""Scraping de perfis do Google Maps via Playwright."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from playwright.sync_api import Page, sync_playwright

from app.enrichment import coletar_site, identificar_whatsapp_por_padrao
from app.qualification import analisar_texto
from app.database import Prospect

GOOGLE_MAPS_URL = "https://www.google.com/maps/search/"


@dataclass
class RawListing:
    nome: str
    endereco: str
    telefone: str
    site: str
    url_perfil: str
    categoria_encontrada: str
    descricao: str
    avaliacoes_texto: str


def _montar_query(categoria: str, regiao: str) -> str:
    return f"{categoria} em {regiao}"


def buscar_perfis(
    categoria: str,
    regiao: str,
    quantidade: int,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Iterator[RawListing]:
    """Abre o Google Maps, busca a categoria+regiao e itera pelos primeiros N resultados."""
    query = _montar_query(categoria, regiao)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="pt-BR")
        page.goto(GOOGLE_MAPS_URL + query.replace(" ", "+"), timeout=60000)
        page.wait_for_timeout(3000)

        feed_selector = 'div[role="feed"]'
        try:
            page.wait_for_selector(feed_selector, timeout=15000)
        except Exception:
            browser.close()
            return

        # Scroll para carregar 'quantidade' resultados
        cards = []
        tentativas = 0
        while len(cards) < quantidade and tentativas < 40:
            cards = page.query_selector_all(f'{feed_selector} a.hfpxzc')
            page.eval_on_selector(feed_selector, "el => el.scrollBy(0, 1200)")
            page.wait_for_timeout(800)
            tentativas += 1

        links = list({c.get_attribute("href") for c in cards if c.get_attribute("href")})[:quantidade]

        for i, link in enumerate(links, start=1):
            if on_progress:
                on_progress(i, len(links), link)
            try:
                listing = _extrair_perfil(page, link, categoria)
                if listing:
                    yield listing
            except Exception:
                continue

        browser.close()


def _texto_seguro(page: Page, selector: str) -> str:
    el = page.query_selector(selector)
    return el.inner_text().strip() if el else ""


def _extrair_perfil(page: Page, url: str, categoria: str) -> Optional[RawListing]:
    page.goto(url, timeout=30000)
    page.wait_for_timeout(2500)

    nome = _texto_seguro(page, "h1")
    endereco = ""
    telefone = ""
    site = ""

    botoes = page.query_selector_all('button[data-item-id], a[data-item-id]')
    for b in botoes:
        item_id = b.get_attribute("data-item-id") or ""
        aria = b.get_attribute("aria-label") or ""
        if item_id.startswith("address"):
            endereco = aria.replace("Endereço: ", "").strip()
        elif item_id.startswith("phone"):
            telefone = re.sub(r"[^\d+]", "", aria.split(":")[-1])
        elif item_id == "authority":
            href = b.get_attribute("href") or ""
            site = href

    descricao = _texto_seguro(page, 'div.PYvSYb')
    avaliacoes_texto = " ".join(
        el.inner_text() for el in page.query_selector_all('span.wiI7pd')[:10]
    )

    if not nome:
        return None

    return RawListing(
        nome=nome,
        endereco=endereco,
        telefone=telefone,
        site=site,
        url_perfil=url,
        categoria_encontrada=categoria,
        descricao=descricao,
        avaliacoes_texto=avaliacoes_texto,
    )


def montar_prospect(listing: RawListing, categoria: str, regiao: str) -> Prospect:
    dados_site = coletar_site(listing.site) if listing.site else {"email": "", "instagram": "", "whatsapp": "", "texto": ""}

    whatsapp = dados_site["whatsapp"]
    if not whatsapp and identificar_whatsapp_por_padrao(listing.telefone):
        whatsapp = listing.telefone

    tag, encontradas = analisar_texto(
        listing.descricao, listing.avaliacoes_texto, dados_site["texto"]
    )

    cidade = regiao
    if "-" in listing.endereco:
        cidade = listing.endereco.split(",")[-1].strip() or regiao

    return Prospect(
        nome=listing.nome,
        categoria=categoria,
        telefone_principal=listing.telefone,
        whatsapp=whatsapp,
        email=dados_site["email"],
        instagram=dados_site["instagram"],
        endereco=listing.endereco,
        cidade=cidade,
        google_maps_url=listing.url_perfil,
        tag_qualificacao=tag,
        palavras_chave_encontradas=", ".join(encontradas),
    )
