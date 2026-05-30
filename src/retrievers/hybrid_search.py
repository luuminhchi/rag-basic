import pickle
import numpy as np
from rank_bm25 import BM25Okapi

def hybrid_search(
        processed_query: dict,
        vectordb,
        bm25_path: str,
        top_k: int = 10
) -> list:
    with open(bm25_path, 'rb') as f:
        bm25 = pickle.load(f)
    bm25_index = bm25['index']
    bm25_ids = bm25['ids']

    rewrite_query = processed_query.get('rewrite_query', '')
    # FAISS chỉ hỗ trợ equality filter, không hỗ trợ array-contains
    # Bỏ filter hoàn toàn để tránh không ra kết quả
    faiss_results = vectordb.similarity_search_with_score(
        query=rewrite_query,
        k=top_k,
    )

    # BM25 dùng rewrite (không inject) vì BM25 tìm chữ
    tokens = rewrite_query.lower().split()
    bm25_scores = bm25_index.get_scores(tokens)
    bm25_top = np.argsort(bm25_scores)[::-1][:top_k]
    bm25_results = [
        {'chunk_id': bm25_ids[i], 'score': float(bm25_scores[i])}
        for i in bm25_top if bm25_scores[i] > 0
    ]

    return _reciprocal_rank_fusion(faiss_results, bm25_results, top_k)


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

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    return [doc_map[cid] for cid in sorted_ids[:top_k] if cid in doc_map]
