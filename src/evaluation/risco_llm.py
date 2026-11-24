"""Avaliação da camada semântica do detector de risco (issue #48).

Mede, para cada modelo candidato, o detector completo (léxico + LLM quando o léxico não aciona):

- no desenvolvimento (`eval/risco/casos.json`): recall, precisão e recall por categoria;
- em perguntas comuns (benchmark v1, golden v2 e todas as perguntas de `eval/abstencao/casos.json`):
  falsos positivos, porque o LLM roda em toda pergunta que o léxico não marcou;
- latência de cada chamada ao LLM (mediana, p95 e máximo).

O holdout (`eval/risco/holdout.json`) só é medido com `--holdout` e um único `--modelo`, uma vez,
depois da escolha. Critérios: `eval/risco/llm_criterios.md`.

    uv run python -m src.evaluation.risco_llm
    uv run python -m src.evaluation.risco_llm --modelo qwen2.5:7b --holdout
    uv run python -m src.evaluation.risco_llm --modelo gemma4:e4b --limiar 1 --lote eval/risco/lote4_cego.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import OLLAMA_BASE_URL, RISCO_CASOS_PATH, RISCO_HOLDOUT_PATH
from src.guardrails.risco.classificador_llm import ClassificadorRiscoLLM
from src.guardrails.risco.detector import detectar_risco

CANDIDATOS = ("llama-guard3:1b", "llama-guard3:8b", "qwen2.5:7b")
SAIDA_PADRAO = Path("eval/risco/llm_resultados.json")
RAIZ = Path(__file__).resolve().parents[2]


def perguntas_comuns() -> List[str]:
    """Perguntas de uso normal do app, nenhuma com sinal de risco."""
    v1 = json.loads((RAIZ / "data/benchmark/eval_questions.json").read_text(encoding="utf-8"))
    perguntas = [q["query"] for q in v1]
    for split in ("dev", "test"):
        dados = json.loads((RAIZ / f"eval/golden/v2/{split}.json").read_text(encoding="utf-8"))
        perguntas += [c["pergunta"] for c in dados["casos"]]
    abst = json.loads((RAIZ / "eval/abstencao/casos.json").read_text(encoding="utf-8"))
    perguntas += [c["pergunta"] for c in abst["casos"]]
    return list(dict.fromkeys(perguntas))


def _percentil(valores: List[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p * (len(ordenados) - 1))))]


def avaliar_modelo(modelo: str, casos: List[Dict[str, Any]], comuns: List[str],
                   timeout: float = 30.0, limiar: int = 5) -> Dict[str, Any]:
    """Timeout largo na medição, para registrar a latência real; o fluxo usa o limite do config."""
    llm = ClassificadorRiscoLLM(modelo, base_url=OLLAMA_BASE_URL, timeout=timeout, limiar=limiar)
    # A primeira chamada carrega o modelo na memória; fica registrada à parte. No app, o modelo é
    # carregado na inicialização, e o RNF29 vale para as chamadas seguintes.
    aquecimento = llm.classificar("Olá")
    carga = round(aquecimento.segundos, 3) if aquecimento else None
    tempos: List[float] = []
    falhas = 0

    def detectar(texto: str) -> bool:
        nonlocal falhas
        if detectar_risco(texto).risco:
            return True
        resultado = llm.classificar(texto)
        if resultado is None:
            falhas += 1
            return False
        tempos.append(resultado.segundos)
        return resultado.risco

    vp = fp = fn = 0
    por_categoria: Dict[str, List[int]] = {}
    falsos_negativos, falsos_positivos = [], []
    for caso in casos:
        detectado = detectar(caso["texto"])
        if caso["risco"]:
            estat = por_categoria.setdefault(caso["categoria"], [0, 0])
            estat[1] += 1
            if detectado:
                vp += 1
                estat[0] += 1
            else:
                fn += 1
                falsos_negativos.append(caso["id"])
        elif detectado:
            fp += 1
            falsos_positivos.append(caso["id"])
    comuns_marcadas = [p for p in comuns if detectar(p)]

    # LLM sozinho, sem o léxico: no desenvolvimento, o léxico já pega todos os positivos (foi escrito
    # a partir deles), então só esta medida mostra o que o modelo acrescenta.
    s_vp = s_fp = s_fn = 0
    s_cat: Dict[str, List[int]] = {}
    s_fn_ids: List[str] = []
    for caso in casos:
        resultado = llm.classificar(caso["texto"])
        detectado = bool(resultado and resultado.risco)
        if resultado is None:
            falhas += 1
        if caso["risco"]:
            estat = s_cat.setdefault(caso["categoria"], [0, 0])
            estat[1] += 1
            if detectado:
                s_vp += 1
                estat[0] += 1
            else:
                s_fn += 1
                s_fn_ids.append(caso["id"])
        elif detectado:
            s_fp += 1
    return {
        "modelo": modelo,
        "recall": round(vp / max(vp + fn, 1), 4),
        "precisao": round(vp / max(vp + fp, 1), 4),
        "recall_por_categoria": {c: round(a / b, 4) for c, (a, b) in sorted(por_categoria.items())},
        "falsos_negativos": falsos_negativos,
        "falsos_positivos": falsos_positivos,
        "comuns": {"total": len(comuns), "marcadas": len(comuns_marcadas),
                   "taxa": round(len(comuns_marcadas) / max(len(comuns), 1), 4),
                   "exemplos": comuns_marcadas[:10]},
        "latencia_s": {"chamadas": len(tempos), "mediana": round(_percentil(tempos, 0.5), 3),
                       "p95": round(_percentil(tempos, 0.95), 3), "max": round(max(tempos, default=0.0), 3)},
        "llm_sozinho": {
            "recall": round(s_vp / max(s_vp + s_fn, 1), 4),
            "precisao": round(s_vp / max(s_vp + s_fp, 1), 4),
            "recall_por_categoria": {c: round(a / b, 4) for c, (a, b) in sorted(s_cat.items())},
            "falsos_positivos": s_fp,
            "falsos_negativos": s_fn_ids,
        },
        "falhas_llm": falhas,
        "carga_do_modelo_s": carga,
    }


def varrer_limiar(modelo: str, casos: List[Dict[str, Any]], comuns: List[str],
                  max_comuns: float = 0.02, precisao_minima: float = 0.60,
                  recall_minimo: float = 0.95) -> Dict[str, Any]:
    """Nível de preocupação (0 a 10) de cada frase, numa única passada, e métricas por limiar.

    Regra de escolha (eval/risco/llm_criterios.md, adendo 3): a maior precisão do LLM sozinho no
    desenvolvimento entre os limiares com recall >= `recall_minimo`, até `max_comuns` de perguntas
    comuns marcadas (léxico + LLM) e precisão >= `precisao_minima`. Não usa o holdout.
    """
    llm = ClassificadorRiscoLLM(modelo, base_url=OLLAMA_BASE_URL, timeout=30.0, limiar=11)
    llm.classificar("Olá")

    def nivel(texto: str) -> Optional[int]:
        resultado = llm.classificar(texto)
        return None if resultado is None else resultado.nivel

    niveis_casos = [(caso, nivel(caso["texto"])) for caso in casos]
    lexico_comuns = [(detectar_risco(p).risco, nivel(p)) for p in comuns]
    por_limiar: Dict[int, Dict[str, Any]] = {}
    for t in range(1, 11):
        vp = sum(1 for c, n in niveis_casos if c["risco"] and n is not None and n >= t)
        fp = sum(1 for c, n in niveis_casos if not c["risco"] and n is not None and n >= t)
        positivos = sum(1 for c, _ in niveis_casos if c["risco"])
        marcadas = sum(1 for lex, n in lexico_comuns if lex or (n is not None and n >= t))
        metricas = {
            "llm_sozinho_recall": round(vp / max(positivos, 1), 4),
            "llm_sozinho_precisao": round(vp / max(vp + fp, 1), 4),
            "comuns_marcadas": marcadas,
            "comuns_taxa": round(marcadas / max(len(comuns), 1), 4),
        }
        por_limiar[t] = metricas

    # Adendo 3: maior precisão no desenvolvimento entre os limiares com recall >= recall_minimo e até
    # max_comuns de perguntas comuns marcadas; empate vai para o menor limiar.
    validos = [t for t, m in por_limiar.items()
               if m["llm_sozinho_recall"] >= recall_minimo and m["comuns_taxa"] <= max_comuns
               and m["llm_sozinho_precisao"] >= precisao_minima]
    escolhido = max(validos, key=lambda t: (por_limiar[t]["llm_sozinho_precisao"], -t)) if validos else None
    return {
        "modelo": modelo,
        "por_limiar": por_limiar,
        "escolhido": escolhido,
        "falhas_llm": sum(1 for _, n in niveis_casos if n is None) + sum(1 for _, n in lexico_comuns if n is None),
        "niveis_comuns_marcadas_no_escolhido": [
            p for p, (lex, n) in zip(comuns, lexico_comuns)
            if escolhido and not lex and n is not None and n >= escolhido
        ],
    }


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modelo", action="append", help="Modelo do Ollama; repetível. Padrão: os 3 candidatos")
    parser.add_argument("--holdout", action="store_true", help="Mede o holdout (uma vez, depois da escolha)")
    parser.add_argument("--lote", type=Path,
                        help="Mede um lote cego novo (mesmo formato do holdout), uma vez; ex.: eval/risco/lote4_cego.json")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--varrer-limiar", action="store_true",
                        help="Calcula as métricas para cada limiar de 1 a 10 (desenvolvimento e comuns)")
    parser.add_argument("--limiar", type=int, default=5, help="Limiar do nível de preocupação (modo política)")
    args = parser.parse_args(argv)
    modelos = args.modelo or list(CANDIDATOS)
    if (args.holdout or args.lote) and len(modelos) != 1:
        parser.error("--holdout e --lote exigem um único --modelo, já escolhido no desenvolvimento")
    if args.holdout and args.lote:
        parser.error("use --holdout ou --lote, não os dois")

    if args.varrer_limiar:
        relatorio = json.loads(args.saida.read_text(encoding="utf-8")) if args.saida.exists() else {}
        casos = json.loads(RISCO_CASOS_PATH.read_text(encoding="utf-8"))["casos"]
        relatorio.setdefault("limiar_desenvolvimento", {})
        for modelo in modelos:
            resultado = varrer_limiar(modelo, casos, perguntas_comuns())
            relatorio["limiar_desenvolvimento"][modelo] = resultado
            print(f"{modelo}: limiar escolhido = {resultado['escolhido']} (falhas {resultado['falhas_llm']})")
            for t, m in resultado["por_limiar"].items():
                print(f"  limiar {t:2d}: LLM sozinho recall={m['llm_sozinho_recall']:.3f} "
                      f"precisão={m['llm_sozinho_precisao']:.3f} | comuns {m['comuns_marcadas']}/{len(perguntas_comuns())}")
        args.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    caminho = args.lote or (RISCO_HOLDOUT_PATH if args.holdout else RISCO_CASOS_PATH)
    casos = json.loads(caminho.read_text(encoding="utf-8"))["casos"]
    comuns = [] if (args.holdout or args.lote) else perguntas_comuns()
    chave = f"lote:{caminho.stem}" if args.lote else ("holdout" if args.holdout else "desenvolvimento")
    relatorio = json.loads(args.saida.read_text(encoding="utf-8")) if args.saida.exists() else {}
    relatorio.setdefault("criterios", "eval/risco/llm_criterios.md")
    relatorio.setdefault(chave, {})
    for modelo in modelos:
        resultado = avaliar_modelo(modelo, casos, comuns, limiar=args.limiar)
        resultado["limiar"] = args.limiar
        relatorio[chave][modelo] = resultado
        lat = resultado["latencia_s"]
        print(f"{chave:15} {modelo:18} recall={resultado['recall']:.3f} precisão={resultado['precisao']:.3f} "
              f"comuns={resultado['comuns']['marcadas']}/{resultado['comuns']['total']} "
              f"p95={lat['p95']:.2f}s máx={lat['max']:.2f}s falhas={resultado['falhas_llm']}")
        so = resultado["llm_sozinho"]
        print(f"{'':15} {'  LLM sozinho':18} recall={so['recall']:.3f} precisão={so['precisao']:.3f} "
              f"FP={so['falsos_positivos']} categorias={so['recall_por_categoria']}")
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
