"""
Portal web (FastAPI + Jinja2 + Tailwind via CDN) para buscar, filtrar e
visualizar os artigos traduzidos, organizados por concorrente, com uma aba
dedicada aos checklists práticos.

Também registra um agendador interno (APScheduler) que roda a varredura
automaticamente todo sábado — como alternativa ao cron externo em
scripts/run_scan.py.
"""
import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.config import BACKFILL_DAYS, COMPETITORS
from app.db import engine, init_db
from app.models import Article
from app.pipeline import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# Caminhos absolutos (baseados na localização deste arquivo), não relativos
# ao diretório de trabalho do processo — em alguns hosts WSGI (ex.:
# PythonAnywhere), o cwd não é a raiz do projeto, e caminhos relativos como
# "app/static" quebram com RuntimeError: Directory does not exist.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
scheduler = BackgroundScheduler()

# Desative com ENABLE_INTERNAL_SCHEDULER=false quando a automação semanal já
# é feita por um cron/tarefa agendada externa (ex.: PythonAnywhere Scheduled
# Tasks, GitHub Actions), para não rodar a varredura duas vezes. No Railway,
# onde o processo web fica sempre ativo, deixe habilitado (padrão).
ENABLE_INTERNAL_SCHEDULER = os.getenv("ENABLE_INTERNAL_SCHEDULER", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if ENABLE_INTERNAL_SCHEDULER:
        # Todo sábado às 08:00 (horário do servidor).
        scheduler.add_job(
            run_scan,
            CronTrigger(day_of_week="sat", hour=8, minute=0),
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


@app.get("/")
def home(request: Request, competitor: str = "todos", q: str = ""):
    with Session(engine) as session:
        statement = select(Article).order_by(Article.processed_at.desc())
        articles = session.exec(statement).all()

    if competitor != "todos":
        articles = [a for a in articles if a.competitor_slug == competitor]
    if q:
        q_lower = q.lower()
        articles = [
            a for a in articles
            if q_lower in a.title_pt.lower() or q_lower in a.content_pt.lower()
        ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "competitors": COMPETITORS,
            "selected_competitor": competitor,
            "query": q,
        },
    )


@app.get("/checklists")
def checklists(request: Request, competitor: str = "todos"):
    with Session(engine) as session:
        statement = select(Article).order_by(Article.processed_at.desc())
        articles = session.exec(statement).all()

    if competitor != "todos":
        articles = [a for a in articles if a.competitor_slug == competitor]
    articles = [a for a in articles if a.checklist_md.strip()]

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
def article_detail(request: Request, article_id: int):
    with Session(engine) as session:
        article = session.get(Article, article_id)
    return templates.TemplateResponse(
        "article.html", {"request": request, "article": article}
    )


@app.post("/rodar-varredura")
def trigger_scan():
    """Dispara a varredura manualmente (só posts recentes) a partir do portal web."""
    run_scan()
    return RedirectResponse(url="/", status_code=303)


@app.post("/rodar-backfill")
def trigger_backfill():
    """
    Dispara o backfill histórico (últimos BACKFILL_DAYS dias, com paginação
    da listagem HTML) a partir do portal web. Pode demorar mais que a
    varredura normal, pois percorre várias páginas por concorrente.
    """
    run_scan(max_new_posts_per_competitor=100, since_days=BACKFILL_DAYS, listing_pages=25)
    return RedirectResponse(url="/", status_code=303)
