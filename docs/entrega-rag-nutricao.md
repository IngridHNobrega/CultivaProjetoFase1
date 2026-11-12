# Entrega: RAG de Nutrição com base curada, banco vetorial e rastreabilidade de fontes

> **Estado das fontes.** O corpus tem 22 fontes catalogadas em [`corpus/manifest.yaml`](../corpus/manifest.yaml). Depois da revisão de aprovação ([`revisao-aprovacao-corpus.md`](../corpus/nutricao/relatorios/revisao-aprovacao-corpus.md), PR #31), **21 estão aprovadas** e só a SBAN segue `pendente`, por possível conflito de interesse. O índice padrão, a demonstração e o benchmark usam **só as fontes aprovadas**; as pendentes entram apenas com `CULTIVA_INCLUIR_PENDENTES=true` (ADR 0002, issue #7). A licença não é critério de aprovação: vale o aceite de risco para projeto acadêmico sem fins lucrativos ([`corpus/README.md`](../corpus/README.md)).

Os números deste documento foram gerados pelo sistema, não escritos à mão: `uv run python -m src.demo_entrega --salvar-artefatos` regrava os artefatos em [`entrega_semanal/`](../entrega_semanal/), e `uv run python -m src.evaluation.run_benchmark --no-ollama` regrava o benchmark.

## 1. Artefatos

### 1.1 Base de conhecimento curada (21 documentos-fonte indexados)

A base é o corpus de Nutrição: **22 documentos-fonte em PDF**, convertidos e divididos em 1873 Trechos. Entram no índice as **21 fontes aprovadas**, com **1818 Trechos** (mínimo exigido: 20 fontes). Cada fonte tem origem, versão e SHA-256 do PDF no manifesto, e o `verify_corpus.py` confere a cadeia de hashes no CI (job "Integridade do corpus").

Ficaram **fora** do índice:

- a SBAN (*Água, Hidratação e Saúde*, 55 Trechos), que segue `pendente`;
- as 10 "sínteses normativas" de `data/raw/guidelines/seed_guidelines.json`, que não têm origem verificável;
- a cópia do Guia Alimentar em `data/raw` (o Guia entra pelo corpus, com página e hash);
- os 31 resumos do PubMed, por estarem em inglês e serem só resumos. O pipeline já aceita esse tipo de fonte (`kind: resumo_pubmed`), e a reinclusão é a issue #28.

| # | Fonte (`fonte_id`) | Tipo | Ano | Trechos | Aprovação |
|---:|---|---|---:|---:|---|
| 1 | Posicionamento sobre o tratamento nutricional do sobrepeso e da obesid… (`abeso-posicionamento-tratamento-nutricional-obesidade-2022`) | diretriz | 2022 | 501 | aprovado |
| 2 | Guia alimentar para a população brasileira (`guia-alimentar-populacao-brasileira-2014`) | diretriz | 2014 | 339 | aprovado |
| 3 | Guia alimentar de dietas vegetarianas para adultos (`guia-dietas-vegetarianas-svb-2012`) | diretriz | 2012 | 165 | aprovado |
| 4 | Modificações dietéticas, reposição hídrica, suplementos alimentares e … (`sbme-modificacoes-dieteticas-suplementos-rbme-2009`) | diretriz | 2009 | 103 | aprovado |
| 5 | Fascículo 1: Protocolos de uso do Guia Alimentar para a população bras… (`protocolos-guia-alimentar-fasciculo1-2021`) | diretriz | 2021 | 87 | aprovado |
| 6 | Água, Hidratação e Saúde (`sban-agua-hidratacao-saude-2016`) | diretriz | 2016 | 55 | pendente (fora do índice) |
| 7 | Código de Ética e de Conduta do Nutricionista (Resolução CFN nº 599/20… (`cfn-codigo-etica-conduta-nutricionista-2018`) | norma | 2018 | 59 | aprovado |
| 8 | Effects of intermittent fasting on metabolism in men (`azevedo-jejum-intermitente-ramb-2013`) | revisao | 2013 | 38 | aprovado |
| 9 | Relação entre sono e obesidade: uma revisão da literatura (`crispim-sono-obesidade-abem-2007`) | revisao | 2007 | 32 | aprovado |
| 10 | Uma nova classificação de alimentos baseada na extensão e propósito do… (`monteiro-nova-classificacao-alimentos-csp-2010`) | revisao | 2010 | 53 | aprovado |
| 11 | Ingestão dietética e fatores associados ao consumo alimentar de univer… (`rossetti-universitarios-consumo-alimentar-san-2015`) | revisao | 2015 | 33 | aprovado |
| 12 | Depressão, ansiedade e estresse e o comportamento alimentar (`brisotto-depressao-ansiedade-estresse-rbtc-2022`) | estudo | 2022 | 43 | aprovado |
| 13 | Contribuições da psicologia e da nutrição para a mudança do comportame… (`franca-psicologia-nutricao-comportamento-alimentar-epsic-2012`) | estudo | 2012 | 39 | aprovado |
| 14 | Ansiedade, qualidade do sono e compulsão alimentar em adultos com sobr… (`fusco-ansiedade-sono-compulsao-reeusp-2020`) | estudo | 2020 | 43 | aprovado |
| 15 | Fatores associados ao consumo de frutas e hortaliças no Brasil, 2006 (`jaime-frutas-hortalicas-brasil-rsp-2009`) | estudo | 2009 | 32 | aprovado |
| 16 | Impacto de alimentos ultraprocessados sobre o teor de micronutrientes … (`louzada-ultraprocessados-micronutrientes-rsp-2015`) | estudo | 2015 | 37 | aprovado |
| 17 | Alimentos ultraprocessados e perfil nutricional da dieta no Brasil (`louzada-ultraprocessados-perfil-nutricional-rsp-2015`) | estudo | 2015 | 48 | aprovado |
| 18 | Participação crescente de produtos ultraprocessados na dieta brasileir… (`martins-ultraprocessados-rsp-2013`) | estudo | 2013 | 34 | aprovado |
| 19 | Conhecimento nutricional e suplementação alimentar por praticantes de … (`moreira-rodrigues-conhecimento-nutricional-suplementacao-2014`) | estudo | 2014 | 29 | aprovado |
| 20 | Perfil dos estudantes que cursam enfermagem: qualidade de vida, sono e… (`salvi-estudantes-enfermagem-sono-reben-2020`) | estudo | 2020 | 38 | aprovado |
| 21 | Barreiras percebidas para o consumo de frutas e de verduras ou legumes… (`santos-barreiras-frutas-verduras-csc-2019`) | estudo | 2019 | 41 | aprovado |
| 22 | Autopercepção do consumo alimentar e adesão aos Dez Passos para Alimen… (`souza-backes-universitarios-csc-2020`) | estudo | 2020 | 24 | aprovado |

Tipos de fonte (campo `source_type`, do qual o nível de evidência é derivado): diretriz e norma viram `GUIDELINE_CONSENSUS`, revisão vira `GRADE_B` e estudo vira `GRADE_C` (heurística do [ADR 0002](adrs/0002-contrato-corpus-retriever.md), a calibrar no benchmark).

### 1.2 Estratégia de chunking

1. **Conversão** (`corpus/scripts/convert_pdfs.py`): cada PDF vira Markdown com um marcador por página física e link para a página no original. Páginas sem texto passam por OCR, e cada conversão gera um relatório com cobertura lexical por página.
2. **Limpeza e divisão** (`corpus/scripts/prepare_rag.py`): remove marcadores, notas de conversão, cabeçalhos e rodapés repetidos, bibliografia, metadados editoriais e ligaturas quebradas. Divide em Trechos de **cerca de 1.000 caracteres (máximo de 1.400)**, cortando em fronteira de frase e **sem atravessar página nem seção**. Páginas que a revisão marcou como inconfiáveis (tabelas corrompidas) ficam fora (`skip_pages`).
3. **Contrato** ([`corpus/schemas/trecho.schema.json`](../corpus/schemas/trecho.schema.json) e ADR 0002): cada Trecho carrega `id` estável, fonte, página do PDF, seção, link, DOI, licença (só informativa) e status de aprovação. O CI valida todos os Trechos contra o esquema.
4. **Cabeçalho contextual na indexação** (`src/rag/contrato.py`): antes de indexar, cada Trecho recebe o cabeçalho `[Documento | Fonte (ano) | Domínio | Nível de evidência | Seção (pág.)]`, que entra no BM25 e no embedding.

A página e a seção nunca são misturadas entre Trechos. É isso que permite citar a página exata do PDF em cada resposta.

### 1.3 Estratégia de embeddings

- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, multilíngue, **384 dimensões**, vetores normalizados (L2) e similaridade por cosseno.
- **Execução local** (biblioteca `fastembed`, ONNX): nenhum texto sai da máquina, o que atende ao RNF05.
- **Busca híbrida** (`src/retrieval/hybrid_retriever.py`): BM25 léxico com sinônimos clínicos e similaridade densa do ChromaDB, fundidos por **Reciprocal Rank Fusion**, seguidos de diversificação (no máximo 2 Trechos por documento). Desde a issue #35, o reranker por sobreposição de termos e nível de evidência e a mistura com TF-IDF/LSA ficam desligados por padrão (`MODO_DENSO`, `RERANK_*` em `src/config.py`); ver `eval/runs/ablacao_mrr_issue35.md`.
- **Ainda não feito:** comparar pelo menos dois modelos em português no golden set (issue #15).

### 1.4 Banco vetorial

- **ChromaDB** persistente (`PersistentClient`) em `data/vector_store/chroma_db`, com índice **HNSW por cosseno**.
- **Parâmetros do HNSW:** `ef_construction` e `ef_search` em 200 (`src/config.py`). Com os padrões do ChromaDB, a busca aproximada perdia vizinhos e variava a cada carga do índice, o que quebrava o determinismo do benchmark no CI. Com 200, o top-24 das 16 perguntas coincide com a busca exata, e um teste (`tests/test_vector_store.py`) exige pelo menos 99% de coincidência e o mesmo resultado ao recarregar o índice.
- **Coleção versionada pelo conteúdo:** o nome da coleção leva a impressão digital do modelo e dos Trechos (`cultiva_nutricao_evidencias_7eea3ce9298a`), que inclui os parâmetros do HNSW. Se o corpus, o modelo ou o índice mudarem, uma coleção nova é criada, em vez de reaproveitar vetores antigos.
- **Metadados por vetor:** `fonte_id`, título, instituição, ano, nível de evidência, seção, página do PDF, link, DOI, licença e status de aprovação.
- **Total indexado:** 1818 vetores de 21 documentos-fonte (só fontes aprovadas).

## 2. Documentação

### 2.1 Pipeline de ingestão

```mermaid
flowchart LR
    M["corpus/manifest.yaml<br/>22 fontes: origem,<br/>SHA-256, source_type, aprovação"] --> C
    P["PDFs originais<br/>corpus/nutricao/originais"] --> C["convert_pdfs.py<br/>Markdown por página + OCR<br/>+ relatório de cobertura"]
    C --> V{"verify_corpus.py<br/>cadeia de hashes do PDF<br/>aos Trechos (CI)"}
    C --> R["prepare_rag.py<br/>limpeza + Trechos de ~1000 caracteres<br/>sem atravessar página nem seção"]
    R --> J["Trechos JSONL<br/>corpus/nutricao/rag<br/>(validados pelo JSON Schema no CI)"]
    J -.-> V
    J --> G{"Gate de aprovação<br/>só aprovado por padrão<br/>(21 de 22 fontes)"}
    G --> T["trecho_para_chunk<br/>cabeçalho contextual +<br/>nível de evidência pelo tipo"]
    T --> E["Embeddings multilíngues<br/>MiniLM-L12, 384d (local)"]
    E --> DB[("ChromaDB HNSW cosseno<br/>coleção por impressão digital")]
    T --> B[("Índice BM25")]
```

### 2.2 Arquitetura de consulta

```mermaid
flowchart TD
    Q["Consulta do usuário"] --> GE["Guardrail de entrada<br/>(Lei 8.234/1991: dieta, dose e diagnóstico<br/>são reenquadrados para evidência populacional)"]
    GE --> HR["Recuperação híbrida<br/>BM25 + ChromaDB + RRF<br/>+ diversificação"]
    DB[("ChromaDB")] --> HR
    B[("BM25")] --> HR
    HR --> K["Top-4 Trechos<br/>com fonte, página, link e status"]
    K --> S["Síntese fundamentada<br/>(Groq ou Ollama; sem LLM, síntese extrativa)<br/>+ Tabela TACO + Grafo causal"]
    S --> GS["Guardrail de saída<br/>(remove linguagem prescritiva)"]
    GS --> R["Resposta + citações rastreáveis<br/>(fonte, seção, página, link, aprovação)"]
```

O fluxo segue a arquitetura provisória da documentação do projeto, com duas diferenças registradas: o banco vetorial é ChromaDB em vez de pgvector, e o portão de risco (CVV 188) ainda não existe (issue #9).

## 3. Demonstração

```bash
uv run python -m src.demo_entrega                            # 3 consultas de exemplo
uv run python -m src.demo_entrega "Sua pergunta aqui"        # uma consulta própria
uv run python -m src.demo_entrega --salvar-artefatos         # regrava entrega_semanal/
```

Cada consulta mostra as quatro etapas pedidas: (A) a consulta submetida e o guardrail; (B) os Trechos recuperados com fonte, página e os scores de cada etapa da busca; (C) a resposta fundamentada; (D) as citações das fontes usadas. O log completo está em [`entrega_semanal/demonstracao/log_demonstracao_consultas.txt`](../entrega_semanal/demonstracao/log_demonstracao_consultas.txt), e as respostas estruturadas, em `resultado_consultas.json`.

Os artefatos foram gerados **sem LLM** (síntese extrativa local e determinística). Com uma chave da Groq no `.env` ou um Ollama local, a etapa C passa a ser gerada pelo modelo, sempre a partir dos mesmos Trechos.

| Caso | Consulta | O que mostra |
|---|---|---|
| 1 | Fibra solúvel da aveia, colesterol LDL e glicemia | Recuperação de evidência sobre fibras (posicionamento da ABESO, guias). |
| 2 | Quatro categorias de alimentos do Guia e ultraprocessados | Recuperação no Guia Alimentar e nos artigos de Martins e Louzada, com página. |
| 3 | Pedido de cardápio de 1.800 kcal para pré-diabetes | Guardrail legal: o pedido é reenquadrado, com o aviso da Lei 8.234/1991. |

### 3.1 Avaliação (benchmark offline)

`run_benchmark.py` sobre as 16 perguntas de `data/benchmark/eval_questions.json`, sem LLM e só com as fontes aprovadas (medido de novo em 10/11/2026, depois da mudança de ranking da #35; entre parênteses, o valor de 08/11/2026):

| Métrica | Valor |
|---|---|
| Recall@4 por fonte | 91.7% (em 12 das 16 perguntas) |
| MRR | 0.778 (0.750) |
| Cobertura de termos esperados | 92.5% (88.1%) |
| Acurácia do guardrail legal | 100% |

- As perguntas foram escritas para o `data/raw`. Os ids esperados foram mapeados para as fontes do corpus (Guia por capítulo vira o Guia inteiro). As 4 perguntas que dependiam só do `seed_guidelines` ou do PubMed ficaram fora da média de recall, e o relatório as lista.
- O recall agora é por fonte e não por capítulo, então os números **não são comparáveis** aos da versão anterior (93,8% com 47 fontes).
- Tirar a SBAN do índice não mudou as métricas: ela aparecia em três perguntas (Q08, Q13 e Q16), mas em nenhuma era a fonte esperada, e as fontes que entraram no lugar também não eram.
- O MRR de 0,778 é o baseline do CI (`eval/baselines/benchmark_offline.json`). A ablação da #35 mostrou que o reranker por sobreposição de termos pesava cerca de 10 vezes a fusão RRF e decidia o ranking sozinho; com RRF puro sobre BM25 + ChromaDB, o MRR subiu de 0,750 para 0,778 (2 perguntas melhoram, 1 piora). No benchmark v2, o MRR por Trecho foi de 0,740 para 0,814. Os ganhos foram medidos em conjuntos pequenos e são hipótese a confirmar.
- O conjunto é pequeno e tem só 3 armadilhas de prescrição. O benchmark v2 é a issue #13.

## 4. Limitações conhecidas

- **Reranker e idioma:** o bônus por sobreposição de termos favorecia Trechos em português e foi um dos motivos para deixar o PubMed (em inglês) fora desta entrega. Ele foi desligado na #35; a reavaliação do PubMed segue na #28.
- **Aprovação das fontes:** 21 de 22 aprovadas (PR #31), por revisão com amostra de páginas e conferência numérica das tabelas, feita com apoio de IA. A SBAN segue pendente por possível conflito de interesse (material com marca da Nestlé). SVB e CFN foram aprovados com ressalva (`data_quality_note`).
- **Código de Ética do CFN:** a versão de 2018 provavelmente foi revogada pela Resolução CFN 856/2026, ainda sem texto oficial localizado.
- **Extração:** há defeitos conhecidos (versaletes do Guia, uma página do Crispim) nas issues #26 e #27.

## 5. Relação com as issues

| Issue | Situação |
|---|---|
| #4 Integrar os JSONL do corpus | Feita: `src/rag/corpus_loader.py` carrega os Trechos pelo contrato do ADR 0002. |
| #7 Filtrar por fonte aprovada | Feita: gate no momento de montar o índice. Demonstração e benchmark usam só fontes aprovadas; `CULTIVA_INCLUIR_PENDENTES=true` inclui as pendentes. |
| #15 Embeddings e banco vetorial | Parcial: modelo multilíngue local e ChromaDB. Falta comparar modelos em português. |
| #11 Rastreabilidade | Parcial: citações com página, link, DOI e status. A impressão digital da coleção é um primeiro passo para o `corpus_version`. |
| #13 Benchmark v2 | Parcial: ids esperados mapeados para as fontes do corpus. O conjunto continua o mesmo. |
| #28 PubMed e TACO no corpus | Decidido para esta entrega: PubMed fora. O suporte a resumos no pipeline está pronto. |
