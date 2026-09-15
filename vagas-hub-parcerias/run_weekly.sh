#!/usr/bin/env bash
# Pipeline semanal de vagas — Hub de Parcerias
# Uso: ./run_weekly.sh
#
# Passo 1 (automático): Greenhouse/Lever via Python — sem custo de IA.
# Passo 2 (manual/Claude Code): busca em boards BR via WebSearch — precisa
#   rodar o prompt em scripts/fetch_br_boards.md dentro do Claude Code
#   ANTES deste script chegar no passo 3, ou integrado via `claude -p`.
# Passo 3-4 (automático): dedupe + export.

set -e
cd "$(dirname "$0")"

echo "== [1/4] Buscando vagas Greenhouse/Lever =="
python3 scripts/fetch_greenhouse.py

echo ""
echo "== [2/4] Buscando vagas em boards BR (via Claude Code) =="
if command -v claude &> /dev/null; then
    claude -p "$(cat scripts/fetch_br_boards.md)" --dangerously-skip-permissions
else
    echo "AVISO: CLI 'claude' não encontrada no PATH."
    echo "Rode manualmente o prompt em scripts/fetch_br_boards.md no Claude Code"
    echo "e salve o resultado em output/raw_br_boards.json antes de continuar."
    read -p "Pressione ENTER quando output/raw_br_boards.json estiver pronto..."
fi

echo ""
echo "== [3/4] Deduplicando e comparando com histórico =="
python3 scripts/dedupe_normalize.py

echo ""
echo "== [4/4] Exportando CSV final =="
python3 scripts/export.py

echo ""
echo "Pipeline concluída. Confira output/ para o CSV desta semana."
