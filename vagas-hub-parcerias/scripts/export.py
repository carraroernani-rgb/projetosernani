#!/usr/bin/env python3
"""
Exporta output/vagas_semana.json para CSV, formato pronto para
importar no hubdeparcerias.com.br.

Uso:
    python3 export.py
"""
import csv
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
SEMANA = OUTPUT_DIR / "vagas_semana.json"

COLUNAS = ["titulo", "empresa", "cidade", "modalidade", "descricao", "link", "data_coleta"]


def main():
    if not SEMANA.exists():
        print("Nada para exportar — rode dedupe_normalize.py primeiro.")
        return

    with open(SEMANA, "r", encoding="utf-8") as f:
        vagas = json.load(f)

    if not vagas:
        print("Nenhuma vaga nova nesta rodada.")
        return

    hoje = date.today().isoformat()
    csv_path = OUTPUT_DIR / f"vagas_{hoje}.csv"

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS)
        writer.writeheader()
        for vaga in vagas:
            writer.writerow({col: vaga.get(col, "") for col in COLUNAS})

    print(f"Exportado: {csv_path} ({len(vagas)} vaga(s))")


if __name__ == "__main__":
    main()
