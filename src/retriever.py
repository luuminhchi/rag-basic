import logging
from typing import List, Callable

from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from src.config import settings
# khai báo nếu đang chạy thì k phải gọi lại
_rerank : CrossEncoder | None = None

def _get_re_rank() -> CrossEncoder:
    global _rerank
    if _rerank is None:
        _rerank = CrossEncoder(settings.RERANKER_MODEL)
    return _rerank

def get_hybrid_retriever(vectorStore):
    raw_doc = list(vectorStore.docstore._dict.values())

    if not raw_doc:
        raise ValueError('Faiss empty')
    
    bm25 = BM25Retriever.from_documents(raw_doc)
    bm25.k = 10
    faiss_retriever = vectorStore.as_retriever(search_kwargs={'k': 10})

    hybrid_seach = EnsembleRetriever(
        retrievers=[bm25, faiss_retriever],
        weights=[0.4,0.6]
    )
    return hybrid_seach
# Small to Big: leo từ Điểm → Khoản (dừng tại Khoản, không lên Điều)
def hierarchical_expand(docs: list[Document], vectorStore: FAISS) -> list[Document]:
    chunk_look: dict[str, Document] = {
        doc.metadata['chunk_id']: doc
        for doc in vectorStore.docstore._dict.values()
        if 'chunk_id' in doc.metadata
    }

    expanded: dict[str, Document] = {}

    for doc in docs:
        current_doc = doc
        loai = current_doc.metadata.get('loai', '')

        # Nếu là chunk Điểm (diem) → leo lên 1 cấp để lấy chunk Khoản (khoan)
        if loai == 'diem':
            p_id = current_doc.metadata.get('parent_id')
            p_doc = chunk_look.get(p_id)
            if p_doc and p_doc.metadata.get('loai') == 'khoan':
                current_doc = p_doc

        # Nếu là chunk Khoản hoặc Điều → giữ nguyên
        # (không leo lên Điều vì chunk Điều quá dài)

        final_id = current_doc.metadata.get('chunk_id', str(id(current_doc)))
        if final_id not in expanded:
            expanded[final_id] = current_doc

    return list(expanded.values())

def rerank(query: str,  docs: list[Document], top_k: int | None = None) -> list[Document]:
    if not docs:
        return docs
    #  get top k
    k = top_k or settings.top_k
    #  goi ham rerank
    rerank_model = _get_re_rank()

    pairs = [(query, doc.page_content) for doc in docs]
    scores = rerank_model.predict(pairs)
    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    
    ranked_top_k = ranked[:k]
    final_result = []
    for _, doc in ranked_top_k:
        final_result.append(doc)
    return final_result

def get_advenced_retrievel(vectordb: FAISS) -> Callable[[str], list[Document]]:
    hybrid = get_hybrid_retriever(vectordb)

    def retrivel(query: str):
        candidates = hybrid.invoke(query)
        expanded = hierarchical_expand(candidates,vectordb)
        final = rerank(query, expanded)
        return final
    return retrivel 