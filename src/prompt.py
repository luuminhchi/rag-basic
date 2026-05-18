def METADAT_PROMPT(raw_text: str) -> str:
    return f"""Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam.
Hãy đọc đoạn văn bản sau (trích từ trang đầu của một văn bản pháp luật) và trích xuất metadata.

Trả về JSON hợp lệ với đúng các trường sau, không thêm trường khác:
{{
  "ten_day_du": "Tên đầy đủ của văn bản (ví dụ: Nghị định 168/2024/NĐ-CP)",
  "so_hieu": "Số hiệu văn bản (ví dụ: 168/2024/NĐ-CP)",
  "loai_van_ban": "Loại văn bản (Nghị định / Thông tư / Luật / Quyết định / ...)",
  "co_quan_ban_hanh": "Cơ quan ban hành (ví dụ: Chính phủ)",
  "ngay_ban_hanh": "Ngày ban hành định dạng YYYY-MM-DD (ví dụ: 2024-12-26)",
  "linh_vuc": "Lĩnh vực áp dụng (ví dụ: Giao thông đường bộ)",
  "hieu_luc_tu": "Ngày có hiệu lực định dạng YYYY-MM-DD, để null nếu không có",
  "mo_ta": "Mô tả ngắn nội dung chính của văn bản (1-2 câu)"
}}

Văn bản cần phân tích:
---
{raw_text}
---

Chỉ trả về JSON, không giải thích thêm.
"""
