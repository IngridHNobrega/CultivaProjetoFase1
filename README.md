# CultivaProjetoFase1 — Módulo de Nutrição Baseada em Evidências (`rag-hibrido`)

Projeto: **CULTIVA**, um aplicativo que usa IA para ajudar jovens adultos e estudantes (18+) a transformar bons hábitos em decisões simples e sustentáveis, sem substituir o profissional de saúde. Alinhado aos ODS 3 (Saúde e Bem-Estar) e 4 (Educação de Qualidade).

📄 **Documentação Completa da Entrega (Artefatos, Chunking, Embeddings, Banco Vetorial, Arquitetura e Ingestão):**
👉 Consulte [`docs/entrega-rag-nutricao.md`](docs/entrega-rag-nutricao.md)

---

## Consultor Científico de Nutrição Baseado em Evidências (RAG Híbrido + ChromaDB + TACO + Grafo Causal)

Implementação completa de um consultor de nutrição baseado em evidências científicas e diretrizes oficiais, operando com **Banco Vetorial Persistente (`ChromaDB` + Embeddings Multilíngues de 384d)**, **Ollama local por padrão (`qwen2.5:7b`, com fallback local `qwen2.5:3b` e síntese extrativa determinística)** (Groq como alternativa opcional desativada por padrão; ver [ADR 0003](docs/adrs/0003-provedor-llm-e-dados-pessoais.md)) e respeitando rigorosamente os limites da **Lei Federal nº 8.234/1991 (Art. 3º - CFN)**.

---

## Resumo dos Artefatos da Entrega

Detalhes, números gerados pelo sistema, diagramas e limitações em [`docs/entrega-rag-nutricao.md`](docs/entrega-rag-nutricao.md).

1. **Base de conhecimento curada:** 21 documentos-fonte aprovados (mínimo exigido: 20) de 22 catalogados em [`corpus/manifest.yaml`](corpus/manifest.yaml) com origem e SHA-256, somando 1.818 Trechos no índice. A SBAN segue pendente; o `seed_guidelines` (sem origem verificável) e os resumos do PubMed (em inglês) ficaram fora do índice.
2. **Chunking:** `corpus/scripts/prepare_rag.py` gera Trechos de cerca de 1.000 caracteres sem atravessar página nem seção, no formato do [ADR 0002](docs/adrs/0002-contrato-corpus-retriever.md), com cabeçalho contextual na indexação.
3. **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões, cosseno), executado localmente, combinado ao BM25 por RRF.
4. **Banco vetorial:** ChromaDB persistente em `data/vector_store/chroma_db`, índice HNSW por cosseno (`ef_search` e `ef_construction` em 200, para o resultado coincidir com a busca exata), coleção versionada pela impressão digital do conteúdo e metadados de rastreabilidade (fonte, página, link, aprovação).
5. **Gate de aprovação:** só fontes `aprovado` entram no índice, inclusive na demonstração e no benchmark. Para testar com as pendentes, use `CULTIVA_INCLUIR_PENDENTES=true` (API e CLI).

---

## Como Executar

### 1. Instalar dependências e verificar integridade do Corpus Oficial
```bash
uv sync
uv run python corpus/scripts/verify_corpus.py
```

### 2. Configurar o Ollama local (Provedor Padrão)
```bash
# Baixar o modelo primário recomendado (Qwen 2.5 7B, ~4.7 GB)
ollama pull qwen2.5:7b

# Opcional: baixar modelo leve para fallback em máquinas com pouca memória (<= 8GB)
ollama pull qwen2.5:3b

# Manter o Ollama estritamente local (sem envio para nuvem):
export OLLAMA_NO_CLOUD=1
```
*A Groq não é necessária para executar o projeto. Consulte a decisão técnica em [`docs/adrs/0003-provedor-llm-e-dados-pessoais.md`](docs/adrs/0003-provedor-llm-e-dados-pessoais.md).*

### 3. Executar a Demonstração Oficial da Entrega (Artefatos + Consulta + Chunks + Resposta + Fontes)
```bash
# Executa a auditoria dos artefatos (>= 20 fontes, chunking, embeddings, ChromaDB) e 3 consultas completas:
uv run python -m src.demo_entrega

# Ou submeta uma pergunta específica na demonstração:
uv run python -m src.demo_entrega "Como a fibra solúvel da aveia age para reduzir o colesterol LDL e a glicemia?"
```

### 4. Rodar a suíte de testes automatizados
```bash
uv run pytest -v
```

### 5. Executar o Benchmark (16 questões) e Estudo de Ablação
```bash
# Estudo de Ablação rápido (Passo 1 vs. Passo 2 vs. Passo 3):
uv run python -m src.evaluation.run_benchmark --no-ollama --ablation

# Benchmark completo com LLM (Ollama local por padrão):
uv run python -m src.evaluation.run_benchmark
```

### 6. Fazer uma consulta via CLI ou API FastAPI
```bash
# Consulta via CLI (exibe Chunks Recuperados, Síntese, Grafo, TACO e Citações):
uv run python -m src.api "Como a fibra solúvel da aveia age para reduzir o colesterol LDL e a glicemia?"

# Subir servidor FastAPI (Swagger em http://localhost:8000/docs):
uv run uvicorn src.api:app --reload
```
