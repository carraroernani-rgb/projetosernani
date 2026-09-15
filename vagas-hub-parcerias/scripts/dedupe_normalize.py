#!/usr/bin/env python3
"""
Junta output/raw_greenhouse.json e output/raw_br_boards.json, remove
duplicatas por link e compara com output/vagas_historico.json para
separar vagas novas desta semana das já vistas antes.

Uso:
    python3 dedupe_normalize.py

Saída:
    output/vagas_semana.json      (só vagas novas desta rodada)
    output/vagas_historico.json   (acumulado, atualizado)
"""
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

RAW_GREENHOUSE = OUTPUT_DIR / "raw_greenhouse.json"
RAW_BR_BOARDS = OUTPUT_DIR / "raw_br_boards.json"
HISTORICO = OUTPUT_DIR / "vagas_historico.json"
SEMANA = OUTPUT_DIR / "vagas_semana.json"

CAMPOS = ["titulo", "empresa", "cidade", "modalidade", "descricao", "link", "fonte", "data_coleta"]


def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(vaga, hoje):
    return {
        "titulo": (vaga.get("titulo") or "").strip(),
        "empresa": (vaga.get("empresa") or "").strip(),
        "cidade": (vaga.get("cidade") or "não informado").strip(),
        "modalidade": (vaga.get("modalidade") or "verificar").strip(),
        "descricao": (vaga.get("descricao") or "").strip(),
        "link": (vaga.get("link") or "").strip(),
        "fonte": vaga.get("fonte", "desconhecida"),
        "data_coleta": vaga.get("data_coleta", hoje),
    }


def main():
    hoje = date.today().isoformat()

    greenhouse = load_json(RAW_GREENHOUSE, [])
    br_boards = load_json(RAW_BR_BOARDS, [])
    historico = load_json(HISTORICO, [])

    historico_links = {v["link"] for v in historico if v.get("link")}

    coletadas = [normalize(v, hoje) for v in greenhouse + br_boards]

    vistas = set()
    unicas = []
    for vaga in coletadas:
        if not vaga["link"] or vaga["link"] in vistas:
            continue
        vistas.add(vaga["link"])
        unicas.append(vaga)

    novas = [v for v in unicas if v["link"] not in historico_links]

    SEMANA.parent.mkdir(parents=True, exist_ok=True)
    with open(SEMANA, "w", encoding="utf-8") as f:
        json.dump(novas, f, ensure_ascii=False, indent=2)

    historico_atualizado = historico + novas
    with open(HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico_atualizado, f, ensure_ascii=False, indent=2)

    print(f"Coletadas: {len(coletadas)} | Únicas (por link): {len(unicas)}")
    print(f"Novas desta semana: {len(novas)} -> {SEMANA}")
    print(f"Histórico atualizado: {len(historico_atualizado)} vaga(s) -> {HISTORICO}")


if __name__ == "__main__":
    main()
