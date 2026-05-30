from langchain_core.documents import Document
from src.llm import llm
from src.prompt import build_user_prompt


def generate_final_answer(user_query: str,retrieved_docs: list[Document], llm) -> str:
    # lấy ngữ cảnh
    context_blocks = []
    for i, doc in enumerate(retrieved_docs):
        text = doc.metadata.get('text', doc.page_content)
        doc_id = doc.metadata.get('chunk_id', 'Không rõ điều luật')

        # format 
        context_blocks.append(f'[Tài liệu {i+1} - Nguồn:{doc_id}]:\n{text}\n')
    
    context = '\n'.join(context_blocks)
    prompt = build_user_prompt.format(query=user_query, context=context)

    response = llm.invoke(prompt)
    return response.content