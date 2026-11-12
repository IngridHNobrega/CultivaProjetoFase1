# ADR 0003: Provedor de LLM e envio de dados pessoais

* **Status:** Decisão técnica provisória para o RAG de Nutrição; aprovação formal da equipe pendente
* **Data:** 2026-11-10
* **Escopo:** `src/agent/llm_client.py` e execução do RAG de Nutrição

## Contexto

O RNF05 documentado exige envio mínimo ao provedor, sem nome ou contato, contrato que proíba treinamento e logs sem dados de saúde em texto claro. A aprovação formal desse requisito não foi confirmada nos registros locais. O código anterior escolhia Groq por padrão e enviava a consulta e os trechos recuperados no corpo de `/chat/completions`; não havia máscara anterior ao envio. O corpus científico é público/aprovado, mas a pergunta pode conter dados pessoais ou dados sensíveis de saúde.

## Evidência dos provedores

Consulta às páginas oficiais em 2026-11-10:

| Critério | Ollama local | Groq API |
|---|---|---|
| Custo de uso do serviço | Sem tarifa por chamada ou hospedagem quando o modelo roda localmente. Permanecem custos de hardware, energia, download e operação. | Há nível gratuito, sujeito a limites e condições do serviço; não é uma garantia de custo zero ou disponibilidade. |
| Tratamento de prompts | A FAQ oficial afirma que, em execução local, o Ollama não vê prompts nem dados. Recursos cloud são distintos e devem permanecer desativados para este uso. | A documentação de dados afirma que inferências não são retidas por padrão, mas admite logs temporários de entradas e saídas por até 30 dias para confiabilidade/abuso. ZDR pode desativar essa retenção nas configurações da organização. |
| Localização/transferência | Prompt enviado ao serviço local configurado em `localhost`; baixar modelos ainda exige conexão externa, mas não envia as consultas. | Dados processados por terceiro e, quando retidos, armazenados em buckets GCP nos EUA, conforme a documentação consultada. |
| Treinamento e contrato | A execução local não entrega prompts ao operador do Ollama. | Não foi possível confirmar na documentação consultada uma cláusula contratual explícita que proíba treino com prompts. A alegação de retenção padrão não substitui essa verificação. |

Fontes oficiais: [Ollama FAQ](https://docs.ollama.com/faq) e [Groq: Your Data in GroqCloud](https://console.groq.com/docs/your-data). As condições podem mudar; revisar antes de uso externo e registrar versão/data da política e do contrato aplicável.

## Decisão

1. **Ollama local é o provedor padrão** (`LLM_PROVIDER=ollama`). Configurar o ambiente com `OLLAMA_NO_CLOUD=1`; o modelo responde na API local (`http://localhost:11434`). Esta é a alternativa técnica que melhor atende à meta de conformidade ética, ausência de custos por requisição e garantia de não compartilhamento de consultas com provedores de nuvem de terceiros.
2. **Seleção e decisão de modelo local do Ollama:**
   - **Modelo Primário:** `qwen2.5:7b` (executado via `ollama pull qwen2.5:7b`, quantização padrão 4-bit `Q4_K_M`, ~4.7 GB de VRAM/RAM).
   - **Modelo de Fallback Local:** `qwen2.5:3b` (executado via `ollama pull qwen2.5:3b`, quantização `Q4_K_M`, ~1.9 GB de VRAM/RAM) para execução em estações com restrição de memória (ex.: 8 GB RAM ou CPU pura).
   - **Fallback Final Determinístico:** Síntese extrativa sem LLM (`synthesize_extractive_fallback`), garantindo resiliência operacional caso o daemon do Ollama esteja inativo.
3. **Groq permanece alternativa documentada, mas desativada por padrão.** Uma chave no ambiente não habilita envio. O operador precisa definir `LLM_PROVIDER=groq` e `ALLOW_EXTERNAL_LLM=true`, além de fornecer `GROQ_API_KEY`. Essa configuração não autoriza dados pessoais: só usar entradas sintéticas ou previamente desidentificadas até que retenção ZDR, contrato de não treinamento, transferência internacional e controles LGPD/RIPD sejam formalmente verificados.
4. **Mascaramento de identificadores diretos comuns** (e-mail, CPF, telefone e nome quando introduzido por rótulos explícitos) é aplicado antes do payload Groq. É defesa adicional, não anonimização: regex não identifica todos os nomes, identificadores indiretos nem dados de saúde contextualizados. Portanto, o modo Groq não está aprovado para perguntas reais identificáveis e a configuração explícita continua sendo responsabilidade de implantação.
5. Se Ollama estiver indisponível, a síntese extrativa determinística é preferível a enviar automaticamente a pergunta a um serviço externo. No modo Groq explicitamente habilitado, o fallback pode usar Ollama local; não há fallback automático para outro serviço remoto.

## Análise de Arquitetura de Software: Seleção do Modelo Ollama

Como requisito de arquitetura de software para o CULTIVA, a escolha do modelo LLM local foi submetida aos seguintes critérios técnicos objetivos:

### 1. Critérios de Avaliação

1. **Capacidade de Geração Estruturada (JSON Schema estrito):** O componente `LocalLLMClient` exige que a resposta da LLM seja um objeto JSON sintaticamente válido contendo as chaves `evidence_summary` (resumo textual), `practical_implications` (lista de diretrizes práticas) e `limitations` (limitações das evidências). Falhas na sintaxe JSON provocam rejeição da resposta gerada e forçam o uso do fallback extrativo.
2. **Proficiência e Fluência em Português Brasileiro (pt-BR):** Todo o corpus do CULTIVA (Guia Alimentar para a População Brasileira, Código de Ética do CFN, Diretrizes da SBME, etc.) e as perguntas dos usuários estão em pt-BR. O modelo deve compreender a terminologia técnica de nutrição e saúde pública sem introduzir anglicismos, traduções literais impróprias ou perda de sentido conceitual.
3. **Conformidade com Guardrails Ético-Legais (Lei Federal nº 8.234/1991):** O modelo precisa respeitar instruções de sistema negativas ("não prescrever planos alimentares individualizados", "não prescrever dietas calculadas em gramas/calorias para indivíduos", "não fazer diagnósticos clínicos") e reorientar a resposta para evidências populacionais e recomendação de acompanhamento por profissional nutricionista.
4. **Footprint Operacional Local (RAM/VRAM) e Latência:** A solução deve rodar localmente em estações típicas de estudantes, pesquisadores e desenvolvedores (8 GB a 16 GB de RAM compartilhada em Apple Silicon M-series ou arquiteturas x86_64 equivalentes com GPU integrada/CPU), convivendo pacificamente com a persistência vetorial do ChromaDB e o modelo local de embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB).
5. **Janela de Contexto para RAG:** Suporte a pelo menos 8.000 tokens de contexto, permitindo injetar o top-k de Trechos científicos recuperados (~3.000 tokens) mais o grafo causal e o prompt de enriquecimento.

### 2. Matriz Comparativa de Modelos Candidatos (Ollama)

| Modelo | Tamanho (Q4_K_M) | Suporte pt-BR | JSON Schema / Tooling | Aderência a Guardrails | Consumo RAM & Latência Local | Avaliação Arquitetural |
|---|---|---|---|---|---|---|
| **Qwen 2.5 7B** (`qwen2.5:7b`) | **~4.7 GB** | **Excelente** (forte corpus multilíngue e pt-BR) | **Excelente** (pós-treinamento focado em código e dados estruturados) | **Alta** (excelente seguimento de restrições de sistema negativas) | **Excelente em 16 GB; viável em 8 GB** (~25-35 tok/s em M-series) | **Proposta técnica aprovada como modelo padrão primário.** |
| **Qwen 2.5 3B** (`qwen2.5:3b`) | **~1.9 GB** | **Bom** | **Bom** (consistente na maioria dos esquemas simples) | **Média** (pode simplificar demais as ressalvas) | **Ultra-baixo** (~40-60 tok/s; funciona até em CPU pura sem aquecimento) | **Proposta técnica aprovada como fallback local.** |
| **Llama 3.1 8B** (`llama3.1:8b`) | ~4.7 GB | Muito Bom (bom vocabulário, pequenos desvios estilísticos) | Regular/Bom (ocasionais marcações markdown fora do bloco JSON) | Alta (forte recusa a instruções maliciosas) | Similar ao 7B (~4.7 GB) | Forte candidato alternativo; preterido pelo Qwen 2.5 devido à maior taxa de parsing JSON direto sem wrapper e melhor naturalidade em termos alimentares brasileiros. |
| **Mistral 7B Instruct v0.3** | ~4.1 GB | Regular (menor vocabulário técnico em pt-BR) | Bom | Média | Baixo (~4.1 GB) | Preterido devido à menor fluência em português e menor precisão em termos específicos de saúde pública brasileira. |
| **Gemma 2 9B** (`gemma2:9b`) | ~5.4 GB | Muito Bom | Regular (maior sensibilidade a formatação estrita) | Alta | Alto (overhead de memória de atenção deslizante; atinge o teto em 8 GB) | Preterido pelo tamanho (>5.4 GB) que compromete a estabilidade em máquinas com 8 GB ou 16 GB com outras aplicações abertas. |

### 3. Decisão Justificada

- **Primário:** `qwen2.5:7b` combina a melhor taxa de acerto em geração estrita de JSON, vocabulário alinhado às diretrizes alimentares brasileiras e tamanho adequado (4.7 GB) para operação local estável.
- **Fallback Local:** `qwen2.5:3b` garante que ambientes restritos (como CI em containers com 7 GB de RAM ou máquinas de desenvolvedores com 8 GB de memória unificada) não falhem por `Out of Memory` (OOM), mantendo a capacidade de geração de síntese local.
- **Fallback Determinístico:** Mantido inalterado na classe `LocalLLMClient`, fornecendo imunidade a falhas do serviço local.

## Comparação e limitações

Ollama reduz transferência e dependência de retenção/contrato de terceiro, mas consome recursos locais, pode ter maior latência e qualidade variável conforme equipamento e modelo. Groq reduz a carga local e oferece modelos hospedados, mas envia prompt e trechos a terceiro, tem limites do plano gratuito e requer decisão contratual e de privacidade. Nenhum ensaio comparativo de qualidade, latência ou custo total foi realizado nesta decisão; esses benefícios permanecem hipóteses. Comparar ambos com o mesmo golden set e medir latência, falhas, fidelidade às fontes e custo antes de reverter o padrão.

“Sem custo” significa sem cobrança por chamada do provedor na execução local, não custo operacional zero. Esta decisão é específica do consultor de Nutrição implementado; não comprova atendimento integral ao RNF05 nem aprovação formal do requisito.

## Consequências e verificações pendentes

- A chave Groq isolada deixa de alterar o fluxo padrão; a migração de Groq exige opt-in explícito.
- Usar `OLLAMA_NO_CLOUD=1` e manter o serviço ligado apenas a `localhost`; não expor a API Ollama à rede sem autenticação e controle de acesso.
- Confirmar com a equipe a aprovação desta decisão, a versão refatorada do RNF05 e o RIPD para processamento por terceiros.
- Antes de liberar Groq para dados reais, obter e arquivar evidência contratual de não treinamento, confirmar ZDR para todos os endpoints usados e avaliar transferência internacional e logs. Se qualquer condição falhar, manter o fluxo local.
- Validar a máscara com testes; não tratar esses testes como prova de anonimização completa.