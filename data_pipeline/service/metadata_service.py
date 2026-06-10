import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

from src.config import settings
from src.prompt import METADATA_PROMPT
# Các trường LLM phải trả về — dùng để validate và fallback
_EXPECTED_FIELDS = {
    "violation_category":     str,
    "hanh_vi_vi_pham":        list,
    "hinh_thuc_phat_bo_sung": list,
    "doi_tuong_ap_dung":      str,
    'tru_diem_gplx':          (int, type(None)),
    'lai_tai_pham':           bool,
}

_FIELD_DEFAULTS: dict[str, Any] = {
    "violation_category":     "",
    "hanh_vi_vi_pham":        [],
    "hinh_thuc_phat_bo_sung": [],
    "doi_tuong_ap_dung":      "",
    'tru_diem_gplx':          None,
    'lai_tai_pham':           False,
}


def _parse_llm_response(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return dict(_FIELD_DEFAULTS)

    result = {}
    for field, expected_type in _EXPECTED_FIELDS.items():
        value = data.get(field, _FIELD_DEFAULTS[field])

        # Ép kiểu nếu LLM trả sai
        if expected_type is list and not isinstance(value, list):
            value = [value] if value else []
        elif expected_type is str and not isinstance(value, str):
            value = str(value) if value is not None else ""
        elif expected_type is int and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = None
        elif expected_type is bool and not isinstance(value, bool):
            value = bool(value)


        result[field] = value

    return result


class MetadataExtractor:
   

    def __init__(self, api_key: str, retry: int = 2, delay: float = 1.0):
        """
        Args:
            api_key: Google Gemini API key.
            retry:   Số lần thử lại khi API lỗi.
            delay:   Giây chờ giữa các lần retry.
        """
        self.llm = ChatOpenAI(
            model=settings.llm_model, # Trong .env hãy set llm_model="deepseek-chat"
            api_key=api_key,
            base_url="https://api.deepseek.com", 
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}} # Ép DeepSeek trả về JSON thuần
        )
        self.retry = retry
        self.delay = delay

    def enrich_chunk(self, chunk: dict) -> dict:
        """
        Gọi LLM API để trích xuất metadata cho 1 chunk.

        """
        text = chunk.get("text", "")
        if not text.strip():
            log.warning("Chunk '%s' có text rỗng, bỏ qua.", chunk.get("chunk_id", "?"))
            return chunk

        # Tạo prompt từ hàm METADAT_PROMPT (nhận raw_text, trả về chuỗi prompt hoàn chỉnh)
        prompt = METADATA_PROMPT(text)

        llm_meta = None
        for attempt in range(1, self.retry + 2):   # retry+1 lần thử tổng cộng
            try:
                response = self.llm.invoke(prompt)
                llm_meta = _parse_llm_response(response.content)
                break   # thành công → thoát vòng retry

            except Exception as e:
                log.warning(
                    "Lần %d/%d — API lỗi cho chunk '%s': %s",
                    attempt, self.retry + 1, chunk.get("chunk_id", "?"), e,
                )
                if attempt <= self.retry:
                    time.sleep(self.delay)
                else:
                    log.error("Đã thử %d lần, dùng metadata mặc định.", self.retry + 1)
                    llm_meta = dict(_FIELD_DEFAULTS)

        # Merge kết quả LLM vào metadata đã có của chunk (không xóa các trường cũ)
        updated_chunk = dict(chunk)
        updated_chunk["metadata"] = {**chunk.get("metadata", {}), **llm_meta}
        return updated_chunk

    def enrich_chunks(self, chunks: list[dict], log_every: int = 50) -> list[dict]:
        """
        Enrich toàn bộ danh sách chunk.
        """
        total = len(chunks)
        result = []

        for i, chunk in enumerate(chunks, 1):
            enriched = self.enrich_chunk(chunk)
            result.append(enriched)

            if i % log_every == 0 or i == total:
                log.info("Metadata enrichment: %d/%d chunks", i, total)

        log.info("Hoàn tất enrich %d chunks.", total)
        return result
