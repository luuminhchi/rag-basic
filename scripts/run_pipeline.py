import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.service.metadata_service import metadata_extract
from data_pipeline.cleaner import clear_text
from data_pipeline.parser import parse_file
from data_pipeline.chunking import chunk_all
from data_pipeline.extractor_raw import LegalMarkdownProcess
from data_pipeline.embeder import build_and_save_vectorDB

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)


def get_valid_files(directory: Path) -> list[Path]:
    if not directory.exists():
        log.error('Thư mục không tồn tại: %s', directory)
        return []
    return [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']


def process_batch_document(raw_dir: Path) -> int:
    raw_files = get_valid_files(raw_dir)
    if not raw_files:
        log.error('Không tìm thấy tài liệu hợp lệ trong %s', raw_dir)
        return 0

    success_count = 0
    for input_file in raw_files:
        document_id = input_file.stem
        log.info('Đang xử lý: %s', document_id)
        try:
            run_pipeline(input_file, document_id)
            success_count += 1
        except Exception as e:
            log.error('Lỗi khi xử lý %s: %s', document_id, e)
    return success_count


def run_pipeline(raw_doc_path: Path, doc_id: str) -> list[dict]:
    # ── Cấu hình đường dẫn ──────────────────────────────────────────────────
    raw_md_path   = Path(f"data/processed/{doc_id}_raw.md")
    clean_md_path = Path(f"data/processed/{doc_id}.md")
    registry_file = Path("docs/docs_registry.json")
    output_json   = Path(f"data/final_chunks/{doc_id}_chunks.json")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY chưa được thiết lập trong .env")

    # ── Bước 1: PDF → Markdown thô ──────────────────────────────────────────
    log.info('[1/5] Chuyển PDF sang Markdown: %s', raw_doc_path.name)
    LegalMarkdownProcess(raw_doc_path, raw_md_path).pdf_to_markdown()

    # ── Bước 2: Trích xuất metadata bằng LLM → registry.json ───────────────
    log.info('[2/5] Trích xuất metadata')
    metadata_extract(api_key=api_key, registry=registry_file).extract_save(raw_doc_path, doc_id)

    # ── Bước 3: Làm sạch Markdown (xoá header/footer/ký tự lạ) ─────────────
    log.info('[3/5] Làm sạch file Markdown')
    clear_text(input_path=raw_md_path, output_path=clean_md_path)

    # ── Bước 4: Parse → Chunk ───────────────────────────────────────────────
    log.info('[4/5] Parse và chunking')
    articles     = parse_file(input_path=clean_md_path, doc_id=doc_id)
    final_chunks = chunk_all(articles)

    # ── Bước 5: Lưu chunks JSON ─────────────────────────────────────────────
    log.info('[5/5] Ghi %d chunks → %s', len(final_chunks), output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(final_chunks, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    return final_chunks


def main():
    raw_dir      = Path("data/raw_data")       # thư mục chứa PDF gốc
    json_dir     = Path("data/final_chunks")
    db_output    = Path("storage/faiss_index")

    success_count = process_batch_document(raw_dir)

    if success_count == 0:
        log.error('Không có file nào xử lý thành công, dừng pipeline.')
        return

    log.info('Xử lý xong %d file, bắt đầu embedding...', success_count)
    try:
        build_and_save_vectorDB(json_dir=json_dir, output_db_path=db_output)
        log.info('Pipeline hoàn tất thành công.')
    except Exception as e:
        log.error('Lỗi khi embedding: %s', e)


if __name__ == "__main__":
    main()
