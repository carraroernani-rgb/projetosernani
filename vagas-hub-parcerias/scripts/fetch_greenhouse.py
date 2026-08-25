#!/usr/bin/env python3
"""
Busca vagas em boards públicos Greenhouse e Lever (sem autenticação).
Filtra por cargos-alvo definidos em config.json e por atuação no Brasil.

Uso:
    python3 fetch_greenhouse.py

Saída:
    output/raw_greenhouse.json  (lista de vagas brutas, já filtradas por cargo/BR)
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
OUTPUT_PATH = BASE_DIR / "output" / "raw_greenhouse.json"

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{token}?mode=json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HubDeParceriasBot/1.0)"}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def http_get_json(url, retries=2, timeout=15):
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError) as e:
            if attempt == retries:
                print(f"  [erro] {url} -> {e}", file=sys.stderr)
                return None
            time.sleep(1.5)
    return None


def matches_cargo(title, cargos_alvo):
    title_lower = title.lower()
    return any(cargo.lower() in title_lower for cargo in cargos_alvo)


def matches_brazil(location_text, cidades_foco):
    if not location_text:
        return False
    text = location_text.lower()
    brasil_hints = ["brazil", "brasil", "latam", "remote"] + [c.lower() for c in cidades_foco]
    return any(hint in text for hint in brasil_hints)


def is_excluded(title, termos_excluir):
    title_lower = title.lower()
    return any(termo.lower() in title_lower for termo in termos_excluir)


def fetch_greenhouse_jobs(token, cargos_alvo, cidades_foco, termos_excluir):
    url = GREENHOUSE_URL.format(token=token)
    data = http_get_json(url)
    if not data or "jobs" not in data:
        return []

    results = []
    for job in data["jobs"]:
        title = job.get("title", "")
        location = (job.get("location") or {}).get("name", "")

        if is_excluded(title, termos_excluir):
            continue
        if not matches_cargo(title, cargos_alvo):
            continue
        if not matches_brazil(location, cidades_foco):
            continue

        content = job.get("content", "")
        description = re.sub(r"<[^>]+>", " ", content)
        description = re.sub(r"\s+", " ", description).strip()[:400]

        results.append({
            "titulo": title,
            "empresa": token,
            "cidade": location or "não informado",
            "modalidade": "verificar" ,
            "descricao": description,
            "link": job.get("absolute_url", ""),
            "fonte": "greenhouse",
        })
    return results


def fetch_lever_jobs(token, cargos_alvo, cidades_foco, termos_excluir):
    url = LEVER_URL.format(token=token)
    data = http_get_json(url)
    if not data:
        return []

    results = []
    for job in data:
        title = job.get("text", "")
        categories = job.get("categories", {}) or {}
        location = categories.get("location", "")

        if is_excluded(title, termos_excluir):
            continue
        if not matches_cargo(title, cargos_alvo):
            continue
        if not matches_brazil(location, cidades_foco):
            continue

        description_html = job.get("descriptionPlain") or job.get("description", "")
        description = re.sub(r"\s+", " ", description_html).strip()[:400]

        results.append({
            "titulo": title,
            "empresa": token,
            "cidade": location or "não informado",
            "modalidade": categories.get("commitment", "verificar"),
            "descricao": description,
            "link": job.get("hostedUrl", ""),
            "fonte": "lever",
        })
    return results


def main():
    config = load_config()
    cargos_alvo = config["cargos_alvo"]
    cidades_foco = config["cidades_foco"]
    termos_excluir = config.get("termos_excluir", [])

    all_jobs = []

    print("Consultando boards Greenhouse...")
    for token in config.get("greenhouse_boards", []):
        jobs = fetch_greenhouse_jobs(token, cargos_alvo, cidades_foco, termos_excluir)
        print(f"  {token}: {len(jobs)} vaga(s) relevante(s)")
        all_jobs.extend(jobs)
        time.sleep(0.5)

    print("Consultando boards Lever...")
    for token in config.get("lever_boards", []):
        jobs = fetch_lever_jobs(token, cargos_alvo, cidades_foco, termos_excluir)
        print(f"  {token}: {len(jobs)} vaga(s) relevante(s)")
        all_jobs.extend(jobs)
        time.sleep(0.5)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_jobs)} vaga(s) salvas em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
