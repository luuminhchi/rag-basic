import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from data_pipeline.indexing.meta_injection import build_meta_injection


def build_faiss_index(chunk_path: str | Path, vector_db_path: str | Path, embedding_model):
    with open(chunk_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    docs = []
    for chunk in chunks_data:
        injection_text = build_meta_injection(chunk['metadata'], chunk['text'])
        doc = Document(
            page_content=injection_text,
            metadata={
                **chunk['metadata'], # toàn bộ metadata gốc
                'chunk_id': chunk['chunk_id'], # giữ lại chunk_id để truy xuất sau này
                'original_text': chunk['text'] # giữ lại text gốc để truy xuất sau này
            }
        )
        docs.append(doc)

    vector_store = FAISS.from_documents(docs, embedding_model)
    vector_store.save_local(str(vector_db_path))
