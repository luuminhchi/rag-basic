"""
Pydantic schemas — định nghĩa Request / Response models cho toàn bộ API.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ─────────────────────────── Chat ────────────────────────────

class ChatRequest(BaseModel):
    """Payload gửi lên endpoint /chat."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Câu hỏi về pháp luật giao thông",
        examples=["Vượt đèn đỏ bị phạt bao nhiêu tiền?"],
    )

    model_config = {"json_schema_extra": {"example": {"query": "Uống rượu bia lái xe bị phạt như thế nào?"}}}


class ViolationDetail(BaseModel):
    """Chi tiết một vi phạm luật giao thông."""
    phuong_tien: list[str] = Field(description="Các phương tiện áp dụng")
    hanh_vi: str = Field(description="Mô tả hành vi vi phạm")
    can_cu: str = Field(description="Căn cứ pháp lý")
    phat_tien: dict[str, int] = Field(description="Khoản tiền phạt min/max")
    phat_bo_sung: list[str] = Field(description="Hình thức phạt bổ sung")
    luu_y: str | None = Field(default="", description="Ghi chú lưu ý thêm")


class ChatAnswerSchema(BaseModel):
    """Cấu trúc câu trả lời của LLM."""
    found: bool
    is_general_query: bool
    general_explanation: str | None = None
    violations: list[ViolationDetail] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Payload trả về từ endpoint /chat."""
    answer: ChatAnswerSchema = Field(description="Câu trả lời tổng hợp từ LLM đã được parse thành object")
    rewritten_query: str | None = Field(default=None, description="Câu hỏi sau khi viết lại bởi AI")
    elapsed_seconds: float = Field(description="Thời gian xử lý (giây)")


# ─────────────────────────── Search ──────────────────────────

class SearchRequest(BaseModel):
    """Payload gửi lên endpoint /search."""
    query: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi tìm kiếm")
    top_k: int = Field(default=5, ge=1, le=50, description="Số lượng tài liệu muốn lấy")


class SourceDocument(BaseModel):
    """Chi tiết một tài liệu tìm thấy."""
    chunk_id: str
    content: str
    score: float | None = None
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Payload trả về từ endpoint /search."""
    query: str
    rewritten_query: str | None = None
    results: list[SourceDocument]
    elapsed_seconds: float


# ─────────────────────────── Health ──────────────────────────

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
