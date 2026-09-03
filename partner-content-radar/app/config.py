"""Configuração central da aplicação, carregada a partir do .env."""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "carraro.ernani@gmail.com")
EMAIL_TO = os.getenv("EMAIL_TO", "carraro.ernani@gmail.com")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/radar.db")

# Quantos dias para trás considerar na varredura de backfill inicial
# (scripts/backfill.py), para popular o portal com histórico ao configurar
# o projeto pela primeira vez.
BACKFILL_DAYS = int(os.getenv("BACKFILL_DAYS", "300"))

# Concorrentes monitorados: nome de exibição, fonte RSS (quando existir) e URL de fallback
# para scraping de HTML. Ajuste os seletores em scraper.py se o layout do site mudar.
COMPETITORS = [
    {
        "slug": "partnerstack",
        "name": "PartnerStack",
        # Site em Webflow com listagem renderizada via JS — RSS não existe e
        # o HTML estático da listagem não traz os links dos posts. O
        # sitemap.xml lista as URLs reais dos conteúdos de "guides"
        # (equivalente aos artigos do blog).
        "rss": None,
        "sitemap_url": "https://partnerstack.com/sitemap.xml",
        "url_pattern": "/resources/guides/",
        "listing_url": "https://partnerstack.com/resources/articles",
        "link_selector": "a[href*='/resources/guides/']",
    },
    {
        "slug": "impartner",
        "name": "Impartner",
        "rss": "https://impartner.com/feed/",
        "listing_url": "https://impartner.com/blog/",
        "link_selector": "a[href*='/blog/']",
    },
    {
        "slug": "allbound",
        "name": "Channelscaler / Allbound",
        "rss": "https://www.allbound.com/blog/rss.xml",
        "listing_url": "https://www.allbound.com/blog/",
        "link_selector": "a[href*='/blog/']",
    },
    {
        "slug": "zinfi",
        "name": "ZINFI",
        "rss": "https://www.zinfi.com/blog/feed/",
        "listing_url": "https://www.zinfi.com/blog/",
        "link_selector": "a[href*='/blog/']",
    },
    {
        "slug": "kiflo",
        "name": "Kiflo",
        "rss": "https://www.kiflo.com/blog/rss.xml",
        "listing_url": "https://www.kiflo.com/blog",
        "link_selector": "a[href*='/blog/']",
    },
]

# Glossário de termos de parcerias para orientar a tradução (contexto para a IA,
# não é uma substituição mecânica — a IA deve adaptar conforme o sentido da frase).
PARTNERSHIP_GLOSSARY = {
    "Channel Partners": "Parceiros de Canal",
    "Nearbound": "Nearbound (motion baseada em rede de parceiros e confiança)",
    "Co-selling": "Venda conjunta (Co-selling)",
    "MDF": "Fundo de Desenvolvimento de Mercado (MDF)",
    "Partner Enablement": "Capacitação de Parceiros",
    "Partner Onboarding": "Onboarding de Parceiros",
    "Deal Registration": "Registro de Oportunidade (Deal Registration)",
    "Referral Partner": "Parceiro Indicador",
    "Reseller": "Revendedor",
    "PRM": "PRM (Plataforma de Gestão de Relacionamento com Parceiros)",
}
