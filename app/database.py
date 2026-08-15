"""Camada de persistencia SQLite para a prospeccao de jardins verticais."""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prospeccao_karyn.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT,
    telefone_principal TEXT,
    whatsapp TEXT,
    email TEXT,
    instagram TEXT,
    endereco TEXT,
    cidade TEXT,
    google_maps_url TEXT,
    tag_qualificacao TEXT,
    palavras_chave_encontradas TEXT,
    status_ultima_busca TEXT,
    data_primeira_extracao TEXT,
    data_ultima_extracao TEXT
);
"""


@dataclass
class Prospect:
    nome: str
    categoria: str = ""
    telefone_principal: str = ""
    whatsapp: str = ""
    email: str = ""
    instagram: str = ""
    endereco: str = ""
    cidade: str = ""
    google_maps_url: str = ""
    tag_qualificacao: str = "🟡 Potencial Parceiro"
    palavras_chave_encontradas: str = ""
    status_ultima_busca: str = field(default="", compare=False)

    def is_valid(self) -> bool:
        """Regra minima: nome + (telefone principal OU whatsapp) + cidade."""
        tem_telefone = bool(self.telefone_principal or self.whatsapp)
        return bool(self.nome) and bool(self.cidade) and tem_telefone

    def dedupe_key(self) -> str:
        if self.google_maps_url:
            base = self.google_maps_url.strip().lower()
        else:
            base = f"{self.nome.strip().lower()}|{self.cidade.strip().lower()}|{self.telefone_principal.strip()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()


@contextmanager
def get_conn(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


UPDATABLE_FIELDS = [
    "telefone_principal",
    "whatsapp",
    "email",
    "instagram",
    "endereco",
    "tag_qualificacao",
    "palavras_chave_encontradas",
]


def upsert_prospect(conn: sqlite3.Connection, prospect: Prospect) -> str:
    """Insere ou atualiza um prospect. Retorna status: 'Novo Cadastro', 'Atualizado' ou 'Sem Alteracao'."""
    key = prospect.dedupe_key()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute("SELECT * FROM prospects WHERE dedupe_key = ?", (key,)).fetchone()

    if row is None:
        conn.execute(
            """INSERT INTO prospects (
                dedupe_key, nome, categoria, telefone_principal, whatsapp, email,
                instagram, endereco, cidade, google_maps_url, tag_qualificacao,
                palavras_chave_encontradas, status_ultima_busca,
                data_primeira_extracao, data_ultima_extracao
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                key, prospect.nome, prospect.categoria, prospect.telefone_principal,
                prospect.whatsapp, prospect.email, prospect.instagram, prospect.endereco,
                prospect.cidade, prospect.google_maps_url, prospect.tag_qualificacao,
                prospect.palavras_chave_encontradas, "Novo Cadastro", now, now,
            ),
        )
        return "Novo Cadastro"

    changed = False
    updates = {}
    for f in UPDATABLE_FIELDS:
        new_val = getattr(prospect, f)
        old_val = row[f] or ""
        if new_val and new_val != old_val:
            updates[f] = new_val
            changed = True

    if not changed:
        conn.execute(
            "UPDATE prospects SET status_ultima_busca = ? WHERE dedupe_key = ?",
            ("Sem Alteracao", key),
        )
        return "Sem Alteracao"

    updates["status_ultima_busca"] = "Atualizado"
    updates["data_ultima_extracao"] = now
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE prospects SET {set_clause} WHERE dedupe_key = ?",
        (*updates.values(), key),
    )
    return "Atualizado"


def fetch_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM prospects ORDER BY data_ultima_extracao DESC").fetchall()


def fetch_filtered(conn: sqlite3.Connection, filtro: str) -> list[sqlite3.Row]:
    if filtro == "Apenas Novos/Atualizados da ultima busca":
        return conn.execute(
            "SELECT * FROM prospects WHERE status_ultima_busca IN ('Novo Cadastro','Atualizado') "
            "ORDER BY data_ultima_extracao DESC"
        ).fetchall()
    if filtro == "Apenas quem ja atua com Jardim Vertical":
        return conn.execute(
            "SELECT * FROM prospects WHERE tag_qualificacao LIKE '🟢%' ORDER BY data_ultima_extracao DESC"
        ).fetchall()
    return fetch_all(conn)
