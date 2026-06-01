"""
Router: Chat — POST /api/v1/chat
Hỏi đáp pháp luật giao thông sử dụng RAG pipeline đầy đủ.
"""
from __future__ import annotations

import logging
import time

import json
from typing import Callable
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.routing import APIRoute

from app.api.dependencies import require_rag_ready, get_retriever, get_generator, get_llm
from app.models.schemas import ChatRequest, ChatResponse
from src.config import settings

logger = logging.getLogger(__name__)


class SafeJSONRoute(APIRoute):
    """
    APIRoute tùy biến để tự động làm sạch JSON body.
    Cho phép các ký tự điều khiển (control characters) chưa được escape như xuống dòng (\n),
    tab (\t) vốn thường gặp khi người dùng copy-paste câu hỏi phức tạp.
    """
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if request.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = await request.body()
                    if body:
                        # strict=False cho phép các ký tự điều khiển chưa escape trong chuỗi JSON
                        parsed = json.loads(body.decode("utf-8"), strict=False)
                        # Dump ngược lại thành JSON chuẩn
                        request._body = json.dumps(parsed).encode("utf-8")
                        if hasattr(request, "_json"):
                            delattr(request, "_json")
                except Exception:
                    # Nếu JSON hoàn toàn lỗi cú pháp (thiếu ngoặc...), cứ để parser mặc định xử lý và trả lỗi 422 chuẩn
                    pass
            return await original_route_handler(request)

        return custom_route_handler


router = APIRouter(route_class=SafeJSONRoute)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Hỏi đáp pháp luật giao thông",
    description=(
        "Nhận câu hỏi từ người dùng, rewrite sang thuật ngữ pháp lý, "
        "tìm kiếm hybrid (FAISS + BM25), rerank rồi sinh câu trả lời bằng LLM."
    ),
)
def ask_question(
    request: ChatRequest,
    _: None = Depends(require_rag_ready),
    retriever=Depends(get_retriever),
    generator=Depends(get_generator),
    llm=Depends(get_llm),
) -> ChatResponse:
    t0 = time.perf_counter()
    top_k = settings.top_k
    logger.info("[CHAT] query=%r  top_k=%d", request.query, top_k)

    try:
        # ── Bước 1: Retrieve ──────────────────────────────────
        docs, rewritten_query = retriever(user_query=request.query, top_k=top_k)

        # ── Bước 2: Generate ────────────────────────────
        answer_raw = generator(
            user_query=request.query,
            retrieved_docs=docs,
            llm=llm,
        )

        try:
            # Parse chuỗi JSON nhận được từ LLM sang dict
            answer = json.loads(answer_raw)
        except Exception as e:
            logger.warning("[CHAT] Không thể parse JSON từ LLM: %s. Sử dụng giải thích thô làm fallback.", e)
            answer = {
                "found": True,
                "is_general_query": True,
                "general_explanation": answer_raw,
                "violations": []
            }

    except Exception as exc:
        logger.exception("[CHAT] Lỗi xử lý: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý câu hỏi: {exc}",
        )

    elapsed = round(time.perf_counter() - t0, 3)
    logger.info("[CHAT] Hoàn tất trong %.3fs", elapsed)

    return ChatResponse(
        answer=answer,
        rewritten_query=rewritten_query,
        elapsed_seconds=elapsed,
    )
