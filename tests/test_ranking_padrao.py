"""Ranking padrão da busca híbrida (issue #35).

Sem configuração, a nota final de cada Trecho é a da fusão RRF: sobreposição de termos 0,
bônus de evidência desligado e busca densa só no ChromaDB. Estes testes evitam que uma mudança
de configuração religue o reranker sem ninguém perceber. Rodam sem variáveis de ambiente
`MODO_DENSO` e `RERANK_*`, como no CI.
"""

import json
from pathlib import Path

import pytest

from src import config
from src.rag.contrato import trecho_para_chunk
from src.retrieval.hybrid_retriever import HybridRetriever

RAIZ = Path(__file__).resolve().parents[1]
GUIA = RAIZ / "corpus/nutricao/rag/guia_alimentar_populacao_brasileira_2ed_2014.jsonl"


def test_configuracao_padrao_e_rrf_puro_sobre_chromadb():
    assert config.MODO_DENSO == "chromadb_pure"
    assert config.RERANK_PESO_SOBREPOSICAO == 0.0
    assert config.RERANK_BONUS_EVIDENCIA is False


@pytest.fixture(scope="module")
def retriever_padrao():
    chunks = [trecho_para_chunk(json.loads(linha)) for linha in GUIA.read_text(encoding="utf-8").splitlines()]
    # Sem o banco vetorial: o teste cobre a nota final e o índice LSA sob demanda, não os embeddings.
    return HybridRetriever(chunks, use_vector_store=False)


def test_retriever_sem_argumentos_usa_o_padrao(retriever_padrao):
    assert retriever_padrao.vector_mode == "chromadb_pure"
    assert retriever_padrao.peso_sobreposicao == 0.0
    assert retriever_padrao.bonus_evidencia is False


def test_nota_final_e_a_da_fusao_rrf(retriever_padrao):
    resultados = retriever_padrao.retrieve("Qual é a regra de ouro do Guia Alimentar?", top_k=4)
    assert resultados
    for item in resultados:
        assert item.rerank_score == pytest.approx(item.rrf_score, abs=1e-6)


def test_indice_lsa_so_e_construido_quando_usado():
    chunks = [trecho_para_chunk(json.loads(linha)) for linha in GUIA.read_text(encoding="utf-8").splitlines()]
    retriever = HybridRetriever(chunks, use_vector_store=False)
    assert retriever.tfidf is None
    # Sem o ChromaDB, a busca densa cai no LSA, que é construído na primeira consulta.
    retriever.retrieve("comer com regularidade e atenção", top_k=2)
    assert retriever.tfidf is not None
