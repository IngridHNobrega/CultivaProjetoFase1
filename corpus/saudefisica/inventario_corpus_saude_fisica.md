# Inventário do Corpus Documental de Saúde Física — CULTIVA Move

> **Contexto:** Este inventário cataloga todas as fontes científicas e institucionais que compõem o corpus documental de **Saúde Física** do projeto **CULTIVA Move**.
> As 8 fontes prioritárias com original e transcrição obtidos foram aprovadas (`approval_status: aprovado`) e **não estão integradas ao pipeline RAG da aplicação**, respeitando estritamente a separação arquitetural do projeto.

---

## 1. Visão Geral do Corpus

- **Total de fontes catalogadas:** 26 fontes avaliadas (11 pré-existentes + 15 novas candidatas).
- **Documentos obtidos e convertidos com sucesso para Markdown:** 19 fontes (8 pré-existentes com derivados + 11 novas convertidas + 1 derivação documental de infográfico).
- **Documentos com texto integral indisponível / acesso restrito (paywall / bot protection):** 6 fontes (ACSM 2026, ACSM 2015, ACC 2026, CDC Adult Overview, CDC Extreme Heat, Age & Ageing Falls 2022).
- **Documentos com erro no repositório institucional de origem:** 1 fonte (Lume UFRGS - HTTP 500 / Timeout).
- **Diretório raiz dos originais:** [`corpus/saudefisica/originais/`](file:///c:/Users/gomxssz/Documents/GITHUB/CultivaProjetoFase1/corpus/saudefisica/originais/)
- **Diretório raiz das transcrições Markdown:** [`corpus/saudefisica/markdown/`](file:///c:/Users/gomxssz/Documents/GITHUB/CultivaProjetoFase1/corpus/saudefisica/markdown/)
- **Diretório raiz dos relatórios técnicos auditáveis:** [`corpus/saudefisica/relatorios/`](file:///c:/Users/gomxssz/Documents/GITHUB/CultivaProjetoFase1/corpus/saudefisica/relatorios/)

---

## 2. Tabela de Fontes Documentais

| ID | Título da Fonte | Instituição / Autores | Categoria | Ano | Idioma | Formato Orig. | Status Obtenção | Status Conversão | Escopo |
|---|---|---|---|---|---|---|---|---|---|
| `guia-atividade-fisica-brasil-2021` | Guia de Atividade Física para a População Brasileira | Ministério da Saúde | D — Fundamentação BR | 2021 | pt-BR | PDF (52 p.) | Obtido | Concluída | Integral |
| `who-diretrizes-atividade-fisica-sedentarismo-2020` | WHO Guidelines on Physical Activity and Sedentary Behaviour | World Health Organization | A — Saúde Geral | 2020 | en | PDF (104 p.) | Obtido | Concluída | Integral |
| `who-physical-activity-factsheet-2024` | Physical Activity Fact Sheet | World Health Organization | A — Saúde Geral | 2024 | en | HTML | Obtido | Concluída | Resumo |
| `acsm-resistance-training-position-stand-2026` | Resistance Training Prescription for Muscle Function, Hypertrophy, and Physical Performance | ACSM | B — Exercícios | 2026 | en | PDF / HTML | Indisponível (Bot Block) | Não convertida | - |
| `acsm-exercise-preparticipation-screening-2015` | Updating ACSM's Recommendations for Exercise Preparticipation Health Screening | ACSM | B — Exercícios | 2015 | en | PDF | Indisponível (Paywall) | Não convertida | - |
| `acc-exercise-prescriptions-cardiovascular-health-2026` | Exercise Prescriptions for Cardiovascular Health in Adults | ACC | B — Exercícios | 2026 | en | PDF | Indisponível (HTTP 403) | Não convertida | - |
| `ioc-load-sport-injury-2016` | IOC consensus statement on load in sport and risk of injury (Part 1) | International Olympic Committee | B — Exercícios | 2016 | en | PDF (13 p.) | Obtido | Concluída | Integral |
| `ioc-load-sport-illness-2016` | IOC consensus statement on load in sport and risk of illness (Part 2) | International Olympic Committee | B — Exercícios | 2016 | en | PDF (11 p.) | Obtido | Concluída | Integral |
| `jospt-low-back-pain-cpg-revision-2021` | Clinical Practice Guidelines for Interventions for Low Back Pain: 2021 Revision | JOSPT | C — Dores/Lesões | 2021 | en | HTML | Obtido | Concluída | Integral |
| `who-package-rehabilitation-musculoskeletal-2023` | Package of Interventions for Rehabilitation: Module 2 — Musculoskeletal Conditions | World Health Organization | C — Dores/Lesões | 2023 | en | PDF (108 p.) | Obtido | Concluída | Integral |
| `jospt-rotator-cuff-tendinopathy-cpg-2025` | Rotator Cuff Tendinopathy Diagnosis, Nonsurgical Medical Care, and Rehabilitation | JOSPT / APTA | C — Dores/Lesões | 2025 | en | PDF (40 p.) | Obtido | Concluída | Integral |
| `who-physical-activity-at-a-glance-2020` | WHO Guidelines on Physical Activity and Sedentary Behaviour: At a Glance | World Health Organization | A — Saúde Geral | 2020 | en | PDF (24 p.) | Obtido | Concluída | Síntese / Resumo |
| `hhs-physical-activity-scientific-report-2018` | 2018 Physical Activity Guidelines Advisory Committee Scientific Report | U.S. DHHS | A — Saúde Geral | 2018 | en | PDF (779 p.) | Obtido | Concluída | Integral |
| `cdc-adult-physical-activity-overview` | Adult Activity: An Overview | CDC | A — Saúde Geral | 2024 | en | HTML | Indisponível (Akamai 403) | Não convertida | - |
| `nhs-physical-activity-adults-19-64` | Physical activity guidelines for adults aged 19 to 64 | NHS | A — Saúde Geral | 2021 | en | HTML | Obtido | Concluída | Guia institucional |
| `cdc-heat-and-athletes` | Extreme Heat and Athletes | CDC | B — Exercícios | 2024 | en | HTML | Indisponível (Akamai 403) | Não convertida | - |
| `nhs-warm-up-before-exercise` | How to warm up before exercising | NHS | B — Exercícios | 2022 | en | HTML | Obtido | Concluída | Guia prático |
| `nice-low-back-pain-sciatica-ng59` | Low back pain and sciatica in over 16s (NICE NG59) | NICE | C — Dores/Lesões | 2016 | en | HTML | Obtido | Concluída | Integral (Recomendações) |
| `cochrane-exercise-chronic-low-back-pain-2021` | Exercícios para o tratamento da dor lombar crônica | Cochrane | C — Dores/Lesões | 2021 | pt-BR / en | HTML | Obtido | Concluída | Resumo de Evidência |
| `nice-osteoarthritis-ng226` | Osteoarthritis in over 16s: diagnosis and management (NICE NG226) | NICE | C — Dores/Lesões | 2022 | en | HTML | Obtido | Concluída | Integral (Recomendações) |
| `jospt-patellofemoral-pain-cpg-2019` | Patellofemoral Pain: Clinical Practice Guideline (Página Oficial / Resumo) | AOPT / JOSPT | C — Dores/Lesões | 2019 | en | HTML | Obtido | Concluída | Parcial (Página pública) |
| `jospt-patellofemoral-pain-infographic-2019` | Patellofemoral Pain: Clinical Practice Guideline (Infográfico Oficial AOPT) | AOPT / JOSPT | C — Dores/Lesões | 2019 | en | PDF (1 p.) | Obtido | Concluída | Resumo visual |
| `jospt-ankle-ligament-sprains-cpg-2021` | Ankle Stability and Movement Coordination Impairments: Lateral Ankle Ligament Sprains | AOPT / JOSPT | C — Dores/Lesões | 2021 | en | PDF (80 p.) | Obtido | Concluída | Integral |
| `who-rehabilitation-musculoskeletal-annex-2023` | Package of Interventions for Rehabilitation: Module 2 — Web Annex (Evidence Tables) | World Health Organization | C — Dores/Lesões | 2023 | en | PDF (110 p.) | Obtido | Concluída | Integral |
| `world-guidelines-falls-prevention-2022` | World Guidelines for Falls Prevention and Management for Older Adults | Age and Ageing / OUP | C — Dores/Lesões | 2022 | en | HTML / PDF | Indisponível (Cloudflare 403) | Não convertida | - |
| `brazilian-physical-activity-recommendations-report-2022` | Physical Activity Guidelines for the Brazilian Population: Recommendations Report | JPAH / UFRGS | D — Fundamentação BR | 2022 | en | PDF | Indisponível (UFRGS 500) | Não convertida | - |
| `ms-guia-atividade-fisica-gestores-profissionais-2021` | Guia de Atividade Física: Recomendações para Gestores e Profissionais de Saúde | Ministério da Saúde | D — Fundamentação BR | 2021 | pt-BR | PDF (20 p.) | Obtido | Concluída | Integral |

---

## 3. Relações e Rastreabilidade Entre Fontes

1. **Diretrizes OMS (Integral x Resumo):**
   - Integral: `who-diretrizes-atividade-fisica-sedentarismo-2020` (104 páginas).
   - Resumo rápido: `who-physical-activity-at-a-glance-2020` (24 páginas, síntese voltada para consulta ágil).
2. **Reabilitação Musculoesquelética da OMS (Módulo 2 x Anexo de Evidências):**
   - Módulo Clínico: `who-package-rehabilitation-musculoskeletal-2023` (108 páginas).
   - Anexo de Evidências: `who-rehabilitation-musculoskeletal-annex-2023` (110 páginas de tabelas GRADE de intervenções).
3. **Consensos do Comitê Olímpico Internacional (IOC 2016):**
   - Carga e Risco de Lesão (Parte 1): `ioc-load-sport-injury-2016` (13 páginas).
   - Carga e Risco de Doença/Infecção (Parte 2): `ioc-load-sport-illness-2016` (11 páginas).
4. **Guias Oficiais do Ministério da Saúde do Brasil (2021):**
   - População Geral: `guia-atividade-fisica-brasil-2021` (52 páginas).
   - Gestores e Profissionais: `ms-guia-atividade-fisica-gestores-profissionais-2021` (20 páginas).
5. **Diretriz de Dor Patelofemoral (JOSPT/AOPT 2019):**
   - O PDF completo de 95 páginas encontra-se sob controle de paywall no site da editora. Foi preservada a página oficial institucional da AOPT (`jospt-patellofemoral-pain-cpg-2019.html`) e o infográfico oficial autorizado de 1 página (`jospt-patellofemoral-pain-infographic-2019.pdf`), identificados explicitamente como conteúdo parcial/resumo.
