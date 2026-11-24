# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regras do projeto

> **Mantenha este arquivo e o `AGENTS.md` atualizados.** Ao mudar comportamento, arquitetura, comandos, fluxo de trabalho ou uma decisão da equipe, atualize os dois no mesmo PR; antes de concluir uma tarefa, confira se algo que eles afirmam ficou desatualizado (issues, números, módulos, flags, decisões) e corrija.

As regras de trabalho estão em [AGENTS.md](AGENTS.md) e valem integralmente aqui. Leia-o junto com [CONTRIBUTING.md](CONTRIBUTING.md) (fluxo de issue, branch, commit, PR e revisão) e [corpus/README.md](corpus/README.md) antes de alterar o repositório. Em resumo:

- O CULTIVA é um app de apoio educativo/organizacional (18+) em Nutrição, Saúde Física e Estudos. A IA **não** diagnostica nem prescreve.
- Requisitos (RN, RF-A, RF-IA, RNF) e a arquitetura vêm do repositório [Documentacao-Cultiva](https://github.com/Cultiva-Challenge-2-Residencia-IA/Documentacao-Cultiva). A arquitetura é uma **proposta provisória, ainda não validada**. Classifique as afirmações em: requisito aprovado / documentado, aprovação não confirmada / proposta técnica / hipótese.
- Etapa funcional atual: **aba Nutrição**, com o corpus e o RAG implementados (entrega da semana 2, PRs #30 a #33). Em 19/11/2026, oito originais prioritários de Saúde Física foram arquivados e onze fontes foram incluídas no manifesto como `kind: original_only`; oito têm Markdown candidato à revisão, ainda sem Trechos, RAG ou aba funcional de Saúde Física. Estudos e a infraestrutura de produção também não existem. O portão de risco (issue #9) existe só para texto; o léxico e a mensagem de acolhimento foram revisados pela equipe, sem profissional de saúde.
- Escreva em português do Brasil, como o restante do repositório.

## Estado real do código

- **Pipeline de corpus** em `corpus/scripts/`: conversão de PDF (PyMuPDF), conversão de HTML (`convert_html.py`), verificação e preparação dos Trechos. Ambiente próprio em `corpus/.venv`.
- **Aplicação Python** (Python 3.11+, `uv`, `pyproject.toml`):
  - `src/rag/`: contrato do ADR 0002 (`contrato.py`) e `corpus_loader.py`, que carrega os Trechos e aplica o gate de aprovação;
  - `src/retrieval/`: `hybrid_retriever.py`, `vector_store.py` (ChromaDB), `taco_tool.py` e `graph_engine.py`;
  - `src/orquestrador/`: grafo principal em LangGraph (issue #76), com os portões de risco e de prompt injection antes de qualquer agente; diagrama em `src/orquestrador/README.md` (`uv run python -m src.orquestrador`);
  - `src/agent/`: `consultant_baseline.py` (`consult()` abre a observação raiz do Langfuse e invoca o grafo do orquestrador; montagem dos componentes e da rastreabilidade), `llm_client.py` (Ollama local por padrão, `gemma4:e4b` com reserva `qwen2.5:7b`, `think: false` e até 2048 tokens de saída, ADR 0004; Groq só com liberação explícita; sem LLM, síntese extrativa; ADR 0003) e `guardrails.py` (guardrail legal da Lei 8.234/1991);
  - `src/guardrails/`: `risco/` (detector de risco por léxico, `lexico.yaml`, e mensagem de acolhimento), `injection/` (prompt injection e delimitação dos Trechos como dado) e `pii/` (máscara de dados pessoais); `prescricao/` e `tom/` reexportam o guardrail legal;
  - `src/rag/abstencao.py`: o "não sei" fora do domínio (issue #6);
  - `src/evaluation/`: `run_benchmark.py` (v1, com `risk_metrics`, `risk_metrics_holdout` e `abstention_metrics`), `benchmark_v2.py`, `benchmark_respostas.py` (comparação de respostas do golden `eval/golden/resposta/{dev,test}.json`, com `--incluir-golden-v2` para os 16 casos de resposta do golden v2: LLM sem RAG, RAG atual, contexto oráculo e síntese extrativa, com teste pareado por bootstrap; resultado em `docs/entrega-semana-3-llm-x-rag.md`; telemetria opcional no Langfuse, com a mesma regra de destino local do ADR 0003), `risco.py`, `abstencao.py`, `ablacao_ranking.py`, `ablacao_seed.py` (issue #5: efeito do `seed_guidelines`, que saiu do índice; resultado em `eval/runs/ablacao_seed_issue5.md`), `exagero.py` (issue #86: checagem de exagero depois da geração, avaliada fora do produto; exige o Ollama), `fundamentacao.py` (issues #12 e #67: conformidade das citações do LLM, frases removidas pela citação literal e amostra julgada do RNF27, em `eval/fundamentacao/`; `amostra --prefixo` separa as amostras por versão do prompt), `gate.py`, `modelo_local/` (comparação de modelos do Ollama, issue #55; fora do CI) e `comparacao_guardrails/` (issue #52: NeMo Guardrails, Guardrails AI e chamada direta ao LLM para o "não sei" e a fundamentação; fora do CI);
  - `src/api.py` (FastAPI e CLI) e `src/demo_entrega.py` (demonstração da entrega);
  - `src/config.py`: caminhos e parâmetros, quase todos sobrescrevíveis por variável de ambiente.
  - `src/observabilidade.py`: Langfuse opcional (proposta técnica; ADR 0003, item 5). Desligado por padrão e no CI; pacote no grupo `observabilidade` (`uv sync --group observabilidade`). Liga com `CULTIVA_LANGFUSE=true` e as chaves; destino padrão `http://localhost:3000`, e servidor externo só com `ALLOW_EXTERNAL_LANGFUSE=true`. Cada trace leva a versão do código (`release`: `LANGFUSE_RELEASE` ou o commit do Git), a versão do prompt, o `corpus_version` e scores 0/1 cuja média no painel é a taxa (`tipo_resposta`, `sintese_extrativa`, `citacoes_validas`, `nao_sei`, `risco_acionado`, `prompt_injection`, `guardrail_lei_8234`; `scores_da_resposta`). O id do trace sai do `response_id` (`id_do_trace`), e o `POST /feedback/incorrect` grava o score `resposta_incorreta` no trace (RF-IA15). A equipe usa o Langfuse Cloud (EUA) com as regras do adendo de 20/11 ao ADR 0003, e o painel é importado no Langfuse a partir dos JSON em `docs/observabilidade-painel/` (instruções e limites em `docs/observabilidade-painel.md`, inclusive a mistura com as métricas de mesmo nome do `langfuse_experimento.py`). O SDK mascara todo texto dos spans, e mensagem que o portão de risco detecta vai só com as categorias (as que o léxico não detecta, a maioria das frases novas pela #48, vão mascaradas como qualquer pergunta). `src/evaluation/langfuse_experimento.py` roda o golden v2 como experimento, com ablação (`--config llm-puro|llm-rag|llm-rag-grafo|completo`); só o `dev` sobe para o dataset, e o `test` exige `--incluir-test`. O "LLM puro" é só da ablação: liga quando busca, TACO e grafo estão desligados na configuração (`modo_llm_puro`), nunca por busca vazia.
- `src/rag/verificador/citacoes.py`: checagem determinística das citações por frase (`[T#]`, `[GRAFO]`, `[TACO]`; issue #12).
- `src/agents/nutricao/grafo.py` é o subgrafo de Nutrição (guardrail de entrada, busca, TACO, grafo causal, "não sei", síntese, guardrail de saída e citações). O resto de `src/agents/nutricao/` e `src/rag/{chunking,reranker,retriever,verificador}/` são fachadas que reexportam ou complementam os módulos acima. `src/agents/{estudos,fisica,sincronizador}/`, `src/api/` e `src/broker/` ainda contêm apenas `.gitkeep`.
- **Testes** em `tests/` (pytest, inclusive o contrato do Trecho contra o JSON Schema) e **lint** com ruff.
- **Decisões de arquitetura** em `docs/adrs/`: 0001 (RAG híbrido, TACO e grafo), 0002 (contrato entre corpus e retriever), 0003 (provedor de LLM e dados pessoais) e 0004 (modelo local do Ollama: `gemma4:e4b`, reserva `qwen2.5:7b`).
- **Modelos de issue e de PR** em `.github/` (tarefa, bug, fonte para o corpus e decisão).
- **Avaliação:** perguntas em `data/benchmark/eval_questions.json`, relatório em `data/benchmark/baseline_report.json`, baseline do gate em `eval/baselines/benchmark_offline.json` e limites em `eval/gates.toml`. O benchmark v2 (issue #13) fica em `eval/golden/v2/` (golden set com Trecho e página esperados, `dev` e `test`) e `src/evaluation/benchmark_v2.py`, com relatório em `data/benchmark/benchmark_v2_report.json`. O benchmark comparativo de respostas fica em `eval/golden/resposta/` e `src/evaluation/benchmark_respostas.py`; seu split `test` é holdout (ainda sem revisão), e `--use-langfuse` envia traces e scores ao `LANGFUSE_BASE_URL` (local por padrão; servidor externo só com `ALLOW_EXTERNAL_LANGFUSE=true`). Esses benchmarks ainda não são gates do CI: o gate continua no v1. `eval/golden/dev` e `eval/golden/test` são cópias das 16 perguntas do v1.

## Comandos (na raiz do repositório)

Aplicação:

```bash
uv sync
uv run ruff check .
uv run pytest -q

# Benchmark offline, determinístico, sem LLM (regrava data/benchmark/baseline_report.json)
uv run python -m src.evaluation.run_benchmark --no-ollama

# Benchmark v2 (Trecho e página esperados; regrava data/benchmark/benchmark_v2_report.json)
uv run python -m src.evaluation.benchmark_v2 --no-ollama
uv run python -m src.evaluation.gate --report data/benchmark/baseline_report.json \
  --baseline eval/baselines/benchmark_offline.json --config eval/gates.toml

# Comparação de modelos locais (issue #55; ver eval/modelo_local/README.md). O juiz é às cegas:
# exportar-cego gera lotes em data/modelo_local/juiz_cego/, subagentes do Claude os julgam, importar-cego confere os controles
uv run python -m src.evaluation.modelo_local congelar|gerar|ferramentas|exportar-cego|importar-cego|bertscore|relatorio
uv sync --group modelo-local   # bert-score e PyTorch para CPU, só para o BERTScore

# Comparação de frameworks de guardrail (issue #52; Ollama local; ver eval/comparacao_guardrails/README.md)
uv sync --group guardrails-frameworks
uv run python -m src.evaluation.comparacao_guardrails casos|respostas|fundamentacao|fundamentacao-reais|abstencao|relatorio

# Demonstração da entrega (regrava entrega_semanal/ com --salvar-artefatos)
uv run python -m src.demo_entrega --salvar-artefatos

# Experimento no Langfuse (opcional; exige uv sync --group observabilidade e as variáveis do .env.example)
uv run python -m src.evaluation.langfuse_experimento --config completo --split dev
```

Corpus:

```bash
python3 -m venv corpus/.venv
corpus/.venv/bin/python -m pip install -r corpus/scripts/requirements.txt

# Verificação de integridade/rastreabilidade de todas as fontes (não aprova conteúdo)
corpus/.venv/bin/python corpus/scripts/verify_corpus.py

# Regenerar Markdown + relatório de UMA fonte (id do manifest.yaml)
corpus/.venv/bin/python corpus/scripts/convert_pdfs.py --source <id> --overwrite

# Regenerar os candidatos de Saúde Física em PDF (kind: original_only; sem Trechos)
corpus/.venv/bin/python corpus/scripts/convert_pdfs.py --candidatos --overwrite

# Primeira execução / originais ou modelo OCR ausentes
corpus/.venv/bin/python corpus/scripts/convert_pdfs.py --download --download-ocr

# Regenerar os Trechos JSONL (todas as fontes ou uma)
corpus/.venv/bin/python corpus/scripts/prepare_rag.py [--source <id>]
```

Após cada alteração documental, rode `git diff --check`. `corpus/.venv/`, `corpus/.cache/` (modelo OCR `por.traineddata`, verificado por SHA-256) e `data/vector_store/` são ignorados pelo Git.

## Arquitetura do pipeline de corpus

O fluxo atravessa vários arquivos, encadeados por hashes:

1. **`corpus/manifest.yaml`**: catálogo único (`version: 1`, `sources`). Fontes do pipeline de Nutrição declaram `id`, `source`, `license`, `version`, `sha256`, `pdf_pages`, caminhos (`original_path`, `markdown_path`, `report_path`, `conversion_config`) e status (`conversion_status`, `approval_status`, `intended_use_license_review`). Fontes `kind: original_only` não entram nos Trechos/RAG; podem ter Markdown candidato à revisão, ligado ao original e ao relatório por hash. Não crie `sources.yaml`. Os scripts **leem** o manifesto, mas nunca o alteram.
2. **`corpus/nutricao/originais/*.pdf`**: bytes preservados. O hash precisa corresponder ao manifesto, e os originais nunca são sobrescritos.
3. **`corpus/scripts/config/<fonte>.yaml`**: decisões por fonte, vinculadas ao SHA-256 do PDF (`sparse_page_decisions`, `ocr_regions`, `page_overrides`, `replacements`, `page_notes`, `strip_false_strikethrough_pages`, `restore_case_from_native`). Substituições estritas falham se o trecho esperado mudar.
4. **`corpus/scripts/ajustes/*.md`**: transcrições manuais de páginas problemáticas, referenciadas em `page_overrides`.
5. **`convert_pdfs.py`** gera `nutricao/markdown/<nome>.md`, com `<!-- PDF_PAGE: N -->`, âncora `pagina-pdf-NNN` e link `...pdf#page=N` em cada página física (base 1, sem imagens exportadas). Também gera `nutricao/relatorios/<nome>.json`, com diagnóstico por página, OCR bruto, cobertura lexical (limiar de 98%, apenas diagnóstico) e hashes do PDF, Markdown, script, config e ajustes.
6. **`prepare_rag.py`** limpa o Markdown e gera os Trechos em `nutricao/rag/*.jsonl` (cerca de 1.000 caracteres, sem atravessar página nem seção), no formato de `corpus/schemas/trecho.schema.json`. Copia o `approval_status` do manifesto; `scripts/config/rag.yaml` define `skip_pages` e descartes por fonte. Registra em `nutricao/rag/geracao.json` os hashes do JSONL, do `.md`, do script e da seção da fonte no `rag.yaml`.
7. **`verify_corpus.py`** recalcula os hashes e falha se: o PDF divergir; o **Markdown for editado após a conversão**; `convert_pdfs.py`, a configuração ou um ajuste mudar sem regeneração; marcadores/links de página faltarem ou estiverem fora de ordem; ou houver imagem `![]()`. Também confere formato e hash dos originais `kind: original_only` e, quando declarados, dos Markdown e relatórios candidatos; informa originais ainda indisponíveis. Chama `verify_trechos.py`, que exclui fontes `original_only` do RAG e falha se um JSONL faltar, foi editado à mão ou ficou para trás em relação ao `.md`, ao `prepare_rag.py` ou ao `rag.yaml`, se um campo copiado do manifesto (como `approval_status` e `licenca`) divergir, ou se `pagina_pdf` sair do intervalo do PDF. Ele não exige nenhum status.

Consequências práticas:

- Ao mudar qualquer campo de uma fonte no manifesto (inclusive o `approval_status`), o `prepare_rag.py` ou o `rag.yaml`, regenere os Trechos no mesmo PR; senão o `verify_corpus.py` falha.
- Correções de transcrição devem ir para `config/` ou `ajustes/` e ser seguidas de `--source <id> --overwrite`. Edições diretas no `.md` quebram a verificação e são perdidas na regeneração.
- Qualquer mudança em `convert_pdfs.py` invalida os relatórios de **todas** as fontes até que sejam regeneradas: as de Nutrição (`--overwrite`, com as aprovadas passando por `pendente`) e os candidatos de Saúde Física (`--candidatos --overwrite`, issue #87). Faça isso também depois de mesclar a `main` se ela trouxe mudança no script.
- `restore_case_from_native: true` (hoje no Guia, issue #27, e na SBME, issue #72) devolve ao Markdown a caixa do texto nativo do PDF, que o `to_markdown` do PyMuPDF perde em versaletes e em inícios de frase. A caixa do nativo só é usada quando é regular e nunca rebaixa uma maiúscula correta.
- Há um único status de aprovação por fonte, `approval_status` (`pendente` ou `aprovado`), que vive só no manifesto (decisão de 06/11/2026; veja `corpus/README.md`). `convert_pdfs.py` se recusa a converter fonte com `approval_status` diferente de `pendente`, para não regenerar uma fonte aprovada por engano, e o verificador não exige nenhum status.
- Para incluir uma nova fonte, siga a seção "Como incluir outro documento" em [corpus/README.md](corpus/README.md). Não copie a licença de outra fonte e use `pendente` quando ela for desconhecida.

## Arquitetura do RAG de Nutrição

**Portões antes da busca** (`src/orquestrador/grafo.py`, issues #9 e #76): primeiro o detector de risco (`src/guardrails/risco/`, RF-IA03), por léxico e regras locais (`lexico.yaml`, inclusive regras com número para jejum, calorias e quantidade de remédios). Quando o léxico não aciona e o Ollama está habilitado, uma camada LLM **local** (`classificador_llm.py`, `RISCO_LLM_MODELO`, issue #48; por padrão o mesmo `OLLAMA_MODEL` da síntese, `gemma4:e4b`, por decisão da equipe de 20/11/2026: dois modelos não cabem juntos numa GPU de 8 GB; o `qwen2.5:7b` fica só como reserva do ADR 0004) classifica a pergunta com uma política escrita a partir do RF-IA03, que devolve um nível de preocupação de 0 a 10 e aciona a partir de `RISCO_LLM_LIMIAR` (1); o modelo é carregado na inicialização e mantido com `keep_alive`, e qualquer falha ou tempo limite (`RISCO_LLM_TIMEOUT`, 3 s) faz valer só o léxico (`risk_llm_status="falhou"`). Com risco, a resposta é a mensagem fixa de acolhimento (CVV 188), sem busca nem LLM de geração, e `risk_layer` diz qual camada acionou. Depois vem o detector de prompt injection (`src/guardrails/injection/`, RNF04), com recusa fixa. O que vai ao LLM leva a pergunta com dados pessoais mascarados (`src/guardrails/pii/`, RNF05) e os Trechos delimitados como dado.

1. **Carga e gate** (`src/rag/corpus_loader.py`): lê os Trechos JSONL e só aceita fontes `aprovado` (hoje 21 de 31: a SBAN e as 9 fontes incluídas em 20/11/2026 estão `pendente`). Com `CULTIVA_INCLUIR_PENDENTES=true`, aceita também as pendentes. A licença não entra no gate.
2. **Contrato** (`src/rag/contrato.py`, ADR 0002): `trecho_para_chunk` adiciona o cabeçalho contextual e deriva o nível de evidência do `source_type`.
3. **Busca híbrida** (`HybridRetriever`): BM25 com sinônimos clínicos e busca densa no ChromaDB (embeddings `paraphrase-multilingual-MiniLM-L12-v2`, 384d, locais via fastembed), fundidas por RRF, com no máximo 2 Trechos por documento. O reranker (sobreposição de termos e bônus por nível de evidência) e a mistura densa com TF-IDF/LSA existem, mas estão desligados por padrão desde a #35 (`MODO_DENSO`, `RERANK_PESO_SOBREPOSICAO`, `RERANK_BONUS_EVIDENCIA` em `src/config.py`): na escala original o reranker valia cerca de 10 vezes a fusão e decidia o ranking sozinho. Para comparar configurações, use `uv run python -m src.evaluation.ablacao_ranking` (v1 e v2 no mesmo índice); antes de comparar, julgue os Trechos que aparecerem como não julgados.
4. **Banco vetorial** (`vector_store.py`): ChromaDB persistente em `data/vector_store/chroma_db`, índice HNSW por cosseno com `ef_construction` e `ef_search` em 200 (`HNSW_EF_*` em `src/config.py`). O nome da coleção leva uma impressão digital de `corpus_version`, modelo, configuração do HNSW e Trechos; alterações do manifesto/JSONL criam outra coleção. FastEmbed roda localmente. A comparação de modelos e a decisão sobre pgvector seguem pendentes na issue #15.
5. **"Não sei"** (`src/rag/abstencao.py`, issue #6, RF-IA01): só quando a pergunta está fora do domínio, isto é, o cosseno do Trecho mais próximo no ChromaDB fica abaixo de `ABSTENCAO_LIMIAR_COSSENO` **e** a pergunta não tem termo do vocabulário de Nutrição (`TERMOS_NUTRICAO`). A resposta é fixa, sem LLM (`abstencao=True`); com resultado do grafo ou da TACO, responde só com eles. O cosseno sozinho recusava perguntas que o corpus responde ("Jejum intermitente funciona?"). Temas de Nutrição ausentes do corpus continuam sendo respondidos (`eval/abstencao/README.md`): na #52, nenhum framework nem a chamada direta ao LLM deu o "não sei" com recusa indevida de até 5% (`eval/comparacao_guardrails/README.md`).
6. **Resposta** (`src/agents/nutricao/grafo.py`): guardrail de entrada (Lei 8.234/1991), síntese a partir dos Trechos, TACO e grafo causal, guardrail de saída e citações com fonte, página e link. **Citação por frase** (issue #12): o prompt numera os Trechos como `[T1]`..`[Tn]` e pede cada campo como lista de `{"frase", "trechos"}` (prompt v3; `normalizar_frases_citadas` monta o texto com os marcadores); `verificar_citacoes` confere o texto do LLM (toda frase citada, todo `[T#]` dentro do intervalo, `[GRAFO]`/`[TACO]` só com a ferramenta, ao menos um `[T#]`), e a resposta que falha é bloqueada e trocada pela síntese extrativa, que marca cada frase copiada (`fundamentacao_status="extrativa_apos_citacao_invalida"`). As citações exibidas são só os Trechos marcados (`trechos_citados`), com o `T#` e a página. Se o LLM disser "Não consta nos trechos recuperados." em vez de responder, a resposta vira o "não sei" (`llm_sem_base`). Medição com `qwen2.5:7b`: conformidade de citação de 95% no `dev` e 89% no `test` com o prompt v3, e de 77% e 87,5% com o prompt v4, que também exige a citação literal (`eval/fundamentacao/`); o RNF27 **não** está cumprido: na amostra de 60 frases do `qwen2.5:7b` julgada com um LLM externo, sem avaliação humana independente, 35% foram sustentadas pelo trecho citado, e o campo `physiological_mechanism` ficou em 17% (`eval/fundamentacao/resultado_amostra.md`; melhoria na #67). Com o prompt v4, uma nova amostra de 59 frases do mesmo modelo e com o mesmo juiz teve 46% sustentadas (`eval/fundamentacao/resultado_amostra_v4.md`). **Prompt v4 (#67):** cada frase traz `citacao`, um pedaço copiado da fonte, e `filtrar_citacoes_literais` remove a frase cuja citação (de pelo menos 4 palavras) não existe literalmente no material entregue; se ela existir em outra fonte, o rótulo é corrigido. O `physiological_mechanism` só é preenchido quando um trecho descreve o mecanismo. A checagem pega invenção, não exagero (frase que vai além da citação). Com o modelo padrão (`gemma4:e4b`, ADR 0004) e o prompt v4, a amostra de 60 frases teve 83% sustentadas (IC de 72% a 91%, nenhuma não sustentada; `eval/fundamentacao/resultado_amostra_v4_gemma4.md`); a amostra do qwen julgada de novo com o mesmo pedido (`prompt_juiz.md`) manteve 46%, então o ganho vem do modelo. Um prompt v5 contra o exagero ficou em 85%, sem ganho mensurável e com menos respostas aceitas, e foi desfeito (`resultado_amostra_v5_gemma4.md`). Uma checagem depois da geração (#86: o `gemma4:e4b` confere cada frase contra o trecho citado) foi medida nas 120 frases julgadas, com critérios definidos antes: achou 36% das parciais no `dev` e 0 de 5 no `test`; um segundo verificador separado, um modelo de NLI no processador (`--verificador nli`, `uv sync --group modelo-local`), achou 1 de 5; a checagem **não** foi ligada no produto (`eval/fundamentacao/resultado_exagero.md`, `uv run python -m src.evaluation.exagero --split dev|test`). Os julgamentos são do ChatGPT, sem avaliação humana independente. A síntese usa o Ollama local por padrão (`LLM_PROVIDER=ollama`); a Groq exige `LLM_PROVIDER=groq` **e** `ALLOW_EXTERNAL_LLM=true` e não deve receber dados pessoais reais (ADR 0003). Sem LLM disponível, a síntese é extrativa e determinística, como no CI.

## CI (`.github/workflows/ci.yml`)

- Obrigatórios: ruff, pytest e integridade do corpus (`verify_corpus.py`).
- Informativo: "Gates de avaliação". Uma execução do benchmark só constrói o índice e é descartada; duas execuções seguintes no mesmo índice precisam gerar relatórios idênticos (determinismo). Depois, `gate.py` compara as métricas com o baseline da branch de destino (regressão máxima de 5 p.p., guardrail legal em 100%). O gate de risco exige recall ≥ 0,95 no conjunto de desenvolvimento (`eval/risco/casos.json`, também com precisão ≥ 0,60) e no holdout (`eval/risco/holdout.json`), que é escrito por quem não escreveu o léxico; veja `eval/risco/README.md`. O holdout atual (lote 3, cego) tem recall de 0,133 só com o léxico, que é o que o CI mede (sem Ollama), e de 0,733 a 1,000 com a camada LLM local, conforme a versão da política, medido à parte e com lote e política do mesmo autor; a configuração em uso (`gemma4:e4b`, limiar 1) não foi medida no holdout, para não fazer uma quarta olhada. Ela foi medida uma vez num lote cego novo (lote 4, `eval/risco/lote4_cego.json`, escrito pelo ChatGPT, aceito pela equipe em 24/11/2026 como autor independente): recall de 1,000, precisão de 0,900 e p95 de 2,43 s (`eval/risco/llm_resultados.md`, `uv run python -m src.evaluation.risco_llm --lote <arquivo>`). Como o CI não tem Ollama, o que ele mede é só o léxico: o gate `risco_holdout:recall` sai como falha conhecida (aviso com o número real; falha se cair abaixo de 0,1333) e o teste de recall no holdout é `xfail` estrito, porque mede só o léxico. Não amplie o léxico a partir do holdout. O gate `[abstencao]` usa o `abstention_metrics` (`eval/abstencao/casos.json`): "não sei" em pelo menos 85% das perguntas fora de Nutrição e no máximo 5% de recusa indevida.

Consequências práticas do RAG:

- Mudar `corpus_version`, Trechos, modelo de embeddings ou parâmetros do HNSW gera uma coleção nova no ChromaDB na próxima execução; não reaproveite índices antigos. A migração para pgvector ainda não foi aprovada.
- Benchmark e demonstração usam só fontes aprovadas. Ao aprovar ou reprovar uma fonte, regenere os Trechos (`prepare_rag.py`), o benchmark e os artefatos da demonstração, e atualize `docs/entrega-rag-nutricao.md`.
- Mudanças que alterem as métricas precisam atualizar `eval/baselines/benchmark_offline.json` de forma justificada; o gate compara com o baseline da branch de destino, então editar o baseline no próprio PR não afrouxa o gate.
- Um teste exige que o HNSW recupere pelo menos 99% dos vizinhos da busca exata. Se ele falhar após o corpus crescer, aumente `ef_search` em vez de afrouxar o teste.

## Inconsistência conhecida

[docs/contexto-projeto.md](docs/contexto-projeto.md) (03/11/2026) está desatualizado em relação ao corpus:

- afirma `sources: []`, que os diretórios ainda não existem e que `src/` e `eval/golden/` contêm só placeholders;
- propõe `originais/<id>/<versao>/documento.<ext>`, mas o layout implementado é plano (`originais/<nome>.pdf`), com a versão registrada no manifesto e no nome do arquivo.

Use `corpus/README.md` e `manifest.yaml` como referência do estado atual. Não altere o contexto sem pedido.
