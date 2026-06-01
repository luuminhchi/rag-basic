"""
Router: Search — POST /api/v1/search
Chỉ retrieve tài liệu, không gọi LLM (nhanh hơn, dùng để debug / kiểm tra).
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import require_rag_ready, get_retriever
from app.models.schemas import SearchRequest, SearchResponse, SourceDocument

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Tìm kiếm tài liệu pháp luật (không sinh câu trả lời)",
    description=(
        "Chạy toàn bộ pipeline retrieval (hybrid search + rerank) "
        "và trả về danh sách tài liệu liên quan — không gọi LLM."
    ),
)
def search_documents(
    request: SearchRequest,
    _: None = Depends(require_rag_ready),
    retriever=Depends(get_retriever),
) -> SearchResponse:
    t0 = time.perf_counter()
    logger.info("[SEARCH] query=%r  top_k=%d", request.query, request.top_k)

    try:
        docs, rewritten_query = retriever(user_query=request.query, top_k=request.top_k)
    except Exception as exc:
        logger.exception("[SEARCH] Lỗi retrieval: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tìm kiếm: {exc}",
        )

    results = [
        SourceDocument(
            chunk_id=doc.metadata.get("chunk_id", f"doc_{i}"),
            content=doc.page_content,
            score=doc.metadata.get("rerank_score"),
            metadata={
                k: v
                for k, v in doc.metadata.items()
                if k not in {"chunk_id", "rerank_score"}
            },
        )
        for i, doc in enumerate(docs)
    ]

    elapsed = round(time.perf_counter() - t0, 3)
    logger.info("[SEARCH] Tìm thấy %d tài liệu trong %.3fs", len(results), elapsed)

    return SearchResponse(
        query=request.query,
        rewritten_query=rewritten_query,
        results=results,
        elapsed_seconds=elapsed,
    )
