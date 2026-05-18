import json
import logging
import sys
from pathlib import Path

import fitz
import google.genai as genai
from google.genai import types

log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config import settings
from src.prompt import METADAT_PROMPT


class metadata_extract:
    def __init__(self, api_key: str, registry: Path | str):
        self.client   = genai.Client(api_key=api_key)
        self.registry = Path(registry)          # ép kiểu Path để .parent luôn dùng được
        self.registry.parent.mkdir(parents=True, exist_ok=True)

    # ── Trích nội dung trang đầu PDF ────────────────────────────────────────
    def extract_first_pages(self, pdf_path: Path, number_page: int = 2) -> str:
        text = ""
        try:
            doc       = fitz.open(pdf_path)
            page_read = min(number_page, len(doc))
            for i in range(page_read):              # fix: range(int), không iterate int
                text += doc[i].get_text()
            doc.close()
        except Exception as e:
            log.error('Lỗi đọc PDF %s: %s', pdf_path, e)
        return text

    # ── Gọi LLM trích metadata → lưu registry ───────────────────────────────
    def extract_save(self, pdf_path: Path, doc_id: str) -> dict:
        raw_text = self.extract_first_pages(pdf_path)
        if not raw_text:
            log.warning('Không đọc được nội dung PDF: %s', pdf_path)
            return {}

        prompt = METADAT_PROMPT(raw_text)
        try:
            response = self.client.models.generate_content(
                model=settings.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json'),
            )
            metadata = json.loads(response.text)
            self._upsert_to_registry(doc_id, metadata)
            return metadata                          # fix: thêm return
        except Exception as e:
            log.error('Lỗi LLM khi trích metadata: %s', e)
            return {}

    # ── Ghi/cập nhật registry.json ──────────────────────────────────────────
    def _upsert_to_registry(self, doc_id: str, new_metadata: dict):
        registry_data = {}

        if self.registry.exists():
            try:
                registry_data = json.loads(self.registry.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                log.warning('registry.json bị lỗi format, tạo lại từ đầu.')

        registry_data[doc_id] = new_metadata
        self.registry.write_text(
            json.dumps(registry_data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        log.info('Đã lưu metadata của %s vào %s', doc_id, self.registry.name)
