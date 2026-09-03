#!/usr/bin/env python3
"""
Script de automação para rodar a varredura manualmente ou via cron/agendador
do sistema operacional (ex.: cron do macOS/Linux ou Task Scheduler do Windows).

Uso:
    python scripts/run_scan.py

Para rodar automaticamente todo sábado às 08h via cron (macOS/Linux):
    0 8 * * 6 cd /caminho/do/projeto && /caminho/do/venv/bin/python scripts/run_scan.py >> logs/scan.log 2>&1
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db
from app.pipeline import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    init_db()
    run_scan()
