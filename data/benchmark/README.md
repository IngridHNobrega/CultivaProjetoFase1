# Benchmark v1 de Nutrição

`eval_questions.json` tem as 16 perguntas do benchmark v1, usado hoje pelo gate do CI (`src/evaluation/run_benchmark.py`, `eval/baselines/benchmark_offline.json`). O benchmark v2, que avalia por Trecho e página, está em `eval/golden/v2/`.

| Arquivo | Conteúdo |
|---|---|
| `eval_questions.json` | Perguntas, ids esperados, palavras-chave e armadilhas de prescrição |
| `baseline_report.json` | Relatório da última execução (regravado pelo `run_benchmark.py`) |
| `benchmark_v2_report.json` | Relatório do benchmark v2 |

`eval/golden/dev/nutricao_eval_questions.json` e `eval/golden/test/nutricao_holdout_questions.json` são cópias idênticas de `eval_questions.json`: o "holdout" do v1 não é um conjunto independente.

## Como os ids esperados viram fontes

As perguntas foram escritas para o antigo `data/raw`. `mapear_esperados` (`run_benchmark.py`) converte cada id em fontes do corpus: `GUIA_MS_*` vira o Guia Alimentar (2014) inteiro, `PUBMED_<grupo>` vira os resumos do grupo, e os `DOC_*` sem procedência verificável ficam fora da média. Por isso as 12 perguntas avaliadas esperam só o Guia.

## Decisão: o Fascículo 1 não é equivalente ao Guia no v1

**Decisão (10/11/2026, issue #35):** nas perguntas que esperam o Guia, o v1 **não** aceita o Fascículo 1 (`protocolos-guia-alimentar-fasciculo1-2021`) como resposta equivalente. A régua do v1 não muda.

- **Proposta:** MatheusSales2773, na issue #35. **Aprovação:** grupo do projeto, sem objeções, em 10/11/2026.
- **Motivo:** a equivalência por conteúdo já é tratada no benchmark v2, que julga cada Trecho pelo que ele responde. Lá, Trechos do Fascículo recebem nota 1 ou 2 quando respondem (V2-REC-03, V2-REC-04, V2-REC-07, V2-REC-08 e V2-ADV-03). Como o v2 deve substituir o v1 no gate, mudar o mapeamento do v1 agora alteraria a régua sem ganho duradouro.
- **Efeito medido, só informativo:** com a equivalência, o MRR do v1 no ranking atual seria 0,819 em vez de 0,778 (`mrr_fasciculo_equivalente` em `eval/runs/ablacao_mrr_issue35.json`).
- **Quando revisar:** se o v1 continuar sendo o gate por muito tempo, ou se a equipe decidir que o Fascículo deve contar como fonte do Guia também fora do v2.
