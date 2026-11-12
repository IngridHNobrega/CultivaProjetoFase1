import re
import unicodedata
from typing import Dict, List, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from src.config import (
    MAX_CHUNKS_PER_DOC,
    MODO_DENSO,
    RERANK_BONUS_EVIDENCIA,
    RERANK_PESO_SOBREPOSICAO,
    RRF_K,
    TOP_K_BM25,
    TOP_K_FINAL,
    TOP_K_VECTOR,
    WEIGHT_BM25,
    WEIGHT_VECTOR,
)
from src.models.schemas import DocumentChunk, RetrievedChunk

PORTUGUESE_STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as",
    "ate", "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles",
    "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em", "entre",
    "era", "eram", "essa", "essas", "esse", "esses", "esta", "estas", "este",
    "estes", "eu", "foi", "for", "foram", "ha", "isso", "isto", "ja", "la",
    "lhe", "lhes", "lo", "mas", "me", "mesmo", "meu", "meus", "minha", "minhas",
    "muito", "na", "nas", "nem", "no", "nos", "nossa", "nossas", "nosso",
    "nossos", "num", "numa", "o", "os", "ou", "para", "pela", "pelas", "pelo",
    "pelos", "por", "qual", "quando", "que", "quem", "se", "seja", "sem", "seu",
    "seus", "so", "sua", "suas", "sao", "tambem", "te", "tem", "tendo", "tenho",
    "ter", "teu", "teus", "tu", "tua", "tuas", "tudo", "um", "uma", "umas",
    "uns", "voce", "voces",
}

CLINICAL_SYNONYMS: Dict[str, str] = {
    "classificacao nova": "alimentos in natura minimamente processados ingredientes culinarios ultraprocessados",
    "quatro categorias": "in natura minimamente processados ingredientes culinarios processados ultraprocessados",
    "regra de ouro": "prefira sempre alimentos in natura ou minimamente processados e preparacoes culinarias a alimentos ultraprocessados dez passos",
    "ultraprocessados": "formulacoes industriais biscoitos refrigerantes embutidos macarrao instantaneo calorias por grama saciedade",
    "ingredientes culinarios": "oleos gorduras sal acucar pequenas quantidades preparacoes culinarias dez passos",
    "comensalidade": "ato de comer regularidade atencao ambientes apropriados companhia",
    "obstaculos": "informacao oferta custo habilidades culinarias tempo publicidade dez passos",
    "doencas especificas": "nutricionistas adaptem recomendacoes condicoes especificas",
    "fibra soluvel": "beta-glucana psyllium viscosidade acidos biliares dietary fiber beta-glucan",
    "aveia": "beta-glucana fibra soluvel oat beta-glucan ldl cholesterol",
    "acucar no sangue": "glicemia glicose hba1c diabetes glycemic index insulin resistance",
    "acucar": "glicose glicemia carboidrato ingredientes culinarios",
    "acafrao": "curcuma curcumina piperina biodisponibilidade curcumin piperine",
    "acafrao-da-terra": "curcuma curcumina piperina curcumin piperine",
    "curcuma": "curcumina piperina biodisponibilidade glicuronidacao curcumin piperine",
    "pressao alta": "hipertensao pressao arterial dash sodio potassio blood pressure",
    "pressao arterial": "hipertensao dash sodio potassio nitrato blood pressure dietary nitrate",
    "colesterol ruim": "colesterol ldl dislipidemia fitoesterois phytosterols ldl cholesterol",
    "colesterol ldl": "dislipidemia fitoesterois gorduras saturadas phytosterols ldl cholesterol",
    "ferritina": "ferro heme nao-heme vitamina c acido ascorbico fitatos taninos non-heme iron ascorbic acid",
    "ferro": "ferro heme nao-heme vitamina c acido ascorbico fitatos taninos feijao non-heme iron",
    "creatina": "fosfocreatina atp creatinina cistatina renal creatine supplementation",
    "flora intestinal": "microbiota intestinal fibras agcc butirato short-chain fatty acids",
    "intestino": "microbiota intestinal fibras soluveis viscosidade",
    "ganhar massa": "hipertrofia sintese proteica mtorc1 leucina proteina muscle mass leucine",
    "massa muscular": "hipertrofia sintese proteica mtorc1 leucina sarcopenia protein intake",
    "rins": "renal creatinina cistatina filtracao glomerular nefropatia renal function",
    "doenca renal": "doenca renal cronica potassio nefropatia",
    "dormir pouco": "restricao de sono leptina grelina circadiano melatonina",
    "fome": "saciedade apetite grelina leptina glp-1 comensalidade",
    "brocolis": "brassicas cruciferos sulforafano glicorafanina mirosinase broccoli sulforaphane",
    "couve": "brassicas cruciferos sulforafano glicorafanina",
}

EVIDENCE_GRADE_BONUS: Dict[str, float] = {
    "GRADE_A": 0.08,
    "GRADE_B": 0.05,
    "GUIDELINE_CONSENSUS": 0.06,
    "GRADE_C": 0.02,
}


def normalize_text(text: str) -> str:
    """Remove acentos e normaliza mantendo hifens e números de siglas biomédicas."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents


def expand_clinical_synonyms(text: str) -> str:
    """Expande expressões populares para terminologia clínica e bioquímica equivalente."""
    norm = normalize_text(text)
    additions: List[str] = []
    for phrase, expansion in CLINICAL_SYNONYMS.items():
        if phrase in norm:
            additions.append(expansion)
    if additions:
        return f"{norm} {' '.join(additions)}"
    return norm


def tokenize_biomedical(text: str) -> List[str]:
    """Tokeniza preservando siglas científicas (ex: hba1c, ldl-c, glp-1, mtorc1, fe2+)."""
    norm = expand_clinical_synonyms(text)
    raw_tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", norm)
    tokens: List[str] = []
    for tok in raw_tokens:
        if len(tok) > 1 and tok not in PORTUGUESE_STOPWORDS:
            tokens.append(tok)
            if "-" in tok:
                for sub in tok.split("-"):
                    if len(sub) > 1 and sub not in PORTUGUESE_STOPWORDS:
                        tokens.append(sub)
    return tokens


class HybridRetriever:
    """
    Motor de Busca Híbrida:
    1. Índice Léxico BM25 (termos exatos, siglas, biomarcadores e compostos).
    2. Índice Vetorial Denso no ChromaDB (embeddings multilíngues 384d). Padrão desde a issue #35
       (`MODO_DENSO="chromadb_pure"`). O índice local TF-IDF n-gramas + SVD/LSA só é construído
       quando usado: no modo `chromadb_dense` (mistura 55% ChromaDB + 45% LSA), no `legacy_lsa`
       ou como alternativa quando o ChromaDB está desligado.
    3. Reciprocal Rank Fusion (RRF) combinando rankings léxico e semântico.
    4. Reranker opcional por sobreposição de termos e grau de evidência GRADE. Desligado
       por padrão desde a issue #35: na escala original ele decidia o ranking sozinho,
       porque valia cerca de 10 vezes a fusão RRF.
    """

    def __init__(
        self,
        chunks: List[DocumentChunk],
        top_k_bm25: int = TOP_K_BM25,
        top_k_vector: int = TOP_K_VECTOR,
        rrf_k: int = RRF_K,
        weight_bm25: float = WEIGHT_BM25,
        weight_vector: float = WEIGHT_VECTOR,
        use_vector_store: bool = True,
        vector_mode: str = MODO_DENSO,
        peso_sobreposicao: float = RERANK_PESO_SOBREPOSICAO,
        bonus_evidencia: bool = RERANK_BONUS_EVIDENCIA,
    ) -> None:
        if not chunks:
            raise ValueError("A lista de chunks para o HybridRetriever não pode estar vazia.")

        self.chunks = chunks
        self.top_k_bm25 = top_k_bm25
        self.top_k_vector = top_k_vector
        self.rrf_k = rrf_k
        self.weight_bm25 = weight_bm25
        self.weight_vector = weight_vector
        self.use_vector_store = use_vector_store
        self.vector_mode = vector_mode
        self.peso_sobreposicao = peso_sobreposicao
        self.bonus_evidencia = bonus_evidencia

        # 1. Construção do índice BM25
        self.tokenized_corpus = [
            tokenize_biomedical(chunk.contextualized_text) for chunk in self.chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # 2. Índice local TF-IDF + SVD/LSA: construído sob demanda (`_garantir_indice_lsa`).
        self.tfidf: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None

        # 3. Banco Vetorial Persistente (ChromaDB + Embeddings Multilíngues 384d)
        self.vector_store = None
        if self.use_vector_store and self.vector_mode != "legacy_lsa":
            from src.retrieval.vector_store import NutritionVectorStore

            is_full_corpus = len(self.chunks) >= 150
            self.vector_store = NutritionVectorStore(
                chunks=self.chunks,
                use_persistent=is_full_corpus,
            )

    def _garantir_indice_lsa(self) -> None:
        """Constrói o índice TF-IDF + SVD/LSA na primeira vez que ele for necessário."""
        if self.tfidf is not None:
            return
        normalized_docs = [
            expand_clinical_synonyms(chunk.contextualized_text) for chunk in self.chunks
        ]
        tfidf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
        tfidf_matrix = tfidf.fit_transform(normalized_docs)

        n_components = min(32, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
        if n_components >= 2:
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            self.doc_vectors = normalize(self.svd.fit_transform(tfidf_matrix))
        else:
            self.svd = None
            self.doc_vectors = normalize(tfidf_matrix.toarray())
        self.tfidf_matrix_norm = normalize(tfidf_matrix)
        self.tfidf = tfidf

    def _search_bm25(self, query: str) -> List[Tuple[int, float]]:
        query_tokens = tokenize_biomedical(query)
        if not query_tokens:
            return [(idx, 0.0) for idx in range(min(self.top_k_bm25, len(self.chunks)))]
        scores = self.bm25.get_scores(query_tokens)
        ranked_indices = np.argsort(scores)[::-1][: self.top_k_bm25]
        return [(int(idx), float(scores[idx])) for idx in ranked_indices]

    def _search_vector(self, query: str) -> List[Tuple[int, float]]:
        if self.vector_store is not None and self.vector_mode == "chromadb_pure":
            return self.vector_store.similarity_search(query, top_k=self.top_k_vector)

        self._garantir_indice_lsa()
        expanded_query = expand_clinical_synonyms(query)
        q_tfidf = self.tfidf.transform([expanded_query])
        q_tfidf_norm = normalize(q_tfidf)

        cosine_tfidf = (self.tfidf_matrix_norm @ q_tfidf_norm.T).toarray().ravel()

        if self.svd is not None:
            q_dense = normalize(self.svd.transform(q_tfidf))
            cosine_lsa = (self.doc_vectors @ q_dense.T).ravel()
            lsa_sim = 0.65 * cosine_tfidf + 0.35 * cosine_lsa
        else:
            lsa_sim = cosine_tfidf

        if self.vector_store is not None:
            chroma_hits = self.vector_store.similarity_search(
                query, top_k=min(len(self.chunks), max(self.top_k_vector * 3, 24))
            )
            chroma_scores = np.zeros(len(self.chunks), dtype=np.float32)
            for doc_idx, sim_score in chroma_hits:
                chroma_scores[doc_idx] = sim_score
            # Combina similaridade do Banco Vetorial Denso (ChromaDB 384d) + precisão contextual LSA
            combined_sim = 0.55 * chroma_scores + 0.45 * lsa_sim
        else:
            combined_sim = lsa_sim

        ranked_indices = np.argsort(combined_sim)[::-1][: self.top_k_vector]
        return [(int(idx), float(combined_sim[idx])) for idx in ranked_indices]

    def _clinical_rerank_score(
        self,
        query_tokens: List[str],
        chunk: DocumentChunk,
        chunk_tokens: List[str],
        rrf_score: float,
    ) -> float:
        if not query_tokens:
            return rrf_score
        q_set = set(query_tokens)
        c_set = set(chunk_tokens)
        overlap_ratio = len(q_set.intersection(c_set)) / max(len(q_set), 1)
        grade_bonus = EVIDENCE_GRADE_BONUS.get(chunk.evidence_level, 0.0) if self.bonus_evidencia else 0.0
        return float(rrf_score + (self.peso_sobreposicao * overlap_ratio) + grade_bonus)

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K_FINAL,
        max_chunks_per_doc: int = MAX_CHUNKS_PER_DOC,
    ) -> List[RetrievedChunk]:
        bm25_results = self._search_bm25(query)
        vector_results = self._search_vector(query)

        bm25_rank_map: Dict[int, Tuple[int, float]] = {
            doc_idx: (rank + 1, score) for rank, (doc_idx, score) in enumerate(bm25_results)
        }
        vector_rank_map: Dict[int, Tuple[int, float]] = {
            doc_idx: (rank + 1, score) for rank, (doc_idx, score) in enumerate(vector_results)
        }

        candidate_indices = set(bm25_rank_map.keys()).union(set(vector_rank_map.keys()))
        query_tokens = tokenize_biomedical(query)

        retrieved_items: List[RetrievedChunk] = []
        for idx in candidate_indices:
            b_rank, b_score = bm25_rank_map.get(idx, (None, 0.0))
            v_rank, v_score = vector_rank_map.get(idx, (None, 0.0))

            rrf = 0.0
            if b_rank is not None:
                rrf += self.weight_bm25 / (self.rrf_k + b_rank)
            if v_rank is not None:
                rrf += self.weight_vector / (self.rrf_k + v_rank)

            chunk = self.chunks[idx]
            rerank_val = self._clinical_rerank_score(
                query_tokens=query_tokens,
                chunk=chunk,
                chunk_tokens=self.tokenized_corpus[idx],
                rrf_score=rrf,
            )

            retrieved_items.append(
                RetrievedChunk(
                    chunk=chunk,
                    bm25_rank=b_rank,
                    bm25_score=round(b_score, 4),
                    vector_rank=v_rank,
                    vector_score=round(v_score, 4),
                    rrf_score=round(rrf, 6),
                    rerank_score=round(rerank_val, 6),
                )
            )

        retrieved_items.sort(key=lambda item: item.rerank_score, reverse=True)

        # Diversificação por documento/capítulo: evita que um único capítulo longo monopolize o Top-K
        if max_chunks_per_doc > 0 and top_k >= 2:
            diversified: List[RetrievedChunk] = []
            overflow: List[RetrievedChunk] = []
            doc_counts: Dict[str, int] = {}

            for item in retrieved_items:
                doc_id = item.chunk.doc_id
                count = doc_counts.get(doc_id, 0)
                if count < max_chunks_per_doc:
                    diversified.append(item)
                    doc_counts[doc_id] = count + 1
                    if len(diversified) == top_k:
                        break
                else:
                    overflow.append(item)

            if len(diversified) < top_k:
                for item in overflow:
                    diversified.append(item)
                    if len(diversified) == top_k:
                        break
            return diversified

        return retrieved_items[:top_k]
