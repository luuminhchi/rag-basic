"""
Entry point của ứng dụng FastAPI — Traffic Law RAG API.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import chat
from app.api.dependencies import startup_rag, shutdown_rag
from app.models.schemas import HealthResponse




# ── Lifespan: khởi tạo / dọn dẹp tài nguyên ─────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_rag()
    yield
    await shutdown_rag()


# ── Khởi tạo FastAPI ─────────────────────────────────────────
app = FastAPI(
    title="Traffic Law RAG API",
  
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Thay bằng domain cụ thể khi deploy production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ──────────────────────────────────────────────────
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


# ── Health check ─────────────────────────────────────────────
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Kiểm tra trạng thái hệ thống",
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Hệ thống RAG đang chạy!",
        version=app.version,
    )
