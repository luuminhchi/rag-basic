from pathlib import Path
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.config import settings

def load_vector_store() -> FAISS:
    db_dict = Path(settings.vector_store_dir)

    embedding = HuggingFaceBgeEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vector_store = FAISS.load_local(
        folder_path=str(db_dict),
        embeddings=embedding,
        allow_dangerous_deserialization=True
    )
    return vector_store

def retriever(query:str, k:int, store:FAISS) -> list[Document]:
    vs = store or load_vector_store()
    return vs.similarity_search(query, k = k or settings.top_k)
