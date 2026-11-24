# Camada semântica do detector de risco: critérios (issue #48)

Registrado em 13/11/2026, **antes** de rodar qualquer modelo.

## Pergunta

Um LLM local, consultado só quando o léxico não aciona, leva o detector de risco ao RF-IA03 (recall ≥ 0,95 e precisão ≥ 0,60) em frases que não orientaram as regras, sem acionar em perguntas comuns e dentro do RNF29 (p95 ≤ 3 s)?

## Decisões já tomadas

- **Execução local, no Ollama.** A mensagem analisada é a de alguém possivelmente em crise, o dado mais sensível do app. Enviá-la à Groq contraria o ADR 0003 enquanto o contrato não for confirmado.
- **O léxico continua como piso.** O LLM só é consultado quando o léxico não aciona; ele pode acrescentar detecções, nunca removê-las.
- **Falha fechada para o léxico.** Se o Ollama estiver fora, o modelo ausente ou a chamada passar do tempo limite, vale só o léxico, e a falha é registrada na resposta.

## Candidatos (fixados antes da execução)

| Id | Modelo | Como classifica |
|---|---|---|
| M1 | `llama-guard3:1b` | Classificador de segurança da Meta, categoria S11 (suicídio e autolesão, inclusive transtorno alimentar), sem política nossa |
| M2 | `llama-guard3:8b` | Mesmo, modelo maior |
| M3 | `qwen2.5:7b` | Modelo de geração do projeto, com uma política escrita a partir das definições das três categorias do RF-IA03 |

Todos com temperatura 0, no mesmo computador (Apple M4, 24 GB).

## Conjuntos

| Conjunto | Uso |
|---|---|
| `eval/risco/casos.json` (110 positivos, 84 negativos difíceis) | **Desenvolvimento**: escolher o modelo e ajustar a política |
| Perguntas comuns: benchmark v1 (16), golden v2 (42) e respondíveis de `eval/abstencao/casos.json` | **Falsos positivos em uso normal**: o LLM roda em toda pergunta que o léxico não marcou |
| `eval/risco/holdout.json` (lote 3: 30 positivos, 25 negativos) | **Uma medição só**, no fim, sem ajustar nada depois dela |

## Conflito de autoria (registrado antes)

O lote 3 foi escrito por MatheusSales2773 (com Claude), que também escreve a política do M3. Para reduzir o viés:

- a política é escrita a partir das definições das categorias, **sem frases de exemplo** de nenhum conjunto;
- nada é ajustado depois da medição no holdout;
- o número no holdout vale como **indicação, não como confirmação**. A confirmação exige um lote novo, cego, escrito por outra pessoa da equipe, sem ver a política.

## Critério para um candidato ser escolhido

No desenvolvimento, com o léxico + o LLM:

1. recall ≥ 0,95 e precisão ≥ 0,60;
2. falsos positivos nas perguntas comuns ≤ 2% (no máximo 2 em cerca de 100);
3. p95 da chamada ao LLM ≤ 3 s, medido na máquina acima.

Entre os que cumprem, vence o de **menor latência**; o empate vai para o menor modelo. Se nenhum cumprir, o padrão não muda (só o léxico), e o resultado é registrado como negativo.

## O que fica fora deste PR

- **Medição no CI:** o CI não tem Ollama. Lá, os testes usam um classificador simulado (falha, tempo limite, ordem das camadas), e o gate continua medindo só o léxico. O número do LLM fica num relatório versionado, gerado localmente.
- **RF-IA04:** o recall por modalidade (áudio, foto, PDF) fica para quando essas entradas existirem.

## Adendo (13/11/2026), antes de ver o desempenho do LLM sozinho

A primeira execução no desenvolvimento deu recall 1,000 para M1 e M2 com léxico + LLM, mas isso não mede o LLM: o léxico já detecta os 110 positivos do desenvolvimento, porque foi escrito a partir deles. O LLM não chegou a ser consultado em nenhum positivo.

Por isso, o critério 1 passa a valer para o **LLM sozinho** (sem o léxico) no desenvolvimento: recall ≥ 0,95 e precisão ≥ 0,60. Os critérios 2 e 3 (perguntas comuns e latência) continuam com léxico + LLM, como no fluxo real. Já visto antes deste adendo: com léxico + LLM, M1 teve 1/151 perguntas comuns marcadas (p95 0,25 s) e M2, 2/151 (p95 0,85 s).

## Adendo 2 (13/11/2026): nota de preocupação, antes de rodar

A primeira versão teve precisão 1,000 e recall 0,733 no holdout. Como o RF-IA03 exige só precisão ≥ 0,60, há margem para trocar alarmes falsos por recall. Mudança: em vez de "risco sim ou não", o modelo devolve um **nível de preocupação de 0 a 10**, e o alerta dispara a partir de um limiar.

**Como o limiar é escolhido, só com o desenvolvimento e as perguntas comuns:**

1. Rodar uma vez, guardando o nível de cada frase.
2. Para cada limiar de 1 a 10, calcular, com léxico + LLM: falsos positivos nas 151 perguntas comuns e, com o LLM sozinho, recall e precisão no desenvolvimento.
3. Escolher o **menor limiar** com no máximo 2% de perguntas comuns marcadas (até 3 de 151) e precisão ≥ 0,60 no desenvolvimento. O menor limiar é o que mais favorece o recall.
4. Medir o holdout uma vez, nesse limiar.

**Transparência:** é a **segunda** medição do mesmo holdout (a primeira foi a versão sim/não). O limiar não olha o holdout, mas o resultado continua valendo como indicação. A confirmação segue dependendo de um lote cego novo, escrito por outra pessoa.

## Adendo 3 (13/11/2026): menos alarmes falsos, antes de rodar

Pedido da equipe: reduzir alarmes falsos. No limiar 1, a versão 2 marcou 22 dos 84 negativos do desenvolvimento, quase todos com nível 3 ou 4. São expressões do dia a dia com palavras fortes ("matar", "sumir", "acabar") aplicadas a comida, treino, trabalho ou provas; metas de cortar um alimento; cansaço da dieta; um acidente doméstico. Já 16 dos 110 positivos também ficam em 3 ou 4, então só subir o limiar custaria recall (no limiar 5, 0,855).

**Mudança na política:** regras gerais tiradas desses erros do **desenvolvimento**, sem frases literais de nenhum conjunto e sem nada do holdout.

**Regra do limiar (substitui a do adendo 2 para esta versão):** o limiar com a **maior precisão do LLM sozinho no desenvolvimento** entre os que mantêm recall do LLM sozinho ≥ 0,95 no desenvolvimento e até 2% de perguntas comuns marcadas. Empate vai para o menor limiar.

**Transparência:** a política passa a ser ajustada nos negativos do desenvolvimento, então a precisão ali fica otimista. O holdout será medido pela **terceira** vez; o resultado é só indicação. A confirmação continua dependendo de um lote cego novo, escrito por outra pessoa.

## Adendo 4 (21/11/2026): lote 4 cego, antes de o lote existir

O lote 3 já foi medido três vezes e tem o mesmo autor da política, então não comprova o RF-IA03. A configuração adotada (`gemma4:e4b`, política da versão 3, limiar 1, decisões de 17/11 e 20/11) nunca foi medida num conjunto de validação. Este adendo fixa como medi-la num lote novo.

- **Autor do lote:** o ChatGPT, numa conversa nova, recebendo só o texto de [`lote4_pedido.md`](lote4_pedido.md). Ele não vê a política, o léxico, o desenvolvimento nem o holdout. **Ressalva registrada:** o RF-IA03 e a #48 pedem um lote escrito por outra **pessoa**. Um lote escrito por um LLM é cego em relação à política, mas as frases tendem a ser mais típicas que as de um usuário real. O resultado vale como validação por autor independente, não como avaliação humana.
- **Sem edição:** o lote entra como o autor devolver, em `eval/risco/lote4_cego.json`. Os rótulos são os do autor. Se uma frase parecer mal rotulada, isso é registrado no resultado, sem trocar o rótulo nem tirar a frase.
- **Configuração congelada:** o código da `main` no momento da medição, com `--modelo gemma4:e4b --limiar 1`. Nada é ajustado antes da medição.
- **Uma medição:** `uv run python -m src.evaluation.risco_llm --modelo gemma4:e4b --limiar 1 --lote eval/risco/lote4_cego.json`, rodada uma vez.
- **Critérios (RF-IA03 e RNF29), com léxico + LLM, como no fluxo real:** recall ≥ 0,95, precisão ≥ 0,60 e p95 da chamada ao LLM ≤ 3 s. Também são registrados o recall por categoria, o LLM sozinho e as falhas.
- **Depois:** o resultado é registrado em `llm_resultados.md`, passe ou não. Se a política ou o limiar mudarem depois disso, o lote 4 deixa de ser cego e vai para o desenvolvimento.
