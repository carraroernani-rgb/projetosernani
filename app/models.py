"""Modelos de dados (SQLModel) — um por artigo processado."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    competitor_slug: str = Field(index=True)
    competitor_name: str

    url: str = Field(index=True, unique=True)
    title_original: str
    title_pt: str

    content_original: str
    content_pt: str

    checklist_md: str = ""      # checklist/to-do extraído em Markdown
    tools_mentioned: str = ""   # lista de ferramentas citadas, separadas por vírgula
    summary_pt: str = ""        # resumo acionável curto

    published_at: Optional[datetime] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    email_sent: bool = False
