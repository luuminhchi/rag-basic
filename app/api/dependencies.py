from src.vector_db import load_vector_store
from src.rag import TrafficLawger

_rag_instance: TrafficLawger | None = None


async def startup_rag():
    global _rag_instance
    vectorstore = load_vector_store()
    _rag_instance = TrafficLawger(vectorstore)


async def shutdown_rag():
    global _rag_instance
    _rag_instance = None


def get_rag() -> TrafficLawger:
    if _rag_instance is None:
        raise RuntimeError("RAG system chưa được khởi tạo")
    return _rag_instance
