import json
import sys
import logging
from pathlib import Path

log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import Settings


def clean_metadata(metadata: dict) -> dict:
    """Chuyển metadata về dạng FAISS chấp nhận: chỉ str/int/float/bool."""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            cleaned[key] = ", ".join(str(v) for v in value)
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def create_documents_from_json(json_dir: Path) -> list[Document]:
    """Đọc tất cả file JSON trong thư mục → list[Document] cho LangChain."""
    if not json_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục: {json_dir}")

    json_files = list(json_dir.glob('*.json'))
    if not json_files:
        log.warning('Không có file JSON nào trong %s', json_dir)
        return []

    documents = []
    for file_path in json_files:
        chunks_data: list[dict] = json.loads(file_path.read_text(encoding='utf-8'))
        for chunk in chunks_data:
            text_content = chunk.get("text", "")

            # Lấy nested metadata, thêm chunk_id vào để truy vết sau này
            meta = dict(chunk.get("metadata", {}))   # copy tránh mutate gốc
            meta["chunk_id"] = chunk.get("chunk_id", "")

            documents.append(Document(
                page_content=text_content,
                metadata=clean_metadata(meta),        # fix: truyền meta, không phải chunk
            ))

    log.info('Đã tải %d documents từ %d file JSON', len(documents), len(json_files))
    return documents


def build_and_save_vectorDB(json_dir: Path, output_db_path: Path):
    """Tạo FAISS vector store từ chunks JSON và lưu xuống disk."""
    documents = create_documents_from_json(json_dir)
    if not documents:
        log.error('Không có chunk nào để embedding.')
        return

    cfg = Settings()
    embedding = HuggingFaceEmbeddings(
        model_name=cfg.embedding_model,
        encode_kwargs={'normalize_embeddings': True},
    )

    vector_store = FAISS.from_documents(documents=documents, embedding=embedding)

    output_db_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(output_db_path))
    log.info('Vector DB đã lưu tại: %s (%d vectors)', output_db_path, len(documents))
