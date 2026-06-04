from __future__ import annotations
from dataclasses import dataclass

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import numpy as np
from src.config import settings


_cached: dict[str, CrossEncoder] = {}


def _get_model(model_name: str) -> CrossEncoder:
    if model_name not in _cached:
        _cached[model_name] = CrossEncoder(model_name, local_files_only=False)
    return _cached[model_name]

@dataclass
class RerankResult:
    chunk:        dict   # chunk gốc với đầy đủ metadata
    rerank_score: float  # score CrossEncoder
    rrf_score:    float  # score từ hybrid search
    source:       str    # 'faiss' | 'bm25' | 'both'


def rerank(
    rewrite_result: dict,
    search_results: list,
    k:              int = 5,
    model_name:     str = settings.RERANKER_MODEL,
) -> list[RerankResult]:

    if not search_results:
        return []

    query = rewrite_result.get('rewrite_query') or \
            rewrite_result.get('original_query', '')
    model = _get_model(model_name)

    # Dùng text_rerank thay vì text_index
    pairs = [
        (query, r.chunk.get('text_rerank') or r.chunk.get('text', ''))
        for r in search_results
    ]

    scores = model.predict(pairs)
    scores = np.array(scores)
    if scores.ndim == 2:
        scores = scores[:, 1] if scores.shape[1] == 2 else scores.flatten()

    ranked = sorted(zip(scores, search_results), key=lambda x: x[0], reverse=True)

    return [
        RerankResult(
            chunk        = r.chunk,
            rerank_score = float(score),
            rrf_score    = r.rrf_score,
            source       = r.source,
        )
        for score, r in ranked[:k]
    ]