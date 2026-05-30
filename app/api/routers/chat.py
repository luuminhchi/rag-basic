import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_rag
from generator import TrafficLawger

router = APIRouter()


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Câu hỏi về pháp luật giao thông")
    vehicle_type: str | None = Field(default=None, description="Loại phương tiện (ô tô, xe máy, ...)")


class ChatResponse(BaseModel):
    answer: str
    rewritten_query: str | None = None
    elapsed_seconds: float


@router.post("/chat", response_model=ChatResponse, summary="Hỏi đáp pháp luật giao thông")
def chat_with_bot(request: ChatRequest, rag: TrafficLawger = Depends(get_rag)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

    t0 = time.perf_counter()

    # Rewrite query để ghi log và tái sử dụng cho ask() tránh gọi LLM 2 lần
    rewritten = rag.understande_query(request.query)
    answer = rag.ask(request.query, search_query=rewritten)

    elapsed = round(time.perf_counter() - t0, 2)

    return ChatResponse(
        answer=answer,
        rewritten_query=rewritten,
        elapsed_seconds=elapsed,
    )
