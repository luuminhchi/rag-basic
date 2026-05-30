# test_faiss_raw.py
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Thêm thư mục gốc vào sys.path để import


from src.vector_db import get_vector_store # Đổi lại đường dẫn import nếu cần

def test_raw_faiss():
    print("⏳ Đang load Database...")
    vectordb = get_vector_store()
    
    # Ép FAISS tìm đúng cụm từ chuẩn pháp lý (Không có chữ vượt đèn đỏ)
    query_chuan = "Mức phạt đối với người điều khiển xe mô tô, xe gắn máy không chấp hành hiệu lệnh của đèn tín hiệu giao thông"
    
    print("\n🔍 ĐANG TÌM KIẾM TRỰC TIẾP TRÊN FAISS...")
    # Gọi trực tiếp, không dùng filter
    docs = vectordb.similarity_search(query=query_chuan, k=3)
    
    for i, doc in enumerate(docs):
        print(f"\n--- KẾT QUẢ TOP {i+1} ---")
        print(f"ID: {doc.metadata.get('chunk_id', 'Không có ID')}")
        print(f"Nội dung: {doc.page_content}")
        print("-" * 30)

if __name__ == "__main__":
    test_raw_faiss()