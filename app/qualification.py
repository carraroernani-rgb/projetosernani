"""Analise textual simples para qualificar afinidade com Jardim Vertical."""
from __future__ import annotations

import re

KEYWORDS = [
    "jardim vertical",
    "jardins verticais",
    "parede verde",
    "paredes verdes",
    "paisagismo vertical",
    "muro verde",
    "preservado",
    "jardim preservado",
    "irrigacao",
    "irrigação",
    "green wall",
    "vertical garden",
]

TAG_JA_TRABALHA = "🟢 Ja trabalha com Jardim Vertical"
TAG_POTENCIAL = "🟡 Potencial Parceiro"


def _normalize(text: str) -> str:
    text = text.lower()
    return re.sub(r"[áàâã]", "a", re.sub(r"[éê]", "e", re.sub(r"[íî]", "i",
        re.sub(r"[óôõ]", "o", re.sub(r"[úû]", "u", re.sub(r"[ç]", "c", text))))))


def analisar_texto(*textos: str) -> tuple[str, list[str]]:
    """Recebe descricao/avaliacoes/site/instagram e retorna (tag, palavras encontradas)."""
    conteudo = _normalize(" \n ".join(t for t in textos if t))
    encontradas = []
    for kw in KEYWORDS:
        if _normalize(kw) in conteudo:
            encontradas.append(kw)

    tag = TAG_JA_TRABALHA if encontradas else TAG_POTENCIAL
    return tag, sorted(set(encontradas))
