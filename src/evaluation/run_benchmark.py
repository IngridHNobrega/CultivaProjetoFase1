import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

from src.agent.consultant_baseline import NutritionConsultantBaseline
from src.config import (
    BENCHMARK_QUESTIONS_PATH,
    BENCHMARK_REPORT_PATH,
    CORPUS_MANIFEST_PATH,
    INCLUDE_PENDING_SOURCES,
    TOP_K_FINAL,
)
from src.retrieval.hybrid_retriever import normalize_text


GUIA_CORPUS_ID = "guia-alimentar-populacao-brasileira-2014"


def mapear_esperados(
    ids: List[str], manifest_path: Path = CORPUS_MANIFEST_PATH
) -> Tuple[List[Set[str]], List[str]]:
    """Converte os ids esperados do benchmark (escritos para o data/raw) em fontes do corpus.

    Cada id vira um grupo de fontes aceitas: GUIA_MS_* -> Guia Alimentar do corpus;
    PUBMED_<grupo> -> qualquer resumo do PubMed daquele grupo (raw_group no manifesto);
    um id que já é fonte do corpus fica como está. Os DOC_* do seed_guidelines, que saiu do
    índice por não ter procedência verificável, são descartados e listados à parte.

    O Fascículo 1 não entra como equivalente ao Guia: decisão do grupo na issue #35, registrada
    em data/benchmark/README.md (a equivalência por conteúdo fica com o benchmark v2).
    """
    fontes = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))["sources"]
    ids_corpus = {f["id"] for f in fontes}
    grupos_pubmed: Dict[str, Set[str]] = defaultdict(set)
    for f in fontes:
        if f.get("kind") == "resumo_pubmed" and f.get("raw_group"):
            grupos_pubmed[f["raw_group"]].add(f["id"])
    grupos: List[Set[str]] = []
    descartados: List[str] = []
    for doc_id in ids:
        if doc_id.startswith("GUIA_MS_"):
            grupo = {GUIA_CORPUS_ID}
        elif doc_id in grupos_pubmed:
            grupo = grupos_pubmed[doc_id]
        elif doc_id in ids_corpus:
            grupo = {doc_id}
        else:
            descartados.append(doc_id)
            continue
        if grupo not in grupos:
            grupos.append(grupo)
    return grupos, descartados


def evaluate_baseline(
    questions_path: Path = BENCHMARK_QUESTIONS_PATH,
    report_path: Path = BENCHMARK_REPORT_PATH,
    enable_ollama: bool = True,
    enable_taco_tool: bool = True,
    enable_graph_engine: bool = True,
    top_k: int = TOP_K_FINAL,
    incluir_pendentes: bool = INCLUDE_PENDING_SOURCES,
    consultant: NutritionConsultantBaseline | None = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Avalia o sistema da entrega sobre o índice padrão, só com fontes aprovadas.
    Fontes pendentes entram apenas com CULTIVA_INCLUIR_PENDENTES=true.

    `consultant` permite reaproveitar um índice já construído (ablação); com
    `write_report=False` o relatório só é devolvido, sem regravar o arquivo."""
    questions: List[Dict[str, Any]] = json.loads(
        questions_path.read_text(encoding="utf-8")
    )
    if consultant is None:
        consultant = NutritionConsultantBaseline(
            enable_ollama=enable_ollama,
            enable_taco_tool=enable_taco_tool,
            enable_graph_engine=enable_graph_engine,
            incluir_pendentes=incluir_pendentes,
        )

    results: List[Dict[str, Any]] = []
    total_recall = 0.0
    total_mrr = 0.0
    avaliadas = 0
    total_kw_coverage = 0.0
    guardrail_correct = 0

    category_stats: Dict[str, Dict[str, Any]] = {}

    for q in questions:
        qid = q["id"]
        category = q["category"]
        query = q["query"]
        expected_docs = set(q.get("expected_doc_ids", []))
        grupos, descartados = mapear_esperados(sorted(expected_docs))
        aceitos = set().union(*grupos) if grupos else set()
        expected_keywords = q.get("expected_keywords", [])
        expect_guardrail = bool(q.get("expect_guardrail_trigger", False))

        response = consultant.consult(query, top_k=top_k)
        retrieved_doc_ids = [item.chunk.doc_id for item in response.retrieved_chunks]
        retrieved_unique_docs = set(retrieved_doc_ids)

        # 1. Recall@K por fonte esperada (cada grupo de fontes aceitas conta uma vez).
        #    Perguntas cujas fontes esperadas saíram do índice ficam fora da média.
        avaliada = bool(grupos)
        hits = sum(1 for g in grupos if g & retrieved_unique_docs)
        doc_recall = hits / len(grupos) if avaliada else 0.0

        # 2. Reciprocal Rank (RR)
        rr = 0.0
        for rank_idx, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id in aceitos:
                rr = 1.0 / rank_idx
                break
        if avaliada:
            avaliadas += 1
            total_recall += doc_recall
            total_mrr += rr

        # 3. Cobertura dos termos técnicos/mecanísticos na resposta gerada
        combined_answer_norm = normalize_text(
            f"{response.evidence_summary} {response.physiological_mechanism} {response.protocol_findings}"
        )
        kw_hits = sum(
            1 for kw in expected_keywords if normalize_text(kw) in combined_answer_norm
        )
        kw_cov = kw_hits / max(len(expected_keywords), 1)
        total_kw_coverage += kw_cov

        # 4. Acurácia do Guardrail Legal (Lei 8.234/91)
        is_guardrail_accurate = response.guardrail_triggered == expect_guardrail
        if is_guardrail_accurate:
            guardrail_correct += 1

        cat_entry = category_stats.setdefault(
            category,
            {"count": 0, "avaliadas": 0, "recall_sum": 0.0, "mrr_sum": 0.0, "kw_cov_sum": 0.0, "guardrail_ok": 0},
        )
        cat_entry["count"] += 1
        if avaliada:
            cat_entry["avaliadas"] += 1
            cat_entry["recall_sum"] += doc_recall
            cat_entry["mrr_sum"] += rr
        cat_entry["kw_cov_sum"] += kw_cov
        cat_entry["guardrail_ok"] += int(is_guardrail_accurate)

        results.append(
            {
                "id": qid,
                "category": category,
                "query": query,
                "effective_query": response.effective_query,
                "guardrail_triggered": response.guardrail_triggered,
                "expect_guardrail_trigger": expect_guardrail,
                "guardrail_accurate": is_guardrail_accurate,
                "expected_doc_ids": sorted(expected_docs),
                "expected_sources": [sorted(g) for g in grupos],
                "expected_removed_from_index": descartados,
                "recall_evaluated": avaliada,
                "retrieved_doc_ids": retrieved_doc_ids,
                "doc_recall_at_k": round(doc_recall, 4),
                "reciprocal_rank": round(rr, 4),
                "keyword_coverage": round(kw_cov, 4),
                "retrieval_mode": response.retrieval_mode,
                "taco_records_count": len(response.taco_records),
                "graph_paths_count": len(response.graph_paths),
                "model_used": response.model_used,
                "evidence_grade": response.evidence_grade,
                "baseline_limitation_note": q.get("baseline_limitation_note"),
                "evidence_summary_preview": response.evidence_summary[:240],
            }
        )

    n = max(len(questions), 1)
    summary_by_category = {}
    for cat, stats in category_stats.items():
        c = max(stats["count"], 1)
        a = max(stats["avaliadas"], 1)
        summary_by_category[cat] = {
            "questions": stats["count"],
            "recall_questions_evaluated": stats["avaliadas"],
            "mean_doc_recall_at_k": round(stats["recall_sum"] / a, 4),
            "mean_mrr": round(stats["mrr_sum"] / a, 4),
            "mean_keyword_coverage": round(stats["kw_cov_sum"] / c, 4),
            "guardrail_accuracy": round(stats["guardrail_ok"] / c, 4),
        }

    phase_label = (
        "PHASE_2_FULL_HYBRID_RAG_PLUS_GRAPH_AND_TACO"
        if (enable_taco_tool and enable_graph_engine)
        else (
            "PHASE_2_STEP2_HYBRID_RAG_PLUS_TACO"
            if enable_taco_tool
            else "PHASE_1_HYBRID_RAG_BASELINE_ONLY"
        )
    )

    report = {
        "phase": phase_label,
        "total_questions": len(questions),
        "top_k": top_k,
        "recall_questions_evaluated": avaliadas,
        "overall_metrics": {
            "mean_doc_recall_at_k": round(total_recall / max(avaliadas, 1), 4),
            "mean_reciprocal_rank_mrr": round(total_mrr / max(avaliadas, 1), 4),
            "mean_keyword_coverage": round(total_kw_coverage / n, 4),
            "legal_guardrail_accuracy": round(guardrail_correct / n, 4),
        },
        "metrics_by_category": summary_by_category,
        "question_results": results,
    }

    if write_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa o benchmark de avaliação e estudo de ablação (Fase 1 vs Passo 2 TACO vs Passo 3 Grafo)."
    )
    parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="Executa com síntese extrativa determinística local (sem chamar o daemon Ollama).",
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Executa o estudo de ablação comparando Passo 1 (Só RAG), Passo 2 (RAG + TACO) e Passo 3 (RAG + TACO + Grafo 4 Camadas).",
    )
    args = parser.parse_args()

    if args.ablation:
        r1 = evaluate_baseline(
            enable_ollama=not args.no_ollama,
            enable_taco_tool=False,
            enable_graph_engine=False,
        )
        r2 = evaluate_baseline(
            enable_ollama=not args.no_ollama,
            enable_taco_tool=True,
            enable_graph_engine=False,
        )
        r3 = evaluate_baseline(
            enable_ollama=not args.no_ollama,
            enable_taco_tool=True,
            enable_graph_engine=True,
        )
        print("=" * 84)
        print("ESTUDO DE ABLAÇÃO — COMPARATIVO CIENTÍFICO (PASSO 1 vs. PASSO 2 vs. PASSO 3)")
        print("=" * 84)
        for label, rep in [
            ("1. Fase 1: Só RAG Híbrido (Baseline)", r1),
            ("2. Passo 2: RAG Híbrido + Tabela TACO", r2),
            ("3. Passo 3: RAG + TACO + Grafo 4 Camadas", r3),
        ]:
            ov = rep["overall_metrics"]
            mh = rep["metrics_by_category"]["multi_hop_and_composition_gap"]
            print(
                f"{label:42s} | Recall@4: {ov['mean_doc_recall_at_k']*100:5.1f}% | "
                f"Termos Gerais: {ov['mean_keyword_coverage']*100:5.1f}% | "
                f"Multi-Hop/TACO/Grafo: {mh['mean_keyword_coverage']*100:5.1f}% | "
                f"Guardrail: {ov['legal_guardrail_accuracy']*100:5.1f}%"
            )
        print("=" * 84)
        return

    report = evaluate_baseline(enable_ollama=not args.no_ollama)
    print("=" * 72)
    print(f"RELATÓRIO DE BENCHMARK — {report['phase']}")
    print("=" * 72)
    overall = report["overall_metrics"]
    print(f"Total de questões avaliadas : {report['total_questions']}")
    print(f"Recall@{report['top_k']} Médio (Documentos): {overall['mean_doc_recall_at_k'] * 100:.1f}%")
    print(f"MRR (Mean Reciprocal Rank)  : {overall['mean_reciprocal_rank_mrr']:.4f}")
    print(f"Cobertura Conceitual/Termos : {overall['mean_keyword_coverage'] * 100:.1f}%")
    print(f"Acurácia Guardrail Legal    : {overall['legal_guardrail_accuracy'] * 100:.1f}%")
    print("-" * 72)
    print("Desempenho por Categoria:")
    for cat, stats in report["metrics_by_category"].items():
        print(
            f"  • {cat:32s} | Qs: {stats['questions']} | "
            f"Recall@{report['top_k']}: {stats['mean_doc_recall_at_k']*100:5.1f}% | "
            f"Termos: {stats['mean_keyword_coverage']*100:5.1f}% | "
            f"Guardrail: {stats['guardrail_accuracy']*100:5.1f}%"
        )
    print("=" * 72)
    print(f"Relatório salvo em: {BENCHMARK_REPORT_PATH}")


if __name__ == "__main__":
    main()
