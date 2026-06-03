

from src.retrievers.query_processor import rewrite_and_inject
from src.retrievers.hybrid_search import hybrid_search
from src.retrievers.query_router import classify_query
from src.retrievers.rerank import rerank
from src.vector_db import get_vector_store
from src.config import settings
from src.llm import llm

import json
from pathlib import Path

_chunks_cache = None

def _get_chunks_map() -> dict:
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache

    chunks_map = {}
    # Sử dụng đường dẫn tuyệt đối hoặc tương đối tới thư mục chứa chunks
    final_chunks_dir = Path("data/final_chunks")
    if final_chunks_dir.exists():
        for p in final_chunks_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for chunk in data:
                        chunks_map[chunk["chunk_id"]] = chunk
            except Exception:
                pass
    _chunks_cache = chunks_map
    return chunks_map


def execute_retrieval_pipeline(user_query: str, top_k: int = 5) -> tuple[list, str]:
    vector_db = get_vector_store()
    bm25 = settings.bm25_path

    # Buoc 0: Phan loai cau hoi -> doc_section (khong ton LLM)
    section = classify_query(user_query)
    try:
        print(f"\n[DEBUG ROUTER]: doc_section = {section}")
    except Exception:
        pass

    # Buoc 1: Rewrite query
    processed = rewrite_and_inject(user_query, llm)
    try:
        print(f"\n[DEBUG AI DA DICH]: {processed['rewrite_query']}\n")
    except Exception:
        pass

    # Buoc 2: Hybrid search voi 2 tang boost
    hybrid_results = hybrid_search(
        processed_query=processed,
        vectordb=vector_db,
        bm25_path=bm25,
        top_k=10,
        target_section=section,
    )

    # Buoc 3: Rerank
    final = rerank(
        query=processed['rewrite_query'],
        docs=hybrid_results,
        k=top_k)

    # ── MỞ RỘNG NGỮ CẢNH CẤP ĐIỀU (Article-level Context Expansion) ──
    # Đối với các nhóm thủ tục, trừ điểm, quy định chung -> Cần đọc trọn vẹn cả Điều để hiểu toàn bộ logic thay vì các khoản cắt lẻ.
    if section != "xu_phat":
        expanded_docs = []
        seen_articles = set()
        chunks_map = _get_chunks_map()

        for doc in final:
            dieu = doc.metadata.get("dieu")
            doc_id = doc.metadata.get("doc_id")
            if dieu and doc_id:
                article_key = (doc_id, dieu)
                if article_key not in seen_articles:
                    seen_articles.add(article_key)
                    parent_id = f"{doc_id}_d{dieu}"
                    if parent_id in chunks_map:
                        # Thay thế content của Document bằng toàn bộ text của Điều luật cha
                        doc.page_content = chunks_map[parent_id]["text"]
                        expanded_docs.append(doc)
                    else:
                        expanded_docs.append(doc)
            else:
                expanded_docs.append(doc)
        final = expanded_docs

    try:
        print(f"\n[DEBUG RERANK]: Giu lai {len(final)} tai lieu tot nhat.")
        for i, doc in enumerate(final):
            section = doc.metadata.get('doc_section', '?')
            dieu = doc.metadata.get('dieu', '?')
            violation_cat = doc.metadata.get('violation_category', '?')
            chunk_type = doc.metadata.get('loai', '?')
            print(f"   Top {i+1}: [section={section}] [dieu={dieu}] [loai={chunk_type}] [cat={violation_cat}]")
            print(f"           {doc.page_content[:120]}...\n")
    except Exception as e:
        print(f"[DEBUG ERROR]: {e}")
        pass
    return final, processed['rewrite_query']

