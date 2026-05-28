import os
import sys
import json
import logging
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import settings
from data_pipeline.service.metadata_service import MetadataExtractor
from data_pipeline.cleaner import clear_text
from data_pipeline.parser import parse_file
from data_pipeline.chunking import chunk_all
from data_pipeline.extractor_raw import LegalMarkdownProcess
from data_pipeline.indexing.embeder import run_indexing_pipeline

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)




def run_pipeline(raw_doc_path: Path, doc_id: str) -> list[dict]:
    # ── Cấu hình đường dẫn ──────────────────────────────────────────────────
    raw_md_path   = Path(f"data/processed/{doc_id}_raw.md")
    clean_md_path = Path(f"data/processed/{doc_id}.md")
    output_json   = Path(f"data/final_chunks/{doc_id}_chunks.json")

    api_key = settings.ds_api_key
    if not api_key:
        raise EnvironmentError("DS_API_KEY chưa được thiết lập trong .env")

    # ── Bước 1: PDF → Markdown thô ──────────────────────────────────────────
    log.info('[1/5] Chuyển PDF sang Markdown: %s', raw_doc_path.name)
    LegalMarkdownProcess(raw_doc_path, raw_md_path).pdf_to_markdown()

    # ── Bước 2: Làm sạch Markdown (xoá header/footer/ký tự lạ) ─────────────
    log.info('[2/5] Làm sạch file Markdown')
    clear_text(input_path=raw_md_path, output_path=clean_md_path)

    # ── Bước 3: Parse → Chunk ───────────────────────────────────────────────
    log.info('[3/5] Parse và chunking')
    articles = parse_file(input_path=clean_md_path, doc_id=doc_id)
    chunks   = chunk_all(articles)

    # ── Bước 4: Enrich metadata ngữ nghĩa qua LLM ───────────────────────────
    # Gọi Gemini API để điền 6 trường: vehicle_types, violation_category,
    # hanh_vi_vi_pham, hinh_thuc_phat_bo_sung, doi_tuong_ap_dung, has_penalty
    log.info('[4/5] Enrich metadata ngữ nghĩa cho %d chunks', len(chunks))
    extractor     = MetadataExtractor(api_key=api_key)
    final_chunks  = extractor.enrich_chunks(chunks)

    # ── Bước 5: Lưu chunks JSON ─────────────────────────────────────────────
    log.info('[5/5] Ghi %d chunks → %s', len(final_chunks), output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(final_chunks, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    return final_chunks


def main():
    raw_dir    = Path("data/raw_data/168_2024_ND-CP_619502.pdf")
    json_dir   = Path("data/final_chunks")
    db_faiss   = Path("storage/faiss_index")
    db_bm25    = Path("storage/bm25_index.pkl")
    doc_id = '168_2024_ND-CP_619502'
    # run_pipeline(raw_dir, doc_id)
    
    try:
        run_indexing_pipeline(
            chunks_path=json_dir / f"{doc_id}_chunks.json",
            vector_db_path=db_faiss,
            embedding_model_name=settings.embedding_model,
            bm25_save_path=db_bm25
        )
        log.info('Pipeline hoàn tất thành công.')
    except Exception as e:
        log.error('Lỗi khi embedding: %s', e)


if __name__ == "__main__":
    main()
