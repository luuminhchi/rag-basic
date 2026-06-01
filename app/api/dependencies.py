"""
Dependencies FastAPI — khởi tạo và inject RAG pipeline.
"""
from __future__ import annotations

import logging
from fastapi import HTTPException, status

from src.vector_db import get_vector_store
from src.retrievers.retriever import execute_retrieval_pipeline
from src.generator import generate_final_answer
from src.llm import llm

logger = logging.getLogger(__name__)

# ── Singleton state ──────────────────────────────────────────
_rag_ready: bool = False


async def startup_rag() -> None:
    """Gọi khi ứng dụng khởi động: load vector store vào bộ nhớ."""
    global _rag_ready
    try:
        logger.info("Đang khởi tạo Vector Store…")
        get_vector_store()          # load & cache lần đầu
        _rag_ready = True
        logger.info("✅ RAG pipeline sẵn sàng.")
    except Exception as exc:
        logger.error("❌ Khởi tạo RAG thất bại: %s", exc)
        _rag_ready = False
        raise


async def shutdown_rag() -> None:
    """Gọi khi ứng dụng tắt."""
    global _rag_ready
    _rag_ready = False
    logger.info("RAG pipeline đã được tắt.")


def require_rag_ready() -> None:
    """
    Dependency FastAPI: raise 503 nếu RAG chưa sẵn sàng.
    Dùng với  `Depends(require_rag_ready)`.
    """
    if not _rag_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hệ thống RAG chưa sẵn sàng, vui lòng thử lại sau.",
        )


def get_retriever():
    """Trả về hàm retrieval pipeline (để dễ mock khi test)."""
    return execute_retrieval_pipeline


def get_generator():
    """Trả về hàm generate_final_answer (để dễ mock khi test)."""
    return generate_final_answer


def get_llm():
    """Trả về LLM singleton."""
    return llm
