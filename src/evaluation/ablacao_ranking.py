"""Ablação do ranking da busca híbrida (issue #35).

Mede, sobre o mesmo índice, o efeito de cada componente do
ranking: bônus de evidência, sobreposição de termos, pesos do RRF e a mistura densa
ChromaDB + TF-IDF/LSA, no benchmark v1 (régua do gate atual) e no v2 (dev para
escolher, test para confirmar). Só mede: não muda a configuração padrão.

Critérios definidos antes da execução: eval/runs/ablacao_mrr_issue35_criterios.md.

    uv run python -m src.evaluation.ablacao_ranking
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from src.agent.consultant_baseline import NutritionConsultantBaseline
from src.evaluation import benchmark_v2
from src.evaluation.run_benchmark import GUIA_CORPUS_ID, evaluate_baseline
from src.retrieval.hybrid_retriever import HybridRetriever

SAIDA_PADRAO = Path("eval/runs/ablacao_mrr_issue35.json")
FASCICULO_ID = "protocolos-guia-alimentar-fasciculo1-2021"
# A0 reproduz a configuração anterior à #35, para manter a comparação fixa mesmo com o padrão novo.
A0 = {"peso_bm25": 0.55, "peso_denso": 0.45, "modo_denso": "chromadb_dense", "sobreposicao": 0.25, "bonus": True}

VARIANTES: List[Dict[str, Any]] = [
    {"id": "A0", "descricao": "Configuração anterior à #35", "hipotese": "referência"},
    {"id": "A1", "descricao": "Sem bônus de evidência", "hipotese": "H1", "bonus": False},
    {"id": "A2", "descricao": "Sem sobreposição de termos", "hipotese": "H1", "sobreposicao": 0.0},
    {"id": "A3", "descricao": "RRF puro (sem bônus e sem sobreposição)", "hipotese": "H1",
     "bonus": False, "sobreposicao": 0.0},
    {"id": "A4", "descricao": "RRF com pesos iguais (0,5/0,5)", "hipotese": "pesos do RRF",
     "peso_bm25": 0.5, "peso_denso": 0.5},
    {"id": "A5", "descricao": "Só BM25 (peso denso 0)", "hipotese": "pesos do RRF",
     "peso_bm25": 1.0, "peso_denso": 0.0},
    {"id": "A6", "descricao": "Só busca densa (peso BM25 0)", "hipotese": "pesos do RRF",
     "peso_bm25": 0.0, "peso_denso": 1.0},
    {"id": "A7", "descricao": "Densa só com ChromaDB (sem TF-IDF/LSA)", "hipotese": "H3",
     "modo_denso": "chromadb_pure"},
    {"id": "A8", "descricao": "Densa só com ChromaDB e RRF puro", "hipotese": "H1 + H3",
     "modo_denso": "chromadb_pure", "bonus": False, "sobreposicao": 0.0},
]


def mrr_alternativo(report: Dict[str, Any], equivalentes: Dict[str, set]) -> float:
    """MRR aceitando fontes equivalentes (ex.: Fascículo 1 no lugar do Guia). Só informativo."""
    total, n = 0.0, 0
    for q in report["question_results"]:
        if not q["recall_evaluated"]:
            continue
        aceitos = set().union(*map(set, q["expected_sources"]))
        for fonte in list(aceitos):
            aceitos |= equivalentes.get(fonte, set())
        rr = next((1.0 / i for i, d in enumerate(q["retrieved_doc_ids"], 1) if d in aceitos), 0.0)
        total += rr
        n += 1
    return round(total / max(n, 1), 4)


METRICAS_V2 = ("acerto_trecho_at_k", "acerto_completo_at_k", "mrr_trecho", "ndcg_trecho_at_k",
               "cobertura_termos", "guardrail_acuracia")


def avaliar_v2(consultor: NutritionConsultantBaseline, k: int = 4) -> Dict[str, Any]:
    """Benchmark v2 reaproveitando o índice. Trecho não julgado no top-k conta como
    irrelevante; a lista sai no resultado para ser julgada antes de comparar variantes."""
    casos = benchmark_v2.carregar_casos()
    resultados = [benchmark_v2.avaliar_caso(c, consultor.consult(c["pergunta"], top_k=k), k) for c in casos]
    rel = benchmark_v2.montar_relatorio(casos, resultados, k)
    return {
        "por_split": {s: {m: rel["por_split"][s][m] for m in METRICAS_V2} for s in benchmark_v2.SPLITS},
        "nao_julgados": {r["id"]: r["nao_julgados_no_top_k"] for r in resultados if r.get("nao_julgados_no_top_k")},
        "rr_por_caso": {r["id"]: r["rr_trecho"] for r in resultados if "rr_trecho" in r},
    }


def rodar(saida: Path = SAIDA_PADRAO) -> Dict[str, Any]:
    consultor = NutritionConsultantBaseline(enable_ollama=False)
    retriever: HybridRetriever = consultor.retriever
    original = {
        "peso_bm25": retriever.weight_bm25,
        "peso_denso": retriever.weight_vector,
        "modo_denso": retriever.vector_mode,
        "sobreposicao": retriever.peso_sobreposicao,
        "bonus": retriever.bonus_evidencia,
    }
    equivalentes = {GUIA_CORPUS_ID: {FASCICULO_ID}}
    resultados = []
    try:
        for v in VARIANTES:
            cfg = {**A0, **{k: v[k] for k in A0 if k in v}}
            retriever.weight_bm25 = cfg["peso_bm25"]
            retriever.weight_vector = cfg["peso_denso"]
            retriever.vector_mode = cfg["modo_denso"]
            retriever.peso_sobreposicao = cfg["sobreposicao"]
            retriever.bonus_evidencia = cfg["bonus"]
            rep = evaluate_baseline(enable_ollama=False, consultant=consultor, write_report=False)
            v2 = avaliar_v2(consultor)
            resultados.append({
                **{k: v[k] for k in ("id", "descricao", "hipotese")},
                "parametros": {
                    "peso_bm25": retriever.weight_bm25,
                    "peso_denso": retriever.weight_vector,
                    "modo_denso": retriever.vector_mode,
                    "peso_sobreposicao": retriever.peso_sobreposicao,
                    "bonus_evidencia": retriever.bonus_evidencia,
                },
                "geral": rep["overall_metrics"],
                "mrr_fasciculo_equivalente": mrr_alternativo(rep, equivalentes),
                "por_categoria": {
                    c: {"mrr": m["mean_mrr"], "recall_at_k": m["mean_doc_recall_at_k"]}
                    for c, m in rep["metrics_by_category"].items()
                },
                "rr_por_pergunta": {
                    q["id"]: q["reciprocal_rank"] for q in rep["question_results"] if q["recall_evaluated"]
                },
                "top4_por_pergunta": {
                    q["id"]: q["retrieved_doc_ids"] for q in rep["question_results"] if q["recall_evaluated"]
                },
                "v2": v2,
            })
    finally:
        retriever.weight_bm25 = original["peso_bm25"]
        retriever.weight_vector = original["peso_denso"]
        retriever.vector_mode = original["modo_denso"]
        retriever.peso_sobreposicao = original["sobreposicao"]
        retriever.bonus_evidencia = original["bonus"]

    relatorio = {
        "criterios": "eval/runs/ablacao_mrr_issue35_criterios.md",
        "golden_set": {"v1": "data/benchmark/eval_questions.json", "v2": "eval/golden/v2/{dev,test}.json"},
        "observacao": "v1: medido dentro da amostra (o holdout antigo é idêntico ao dev). "
                      "v2: escolher pelo dev e confirmar no test.",
        "variantes": resultados,
    }
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return relatorio


_CASOS_V2 = benchmark_v2.carregar_casos()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()
    rel = rodar(args.saida)
    print(f"{'Id':3} {'Variante':44} {'Recall':>7} {'MRR':>6} {'MRR*':>6} {'Termos':>7} {'Guard':>6}")
    for v in rel["variantes"]:
        g = v["geral"]
        print(f"{v['id']:3} {v['descricao'][:44]:44} {g['mean_doc_recall_at_k']:7.4f} "
              f"{g['mean_reciprocal_rank_mrr']:6.4f} {v['mrr_fasciculo_equivalente']:6.4f} "
              f"{g['mean_keyword_coverage']:7.4f} {g['legal_guardrail_accuracy']:6.4f}")
    print("MRR* = MRR aceitando o Fascículo 1 como equivalente ao Guia (só informativo).")
    print()
    print(f"{'Id':3} {'v2':4} {'Trecho':>7} {'Compl.':>7} {'MRR':>6} {'nDCG':>6} {'Termos':>7} {'Guard':>6} {'NãoJulg':>8}")
    for v in rel["variantes"]:
        for split, m in v["v2"]["por_split"].items():
            nj = sum(len(t) for c, t in v["v2"]["nao_julgados"].items()
                     if any(r["id"] == c and r["split"] == split for r in _CASOS_V2))
            print(f"{v['id']:3} {split:4} {m['acerto_trecho_at_k']:7.4f} {m['acerto_completo_at_k']:7.4f} "
                  f"{m['mrr_trecho']:6.4f} {m['ndcg_trecho_at_k']:6.4f} {m['cobertura_termos']:7.4f} "
                  f"{m['guardrail_acuracia']:6.4f} {nj:8d}")
    print(f"Relatório: {args.saida}")


if __name__ == "__main__":
    main()
