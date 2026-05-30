

from src.retrievers.query_processor import rewrite_and_inject
from src.retrievers.hybrid_search import hybrid_search
# from retriever.small_to_big import expand_chunks, expand_full_to_dieu
from src.retrievers.rerank import rerank
from src.vector_db import get_vector_store
from src.config import settings
from src.llm import llm

def execute_retrieval_pipeline(user_query: str, top_k: int = 3) -> list:
    vector_db = get_vector_store()
    bm25 = settings.bm25_path
    processed = rewrite_and_inject(user_query, llm)
    print(f"\n[DEBUG AI ĐÃ DỊCH]: {processed['rewrite_query']}\n")
    # bước 2
    hybrid_results = hybrid_search(
        processed_query=processed,
        vectordb=vector_db,
        bm25_path=bm25,
        top_k=10)

    # bước 4
    final = rerank(
        query=user_query,
        docs=hybrid_results,
        k=top_k)
    
    print(f"\n[DEBUG 2 - RERANK]: Giữ lại {len(final)} tài liệu tốt nhất.")
    for i, doc in enumerate(final):
        # In thử 150 ký tự đầu tiên của tài liệu xem nó đang chứa cái gì
        print(f"   👉 Top {i+1}: {doc.page_content[:150]}...\n")
    return final

