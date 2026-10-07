# fetch_br_boards — instruções para o Claude Code

Vagas.com, Indeed BR, Catho, JobLeads e Idealist não têm API pública estável.
Este passo NÃO é um script Python — é um prompt que o Claude Code executa
usando suas ferramentas nativas de busca web (WebSearch / WebFetch).

## Como rodar

Cole isto como prompt para o Claude Code (ou salve como comando customizado
`.claude/commands/vagas-br.md` no seu projeto):

---

Você vai pesquisar vagas de emprego no Brasil para os cargos listados em
`config.json` (campo `cargos_alvo`), usando WebSearch.

Regras:
1. Para cada cargo em `cargos_alvo`, rode 1-2 buscas no formato:
   `"<cargo>" vaga Brasil 2026`
2. Priorize resultados de: vagas.com.br, br.indeed.com, catho.com.br,
   jobleads.com, idealist.org, infojobs.com.br (ver `fontes_busca_br`
   no config.json). Ignore LinkedIn e Glassdoor — eles não expõem link
   de vaga individual em busca, só páginas agregadas.
3. Descarte vagas que contenham qualquer termo de `termos_excluir`
   (estágio, trainee, jovem aprendiz) no título.
4. Para cada vaga relevante encontrada, extraia:
   - titulo
   - empresa
   - cidade (cidade + UF, ou "Remoto")
   - modalidade (Presencial / Híbrido / Remoto — se não informado, "verificar")
   - descricao (2-3 frases, resumo das responsabilidades)
   - link (URL direta da vaga — NUNCA a URL de busca/listagem)
   - fonte: "busca_br"
   - data_coleta: data de hoje (YYYY-MM-DD)
5. Se o link encontrado for de uma página de listagem (não de vaga
   individual), descarte — não adivinhe URLs de vaga.
6. Salve o resultado como JSON em `output/raw_br_boards.json`, mesmo
   formato de `raw_greenhouse.json`.

Meta: 5-15 vagas novas por rodada. Não repita vagas já presentes em
`output/vagas_historico.json` (mesmo link = mesma vaga).
