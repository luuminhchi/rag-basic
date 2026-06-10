import pickle
import numpy as np
import faiss
from dataclasses import dataclass
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS as LangchainFAISS
from langchain_huggingface import HuggingFaceEmbeddings

@dataclass
class SearchResult:
    chunk:     dict
    rrf_score: float
    source:    str   # 'faiss' | 'bm25' | 'both'


class HybridSearcher:
    def __init__(self, faiss_index, bm25_index, chunks: list[dict], embedder):
        self.faiss    = faiss_index
        self.bm25     = bm25_index
        self.chunks   = chunks
        self.embedder = embedder

        self.id_to_chunk    = {c['metadata']['chunk_id']: c for c in chunks}
        self.chunk_ids_list = [c['metadata']['chunk_id'] for c in chunks]


    # FAISS
    def _search_faiss(self, injected_query: str, fetch_k: int) -> list[tuple]:
        """Returns: [(chunk_id, score), ...]"""
        q_vec = self.embedder.encode(
            injected_query,
            normalize_embeddings=True
        ).reshape(1, -1).astype('float32')

        scores, indices = self.faiss.search(q_vec, fetch_k)

        return [
            (self.chunk_ids_list[idx], float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx != -1
        ]


    # BM25
    def _search_bm25(self, rewrite_query: str, fetch_k: int) -> list[tuple]:
        """Returns: [(chunk_id, score), ...]"""
        tokens     = rewrite_query.lower().split()
        bm25_scores = self.bm25.get_scores(tokens)

        top_indices = np.argsort(bm25_scores)[::-1][:fetch_k]

        return [
            (self.chunk_ids_list[i], float(bm25_scores[i]))
            for i in top_indices
            if bm25_scores[i] > 0
        ]


    # RRF fusion
    def _rrf_fusion(
        self,
        faiss_hits: list[tuple],  # [(chunk_id, score), ...]
        bm25_hits:  list[tuple],
        K: int = 60,
    ) -> list[SearchResult]:
        """
        Trả về list SearchResult đã sort theo rrf_score giảm dần.
        Giữ score + source theo suốt để dùng ở bước sau.
        """
        rrf_scores  = {}
        source_map  = {}  # chunk_id → 'faiss' | 'bm25' | 'both'

        for rank, (cid, _) in enumerate(faiss_hits):
            rrf_scores[cid]  = rrf_scores.get(cid, 0) + 1 / (K + rank + 1)
            source_map[cid]  = 'faiss'

        for rank, (cid, _) in enumerate(bm25_hits):
            rrf_scores[cid]  = rrf_scores.get(cid, 0) + 1 / (K + rank + 1)
            source_map[cid]  = 'both' if source_map.get(cid) == 'faiss' else 'bm25'

        # Sort theo rrf_score (__getitem__ chỉ sắp xếp các trường score)
        sorted_cids = sorted(rrf_scores, key=rrf_scores.__getitem__, reverse=True)

        return [
            SearchResult(
                chunk     = self.id_to_chunk[cid],
                rrf_score = rrf_scores[cid],
                source    = source_map[cid],
            )
            for cid in sorted_cids
            if cid in self.id_to_chunk   # safety check
        ]
    # ─────────────────────────────────────────
    # Filter
    # ─────────────────────────────────────────
    def _apply_filter(
        self,
        results: list[SearchResult],
        filter_dict: dict,
    ) -> list[SearchResult]:
        if not filter_dict:
            return results

        filtered = []
        for r in results:
            meta  = r.chunk.get('metadata', {})
            match = True

            for key, val in filter_dict.items():
                if val is None:
                    continue
                meta_val = meta.get(key)

                if isinstance(meta_val, list):
                    # List field: check intersection
                    check = val if isinstance(val, list) else [val]
                    if not set(check) & set(meta_val):
                        match = False; break
                else:
                    if meta_val != val:
                        match = False; break

            if match:
                filtered.append(r)

        return filtered  # vẫn giữ thứ tự rrf_score vì input đã sorted


    # ─────────────────────────────────────────
    # Main search
    # ─────────────────────────────────────────
    def search(
        self,
        rewrite_result: dict,
        top_k:         int  = 10,
    ) -> list[SearchResult]:

        injected_query = rewrite_result['injected_query']
        rewrite_query  = rewrite_result['rewrite_query']
        filter_dict    = rewrite_result.get('filter', {})
        fetch_k        = top_k * 3

        # ── 1. Search 2 index ──────────────────────
        faiss_hits = self._search_faiss(injected_query, fetch_k)
        bm25_hits  = self._search_bm25(rewrite_query,   fetch_k)

        # ── 2. RRF fusion → list SearchResult sorted ─
        fused = self._rrf_fusion(faiss_hits, bm25_hits)

        # ── 3. Filter có fallback ──────────────────
        filtered = self._apply_filter(fused, filter_dict)

        if len(filtered) < top_k // 2:
            # Relax bỏ field ít quan trọng nhất
            filtered = self._apply_filter(fused, _relax_filter(filter_dict))

        if not filtered:
            # Fallback cuối: không filter, vẫn giữ rank RRF
            filtered = fused

        return filtered[:top_k]


# Filter relaxation

# Thứ tự ưu tiên: số nhỏ = quan trọng hơn = giữ lâu hơn
FILTER_PRIORITY = {
    'doc_section':       1,
    'doc_subsection':    2,
    'vehicle_groups':    3,
    'violation_category':4,
}

def _relax_filter(filter_dict: dict) -> dict:
    """Bỏ field ít quan trọng nhất, luôn giữ doc_section."""
    relaxed    = dict(filter_dict)
    candidates = [
        f for f in relaxed
        if f != 'doc_section' and f in FILTER_PRIORITY
    ]
    if candidates:
        # Bỏ field có priority số lớn nhất (ít quan trọng nhất)
        to_drop = max(candidates, key=lambda f: FILTER_PRIORITY[f])
        del relaxed[to_drop]
    return relaxed


# ─────────────────────────────────────────
# Singleton loader
# ─────────────────────────────────────────
_searcher: HybridSearcher | None = None

def _get_searcher() -> HybridSearcher:
    global _searcher
    if _searcher is not None:
        return _searcher

    from src.config import settings

    # Load embedder
    embedder = SentenceTransformer(settings.embedding_model)

    # Load LangChain FAISS để lấy raw index + chunk ordering
    lc_faiss = LangchainFAISS.load_local(
        folder_path=str(settings.vector_store_dir),
        embeddings=HuggingFaceEmbeddings(model_name=settings.embedding_model),
        allow_dangerous_deserialization=True,
    )
    raw_faiss = lc_faiss.index

    # Reconstruct chunks list theo đúng thứ tự của faiss index
    chunks = []
    for pos in range(raw_faiss.ntotal):
        doc_id  = lc_faiss.index_to_docstore_id[pos]
        doc     = lc_faiss.docstore.search(doc_id)
        meta    = dict(doc.metadata)
        orig    = meta.pop('original_text', doc.page_content)
        chunks.append({'metadata': meta, 'text': orig})

    # Load BM25
    with open(settings.bm25_path, 'rb') as f:
        bm25_data = pickle.load(f)
    bm25 = bm25_data['index']

    _searcher = HybridSearcher(
        faiss_index=raw_faiss,
        bm25_index=bm25,
        chunks=chunks,
        embedder=embedder,
    )
    return _searcher


def search(rewrite_result: dict, top_k: int = 10) -> list[SearchResult]:
    return _get_searcher().search(rewrite_result, top_k=top_k)

