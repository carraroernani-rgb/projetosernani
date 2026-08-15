"""Enriquecimento de contatos a partir do site associado ao perfil do Google."""
from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
INSTAGRAM_RE = re.compile(r"(?:instagram\.com/)([a-zA-Z0-9_.]+)")
WHATSAPP_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d+)")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ProspeccaoKaryn/1.0)"}


def coletar_site(url: str, timeout: int = 10) -> dict:
    """Busca a pagina inicial do site e extrai email, instagram, whatsapp e texto bruto."""
    resultado = {"email": "", "instagram": "", "whatsapp": "", "texto": ""}
    if not url:
        return resultado
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return resultado

    soup = BeautifulSoup(resp.text, "html.parser")
    html = resp.text
    texto_visivel = soup.get_text(separator=" ", strip=True)

    email_match = EMAIL_RE.search(html)
    if email_match:
        resultado["email"] = email_match.group(0)

    insta_match = INSTAGRAM_RE.search(html)
    if insta_match:
        resultado["instagram"] = f"@{insta_match.group(1)}"

    wa_match = WHATSAPP_RE.search(html)
    if wa_match:
        resultado["whatsapp"] = wa_match.group(1)

    resultado["texto"] = texto_visivel[:5000]
    return resultado


def identificar_whatsapp_por_padrao(telefone: str) -> bool:
    """Heuristica simples: numeros BR de celular (9 digitos apos DDD) tendem a ser WhatsApp."""
    digitos = re.sub(r"\D", "", telefone or "")
    if digitos.startswith("55"):
        digitos = digitos[2:]
    return len(digitos) == 11 and digitos[2] == "9"
