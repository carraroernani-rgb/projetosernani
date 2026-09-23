# Vagas Hub de Parcerias

Robô semanal que busca vagas de emprego no Brasil para: gerente de
parcerias, analista de canais, analista de parcerias, coordenador de
parcerias, diretor de parcerias — e formatos equivalentes em inglês.

## Como funciona

1. **`scripts/fetch_greenhouse.py`** — consulta APIs públicas do
   Greenhouse e Lever (sem chave, sem login) para as empresas listadas
   em `config.json`. Rápido e determinístico.
2. **`scripts/fetch_br_boards.md`** — não é Python. É um prompt para o
   Claude Code rodar WebSearch nos boards brasileiros (Vagas.com,
   Indeed BR, Catho, JobLeads, Idealist), já que esses sites não têm
   API pública estável.
3. **`scripts/dedupe_normalize.py`** — junta as duas fontes, remove
   duplicatas por link, e separa "vagas novas desta semana" de
   "histórico acumulado" (pra não repetir vaga já vista).
4. **`scripts/export.py`** — gera o CSV final (`output/vagas_AAAA-MM-DD.csv`)
   pronto para importar no site.

Tudo orquestrado por **`run_weekly.sh`**.

## Setup

```bash
cd vagas-hub-parcerias
chmod +x run_weekly.sh
```

Só precisa de Python 3 (sem dependências externas — usa só stdlib).
Se quiser rodar o passo 2 automaticamente, precisa da CLI `claude`
instalada e autenticada (`npm install -g @anthropic-ai/claude-code`).

## Rodando manualmente

```bash
./run_weekly.sh
```

Se a CLI `claude` não estiver disponível, o script pausa e pede pra
você rodar o prompt de `scripts/fetch_br_boards.md` manualmente dentro
do Claude Code, salvando o resultado em `output/raw_br_boards.json`.

## Agendando (semanal)

Este projeto **não tem** agendador embutido. Escolha uma opção:

### Opção A — cron local (Mac/Linux)
```bash
crontab -e
# roda toda segunda 8h
0 8 * * 1 cd /caminho/para/vagas-hub-parcerias && ./run_weekly.sh >> log.txt 2>&1
```

### Opção B — GitHub Actions (recomendado, não depende do seu computador ligado)
Veja `.github/workflows/vagas-semanais.yml` neste repositório.
Precisa cadastrar `ANTHROPIC_API_KEY` nos Secrets do repositório.

## Notas e limitações

- **Greenhouse/Lever**: cobre bem empresas SaaS internacionais
  (a lista em `config.json` é um ponto de partida — adicione outras
  conforme achar boards relevantes; para descobrir o "token" de uma
  empresa, olhe a URL `boards.greenhouse.io/<token>` ou
  `jobs.lever.co/<token>`).
- **LinkedIn e Glassdoor foram propositalmente excluídos** — bloqueiam
  scraping e só retornam páginas de listagem agregada, sem link de
  vaga individual confiável.
- Ambientes com allowlist de rede restrita (como o sandbox usado para
  criar este projeto) podem retornar 403 nas APIs públicas do
  Greenhouse/Lever — isso é bloqueio de rede local, não das APIs.
  Funciona normalmente em máquina própria ou GitHub Actions.
- Ajuste `config.json` (`cargos_alvo`, `greenhouse_boards`,
  `lever_boards`, `cidades_foco`) livremente — não precisa mexer nos
  scripts.
