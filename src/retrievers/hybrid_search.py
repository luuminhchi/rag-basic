import pickle
import numpy as np
from rank_bm25 import BM25Okapi

def hybrid_search(
        processed_query: dict,
        vectordb,
        bm25_path: str,
        top_k: int = 10,
        target_section: str = "",        # [MOI] section tu Query Router
) -> list:
    with open(bm25_path, 'rb') as f:
        bm25 = pickle.load(f)
    bm25_index = bm25['index']
    bm25_ids = bm25['ids']

    # Dùng injected_query cho FAISS: khớp với embedding space của chunks đã index
    faiss_query = processed_query.get('injected_query') or processed_query.get('rewrite_query', '')
    rewrite_query = processed_query.get('rewrite_query', '')

    # Lấy nhiều hơn để doc_map có đủ Document objects cho BM25 results
    fetch_k = max(top_k * 3, 30)
    faiss_results = vectordb.similarity_search_with_score(
        query=faiss_query,
        k=fetch_k,
    )

    # BM25 dùng rewrite (không inject) vì BM25 tìm chữ
    tokens = rewrite_query.lower().split()
    bm25_scores = bm25_index.get_scores(tokens)
    bm25_top = np.argsort(bm25_scores)[::-1][:fetch_k]
    bm25_results = [
        {'chunk_id': bm25_ids[i], 'score': float(bm25_scores[i])}
        for i in bm25_top if bm25_scores[i] > 0
    ]

    # Soft boost 2 tang: section (tho) -> category (tinh)
    target_category = processed_query.get('filter', {}).get('violation_category', '')
    results = _reciprocal_rank_fusion(faiss_results, bm25_results, fetch_k)
    if target_section:
        results = _soft_section_boost(results, target_section, top_k * 2)
    if target_category:
        results = _soft_category_boost(results, target_category, top_k)
    else:
        results = results[:top_k]

    return results


def _reciprocal_rank_fusion(faiss_results, bm25_results, top_k, K=60) -> list:
    rrf_scores = {}
    doc_map = {}

    for rank, (doc, score) in enumerate(faiss_results[:K]):
        cid = doc.metadata['chunk_id']
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (K + rank + 1)
        doc_map[cid] = doc

    for rank, item in enumerate(bm25_results[:K]):
        cid = item['chunk_id']
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (K + rank + 1)
        # BM25-only docs: chỉ có score, không có Document → skip nếu không có trong doc_map

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    # Chỉ trả về docs mà chúng ta có Document object (từ FAISS)
    return [doc_map[cid] for cid in sorted_ids if cid in doc_map][:top_k * 2]


def _soft_section_boost(docs, target_section: str, top_k: int) -> list:
    """
    Tang boost thu nhat (tho): dua docs dung nhom doc_section len truoc.
    Giu lai tat ca docs lam fallback, dam bao luon du top_k.
    """
    matched = [d for d in docs if d.metadata.get('doc_section') == target_section]
    others  = [d for d in docs if d.metadata.get('doc_section') != target_section]
    return (matched + others)[:top_k]


def _soft_category_boost(docs, target_category: str, top_k: int) -> list:
    """
    Ưu tiên docs khớp category lên đầu, nhưng vẫn giữ các docs khác làm fallback.
    Đảm bảo luôn trả về top_k docs.
    """
    matched = [d for d in docs if d.metadata.get('violation_category') == target_category]
    others = [d for d in docs if d.metadata.get('violation_category') != target_category]

    combined = matched + others
    return combined[:top_k]
