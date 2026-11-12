"""Golden set v2 e métricas determinísticas do benchmark v2 (issue #13)."""

from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from src.evaluation import benchmark_v2 as b

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = RAIZ / "eval/golden/v2"
CASOS = b.carregar_casos(GOLDEN)
TRECHOS = {
    t["id"]: t
    for arquivo in (RAIZ / "corpus/nutricao/rag").glob("*.jsonl")
    for t in map(json.loads, arquivo.read_text(encoding="utf-8").splitlines())
}


@pytest.mark.parametrize("split", b.SPLITS)
def test_golden_segue_o_schema(split):
    schema = json.loads((GOLDEN / "caso.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads((GOLDEN / f"{split}.json").read_text(encoding="utf-8")), schema)


def test_golden_tem_pelo_menos_30_casos_e_todos_os_tipos_no_test():
    assert len(CASOS) >= 30  # RNF28
    tipos = Counter(c["tipo"] for c in CASOS)
    assert set(tipos) == {"recuperacao", "prescricao", "adversarial", "fora_de_escopo", "grafo", "taco"}
    no_test = {c["tipo"] for c in CASOS if c["split"] == "test"}
    assert no_test == set(tipos)


def test_prefixo_do_id_corresponde_ao_tipo():
    prefixos = {"recuperacao": "REC", "prescricao": "PRE", "adversarial": "ADV", "fora_de_escopo": "FOR",
                "grafo": "GRA", "taco": "TAC"}
    assert all(c["id"].split("-")[1] == prefixos[c["tipo"]] for c in CASOS)


@pytest.mark.parametrize("caso", [c for c in CASOS if c["recuperacao"]], ids=lambda c: c["id"])
def test_evidencias_existem_sao_aprovadas_e_contem_a_citacao(caso):
    """Pega Trechos que mudaram de id ou de texto quando o corpus é regenerado."""
    for trecho_id, evidencia in caso["recuperacao"]["evidencias"].items():
        assert trecho_id in TRECHOS, f"{caso['id']}: Trecho inexistente {trecho_id}"
        assert TRECHOS[trecho_id]["approval_status"] == "aprovado", f"{caso['id']}: {trecho_id} não aprovado"
        assert evidencia["citacao"] in TRECHOS[trecho_id]["texto"], f"{caso['id']}: citação não está mais em {trecho_id}"
    irrelevantes = set(caso["recuperacao"]["julgados_irrelevantes"])
    assert irrelevantes <= set(TRECHOS), f"{caso['id']}: Trecho julgado inexistente"
    assert not irrelevantes & set(caso["recuperacao"]["evidencias"]), f"{caso['id']}: Trecho com duas notas"


@pytest.mark.parametrize("caso", [c for c in CASOS if c["taco"]], ids=lambda c: c["id"])
def test_valor_esperado_bate_com_a_taco(caso):
    tabela = json.loads((RAIZ / "data/raw/taco/taco_raw.json").read_text(encoding="utf-8"))
    alimento = next(a for a in tabela if a["description"] == caso["taco"]["alimento"])
    assert abs(float(alimento[caso["taco"]["campo"]]) - caso["taco"]["valor"]) <= caso["taco"]["tolerancia"]


def test_metricas_de_recuperacao_por_trecho_pagina_e_fonte():
    notas = {"guia-p048-01": 2, "guia-p049-02": 1}
    recuperados = ["svb-p005-01", "guia-p049-01", "guia-p048-01", "guia-p010-01"]
    m = b.metricas_de_recuperacao(notas, recuperados, k=4)
    assert {k: m[k] for k in ("acerto_trecho", "acerto_completo", "recall_trecho", "rr_trecho",
                              "acerto_pagina", "acerto_fonte")} == {
        "acerto_trecho": 1.0, "acerto_completo": 1.0, "recall_trecho": 0.5, "rr_trecho": 1 / 3,
        "acerto_pagina": 1.0, "acerto_fonte": 1.0}
    m = b.metricas_de_recuperacao({"guia-p048-01": 2}, ["guia-p048-02", "x-p001-01"], k=4)
    assert (m["acerto_trecho"], m["acerto_pagina"], m["rr_trecho"], m["ndcg_trecho"]) == (0.0, 1.0, 0.0, 0.0)


def test_ndcg_premia_nota_alta_no_topo():
    notas = {"a-p001-01": 2, "a-p002-01": 1}
    ideal = b.metricas_de_recuperacao(notas, ["a-p001-01", "a-p002-01"], k=4)["ndcg_trecho"]
    invertido = b.metricas_de_recuperacao(notas, ["a-p002-01", "a-p001-01"], k=4)["ndcg_trecho"]
    so_parcial = b.metricas_de_recuperacao(notas, ["x-p001-01", "a-p002-01"], k=4)
    assert ideal == pytest.approx(1.0)
    assert 0 < invertido < ideal
    assert so_parcial["acerto_trecho"] == 1.0 and so_parcial["acerto_completo"] == 0.0


def test_metrica_ignora_o_que_vem_depois_do_top_k():
    m = b.metricas_de_recuperacao({"a-p001-01": 2}, ["b-p001-01", "a-p001-01"], k=1)
    assert m["acerto_trecho"] == 0.0 and m["acerto_fonte"] == 0.0


def test_cobertura_por_grupo_de_sinonimos():
    texto = "o guia recomenda feijao com arroz"
    assert b.cobertura([["feijão"], ["arroz", "macarrão"]], texto) == 1.0
    assert b.cobertura([["feijão"], ["batata"]], texto) == 0.5


def test_citacoes_validas_exige_fonte_recuperada():
    docs = {"guia"}
    assert b.citacoes_validas(["[guia] Guia — MS", "[TACO_4ED_UNICAMP] Tabela"], docs)
    assert not b.citacoes_validas(["[svb] Guia SVB"], docs)
    assert not b.citacoes_validas(["[KG_4LAYER_PICO_GRADE] Grafo"], docs)


def _cadeia(composto, mecanismo="", contraindicada=False):
    return SimpleNamespace(food_node="Feijão", compound_node=composto, mechanism_node=mecanismo,
                           outcome_node="Pressão arterial", is_contraindicated_for_query=contraindicada)


def test_grafo_composto_proibido_so_conta_sem_contraindicacao():
    spec = {"composto_proibido": [["potassio"]]}
    segura = _cadeia("Redução de sódio", mecanismo="sem aportar carga de potássio")
    assert b.avaliar_grafo(spec, [segura, _cadeia("Potássio", contraindicada=True)])["composto_proibido_ausente"] == 1.0
    assert b.avaliar_grafo(spec, [_cadeia("Potássio dietético")])["composto_proibido_ausente"] == 0.0


def test_grafo_cadeia_esperada_precisa_de_todos_os_grupos_na_mesma_cadeia():
    spec = {"cadeia_esperada": [["feijao"], ["vitamina c"]]}
    assert b.avaliar_grafo(spec, [_cadeia("Ferro não-heme + vitamina C")])["cadeia_encontrada"] == 1.0
    assert b.avaliar_grafo(spec, [_cadeia("Ferro não-heme")])["cadeia_encontrada"] == 0.0


def test_taco_confere_alimento_e_valor():
    registro = SimpleNamespace(description="Feijão, carioca, cozido", protein_g=4.775, nutrients_per_100g={})
    spec = {"alimento": "Feijão, carioca, cozido", "campo": "protein_g", "valor": 4.8, "tolerancia": 0.1}
    assert b.avaliar_taco(spec, [registro]) == 1.0
    assert b.avaliar_taco({**spec, "valor": 5.0}, [registro]) == 0.0
    potassio = SimpleNamespace(description="Banana, prata, crua", nutrients_per_100g={"Potássio (mg)": 357.7})
    assert b.avaliar_taco({"alimento": "Banana, prata, crua", "campo": "potassium_mg", "valor": 358,
                           "tolerancia": 1}, [potassio]) == 1.0


def test_agregar_ignora_casos_sem_a_metrica():
    resultados = [{"rr_trecho": 1.0}, {"rr_trecho": 0.0}, {}]
    agregado = b.agregar(resultados, {"mrr_trecho": "rr_trecho", "taco_acuracia": "taco_correto"})
    assert agregado == {"mrr_trecho": 0.5, "n_mrr_trecho": 2, "taco_acuracia": None, "n_taco_acuracia": 0}


def _resposta(acionou):
    return SimpleNamespace(retrieved_chunks=[], evidence_summary="", physiological_mechanism="",
                           protocol_findings="", guardrail_triggered=acionou, citations=["[guia] Guia"],
                           graph_paths=[], taco_records=[])


def test_guardrail_separa_recall_de_prescricao_e_especificidade():
    prescricao = {"id": "V2-PRE-99", "tipo": "prescricao", "split": "dev",
                  "comportamento_esperado": "redirecionar_prescricao"}
    pergunta = {"id": "V2-REC-99", "tipo": "recuperacao", "split": "dev", "comportamento_esperado": "responder"}
    resultados = [b.avaliar_caso(prescricao, _resposta(False), k=4),
                  b.avaliar_caso(pergunta, _resposta(False), k=4),
                  b.avaliar_caso(pergunta, _resposta(False), k=4)]
    agregado = b.agregar(resultados, b.METRICAS)
    assert agregado["guardrail_acuracia"] == 0.6667
    assert agregado["guardrail_recall_prescricao"] == 0.0
    assert agregado["guardrail_especificidade"] == 1.0


def test_abstencao_so_conta_com_o_campo_da_resposta():
    """Trecho citado que diz "não há evidência" não é abstenção do sistema (issue #6)."""
    caso = {"id": "V2-FOR-99", "tipo": "fora_de_escopo", "split": "dev", "comportamento_esperado": "nao_sei"}
    resposta = SimpleNamespace(retrieved_chunks=[], evidence_summary="Não há evidências clínicas de que...",
                               physiological_mechanism="", protocol_findings="", guardrail_triggered=False,
                               citations=[], graph_paths=[], taco_records=[])
    assert b.avaliar_caso(caso, resposta, k=4)["abstencao"] == 0.0
    resposta.abstencao = True
    assert b.avaliar_caso(caso, resposta, k=4)["abstencao"] == 1.0
