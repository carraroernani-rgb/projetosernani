# Prospeccao B2B - Jardins Verticais

Aplicacao Streamlit para prospeccao comercial de paisagistas, arquitetos, designers de interiores
e jardineiros no Google Maps, com foco em identificar oportunidades para venda/parceria de jardins verticais.

## Estrutura

```
projetosernani/
├── streamlit_app.py       # Interface (Streamlit)
├── app/
│   ├── database.py        # Modelo Prospect + SQLite (dedup e upsert)
│   ├── scraper.py          # Busca e extracao de perfis no Google Maps (Playwright)
│   ├── enrichment.py       # Extracao de e-mail/instagram/whatsapp do site do perfil
│   ├── qualification.py    # Analise de palavras-chave e tag de qualificacao
│   └── exporter.py         # Exportacao CSV / Excel
├── data/
│   └── prospeccao_karyn.db # Banco SQLite local (gerado em runtime)
└── requirements.txt
```

## Como rodar

```bash
pip install -r requirements.txt
playwright install chromium
streamlit run streamlit_app.py
```

## Regras principais

- **Validacao minima**: um registro so e salvo se tiver Nome + (Telefone Principal ou WhatsApp) + Cidade.
- **Antiduplicacao**: chave unica por URL do perfil no Google Maps (ou Nome+Cidade+Telefone como fallback).
  Registros existentes sao atualizados somente quando ha dado novo (email, whatsapp, instagram etc.).
- **Qualificacao**: analise textual de descricao/avaliacoes/site em busca de palavras-chave
  ("jardim vertical", "parede verde", "paisagismo vertical", "preservado", "irrigacao") define a tag
  🟢 Ja trabalha com Jardim Vertical ou 🟡 Potencial Parceiro.
