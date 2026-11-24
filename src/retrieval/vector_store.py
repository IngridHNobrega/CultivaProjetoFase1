import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from sklearn.preprocessing import normalize

from src.config import (
    PROJECT_ROOT,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_SEARCH,
    VECTOR_COLLECTION_NAME,
    VECTOR_STORE_DIR,
)
from src.agent.traceability import corpus_version_do_indice
from src.models.schemas import DocumentChunk
from src.retrieval.hybrid_retriever import expand_clinical_synonyms

_FASTEMBED_MODEL_CACHE: Dict[str, Any] = {}


def _caminho_relativo(caminho: Path) -> str:
    """Caminho relativo à raiz do projeto, para não gravar o caminho da máquina em artefatos."""
    try:
        return str(Path(caminho).resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(caminho)


def configuracao_hnsw() -> Dict[str, Any]:
    """Configuração do índice HNSW (cosseno) usada ao criar a coleção."""
    return {
        "space": "cosine",
        "ef_construction": HNSW_EF_CONSTRUCTION,
        "ef_search": HNSW_EF_SEARCH,
    }


def impressao_digital(
    chunks: List[DocumentChunk], modelo: str, corpus_version: Optional[str] = None
) -> str:
    """Hash da versão do corpus, do modelo, do HNSW e do conteúdo indexado.

    A versão do corpus inclui manifesto e JSONL, inclusive metadados que não aparecem no texto
    contextualizado. Assim, qualquer mudança na versão rastreada cria uma coleção nova.
    """
    h = hashlib.sha256(modelo.encode())
    h.update((corpus_version or corpus_version_do_indice(chunks)).encode())
    h.update(repr(sorted(configuracao_hnsw().items())).encode())
    for c in chunks:
        h.update(c.chunk_id.encode())
        h.update(c.contextualized_text.encode())
    return h.hexdigest()


def _get_fastembed_model(model_name: str) -> Any:
    """Carrega e mantém em cache de processo o modelo ONNX de embeddings densos."""
    if model_name not in _FASTEMBED_MODEL_CACHE:
        from fastembed import TextEmbedding

        _FASTEMBED_MODEL_CACHE[model_name] = TextEmbedding(model_name=model_name)
    return _FASTEMBED_MODEL_CACHE[model_name]


class DenseMultilingualEmbedder:
    """
    Gerador de Embeddings Densos Multilíngues (384 dimensões, normalizados em norma L2)
    baseado em `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (via FastEmbed/ONNX).
    Permite alinhamento semântico cross-lingual entre consultas em português e diretrizes/artigos em PT-BR e EN.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        dimension: int = EMBEDDING_DIMENSION,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model = _get_fastembed_model(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        raw_vectors = np.array(list(self._model.embed(texts)), dtype=np.float32)
        normalized = normalize(raw_vectors, norm="l2")
        return normalized.tolist()

    def embed_query(self, query: str) -> List[float]:
        expanded = expand_clinical_synonyms(query)
        raw_vec = np.array(list(self._model.embed([expanded])), dtype=np.float32)
        normalized = normalize(raw_vec, norm="l2")
        return normalized[0].tolist()


class NutritionVectorStore:
    """
    Banco de Dados Vetorial Persistente (ChromaDB + Índice HNSW Cosseno):
    Armazena em disco (`data/vector_store/chroma_db`) os embeddings densos de 384 dimensões,
    os textos contextualizados dos chunks e os metadados auditáveis de cada fonte científica.
    """

    def __init__(
        self,
        chunks: List[DocumentChunk],
        persist_directory: Optional[Path] = VECTOR_STORE_DIR,
        collection_name: str = VECTOR_COLLECTION_NAME,
        embedding_model_name: str = EMBEDDING_MODEL_NAME,
        use_persistent: bool = True,
    ) -> None:
        self.chunks = chunks
        self.chunk_id_to_index: Dict[str, int] = {
            c.chunk_id: idx for idx, c in enumerate(chunks)
        }
        self.persist_directory = persist_directory
        # Corpus, modelo ou parâmetros diferentes geram outra coleção. O corpus_version também
        # cobre mudanças de manifesto/metadados que não alteram o texto contextualizado.
        self.corpus_version = corpus_version_do_indice(chunks)
        self.fingerprint = impressao_digital(chunks, embedding_model_name, self.corpus_version)
        self.collection_name = f"{collection_name}_{self.fingerprint[:12]}"
        self.embedding_model_name = embedding_model_name
        self.use_persistent = use_persistent and (persist_directory is not None)

        self.embedder = DenseMultilingualEmbedder(model_name=embedding_model_name)

        if self.use_persistent and self.persist_directory is not None:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        else:
            self.client = chromadb.EphemeralClient()

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            configuration={"hnsw": configuracao_hnsw()},
            metadata={
                "embedding_model": self.embedding_model_name,
                "dimension": str(self.embedder.dimension),
                "corpus_version": self.corpus_version,
            },
        )
        self._ensure_indexed()

    def _ensure_indexed(self) -> int:
        """
        Verifica se todos os chunks já estão persistidos no ChromaDB.
        Caso o banco em disco já contenha todos os IDs esperados, reutiliza o índice
        persistido imediatamente sem recalcular embeddings.
        """
        if not self.chunks:
            return 0

        expected_ids = [c.chunk_id for c in self.chunks]
        existing_count = self.collection.count()

        if existing_count == len(expected_ids):
            existing = self.collection.get(ids=expected_ids[:5], include=[])
            if len(existing.get("ids", [])) == min(5, len(expected_ids)):
                return existing_count

        return self.index_chunks(self.chunks)

    def index_chunks(self, chunks: List[DocumentChunk], batch_size: int = 128) -> int:
        """Gera os embeddings densos L2-normalizados e persiste no banco vetorial ChromaDB."""
        texts = [expand_clinical_synonyms(c.contextualized_text) for c in chunks]
        vectors = self.embedder.embed_documents(texts)

        for start in range(0, len(chunks), batch_size):
            end = min(start + batch_size, len(chunks))
            batch_chunks = chunks[start:end]
            batch_vecs = vectors[start:end]

            ids = [c.chunk_id for c in batch_chunks]
            docs = [c.contextualized_text for c in batch_chunks]
            metadatas: List[Dict[str, Any]] = [
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "fonte_id": c.doc_id,
                    "title": c.title,
                    "source_organization": c.source_organization,
                    "publication_year": int(c.publication_year),
                    "clinical_domain": c.clinical_domain,
                    "evidence_level": c.evidence_level,
                    "section_path": c.section_path,
                    "fonte_url": c.fonte_url or "",
                    "doi": c.doi or "",
                    "licenca": c.licenca or "pendente",
                    "approval_status": c.approval_status or "pendente",
                    "pagina_pdf": int(c.pagina_pdf) if c.pagina_pdf is not None else -1,
                }
                for c in batch_chunks
            ]

            self.collection.upsert(
                ids=ids,
                embeddings=batch_vecs,
                documents=docs,
                metadatas=metadatas,
            )

        return self.collection.count()

    def similarity_search(
        self,
        query: str,
        top_k: int = 8,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[int, float]]:
        """
        Busca por similaridade de cosseno no índice HNSW do ChromaDB.
        Retorna lista de tuplas (chunk_index, cosine_similarity_score).
        A qualidade da busca aproximada depende de `ef_search` (ver `configuracao_hnsw`).
        """
        if not self.chunks:
            return []

        n_results = min(top_k, len(self.chunks))
        query_vec = self.embedder.embed_query(query)

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": n_results,
            "include": ["distances", "metadatas"],
        }
        if where:
            query_kwargs["where"] = where

        res = self.collection.query(**query_kwargs)
        ids_list = res.get("ids", [[]])[0]
        distances_list = res.get("distances", [[]])[0]

        results: List[Tuple[int, float]] = []
        for chunk_id, dist in zip(ids_list, distances_list):
            if chunk_id in self.chunk_id_to_index:
                idx = self.chunk_id_to_index[chunk_id]
                # No ChromaDB com hnsw:space="cosine", distance = 1.0 - cosine_similarity
                cosine_sim = max(0.0, 1.0 - float(dist))
                results.append((idx, cosine_sim))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas auditáveis do Banco Vetorial persistido."""
        unique_sources = {c.doc_id for c in self.chunks}
        unique_docs = {c.doc_id for c in self.chunks}
        return {
            "vector_db_engine": "ChromaDB (HNSW Cosine Index + SQLite Metadata Store)",
            "persistent": self.use_persistent,
            "persist_directory": _caminho_relativo(self.persist_directory) if self.persist_directory else "in-memory",
            "collection_name": self.collection_name,
            "content_fingerprint": self.fingerprint,
            "corpus_version": self.corpus_version,
            "embedding_model": self.embedding_model_name,
            "embedding_dimension": self.embedder.dimension,
            "distance_metric": "cosine (L2-normalized vectors)",
            "hnsw": configuracao_hnsw(),
            "total_vectors_indexed": self.collection.count(),
            "unique_doc_ids": len(unique_docs),
            "unique_source_documents": len(unique_sources),
        }
