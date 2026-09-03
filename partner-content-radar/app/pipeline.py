"""
Pipeline de varredura: para cada concorrente, descobre posts novos,
extrai o conteúdo completo e, se houver ANTHROPIC_API_KEY configurada,
traduz + extrai checklist via IA. Sem a chave configurada, o artigo é salvo
e enviado por e-mail no idioma original (sem tradução/checklist). Em ambos
os casos, salva no banco e dispara o e-mail de notificação.

Usado tanto pelo agendador semanal (scripts/run_scan.py) quanto pelo botão
"Rodar varredura agora" do portal web.
"""
import logging

from sqlmodel import Session, select

from app.config import ANTHROPIC_API_KEY, COMPETITORS
from app.db import engine
from app.email_notifier import send_article_email
from app.models import Article
from app.scraper import discover_posts, fetch_full_article
from app.translator import translate_and_extract

logger = logging.getLogger("pipeline")

# Limite de posts novos processados por concorrente a cada rodada, para não
# estourar custo/tempo de API caso um feed retorne muitos itens de uma vez.
MAX_NEW_POSTS_PER_COMPETITOR = 5


def run_scan() -> list[Article]:
    """Executa uma varredura completa em todos os concorrentes configurados."""
    processed: list[Article] = []

    with Session(engine) as session:
        for competitor in COMPETITORS:
            try:
                processed.extend(_scan_competitor(session, competitor))
            except Exception:
                logger.exception("Falha ao varrer %s", competitor["name"])

    logger.info("Varredura concluída. %d artigo(s) novo(s) processado(s).", len(processed))
    return processed


def _scan_competitor(session: Session, competitor: dict) -> list[Article]:
    logger.info("Varrendo %s...", competitor["name"])
    discovered = discover_posts(competitor)
    new_articles: list[Article] = []

    count = 0
    for post in discovered:
        if count >= MAX_NEW_POSTS_PER_COMPETITOR:
            break

        existing = session.exec(select(Article).where(Article.url == post.url)).first()
        if existing:
            continue

        try:
            article = _process_post(competitor, post.url, post.title)
        except Exception:
            logger.exception("Falha ao processar post %s", post.url)
            continue

        session.add(article)
        session.commit()
        session.refresh(article)

        try:
            send_article_email(article)
            article.email_sent = True
            session.add(article)
            session.commit()
        except Exception:
            logger.exception("Falha ao enviar e-mail para %s", article.url)

        new_articles.append(article)
        count += 1

    return new_articles


def _process_post(competitor: dict, url: str, fallback_title: str) -> Article:
    title_original, content_original = fetch_full_article(url)
    title_original = title_original or fallback_title

    if ANTHROPIC_API_KEY:
        ai_result = translate_and_extract(title_original, content_original, url)
    else:
        logger.info(
            "ANTHROPIC_API_KEY não configurada — salvando '%s' sem tradução/checklist.",
            title_original,
        )
        ai_result = {
            "title_pt": title_original,
            "content_pt": content_original,
            "summary_pt": "",
            "checklist_md": "",
            "tools_mentioned": "",
        }

    return Article(
        competitor_slug=competitor["slug"],
        competitor_name=competitor["name"],
        url=url,
        title_original=title_original,
        title_pt=ai_result["title_pt"],
        content_original=content_original,
        content_pt=ai_result["content_pt"],
        checklist_md=ai_result["checklist_md"],
        tools_mentioned=ai_result["tools_mentioned"],
        summary_pt=ai_result["summary_pt"],
    )
