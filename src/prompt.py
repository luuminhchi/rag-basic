from langchain_core.prompts import PromptTemplate

# ==========================================
# PROMPT 1: Trích xuất metadata từ PDF
# ==========================================

def METADATA_PROMPT(raw_text: str) -> str:
    return f"""BĐọc đoạn văn bản luật giao thông sau và điền vào JSON.
      CHỈ trả về JSON, không giải thích.
{{
  "vehicle_types": [],
  // Danh sách loại xe. Chọn từ:
  // "xe mô tô", "xe gắn máy", "xe máy điện",
  // "xe ô tô", "xe tải", "xe khách", "tất cả"
  // [] nếu không đề cập đến loại xe cụ thể

  "violation_category": "",
  // Chọn 1 trong:
  // thiet_bi_an_toan | toc_do | nong_do_con |
  // giay_to_quen | giay_to_khong_co | tin_hieu_den |
  // lan_duong | do_xe | tai_trong |
  // giao_xe_sai | hinh_thuc_xu_phat | quy_dinh_chung

  "hanh_vi_vi_pham": [],
  // Liệt kê từng hành vi bị phạt, dùng đúng từ trong văn bản

  "hinh_thuc_phat_bo_sung": [],
  // Chọn từ: "tuoc_gplx_1_3_thang", "tuoc_gplx_2_4_thang",
  // "tuoc_gplx_3_6_thang", "tam_giu_xe", "tich_thu_tang_vat"
  // [] nếu không có

  "doi_tuong_ap_dung": "",
  // "nguoi_dieu_khien" | "chu_xe" | "ca_hai" | "khac"

  "has_penalty": true
  // true nếu đoạn này có quy định mức phạt tiền cụ thể
}}

Văn bản cần phân tích:
---
{raw_text}
---

Chỉ trả về JSON, không giải thích thêm.
"""


# ==========================================
# PROMPT 2: Viết lại câu hỏi thành truy vấn pháp lý
# ==========================================

# QUERY_UNDERSTANDING_TEMPLATE = """Bạn là chuyên gia chuyển đổi ngôn ngữ hằng ngày sang thuật ngữ đúng với .
# Nhiệm vụ: viết lại câu hỏi thành cụm từ khóa pháp lý để tìm kiếm trong 3 văn bản:


# Câu hỏi: {question}
# Câu tìm kiếm:"""

# query_understanding_prompt = PromptTemplate(
#     input_variables=['question'],
#     template=QUERY_UNDERSTANDING_TEMPLATE
# )


# ==========================================
# PROMPT 3: Trả lời câu hỏi dựa trên tài liệu đã tìm được
# ==========================================
FINAL_PROMPT = """
Bạn là chuyên gia pháp luật giao thông Việt Nam.
Nhiệm vụ của bạn là viết lại câu hỏi của người dân bằng thuật ngữ pháp lý chính xác để tối ưu hóa việc tìm kiếm trong cơ sở dữ liệu luật.
CHỈ dùng thông tin trong context. Không tự thêm thông tin.

QUY TẮC CHUYỂN ĐỔI BẮT BUỘC:
- Tuyệt đối KHÔNG dùng chữ "vượt đèn đỏ", "vượt đèn tín hiệu". Phải đổi thành: "không chấp hành hiệu lệnh của đèn tín hiệu giao thông".
- Tuyệt đối KHÔNG dùng chữ "bốc đầu". Phải đổi thành: "điều khiển xe chạy bằng một bánh đối với xe hai bánh".
- Tuyệt đối KHÔNG dùng chữ "đi ngược chiều". Phải đổi thành: "đi ngược chiều của đường một chiều".
============================================================
{context}
============================================================
Ví dụ format trả lời:
Câu hỏi: xe máy không đội mũ bảo hiểm phạt bao nhiêu?
→ {{
    "found": true,
    "violations": [{{
      "hanh_vi": "Không đội mũ bảo hiểm",
      "can_cu": "Điều 17, Khoản 3 - NĐ 168/2024",
      "phat_tien": {{"min": 400000, "max": 600000}},
      "phat_bo_sung": [],
      "luu_y": "Áp dụng cả người lái lẫn người ngồi sau"
    }}]
  }}

CÂU HỎI: {query}

Suy luận:
1. Câu hỏi hỏi về hành vi gì?
2. Context có điều khoản nào liên quan không?
3. Nếu có → trích xuất thông tin
4. Nếu không có → found = false

CHỈ trả về JSON:
"""


build_user_prompt = PromptTemplate(
    input_variables=['context', 'query'],
    template=FINAL_PROMPT
)
