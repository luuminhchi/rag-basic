from src.retrievers.query_processor import rewrite_query
from src.retrievers.hybrid_search import search
from src.retrievers.query_router import classify_query
from src.retrievers.rerank import rerank
from src.llm import llm


def execute_retrieval_pipeline(
    user_query: str,
    top_k: int = 5
) -> tuple[list, dict]:
   

    classify_result = classify_query(user_query)

    print(f"[DEBUG CLASSIFY] section={classify_result.get('doc_section')} "
          f"| subsection={classify_result.get('doc_subsection')} "
          f"| intent={classify_result.get('intent')}")

    # Bước 2: Rewrite — chuẩn hoá thuật ngữ + build injected_query
    processed = rewrite_query(user_query, classify_result, llm)

    print(f"[DEBUG REWRITE]  {processed['rewrite_query']}")
    print(f"[DEBUG FILTER]   {processed['filter']}")

    # Bước 3: Hybrid search — FAISS + BM25 + RRF → top 10
    hybrid_results = search(processed, top_k=10)

    print(f"[DEBUG SEARCH]   {len(hybrid_results)} results "
          f"| sources: {[r.source for r in hybrid_results]}")

    # Bước 4: Rerank — CrossEncoder → top k
    final = rerank(processed, hybrid_results, k=top_k)

    print(f"[DEBUG RERANK]   top scores: "
          f"{[round(r.rerank_score, 3) for r in final]}")

    return final, classify_result