from src.llm import llm
from src.prompt import build_user_prompt, query_understanding_prompt
from src.retriever import get_advenced_retrievel


class TrafficLawger:
    def __init__(self, vectorstore):
        self.retriever = get_advenced_retrievel(vectorstore)
        self.llm       = llm                    # dùng singleton từ src/llm.py

    def understande_query(self, query: str) -> str:
        """Dịch câu hỏi hằng ngày sang thuật ngữ pháp lý để tìm kiếm hiệu quả hơn."""
        prompt = query_understanding_prompt.format(question=query)
        try:
            result = self.llm.generate(prompt, max_tokens=128, temperature=0.1)
            if result:
                return result
        except Exception:
            pass
        return query

    def ask(self, query: str, search_query: str = None) -> str:
        """
        Trả lời câu hỏi pháp lý giao thông dựa trên RAG.
        - query       : câu hỏi gốc của người dùng (dùng để LLM trả lời)
        - search_query: câu tìm kiếm đã tối ưu (nếu None sẽ tự gọi understande_query)
        """
        # 1. Dịch câu hỏi nếu chưa có search_query
        if search_query is None:
            search_query = self.understande_query(query)

        # 2. Tìm kiếm tài liệu liên quan
        docs = self.retriever(search_query)

        if not docs:
            return 'Tài liệu hiện tại không có quy định về vấn đề này.'

        # 3. Gom ngữ cảnh kèm nhãn Điều/Khoản/Điểm và Tiêu đề điều luật
        parts = []
        for i, doc in enumerate(docs, start=1):
            m       = doc.metadata
            dieu    = m.get('dieu', '')
            khoan   = m.get('khoan', '')
            diem    = m.get('diem', '')
            tieu_de = m.get('tieu_de', '')

            label_parts = [f"Điều {dieu}"] if dieu else []
            if khoan:
                label_parts.append(f"Khoản {khoan}")
            if diem:
                label_parts.append(f"Điểm {diem}")
            if tieu_de:
                label_parts.append(f"({tieu_de})")

            nhan_nguon    = ' '.join(label_parts)
            noi_dung_luat = doc.page_content.strip()
            parts.append(f'[Nguồn {i}] {nhan_nguon}:\n{noi_dung_luat}')

        context_text = '\n\n'.join(parts)

        # 4. Xây dựng prompt và gọi LLM
        final_prompt = build_user_prompt.format(
            question=query,
            context=context_text,
        )

        try:
            return self.llm.generate(final_prompt, max_tokens=1024, temperature=0.1)
        except Exception as e:
            return f'Hệ thống đang bận hoặc gặp lỗi kết nối: {e}'