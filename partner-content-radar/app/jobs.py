"""
Execução das varreduras em segundo plano.

Os botões do portal só disparam o job e voltam imediatamente (antes a página
ficava travada por minutos esperando a varredura terminar). O estado atual
fica em `state` e é exibido como um aviso no topo do portal.
"""
import logging
import threading
from datetime import datetime
from typing import Optional

from app.config import BACKFILL_DAYS
from app.pipeline import run_scan

logger = logging.getLogger("jobs")

LABELS = {
    "scan": "Varredura semanal",
    "backfill": f"Busca de histórico ({BACKFILL_DAYS} dias)",
    "seed": f"Carga inicial do histórico ({BACKFILL_DAYS} dias)",
}

state: dict = {
    "running": False,
    "kind": "",
    "label": "",
    "started_at": None,
    "finished_at": None,
    "count": None,
    "error": None,
}
_lock = threading.Lock()


def run_job(kind: str) -> bool:
    """Roda o job de forma síncrona. Retorna False se já houver um em andamento."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        state.update(
            running=True, kind=kind, label=LABELS[kind],
            started_at=datetime.utcnow(), finished_at=None, count=None, error=None,
        )
        if kind == "scan":
            articles = run_scan(notify="individual")
        elif kind == "backfill":
            articles = run_scan(
                max_new_posts_per_competitor=100,
                since_days=BACKFILL_DAYS,
                listing_pages=25,
                notify="summary",
            )
        else:  # seed: popula o banco vazio sem disparar e-mails
            articles = run_scan(
                max_new_posts_per_competitor=100,
                since_days=BACKFILL_DAYS,
                listing_pages=25,
                notify="none",
            )
        state["count"] = len(articles)
    except Exception as exc:
        logger.exception("Job %s falhou", kind)
        state["error"] = str(exc)
    finally:
        state.update(running=False, finished_at=datetime.utcnow())
        _lock.release()
    return True


def start_job(kind: str) -> bool:
    """Dispara o job em uma thread e retorna na hora."""
    if state["running"]:
        return False
    threading.Thread(target=run_job, args=(kind,), daemon=True).start()
    return True


def current_job() -> Optional[dict]:
    return state if state["running"] else None
