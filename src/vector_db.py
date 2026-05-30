from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from src.config import settings

# Singleton pattern cho VectorStore, tránh load nhiều lần khi gọi retriever nhiều lần
_vector_store_instance: VectorStore  | None = None

def get_vector_store() -> FAISS:
    global _vector_store_instance

    if _vector_store_instance is not None:
        return _vector_store_instance
    db_dict = Path(settings.vector_store_dir)

    if not db_dict.exists():
        raise FileNotFoundError(f'Not found vector store at {db_dict}')
    
    embedding = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={"normalize_embeddings": True}
    )
    
    _vector_store_instance = FAISS.load_local(
        folder_path=str(db_dict),
        embeddings=embedding,
        allow_dangerous_deserialization=True
        )
    
    return _vector_store_instance


