"""Exportacao de resultados para CSV e Excel."""
from __future__ import annotations

import io
import sqlite3

import pandas as pd

COLUNAS_EXPORT = [
    "nome", "categoria", "telefone_principal", "whatsapp", "email", "instagram",
    "endereco", "cidade", "google_maps_url", "tag_qualificacao",
    "palavras_chave_encontradas", "status_ultima_busca",
    "data_primeira_extracao", "data_ultima_extracao",
]


def rows_to_dataframe(rows: list[sqlite3.Row]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLUNAS_EXPORT)
    df = pd.DataFrame([dict(r) for r in rows])
    return df[COLUNAS_EXPORT]


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Prospeccao")
    return buffer.getvalue()
