# Radar de Conteúdo de Concorrentes

Aplicação para monitorar semanalmente os blogs dos principais concorrentes do
PartnerStack, traduzir os posts na íntegra para português do Brasil (com
adaptação de termos de Channel Partnerships), extrair checklists/to-do
acionáveis, enviar notificação por e-mail e disponibilizar tudo em um portal
web local.

## Concorrentes monitorados
- PartnerStack
- Impartner
- Channelscaler / Allbound
- ZINFI
- Kiflo

(Fontes RSS/URLs em [app/config.py](app/config.py) — ajuste ali se algum
concorrente mudar de layout ou feed.)

## Estrutura do projeto
```
partner-content-radar/
├── app/
│   ├── main.py            # Portal web (FastAPI) + agendador interno (sábados)
│   ├── scraper.py          # Varredura RSS/HTML dos blogs concorrentes
│   ├── translator.py       # Tradução na íntegra + extração de checklist via Claude
│   ├── email_notifier.py   # Envio do e-mail HTML de notificação
│   ├── pipeline.py         # Orquestra scraper -> translator -> banco -> e-mail
│   ├── models.py           # Modelo Article (SQLModel)
│   ├── db.py                # Engine/sessão do banco (SQLite)
│   ├── config.py            # Concorrentes, glossário de termos, variáveis de ambiente
│   ├── templates/           # Portal web (Jinja2 + Tailwind via CDN)
│   └── static/
├── scripts/
│   └── run_scan.py          # Script de automação (uso via cron externo)
├── .github/workflows/
│   └── weekly-scan.yml      # Alternativa: rodar a varredura via GitHub Actions
├── requirements.txt
├── .env.example
└── data/
    └── radar.db              # Banco SQLite (criado automaticamente)
```

## Como funciona
1. **Varredura**: `scraper.py` tenta primeiro o feed RSS de cada concorrente;
   se não existir/estiver vazio, faz fallback para scraping HTML da página de
   listagem (`app/config.py` define os seletores).
2. **Extração de conteúdo completo**: cada post novo é baixado e limpo com
   `readability-lxml` (remove menu, rodapé, etc.).
3. **Tradução + checklist**: `translator.py` envia o conteúdo para a API da
   Anthropic (Claude) em uma única chamada, retornando JSON com título,
   conteúdo traduzido na íntegra, resumo acionável, checklist em Markdown e
   ferramentas citadas.
4. **Persistência**: tudo é salvo em SQLite (`data/radar.db`) via SQLModel,
   com deduplicação por URL.
5. **E-mail**: `email_notifier.py` envia um e-mail HTML formatado para
   `carraro.ernani@gmail.com` a cada artigo novo processado.
6. **Portal web**: `main.py` expõe páginas para buscar/filtrar artigos por
   concorrente, ver o artigo completo e uma aba dedicada aos "Checklists
   Práticos".

## Pré-requisitos
- Python 3.11+
- Uma chave de API da Anthropic (https://console.anthropic.com)
- Uma conta de e-mail com SMTP habilitado (ex.: Gmail com "senha de app")

## Instalação
```bash
cd partner-content-radar
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` com:
- `ANTHROPIC_API_KEY`
- `SMTP_USER` / `SMTP_PASSWORD` (para Gmail, gere uma "senha de app" em
  https://myaccount.google.com/apppasswords)
- `EMAIL_TO` já vem configurado como `carraro.ernani@gmail.com`

## Rodando o portal web
```bash
uvicorn app.main:app --reload
```
Acesse http://localhost:8000

O portal já inicia com um agendador interno (APScheduler) que roda a
varredura automaticamente **todo sábado às 08:00** enquanto o servidor
estiver de pé. Também há um botão **"Rodar varredura agora"** no topo da
página para disparar manualmente a qualquer momento.

## Rodando a varredura manualmente (sem o portal)
```bash
python scripts/run_scan.py
```

## Backfill histórico (últimos 300 dias)
Para popular o portal com conteúdo já existente na primeira configuração
(em vez de só posts novos daqui pra frente), rode o backfill — ele percorre
várias páginas de listagem de cada concorrente (quando não há RSS) e ignora
posts mais antigos que a janela definida:
```bash
python scripts/backfill.py
# ou com parâmetros customizados:
python scripts/backfill.py --days 300 --pages 25 --max-per-competitor 100
```
Também dá para disparar pelo botão **"Buscar histórico (300 dias)"** no
topo do portal web (pode demorar alguns minutos, pois percorre várias
páginas por concorrente). O período padrão é 300 dias, configurável via
`BACKFILL_DAYS` no `.env`.

> Observação: o filtro por data só é aplicado quando a data de publicação é
> conhecida (normalmente via RSS). Quando o concorrente não tem RSS e o
> sistema cai no fallback de scraping HTML, a data de cada post não é
> conhecida antecipadamente — nesse caso todos os posts encontrados nas
> páginas percorridas são processados, independente da idade.

## Automação sem manter o servidor ligado (recomendado para produção)
Como o agendador interno só funciona com o `uvicorn` rodando continuamente,
para automação real escolha uma das opções:

### Opção A — cron local (macOS/Linux)
```bash
crontab -e
```
Adicione (ajuste os caminhos):
```
0 8 * * 6 cd /caminho/para/partner-content-radar && .venv/bin/python scripts/run_scan.py >> logs/scan.log 2>&1
```

### Opção B — GitHub Actions (já incluído em `.github/workflows/weekly-scan.yml`)
Roda todo sábado (11:00 UTC = 08:00 em Brasília) direto no GitHub, sem
depender do seu computador ligado. Configure em
**Settings → Secrets and variables → Actions** do repositório:
- Secrets: `ANTHROPIC_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD`
- Variables: `CLAUDE_MODEL`, `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, `EMAIL_TO`

> Observação: `data/radar.db` está no `.gitignore` por padrão (evita
> versionar dados locais). Se for usar a Opção B para persistir o histórico
> de artigos entre execuções do Actions, remova `data/radar.db` do
> `.gitignore` e faça um commit inicial do banco (mesmo vazio) — o workflow
> já commita o banco atualizado automaticamente após cada varredura.

## Ajustando o glossário de tradução
Termos como *Channel Partners*, *Nearbound*, *Co-selling* e *MDF* têm suas
adaptações sugeridas em `PARTNERSHIP_GLOSSARY` (`app/config.py`). O modelo
usa isso como referência, não como substituição mecânica — ele adapta a
frase para soar natural em português mantendo o termo técnico quando
relevante.

## Limitações conhecidas
- Sites que bloqueiam scraping automatizado (proteção anti-bot, JS pesado)
  podem exigir ajustes nos seletores de `app/config.py` ou uso de uma
  ferramenta de scraping com renderização JS (fora do escopo inicial).
- O script assume que os feeds RSS/URLs configurados continuam válidos —
  revise periodicamente se algum concorrente mudar o layout do blog.
