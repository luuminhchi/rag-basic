import sys
from pathlib import Path
env_path = Path(__file__).resolve().parents[1]/'.env'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrievers.generator import generate_final_answer
from src.retrievers.retriever import execute_retrieval_pipeline
from src.llm import llm


class TrafficLawger:
    def __init__(self):
        self.llm = llm

    def chat(self, user_query: str) -> str:
        final_chunks, classify_result = execute_retrieval_pipeline(user_query = user_query, top_k=5)
        if not final_chunks:
            return "Xin lỗi, tôi không tìm thấy tài liệu nào liên quan đến câu hỏi của bạn."

        print("Đang phân tích và tổng hợp câu trả lời...")
        final_response = generate_final_answer(
            user_query,
            final_chunks,
            classify_result,
            self.llm
        )
        
        return final_response
    
if __name__ == "__main__":
    chatbot = TrafficLawger()
    while True:
        query = input("Bạn: ")
        if query.lower() in ["exit", "quit"]:
            print("Kết thúc cuộc trò chuyện. Hẹn gặp lại!")
            break
        answer = chatbot.chat(query)
        print(f"Chatbot: {answer}\n")
