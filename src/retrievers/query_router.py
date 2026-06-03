"""
Query Router — phân loại câu hỏi thành doc_section không cần gọi LLM.

Nguyên tắc ưu tiên:
    tru_diem > thu_tuc > quy_dinh_chung > xu_phat (fallback)

Nhóm xu_phat là fallback vì:
- Chiếm phần lớn câu hỏi người dùng (hỏi về phạt tiền theo xe)
- Ngay cả khi router nhầm sang xu_phat, hybrid search vẫn tìm được nếu
  FAISS semantic đủ tốt.
"""
from __future__ import annotations
import re

# ── Keyword rules theo thứ tự ưu tiên ────────────────────────
ROUTE_RULES: dict[str, list[str]] = {
    "tru_diem": [
        "trừ điểm", "tru diem",
        "mất điểm", "mat diem",
        "bị trừ mấy điểm", "bị trừ bao nhiêu điểm",
        "còn mấy điểm", "con may diem",
        "phục hồi điểm", "phuc hoi diem",
        "khôi phục điểm", "khoi phuc diem",
        "điểm giấy phép", "diem giay phep",
        "điểm gplx", "diem gplx",
    ],
    "thu_tuc": [
        "nộp phạt ở đâu", "nop phat o dau",
        "ai có quyền phạt", "ai co quyen phat",
        "thủ tục", "thu tuc",
        "khiếu nại", "khieu nai",
        "thi hành", "thi hanh",
        "thẩm quyền", "tham quyen",
        "nộp tiền phạt", "nop tien phat",
        "biên bản", "bien ban",
        "quyết định xử phạt", "quyet dinh xu phat",
        "cơ quan nào", "co quan nao",
        "trình tự", "trinh tu",
    ],
    "quy_dinh_chung": [
        "định nghĩa", "dinh nghia",
        "khái niệm", "khai niem",
        "nguyên tắc chung", "nguyen tac chung",
        "phạm vi áp dụng", "pham vi ap dung",
        "hiệu lực thi hành", "hieu luc thi hanh",
        "giải thích từ ngữ", "giai thich tu ngu",
    ],
}


def extract_article_for_routing(query: str) -> str | None:
    """
    Extract article number from query and determine its doc_section.
    
    Args:
        query: Câu hỏi từ người dùng
        
    Returns:
        doc_section or None if no article detected
        
    Logic (based on _assign_doc_section in chunking.py):
    - Articles 1-5: quy_dinh_chung
    - Articles 6-38: xu_phat
    - Articles 39-55: thu_tuc
    - Articles 56-58: tru_diem  
    - Articles 59-70: thu_tuc
    """
    match = re.search(r'Điều\s+(\d+)', query, re.IGNORECASE)
    if not match:
        return None
    
    dieu_num = int(match.group(1))
    
    # Mirroring chunking.py _assign_doc_section logic
    if 1 <= dieu_num <= 5:
        return "quy_dinh_chung"
    elif 6 <= dieu_num <= 38:
        return "xu_phat"
    elif 39 <= dieu_num <= 55:
        return "thu_tuc"
    elif 56 <= dieu_num <= 58:
        return "tru_diem"
    elif 59 <= dieu_num <= 70:
        return "thu_tuc"
    
    return None


def classify_query(query: str) -> str:
    """
    Phân loại câu hỏi → doc_section.
    
    Thứ tự ưu tiên:
    1. Extract article number (Điều N)
    2. Match keyword rules (tru_diem, thu_tuc, quy_dinh_chung)
    3. Fallback to xu_phat

    Args:
        query: Câu hỏi gốc từ người dùng.

    Returns:
        Một trong: 'xu_phat' | 'tru_diem' | 'thu_tuc' | 'quy_dinh_chung'
    """
    # Priority 1: Check for article number
    article_section = extract_article_for_routing(query)
    if article_section:
        return article_section
    
    # Priority 2: Match keywords
    query_lower = query.lower().strip()

    for section, keywords in ROUTE_RULES.items():
        if any(kw in query_lower for kw in keywords):
            return section

    # Fallback: nhóm phổ biến nhất
    return "xu_phat"
