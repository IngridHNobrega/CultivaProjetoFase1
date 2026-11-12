# Ablação do ranking (issue #35): resultados e decisão

Executada em 10/11/2026. Os critérios foram registrados antes, em [`ablacao_mrr_issue35_criterios.md`](ablacao_mrr_issue35_criterios.md); os números completos, inclusive o RR por pergunta, estão em [`ablacao_mrr_issue35.json`](ablacao_mrr_issue35.json).

Reproduzir:

```bash
uv run python -m src.evaluation.ablacao_ranking
```

Condições: mesmo índice ChromaDB para todas as variantes, `top_k = 4`, no máximo 2 Trechos por documento, síntese extrativa sem LLM, só fontes aprovadas. A0 é a configuração anterior à #35, fixada no script para a comparação continuar reproduzível.

## Diagnóstico

A nota final de cada Trecho era `RRF + 0,25 × sobreposição de termos + bônus de evidência`. Nas 16 perguntas do v1, olhando os 10 primeiros candidatos:

| Parcela | Mediana | Máximo |
|---|---:|---:|
| Fusão RRF (BM25 + densa) | 0,0085 | 0,0164 |
| Sobreposição de termos × 0,25 | 0,0929 | 0,2321 |
| Bônus de evidência | 0,02 a 0,06 | 0,08 |

A sobreposição valia, em mediana, **cerca de 11 vezes** a fusão. Por isso A0, A4 (pesos 0,5/0,5) e A5 (só BM25) deram resultados idênticos no v1: os pesos do RRF não alteravam o ranking, que era decidido pela contagem de termos em comum. Esse é o motivo da mudança, e ele não depende da métrica: a busca híbrida não estava sendo usada de fato.

## Resultados

### Benchmark v1 (régua do gate do CI; 12 perguntas avaliadas, todas esperam o Guia)

| Id | Variante | Recall@4 | MRR | MRR* | Termos | Guardrail |
|---|---|---:|---:|---:|---:|---:|
| A0 | Configuração anterior | 0,9167 | 0,7500 | 0,8333 | 0,8812 | 1,0 |
| A1 | Sem bônus de evidência | 0,9167 | 0,7500 | 0,8333 | 0,8812 | 1,0 |
| A2 | Sem sobreposição | 0,9167 | 0,7778 | 0,8194 | 0,9250 | 1,0 |
| A3 | RRF puro | 0,9167 | 0,7778 | 0,8194 | 0,9250 | 1,0 |
| A4 | RRF 0,5/0,5 | 0,9167 | 0,7500 | 0,8333 | 0,8812 | 1,0 |
| A5 | Só BM25 | 0,9167 | 0,7500 | 0,8333 | 0,8812 | 1,0 |
| A6 | Só densa | 0,9167 | 0,7917 | 0,8750 | 0,8812 | 1,0 |
| A7 | Densa só ChromaDB | 0,9167 | 0,7500 | 0,8333 | 0,8812 | 1,0 |
| **A8** | **Densa só ChromaDB + RRF puro** | **0,9167** | **0,7778** | 0,8194 | **0,9250** | **1,0** |

MRR* aceita o Fascículo 1 como equivalente ao Guia. É só informativo: a régua não mudou.

### Benchmark v2 (dev para escolher, test para conferir; todos os Trechos do top-4 julgados)

| Id | Split | Trecho@4 | Completo@4 | MRR | nDCG | Termos | Guardrail |
|---|---|---:|---:|---:|---:|---:|---:|
| A0 | dev | 0,889 | 0,611 | 0,662 | 0,418 | 0,735 | 0,852 |
| A1 | dev | 0,944 | 0,667 | 0,676 | 0,446 | 0,765 | 0,852 |
| A2 | dev | 0,944 | 0,611 | 0,722 | 0,440 | 0,735 | 0,852 |
| A3 | dev | 1,000 | 0,667 | 0,727 | 0,464 | 0,735 | 0,852 |
| A4 | dev | 0,889 | 0,611 | 0,662 | 0,413 | 0,735 | 0,852 |
| A5 | dev | 0,889 | 0,667 | 0,648 | 0,397 | 0,706 | 0,852 |
| A6 | dev | 0,889 | 0,722 | 0,607 | 0,420 | 0,794 | 0,852 |
| A7 | dev | 0,889 | 0,556 | 0,685 | 0,389 | 0,765 | 0,852 |
| **A8** | **dev** | **0,944** | **0,667** | **0,732** | **0,457** | **0,706** | **0,852** |
| A0 | test | 1,000 | 0,750 | 0,917 | 0,519 | 0,875 | 1,000 |
| A3 | test | 1,000 | 0,750 | 0,938 | 0,491 | 0,875 | 1,000 |
| **A8** | **test** | **1,000** | **0,750** | **1,000** | **0,479** | **0,875** | **1,000** |

O guardrail é igual em todas as variantes: ele não depende do ranking (as falhas de prescrição estão na #39).

## Decisão

Pela regra registrada antes da execução final: A8, A3 e A2 cumprem as restrições no dev e ficam a menos de uma pergunta de distância (0,732, 0,727 e 0,722; uma pergunta vale 0,056). Entre equivalentes, a regra escolhe a mais simples: **A8**, que desliga a sobreposição, o bônus de evidência e a mistura com TF-IDF/LSA. Ela passa na conferência do test (MRR 1,000 contra 0,917 de A0) e nos critérios do gate v1.

Configuração padrão nova (`src/config.py`, sobrescrevível por variável de ambiente):

| Parâmetro | Antes | Agora |
|---|---|---|
| `MODO_DENSO` | `chromadb_dense` (ChromaDB 55% + TF-IDF/LSA 45%) | `chromadb_pure` |
| `RERANK_PESO_SOBREPOSICAO` | 0,25 | 0,0 |
| `RERANK_BONUS_EVIDENCIA` | ligado | desligado |

O código do reranker e do TF-IDF/LSA continua no `HybridRetriever`, para reproduzir A0 e comparar. Removê-lo de vez pode ficar para a #15.

## Resultados desfavoráveis

- **O ganho é pequeno.** No v1, só 3 das 12 perguntas mudam: Q03 e Q06 sobem de 0,5 para 1,0; Q15 cai de 1,0 para 0,33. Em MRR de categoria, `multi_hop_and_composition_gap` cai de 0,600 para 0,567.
- **No v2 dev, 4 casos pioram**, contra 9 que melhoram: V2-REC-08 (1,0 → 0,25), V2-REC-17 (1,0 → 0,33), V2-ADV-04 (1,0 → 0,33) e V2-REC-20 (0,5 → 0, sai do top-4).
- **A cobertura de termos do v2 cai** 2,9 p.p. no dev (0,735 → 0,706) e 2 p.p. no total (78,0% → 76,0%), dentro da tolerância de 5 p.p. Ela subiu no v1 (0,881 → 0,925).
- **O nDCG do test cai** de 0,519 para 0,479, embora o MRR suba.

## Limitações

- **Amostras pequenas:** 12 perguntas no v1, 18 casos de recuperação no dev e 8 no test do v2. Uma pergunta muda o MRR em 5 a 12 p.p.
- **O test do v2 não é mais cego** para esta escolha: os números de A3 foram vistos na revisão do #40, antes da regra final. O ganho é **hipótese**, não resultado confirmado.
- **Julgamentos novos sem revisão humana:** 22 Trechos foram julgados nesta issue (16 nota 0, 5 nota 1, 1 nota 2), registrados no campo `pool` de cada caso. Como Trecho não julgado conta como irrelevante, sem eles as variantes novas seriam penalizadas.
- **Revisão do PR #42:** a nota de `santos-barreiras-frutas-verduras-csc-2019-p008-02` em V2-REC-20 subiu de 1 para 2. Isso muda só o nDCG do dev das variantes A0 a A7 (e o acerto completo de A6); A8 e a decisão não mudam. A tabela acima já tem os valores novos.
- **O v1 ainda é a régua do gate**, e as 12 perguntas avaliadas esperam só o Guia. A troca do gate para o v2 segue pendente.

## Decisão sobre o Fascículo 1

Em 10/11/2026 o grupo aprovou, sem objeções, a proposta de **não** tratar o Fascículo 1 como equivalente ao Guia no v1: a equivalência por conteúdo já é tratada no v2, que deve substituir o v1 no gate. Registro e motivo em [`data/benchmark/README.md`](../../data/benchmark/README.md).

## Pendências

- Revisar os 22 julgamentos novos.
- Confirmar o ganho num conjunto novo, que não tenha sido visto.
