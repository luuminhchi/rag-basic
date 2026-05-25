from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import chat
from app.api.dependencies import startup_rag, shutdown_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_rag()
    yield
    await shutdown_rag()


app = FastAPI(
    title="Traffic Law RAG API",
    description="API tra cứu và hỏi đáp văn bản pháp luật giao thông Việt Nam",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Hệ thống RAG đang chạy!"}
