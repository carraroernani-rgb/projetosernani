"""Interface Streamlit: Prospeccao B2B - Jardins Verticais (Karyn Carraro)."""
from __future__ import annotations

import streamlit as st

from app.database import get_conn, upsert_prospect, fetch_filtered
from app.exporter import rows_to_dataframe, to_csv_bytes, to_xlsx_bytes
from app.scraper import buscar_perfis, montar_prospect

st.set_page_config(page_title="Prospeccao Jardins Verticais", page_icon="🌿", layout="wide")

CATEGORIAS = [
    "Paisagista",
    "Arquiteto / Escritorio de Arquitetura",
    "Designer de Interiores",
    "Jardineiro / Empresa de Jardinagem",
]

st.title("🌿 Prospeccao B2B - Jardins Verticais")
st.caption("Ferramenta de prospeccao para Karyn Carraro no Google Maps / Google Meu Negocio")

with st.sidebar:
    st.header("Parametros de Busca")
    categoria = st.selectbox("Categoria", CATEGORIAS)
    regiao = st.text_input("Regiao / Cidade", placeholder="Ex: Curitiba - PR")
    quantidade = st.selectbox("Quantidade por lote", [20, 50, 100], index=0)
    iniciar = st.button("🔎 Iniciar Extracao", type="primary", use_container_width=True)

if "resumo" not in st.session_state:
    st.session_state.resumo = None

if iniciar:
    if not regiao.strip():
        st.error("Informe a Regiao/Cidade antes de iniciar a extracao.")
    else:
        progresso = st.progress(0, text="Iniciando...")
        contadores = {"novos": 0, "atualizados": 0, "ignorados": 0, "jardim_vertical": 0, "invalidos": 0}

        def on_progress(atual: int, total: int, _link: str) -> None:
            progresso.progress(atual / max(total, 1), text=f"Analisando perfil {atual}/{total}")

        with get_conn() as conn:
            for listing in buscar_perfis(categoria, regiao, quantidade, on_progress=on_progress):
                prospect = montar_prospect(listing, categoria, regiao)

                if not prospect.is_valid():
                    contadores["invalidos"] += 1
                    continue

                status = upsert_prospect(conn, prospect)
                if status == "Novo Cadastro":
                    contadores["novos"] += 1
                elif status == "Atualizado":
                    contadores["atualizados"] += 1
                else:
                    contadores["ignorados"] += 1

                if prospect.tag_qualificacao.startswith("🟢"):
                    contadores["jardim_vertical"] += 1

        progresso.progress(1.0, text="Extracao concluida")
        st.session_state.resumo = contadores

if st.session_state.resumo:
    c = st.session_state.resumo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 Novos", c["novos"])
    col2.metric("🌿 Ja atuam c/ Jardim Vertical", c["jardim_vertical"])
    col3.metric("🟡 Atualizados", c["atualizados"])
    col4.metric("⚪ Ignorados", c["ignorados"])
    if c["invalidos"]:
        st.caption(f"{c['invalidos']} perfis descartados por falta de dados minimos (nome, telefone/whatsapp e cidade).")

st.divider()
st.subheader("Base de Prospeccao")

filtro = st.radio(
    "Filtro para visualizacao / exportacao",
    ["Base Completa", "Apenas Novos/Atualizados da ultima busca", "Apenas quem ja atua com Jardim Vertical"],
    horizontal=True,
)

with get_conn() as conn:
    rows = fetch_filtered(conn, filtro)

df = rows_to_dataframe(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        "⬇️ Exportar CSV",
        data=to_csv_bytes(df),
        file_name="prospeccao_karyn.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=df.empty,
    )
with col_b:
    st.download_button(
        "⬇️ Exportar Excel (.xlsx)",
        data=to_xlsx_bytes(df),
        file_name="prospeccao_karyn.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=df.empty,
    )
