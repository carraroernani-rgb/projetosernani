"""
Tradução na íntegra + extração de entregáveis (checklist/to-do/ferramentas)
usando a API da Anthropic (Claude).

Uma única chamada retorna um JSON estruturado para evitar duas idas à API
e manter tradução e extração consistentes entre si.
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, PARTNERSHIP_GLOSSARY

logger = logging.getLogger("translator")

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada. Defina no arquivo .env."
            )
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """Você é um tradutor e editor sênior especializado em Channel \
Partnerships / Partner Marketing, trabalhando para um criador de infoprodutos \
brasileiro que reaproveita conteúdo de blogs concorrentes (PartnerStack, \
Impartner, Allbound, ZINFI, Kiflo) em cursos e artigos no Brasil.

Sua tarefa tem duas partes e deve retornar SOMENTE um JSON válido, sem texto \
fora do JSON, no formato:

{
  "titulo_pt": "...",
  "conteudo_pt": "...",
  "resumo_acionavel": "...",
  "checklist_md": "...",
  "ferramentas_citadas": ["...", "..."]
}

Regras:
1. "titulo_pt": tradução do título, natural e atrativo em português do Brasil.
2. "conteudo_pt": TRADUÇÃO NA ÍNTEGRA do artigo (não resuma, não corte \
parágrafos), em português do Brasil, com parágrafos preservados (use \\n\\n \
entre parágrafos). Adapte termos técnicos de parcerias ao vocabulário usado \
no mercado brasileiro, mantendo o termo em inglês entre parênteses na \
primeira ocorrência quando for um termo consagrado (ex.: "Motion Nearbound \
(Nearbound)"). Use como referência este glossário: """ + json.dumps(
    PARTNERSHIP_GLOSSARY, ensure_ascii=False
) + """
3. "resumo_acionavel": 3 a 6 frases resumindo o que há de mais aplicável no \
artigo para quem produz cursos e conteúdo sobre parcerias no Brasil.
4. "checklist_md": um checklist/to-do em Markdown (usando "- [ ] item"), \
extraído do artigo, com os passos práticos, frameworks ou etapas descritas, \
prontos para serem usados como material de curso. Se o artigo não tiver \
passo a passo explícito, gere um checklist inferido a partir dos conceitos \
apresentados.
5. "ferramentas_citadas": lista de ferramentas, plataformas ou produtos \
mencionados no texto (nomes próprios). Lista vazia se nenhuma for citada.

Nunca invente fatos que não estejam no texto original. Não adicione \
comentários, apenas o JSON.
"""


def translate_and_extract(title: str, content: str, source_url: str) -> dict:
    """Chama o Claude para traduzir na íntegra e extrair os entregáveis."""
    client = _get_client()

    user_prompt = f"""URL de origem: {source_url}

TÍTULO ORIGINAL:
{title}

CONTEÚDO ORIGINAL (em inglês):
{content}
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    # Alguns modelos podem envolver o JSON em ```json ... ``` — removemos se ocorrer.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Resposta da IA não é um JSON válido: %s", raw_text[:500])
        raise

    return {
        "title_pt": data.get("titulo_pt", title),
        "content_pt": data.get("conteudo_pt", ""),
        "summary_pt": data.get("resumo_acionavel", ""),
        "checklist_md": data.get("checklist_md", ""),
        "tools_mentioned": ", ".join(data.get("ferramentas_citadas", [])),
    }
