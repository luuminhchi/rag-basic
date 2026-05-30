"""CrossEncoder reranker for re-scoring retrieved documents."""
from __future__ import annotations

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import numpy as np
from src.config import settings


_cached: dict[str, CrossEncoder] = {}


def _get_model(model_name: str) -> CrossEncoder:
    if model_name not in _cached:
        _cached[model_name] = CrossEncoder(model_name, local_files_only=False)
    return _cached[model_name]


def rerank(
    query: str,
    docs: list[Document],
    k: int = 5,
    model_name: str = settings.RERANKER_MODEL,
) -> list[Document]:
    """Re-score docs with a CrossEncoder and return top-k."""
    if not docs:
        return []
    model = _get_model(model_name)
    pairs = [(query, doc.page_content) for doc in docs]
    scores = model.predict(pairs)
    scores = np.array(scores)

    if scores.ndim == 2:
        if scores.shape[1] == 2:
            scores = scores[:, 1]  # use relevance score
        elif scores.shape[1] == 1:
            scores = scores.flatten()


    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:k]]
