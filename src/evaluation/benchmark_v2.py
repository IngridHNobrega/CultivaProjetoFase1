"""Benchmark v2 de Nutrição (issue #13): recuperação por Trecho separada da geração.

Uso:
    python -m src.evaluation.benchmark_v2 --no-ollama

Lê `eval/golden/v2/{dev,test}.json` e grava `data/benchmark/benchmark_v2_report.json`.
Todas as checagens são determinísticas, sem juiz LLM:

- recuperação: acerto, recall, MRR e nDCG por Trecho (notas 0/1/2 julgadas por pooling),
  e acerto por página e por fonte;
- geração: termos obrigatórios e proibidos, citações apontando para Trechos recuperados;
- comportamento: guardrail da Lei 8.234/1991, com o recall nos pedidos de prescrição separado da
  especificidade (não acionar sem motivo), e abstenção ("não sei") nos casos fora de escopo;
- grafo: cadeia esperada presente e nenhum composto proibido em cadeia não marcada como contraindicada;
- TACO: alimento devolvido com o valor esperado por 100 g.

A abstenção ainda não existe no sistema (issue #6). Ela só é reconhecida pelo campo
`abstencao` da resposta, que a #6 deve criar: procurar frases como "não há evidência" no texto
confunde a abstenção com Trechos citados que dizem isso. A métrica fica em
`metricas_informativas`, fora de `overall_metrics`, que é o que o gate compara.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.config import BENCHMARK_V2_REPORT_PATH, GOLDEN_V2_DIR, INCLUDE_PENDING_SOURCES, TOP_K_FINAL
from src.retrieval.hybrid_retriever import normalize_text
from src.retrieval.taco_tool import NUTRIENT_ALIASES

SPLITS = ("dev", "test")
# Citações de ferramentas, que não apontam para Trechos do corpus.
CITACOES_DE_FERRAMENTA = {"KG_4LAYER_PICO_GRADE", "TACO_4ED_UNICAMP"}
ROTULO_TACO = {campo: rotulo for campo, rotulo in NUTRIENT_ALIASES.values()}


def carregar_casos(diretorio: Path = GOLDEN_V2_DIR) -> List[Dict[str, Any]]:
    casos: List[Dict[str, Any]] = []
    for split in SPLITS:
        dados = json.loads((diretorio / f"{split}.json").read_text(encoding="utf-8"))
        for caso in dados["casos"]:
            if caso["split"] != split:
                raise ValueError(f"{caso['id']} está em {split}.json com split={caso['split']}")
            casos.append(caso)
    ids = [c["id"] for c in casos]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise ValueError(f"ids repetidos no golden set: {', '.join(repetidos)}")
    return casos


def cobertura(grupos: Iterable[Iterable[str]], texto_normalizado: str) -> float:
    grupos = [list(g) for g in grupos]
    if not grupos:
        return 1.0
    atendidos = sum(1 for g in grupos if any(normalize_text(t) in texto_normalizado for t in g))
    return atendidos / len(grupos)


def metricas_de_recuperacao(notas: Dict[str, int], recuperados: List[str], k: int) -> Dict[str, float]:
    """Por Trecho. `notas` mapeia o id do Trecho relevante à nota (1 parcial, 2 completo); Trecho
    ausente vale 0. Acerto, recall e MRR contam nota >= 1; o nDCG usa ganho 2^nota - 1."""
    topo = recuperados[:k]
    relevantes = [t for t, n in notas.items() if n >= 1]
    rr = next((1.0 / i for i, tid in enumerate(topo, 1) if tid in relevantes), 0.0)
    dcg = sum((2 ** notas.get(t, 0) - 1) / math.log2(i + 1) for i, t in enumerate(topo, 1))
    ideal = sorted(notas.values(), reverse=True)[:k]
    idcg = sum((2 ** n - 1) / math.log2(i + 1) for i, n in enumerate(ideal, 1))

    def pagina(tid: str) -> str:
        return tid.rsplit("-", 1)[0]

    def fonte(tid: str) -> str:
        return re.sub(r"-(p[0-9]{3}|resumo)-[0-9]{2}$", "", tid)

    paginas = {pagina(t) for t in relevantes}
    fontes = {fonte(t) for t in relevantes}
    return {
        "acerto_trecho": float(any(t in relevantes for t in topo)),
        "acerto_completo": float(any(notas.get(t, 0) == 2 for t in topo)),
        "ndcg_trecho": dcg / idcg if idcg else 0.0,
        "recall_trecho": len(set(topo) & set(relevantes)) / min(len(relevantes), k),
        "rr_trecho": rr,
        "acerto_pagina": float(any(pagina(t) in paginas for t in topo)),
        "acerto_fonte": float(any(fonte(t) in fontes for t in topo)),
    }


def citacoes_validas(citacoes: List[str], docs_recuperados: set[str]) -> bool:
    """Toda citação [doc_id] aponta para um documento recuperado; resposta sem citação de fonte é inválida."""
    ids = [m.group(1) for c in citacoes for m in [re.match(r"\[([^\]]+)\]", c)] if m]
    de_fonte = [i for i in ids if i not in CITACOES_DE_FERRAMENTA]
    return bool(de_fonte) and all(i in docs_recuperados for i in de_fonte)


def _texto_da_cadeia(caminho: Any) -> str:
    return normalize_text(" ".join([caminho.food_node, caminho.compound_node, caminho.mechanism_node,
                                    caminho.outcome_node]))


def avaliar_grafo(spec: Dict[str, Any], caminhos: List[Any]) -> Dict[str, Optional[float]]:
    resultado: Dict[str, Optional[float]] = {"cadeia_encontrada": None, "composto_proibido_ausente": None}
    if spec.get("cadeia_esperada"):
        resultado["cadeia_encontrada"] = float(any(
            cobertura(spec["cadeia_esperada"], _texto_da_cadeia(c)) == 1.0 for c in caminhos))
    if spec.get("composto_proibido"):
        # Só o composto: o mecanismo de uma cadeia segura pode citar o termo ("sem carga de potássio").
        resultado["composto_proibido_ausente"] = float(not any(
            cobertura(spec["composto_proibido"], normalize_text(c.compound_node)) == 1.0
            and not c.is_contraindicated_for_query
            for c in caminhos))
    return resultado


def valor_taco(registro: Any, campo: str) -> Optional[float]:
    if hasattr(registro, campo) and getattr(registro, campo) is not None:
        return float(getattr(registro, campo))
    rotulo = ROTULO_TACO.get(campo)
    if rotulo and rotulo in registro.nutrients_per_100g:
        return float(registro.nutrients_per_100g[rotulo])
    return None


def avaliar_taco(spec: Dict[str, Any], registros: List[Any]) -> float:
    for registro in registros:
        if registro.description == spec["alimento"]:
            valor = valor_taco(registro, spec["campo"])
            return float(valor is not None and abs(valor - spec["valor"]) <= spec["tolerancia"])
    return 0.0


def avaliar_caso(caso: Dict[str, Any], resposta: Any, k: int) -> Dict[str, Any]:
    recuperados = [item.chunk.chunk_id for item in resposta.retrieved_chunks]
    docs = {item.chunk.doc_id for item in resposta.retrieved_chunks}
    texto = normalize_text(" ".join([resposta.evidence_summary, resposta.physiological_mechanism,
                                     resposta.protocol_findings]))
    esperado = caso["comportamento_esperado"]
    resultado: Dict[str, Any] = {
        "id": caso["id"],
        "tipo": caso["tipo"],
        "split": caso["split"],
        "comportamento_esperado": esperado,
        "guardrail_acionado": resposta.guardrail_triggered,
        "trechos_recuperados": recuperados,
    }
    if esperado == "nao_sei":
        resultado["abstencao"] = float(bool(getattr(resposta, "abstencao", False)))
    else:
        resultado["guardrail_correto"] = float(resposta.guardrail_triggered == (esperado == "redirecionar_prescricao"))
        # Deixar passar uma prescrição (RN01) é o erro grave: o recall fica separado, para a média
        # dos casos que não devem acionar não esconder as falhas.
        chave = "prescricao_detectada" if esperado == "redirecionar_prescricao" else "sem_acionamento_indevido"
        resultado[chave] = float(resposta.guardrail_triggered == (esperado == "redirecionar_prescricao"))
    if esperado == "responder":
        resultado["citacoes_validas"] = float(citacoes_validas(resposta.citations, docs))
    if caso.get("recuperacao"):
        notas = {t: e["nota"] for t, e in caso["recuperacao"]["evidencias"].items()}
        julgados = set(notas) | set(caso["recuperacao"]["julgados_irrelevantes"])
        resultado["trechos_relevantes"] = notas
        resultado["nao_julgados_no_top_k"] = [t for t in recuperados[:k] if t not in julgados]
        resultado.update(metricas_de_recuperacao(notas, recuperados, k))
    geracao = caso.get("geracao") or {}
    if geracao.get("termos_obrigatorios"):
        resultado["cobertura_termos"] = cobertura(geracao["termos_obrigatorios"], texto)
    if geracao.get("termos_proibidos"):
        resultado["sem_termos_proibidos"] = float(
            not any(normalize_text(t) in texto for t in geracao["termos_proibidos"]))
    if caso.get("grafo"):
        resultado.update({k_: v for k_, v in avaliar_grafo(caso["grafo"], resposta.graph_paths).items()
                          if v is not None})
        resultado["cadeias_devolvidas"] = [c.path_id for c in resposta.graph_paths]
    if caso.get("taco"):
        resultado["taco_correto"] = avaliar_taco(caso["taco"], resposta.taco_records)
        resultado["taco_devolvidos"] = [r.description for r in resposta.taco_records]
    return resultado


# Métricas do gate (média sobre os casos que têm o campo) e informativas.
METRICAS = {
    "acerto_trecho_at_k": "acerto_trecho",
    "acerto_completo_at_k": "acerto_completo",
    "ndcg_trecho_at_k": "ndcg_trecho",
    "recall_trecho_at_k": "recall_trecho",
    "mrr_trecho": "rr_trecho",
    "acerto_pagina_at_k": "acerto_pagina",
    "acerto_fonte_at_k": "acerto_fonte",
    "cobertura_termos": "cobertura_termos",
    "citacoes_validas": "citacoes_validas",
    "guardrail_acuracia": "guardrail_correto",
    "guardrail_recall_prescricao": "prescricao_detectada",
    "guardrail_especificidade": "sem_acionamento_indevido",
    "grafo_cadeia_encontrada": "cadeia_encontrada",
    "grafo_composto_proibido_ausente": "composto_proibido_ausente",
    "taco_acuracia": "taco_correto",
}
METRICAS_INFORMATIVAS = {"abstencao_fora_de_escopo": "abstencao"}


def agregar(resultados: List[Dict[str, Any]], metricas: Dict[str, str]) -> Dict[str, Any]:
    agregado: Dict[str, Any] = {}
    for nome, campo in metricas.items():
        valores = [r[campo] for r in resultados if campo in r]
        agregado[nome] = round(sum(valores) / len(valores), 4) if valores else None
        agregado[f"n_{nome}"] = len(valores)
    return agregado


def montar_relatorio(casos: List[Dict[str, Any]], resultados: List[Dict[str, Any]], k: int) -> Dict[str, Any]:
    tipos = sorted({c["tipo"] for c in casos})
    return {
        "benchmark": "v2",
        "top_k": k,
        "casos": len(casos),
        "casos_por_split": {s: sum(c["split"] == s for c in casos) for s in SPLITS},
        "casos_revisados": sum(c["autoria"]["revisao"] == "revisado" for c in casos),
        # Trechos no top-k sem julgamento contam como irrelevantes; se crescer, refaça o pooling.
        "trechos_nao_julgados_no_top_k": sum(len(r.get("nao_julgados_no_top_k", [])) for r in resultados),
        "overall_metrics": agregar(resultados, METRICAS),
        "metricas_informativas": agregar(resultados, METRICAS_INFORMATIVAS),
        "por_split": {s: agregar([r for r in resultados if r["split"] == s], {**METRICAS, **METRICAS_INFORMATIVAS})
                      for s in SPLITS},
        "por_tipo": {t: agregar([r for r in resultados if r["tipo"] == t], {**METRICAS, **METRICAS_INFORMATIVAS})
                     for t in tipos},
        "resultados": resultados,
    }


def executar(
    diretorio: Path = GOLDEN_V2_DIR,
    relatorio_path: Path = BENCHMARK_V2_REPORT_PATH,
    enable_ollama: bool = False,
    top_k: int = TOP_K_FINAL,
    incluir_pendentes: bool = INCLUDE_PENDING_SOURCES,
) -> Dict[str, Any]:
    from src.agent.consultant_baseline import NutritionConsultantBaseline

    casos = carregar_casos(diretorio)
    consultor = NutritionConsultantBaseline(enable_ollama=enable_ollama, incluir_pendentes=incluir_pendentes)
    resultados = [avaliar_caso(c, consultor.consult(c["pergunta"], top_k=top_k), top_k) for c in casos]
    relatorio = montar_relatorio(casos, resultados, top_k)
    relatorio_path.parent.mkdir(parents=True, exist_ok=True)
    relatorio_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return relatorio


def _formatar(valor: Optional[float], n: int) -> str:
    return "   n/a" if valor is None else f"{valor * 100:5.1f}% (n={n})"


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Benchmark v2 de Nutrição (issue #13).")
    parser.add_argument("--no-ollama", action="store_true",
                        help="Síntese extrativa determinística local, sem chamar LLM.")
    args = parser.parse_args(argv)
    relatorio = executar(enable_ollama=not args.no_ollama)
    print("=" * 78)
    print(f"BENCHMARK V2 — {relatorio['casos']} casos {relatorio['casos_por_split']}, "
          f"top_k={relatorio['top_k']}, revisados: {relatorio['casos_revisados']}, "
          f"Trechos não julgados no top-k: {relatorio['trechos_nao_julgados_no_top_k']}")
    print("=" * 78)
    for bloco, metricas in [("Gate", relatorio["overall_metrics"]), ("Informativas", relatorio["metricas_informativas"])]:
        print(f"{bloco}:")
        for nome in (m for m in metricas if not m.startswith("n_")):
            print(f"  {nome:32s} {_formatar(metricas[nome], metricas[f'n_{nome}'])}")
    print("-" * 78)
    for split, metricas in relatorio["por_split"].items():
        print(f"{split:5s} trecho@k {_formatar(metricas['acerto_trecho_at_k'], metricas['n_acerto_trecho_at_k'])} | "
              f"MRR {_formatar(metricas['mrr_trecho'], metricas['n_mrr_trecho'])} | "
              f"termos {_formatar(metricas['cobertura_termos'], metricas['n_cobertura_termos'])}")
    print(f"Relatório: {BENCHMARK_V2_REPORT_PATH}")


if __name__ == "__main__":
    main()
