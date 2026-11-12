# Ablação do ranking — critérios definidos antes da execução (issue #35)

Registrado em 10/11/2026, antes de rodar qualquer variante. Resultados e decisão: [`ablacao_mrr_issue35.md`](ablacao_mrr_issue35.md).

## Pergunta

Por que a fonte esperada nem sempre aparece em 1º lugar (MRR 0,750), e alguma das três hipóteses da issue explica a queda?

## Conjunto e limitações conhecidas antes da execução

- Golden set: `data/benchmark/eval_questions.json` (16 perguntas; 12 com fonte esperada no corpus aprovado).
- As 12 perguntas avaliadas esperam a **mesma fonte**: o Guia Alimentar (2014). O MRR mede, na prática, se o Guia vem em 1º lugar. Um ajuste que favoreça o Guia melhora a métrica sem demonstrar melhora da busca.
- `eval/golden/test/nutricao_holdout_questions.json` é idêntico byte a byte ao conjunto de desenvolvimento. **Não há conjunto independente**: todo resultado aqui é medido dentro da amostra usada para escolher a variante.
- Por isso, nenhum resultado desta ablação é tratado como evidência de melhora geral. Ganhos são **hipóteses** a confirmar em um conjunto novo (#13).

## Variantes (fixadas antes da execução)

| Id | Variante | Hipótese da issue |
|---|---|---|
| A0 | Configuração atual (RRF 0,55/0,45; sobreposição 0,25; bônus de evidência) | referência |
| A1 | Sem bônus de evidência | H1 |
| A2 | Sem sobreposição de termos | H1 |
| A3 | Sem bônus e sem sobreposição (RRF puro) | H1 |
| A4 | RRF com pesos iguais (0,5/0,5) | pesos do RRF |
| A5 | Só BM25 | pesos do RRF |
| A6 | Só a busca densa | pesos do RRF |
| A7 | Busca densa só com ChromaDB (sem TF-IDF/LSA) | H3 |
| A8 | A7 sem bônus e sem sobreposição | H1 + H3 |

Todas usam o mesmo índice, as mesmas 16 perguntas, `top_k = 4`, no máximo 2 Trechos por documento, síntese extrativa sem LLM e só fontes aprovadas.

## Métricas

- Recall@4, MRR, cobertura de palavras-chave e acurácia do guardrail, gerais e por categoria, com a mesma régua do `run_benchmark.py`.
- **MRR alternativo (H2)**, apenas informativo: aceita o Fascículo 1 como equivalente ao Guia. Ele **não substitui** a régua oficial; mudar a régua é decisão da equipe.
- RR por pergunta, para mostrar quais perguntas mudam.

## Critério para uma variante ser candidata

Todos ao mesmo tempo, contra A0:

1. MRR oficial > 0,750;
2. Recall@4 ≥ 0,9167;
3. Guardrail legal = 1,0;
4. Cobertura de palavras-chave sem queda maior que 5 p.p.

Ser candidata não basta para virar padrão: a mudança precisa ter justificativa independente da métrica (não pode ser só "favorece o Guia"), e a decisão fica registrada como proposta técnica até haver conjunto independente.

Resultados desfavoráveis (nenhuma variante candidata, ou ganho só no MRR alternativo) são registrados como estão.

## Adendo de 10/11/2026: benchmark v2 (#40)

Registrado depois da primeira execução no v1 e **antes** da execução final no v2.

### O que já tinha sido visto antes deste adendo (transparência)

- Os números das 9 variantes no v1 (seção acima).
- Na revisão do PR #40, o resultado de A3 no v2 completo (dev e test), com 5 Trechos não julgados.
- Uma execução das 9 variantes no v2 (dev e test) com **22 Trechos não julgados**, contados como irrelevantes. Ela serviu para listar os Trechos a julgar.

Os 22 Trechos foram julgados pelo conteúdo, com a mesma escala do #40 (2 responde, 1 em parte, 0 não responde), sem olhar qual variante os trazia: 16 com nota 0, 5 com nota 1 e 1 com nota 2. Ficam registrados em `eval/golden/v2/{dev,test}.json`, no campo `pool` de cada caso, como pendentes de revisão humana.

O test do v2 **não é mais um holdout cego** para esta escolha: seus números de A3 já foram vistos. Ele continua útil para detectar regressão grande, não para confirmar um ganho pequeno.

### Regra de decisão (fixada antes da execução final)

1. **Escolha pelo v2 dev**, com todos os Trechos do top-4 julgados (`nao_julgados = 0` em todas as variantes; se não, julgar antes e repetir):
   - métrica principal: `mrr_trecho`; desempate por `ndcg_trecho_at_k`;
   - sem queda frente a A0 em `acerto_trecho_at_k` e `acerto_completo_at_k`, nem queda maior que 5 p.p. em `cobertura_termos`; `guardrail_acuracia` igual.
2. **Conferência no v2 test**: a variante escolhida não pode cair mais que 5 p.p. frente a A0 em `mrr_trecho` nem em `acerto_trecho_at_k`.
3. **Gate do CI (v1)**: precisa cumprir os quatro critérios da seção anterior (MRR > 0,750, recall@4 ≥ 0,9167, guardrail 1,0, termos sem queda > 5 p.p.).
4. **Justificativa independente da métrica** e, entre variantes equivalentes (diferença de MRR no dev menor que 1/18, ou seja, menos de uma pergunta), a **mais simples** (menos componentes).
5. Se nenhuma variante cumprir 1 a 3, o padrão não muda e o resultado é registrado como negativo.
