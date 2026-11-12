# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regras do projeto

As regras de trabalho estão em [AGENTS.md](AGENTS.md) e valem integralmente aqui. Leia-o junto com [docs/contexto-projeto.md](docs/contexto-projeto.md) e [corpus/README.md](corpus/README.md) antes de alterar o repositório. Em resumo:

- O CULTIVA é um app de apoio educativo/organizacional (18+) em Nutrição, Saúde Física e Estudos. A IA **não** diagnostica nem prescreve.
- Requisitos (RN, RF-A, RF-IA, RNF) e a arquitetura vêm do repositório [Documentacao-Cultiva](https://github.com/Cultiva-Challenge-2-Residencia-IA/Documentacao-Cultiva). A arquitetura é uma **proposta provisória, ainda não validada**. Classifique as afirmações em: requisito aprovado / documentado, aprovação não confirmada / proposta técnica / hipótese.
- Etapa atual: **aba Nutrição**, com o corpus e o RAG implementados (entrega da semana 2, PRs #30 a #33). Saúde Física, Estudos, o detector de risco (issue #9) e a infraestrutura de produção ainda não existem; não os implemente sem pedido explícito.
- Escreva em português do Brasil, como o restante do repositório.

## Estado real do código

- **Pipeline de corpus** em `corpus/scripts/` (PyMuPDF): conversão, verificação e preparação dos Trechos. Ambiente próprio em `corpus/.venv`.
- **Aplicação Python** (Python 3.11+, `uv`, `pyproject.toml`):
  - `src/rag/`: contrato do ADR 0002 (`contrato.py`) e `corpus_loader.py`, que carrega os Trechos e aplica o gate de aprovação;
  - `src/retrieval/`: `hybrid_retriever.py`, `vector_store.py` (ChromaDB), `taco_tool.py` e `graph_engine.py`;
  - `src/agent/`: `consultant_baseline.py` (orquestra busca, síntese e guardrails), `llm_client.py` (Groq ou Ollama; sem LLM, síntese extrativa) e `guardrails.py`;
  - `src/evaluation/`: `run_benchmark.py` e `gate.py`;
  - `src/api.py` (FastAPI e CLI) e `src/demo_entrega.py` (demonstração da entrega);
  - `src/config.py`: caminhos e parâmetros, quase todos sobrescrevíveis por variável de ambiente.
- `src/agents/nutricao/`, `src/rag/{chunking,reranker,retriever,verificador}/` e `src/guardrails/*/` são fachadas que reexportam ou complementam os módulos acima. `src/agents/{estudos,fisica,sincronizador}/`, `src/api/` e `src/broker/` ainda contêm apenas `.gitkeep`.
- **Testes** em `tests/` (pytest, inclusive o contrato do Trecho contra o JSON Schema) e **lint** com ruff.
- **Avaliação:** perguntas em `data/benchmark/eval_questions.json`, relatório em `data/benchmark/baseline_report.json`, baseline do gate em `eval/baselines/benchmark_offline.json` e limites em `eval/gates.toml`. O benchmark v2 (issue #13) fica em `eval/golden/v2/` (golden set com Trecho e página esperados, `dev` e `test`) e `src/evaluation/benchmark_v2.py`, com relatório em `data/benchmark/benchmark_v2_report.json`. Ele ainda não é gate do CI: o gate continua no v1. `eval/golden/dev` e `eval/golden/test` são cópias das 16 perguntas do v1.

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

# Demonstração da entrega (regrava entrega_semanal/ com --salvar-artefatos)
uv run python -m src.demo_entrega --salvar-artefatos
```

Corpus:

```bash
python3 -m venv corpus/.venv
corpus/.venv/bin/python -m pip install -r corpus/scripts/requirements.txt

# Verificação de integridade/rastreabilidade de todas as fontes (não aprova conteúdo)
corpus/.venv/bin/python corpus/scripts/verify_corpus.py

# Regenerar Markdown + relatório de UMA fonte (id do manifest.yaml)
corpus/.venv/bin/python corpus/scripts/convert_pdfs.py --source <id> --overwrite

# Primeira execução / originais ou modelo OCR ausentes
corpus/.venv/bin/python corpus/scripts/convert_pdfs.py --download --download-ocr

# Regenerar os Trechos JSONL (todas as fontes ou uma)
corpus/.venv/bin/python corpus/scripts/prepare_rag.py [--source <id>]
```

Após cada alteração documental, rode `git diff --check`. `corpus/.venv/`, `corpus/.cache/` (modelo OCR `por.traineddata`, verificado por SHA-256) e `data/vector_store/` são ignorados pelo Git.

## Arquitetura do pipeline de corpus

O fluxo atravessa vários arquivos, encadeados por hashes:

1. **`corpus/manifest.yaml`**: catálogo único (`version: 1`, `sources`). Cada fonte declara `id`, `source`, `license`, `version`, `sha256`, `pdf_pages`, caminhos (`original_path`, `markdown_path`, `report_path`, `conversion_config`) e status (`conversion_status`, `approval_status`, `intended_use_license_review`). Não crie `sources.yaml`. Os scripts **leem** o manifesto, mas nunca o alteram.
2. **`corpus/nutricao/originais/*.pdf`**: bytes preservados. O hash precisa corresponder ao manifesto, e os originais nunca são sobrescritos.
3. **`corpus/scripts/config/<fonte>.yaml`**: decisões por fonte, vinculadas ao SHA-256 do PDF (`sparse_page_decisions`, `ocr_regions`, `page_overrides`, `replacements`, `page_notes`, `strip_false_strikethrough_pages`). Substituições estritas falham se o trecho esperado mudar.
4. **`corpus/scripts/ajustes/*.md`**: transcrições manuais de páginas problemáticas, referenciadas em `page_overrides`.
5. **`convert_pdfs.py`** gera `nutricao/markdown/<nome>.md`, com `<!-- PDF_PAGE: N -->`, âncora `pagina-pdf-NNN` e link `...pdf#page=N` em cada página física (base 1, sem imagens exportadas). Também gera `nutricao/relatorios/<nome>.json`, com diagnóstico por página, OCR bruto, cobertura lexical (limiar de 98%, apenas diagnóstico) e hashes do PDF, Markdown, script, config e ajustes.
6. **`prepare_rag.py`** limpa o Markdown e gera os Trechos em `nutricao/rag/*.jsonl` (cerca de 1.000 caracteres, sem atravessar página nem seção), no formato de `corpus/schemas/trecho.schema.json`. Copia o `approval_status` do manifesto; `scripts/config/rag.yaml` define `skip_pages` e descartes por fonte. Registra em `nutricao/rag/geracao.json` os hashes do JSONL, do `.md`, do script e da seção da fonte no `rag.yaml`.
7. **`verify_corpus.py`** recalcula os hashes e falha se: o PDF divergir; o **Markdown for editado após a conversão**; `convert_pdfs.py`, a configuração ou um ajuste mudar sem regeneração; marcadores/links de página faltarem ou estiverem fora de ordem; ou houver imagem `![]()`. Também chama o `verify_trechos.py`, que falha se um JSONL faltar, foi editado à mão ou ficou para trás em relação ao `.md`, ao `prepare_rag.py` ou ao `rag.yaml`, se um campo copiado do manifesto (como `approval_status` e `licenca`) divergir, ou se `pagina_pdf` sair do intervalo do PDF. Ele não exige nenhum status.

Consequências práticas:

- Ao mudar qualquer campo de uma fonte no manifesto (inclusive o `approval_status`), o `prepare_rag.py` ou o `rag.yaml`, regenere os Trechos no mesmo PR; senão o `verify_corpus.py` falha.
- Correções de transcrição devem ir para `config/` ou `ajustes/` e ser seguidas de `--source <id> --overwrite`. Edições diretas no `.md` quebram a verificação e são perdidas na regeneração.
- Qualquer mudança em `convert_pdfs.py` invalida os relatórios de **todas** as fontes até que sejam regeneradas.
- Há um único status de aprovação por fonte, `approval_status` (`pendente` ou `aprovado`), que vive só no manifesto (decisão de 06/11/2026; veja `corpus/README.md`). `convert_pdfs.py` se recusa a converter fonte com `approval_status` diferente de `pendente`, para não regenerar uma fonte aprovada por engano, e o verificador não exige nenhum status.
- Para incluir uma nova fonte, siga a seção "Como incluir outro documento" em [corpus/README.md](corpus/README.md). Não copie a licença de outra fonte e use `pendente` quando ela for desconhecida.

## Arquitetura do RAG de Nutrição

1. **Carga e gate** (`src/rag/corpus_loader.py`): lê os Trechos JSONL e só aceita fontes `aprovado` (hoje 21 de 22; a SBAN está `pendente`). Com `CULTIVA_INCLUIR_PENDENTES=true`, aceita também as pendentes. A licença não entra no gate.
2. **Contrato** (`src/rag/contrato.py`, ADR 0002): `trecho_para_chunk` adiciona o cabeçalho contextual e deriva o nível de evidência do `source_type`.
3. **Busca híbrida** (`HybridRetriever`): BM25 com sinônimos clínicos e busca densa no ChromaDB (embeddings `paraphrase-multilingual-MiniLM-L12-v2`, 384d, locais via fastembed), fundidas por RRF, com no máximo 2 Trechos por documento. O reranker (sobreposição de termos e bônus por nível de evidência) e a mistura densa com TF-IDF/LSA existem, mas estão desligados por padrão desde a #35 (`MODO_DENSO`, `RERANK_PESO_SOBREPOSICAO`, `RERANK_BONUS_EVIDENCIA` em `src/config.py`): na escala original o reranker valia cerca de 10 vezes a fusão e decidia o ranking sozinho. Para comparar configurações, use `uv run python -m src.evaluation.ablacao_ranking` (v1 e v2 no mesmo índice); antes de comparar, julgue os Trechos que aparecerem como não julgados.
4. **Banco vetorial** (`vector_store.py`): ChromaDB persistente em `data/vector_store/chroma_db`, índice HNSW por cosseno com `ef_construction` e `ef_search` em 200 (`HNSW_EF_*` em `src/config.py`). O nome da coleção leva uma impressão digital do modelo, da configuração do HNSW e dos Trechos.
5. **Resposta** (`consultant_baseline.py`): guardrail de entrada (Lei 8.234/1991), síntese a partir dos Trechos, TACO e grafo causal, guardrail de saída e citações com fonte, página e link.

## CI (`.github/workflows/ci.yml`)

- Obrigatórios: ruff, pytest e integridade do corpus (`verify_corpus.py`).
- Informativo: "Gates de avaliação". Uma execução do benchmark só constrói o índice e é descartada; duas execuções seguintes no mesmo índice precisam gerar relatórios idênticos (determinismo). Depois, `gate.py` compara as métricas com o baseline da branch de destino (regressão máxima de 5 p.p., guardrail legal em 100%). O gate de risco fica `PENDENTE` até existir o detector (issue #9).

Consequências práticas do RAG:

- Mudar Trechos, modelo de embeddings ou parâmetros do HNSW gera uma coleção nova no ChromaDB na próxima execução; não reaproveite índices antigos.
- Benchmark e demonstração usam só fontes aprovadas. Ao aprovar ou reprovar uma fonte, regenere os Trechos (`prepare_rag.py`), o benchmark e os artefatos da demonstração, e atualize `docs/entrega-rag-nutricao.md`.
- Mudanças que alterem as métricas precisam atualizar `eval/baselines/benchmark_offline.json` de forma justificada; o gate compara com o baseline da branch de destino, então editar o baseline no próprio PR não afrouxa o gate.
- Um teste exige que o HNSW recupere pelo menos 99% dos vizinhos da busca exata. Se ele falhar após o corpus crescer, aumente `ef_search` em vez de afrouxar o teste.

## Inconsistência conhecida

[docs/contexto-projeto.md](docs/contexto-projeto.md) (03/11/2026) está desatualizado em relação ao corpus:

- afirma `sources: []`, que os diretórios ainda não existem e que `src/` e `eval/golden/` contêm só placeholders;
- propõe `originais/<id>/<versao>/documento.<ext>`, mas o layout implementado é plano (`originais/<nome>.pdf`), com a versão registrada no manifesto e no nome do arquivo.

Use `corpus/README.md` e `manifest.yaml` como referência do estado atual. Não altere o contexto sem pedido.
