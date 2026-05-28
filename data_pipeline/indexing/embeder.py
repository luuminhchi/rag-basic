import logging
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from data_pipeline.indexing.faiss_index import build_faiss_index
from data_pipeline.indexing.bm25_index import build_bm25_index

log = logging.getLogger(__name__)


def run_indexing_pipeline(chunks_path, vector_db_path, embedding_model_name, bm25_save_path):
    log.info("Đang load embedding model: %s", embedding_model_name)
    embedding_model = HuggingFaceBgeEmbeddings(
        model_name=embedding_model_name,
        encode_kwargs={'normalize_embeddings': True}
    )

    log.info("Build FAISS index...")
    build_faiss_index(chunks_path, vector_db_path, embedding_model)

    log.info("Build BM25 index...")
    build_bm25_index(chunks_path, bm25_save_path)