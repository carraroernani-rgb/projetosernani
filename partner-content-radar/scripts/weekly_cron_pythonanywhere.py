#!/usr/bin/env python3
"""
Wrapper para o "Scheduled Task" gratuito do PythonAnywhere, que só permite
agendar execuções DIÁRIAS (não semanais) no plano free.

Este script roda todo dia (configurado no painel do PythonAnywhere), mas só
executa a varredura de verdade quando o dia da semana é sábado — replicando
o comportamento de "toda semana, aos sábados" do agendador interno.

Uso no painel do PythonAnywhere (aba Tasks):
    python3.11 /home/SEU_USUARIO/projetosernani/partner-content-radar/scripts/weekly_cron_pythonanywhere.py
Agendado para rodar 1x por dia, em qualquer horário (ex.: 08:00 UTC).
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db
from app.pipeline import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("weekly_cron")

SATURDAY = 5  # datetime.weekday(): segunda=0 ... sábado=5, domingo=6

if __name__ == "__main__":
    if datetime.utcnow().weekday() != SATURDAY:
        logger.info("Hoje não é sábado — pulando execução (rodando só para checar o dia).")
        sys.exit(0)

    init_db()
    run_scan()
