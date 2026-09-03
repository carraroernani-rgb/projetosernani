#!/usr/bin/env python3
"""
Backfill histórico: busca posts publicados nos últimos BACKFILL_DAYS dias
(300 por padrão, ajustável em .env) para popular o portal com conteúdo
existente na primeira configuração do projeto.

Uso:
    python scripts/backfill.py
    python scripts/backfill.py --days 180 --pages 15

Diferente da varredura semanal (scripts/run_scan.py), aqui o limite de posts
processados por concorrente é bem maior e a listagem HTML (fallback) é
paginada para alcançar posts mais antigos.
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BACKFILL_DAYS
from app.db import init_db
from app.pipeline import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill histórico de posts dos concorrentes.")
    parser.add_argument("--days", type=int, default=BACKFILL_DAYS, help="Janela de dias para trás.")
    parser.add_argument(
        "--max-per-competitor",
        type=int,
        default=100,
        help="Máximo de posts novos processados por concorrente.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=25,
        help="Páginas de listagem HTML a percorrer por concorrente (fallback sem RSS).",
    )
    args = parser.parse_args()

    init_db()
    run_scan(
        max_new_posts_per_competitor=args.max_per_competitor,
        since_days=args.days,
        listing_pages=args.pages,
    )
