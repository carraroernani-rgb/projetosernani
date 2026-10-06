"""
Portal web (FastAPI + Jinja2) para buscar, filtrar e visualizar os artigos
dos concorrentes, organizados por concorrente, com uma aba dedicada aos
checklists práticos.

Varreduras rodam em segundo plano (app/jobs.py): os botões do portal
respondem na hora. Um agendador interno (APScheduler) dispara a varredura
semanal aos sábados, e se o banco estiver vazio na inicialização (ex.: após
um deploy no Render free, cujo disco é efêmero) o histórico é recarregado
automaticamente, sem enviar e-mails.
"""
import logging
import math
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import defer
from sqlmodel import Session, select

from app import jobs
from app.config import COMPETITORS
from app.db import engine, init_db
from app.models import Article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGE_SIZE = 30

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["current_job"] = jobs.current_job
scheduler = BackgroundScheduler()

# Desative com ENABLE_INTERNAL_SCHEDULER=false quando a automação semanal já
# é feita por um cron externo (ex.: GitHub Actions), para não rodar em dobro.
ENABLE_INTERNAL_SCHEDULER = os.getenv("ENABLE_INTERNAL_SCHEDULER", "true").lower() == "true"
# Recarrega o histórico sozinho quando o banco está vazio na inicialização.
AUTO_SEED = os.getenv("AUTO_SEED", "true").lower() == "true"


def _count_articles() -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(Article)).one()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if AUTO_SEED and _count_articles() == 0:
        logger.info("Banco vazio — iniciando carga inicial do histórico em segundo plano.")
        jobs.start_job("seed")
    if ENABLE_INTERNAL_SCHEDULER:
        scheduler.add_job(
            jobs.run_job,
            CronTrigger(day_of_week="sat", hour=8, minute=0),
            args=["scan"],
            id="weekly_scan",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Agendador iniciado: varredura semanal aos sábados às 08:00.")
    yield
    if ENABLE_INTERNAL_SCHEDULER:
        scheduler.shutdown()


app = FastAPI(title="Radar de Conteúdo de Concorrentes", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
init_db()


@app.get("/healthz")
async def healthz():
    """Resposta mínima (sem banco) usada pelo keep-alive para evitar que o serviço durma."""
    return PlainTextResponse("ok")


@app.get("/")
async def home(request: Request, competitor: str = "todos", q: str = "", page: int = 1):
    # Não carrega o texto completo dos artigos na listagem — era o que deixava a página lenta.
    statement = select(Article).options(
        defer(Article.content_original), defer(Article.content_pt), defer(Article.checklist_md)
    )
    count_stmt = select(func.count()).select_from(Article)

    filters = []
    if competitor != "todos":
        filters.append(Article.competitor_slug == competitor)
    if q:
        like = f"%{q}%"
        filters.append(or_(Article.title_pt.ilike(like), Article.content_pt.ilike(like)))
    for f in filters:
        statement = statement.where(f)
        count_stmt = count_stmt.where(f)

    page = max(page, 1)
    with Session(engine) as session:
        total = session.exec(count_stmt).one()
        pages = max(math.ceil(total / PAGE_SIZE), 1)
        page = min(page, pages)
        articles = session.exec(
            statement.order_by(Article.processed_at.desc(), Article.id.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
        ).all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "competitors": COMPETITORS,
            "selected_competitor": competitor,
            "query": q,
            "page": page,
            "pages": pages,
            "total": total,
        },
    )


@app.get("/checklists")
async def checklists(request: Request, competitor: str = "todos"):
    statement = (
        select(Article)
        .options(defer(Article.content_original), defer(Article.content_pt))
        .where(Article.checklist_md != "")
    )
    if competitor != "todos":
        statement = statement.where(Article.competitor_slug == competitor)

    with Session(engine) as session:
        articles = session.exec(statement.order_by(Article.processed_at.desc())).all()

    return templates.TemplateResponse(
        "checklists.html",
        {
            "request": request,
            "articles": articles,
            "competitors": COMPETITORS,
            "selected_competitor": competitor,
        },
    )


@app.get("/artigo/{article_id}")
async def article_detail(request: Request, article_id: int):
    with Session(engine) as session:
        article = session.get(Article, article_id)
    return templates.TemplateResponse(
        "article.html", {"request": request, "article": article}
    )


@app.post("/rodar-varredura")
async def trigger_scan():
    """Dispara a varredura em segundo plano e volta para a página na hora."""
    jobs.start_job("scan")
    return RedirectResponse(url="/", status_code=303)


@app.post("/rodar-backfill")
async def trigger_backfill():
    """Dispara a busca de histórico em segundo plano e volta para a página na hora."""
    jobs.start_job("backfill")
    return RedirectResponse(url="/", status_code=303)
