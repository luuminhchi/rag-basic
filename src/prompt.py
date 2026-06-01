from langchain_core.prompts import PromptTemplate

# ==========================================
# PROMPT 1: Trích xuất metadata từ PDF
# ==========================================

def METADATA_PROMPT(raw_text: str) -> str:
    return f"""Đọc đoạn văn bản luật giao thông sau và điền vào JSON.
      CHỈ trả về JSON, không giải thích.
{{
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

}}

Văn bản cần phân tích:
---
{raw_text}
---

Chỉ trả về JSON, không giải thích thêm.
"""


# ==========================================
# PROMPT 3: Trả lời câu hỏi dựa trên tài liệu đã tìm được
# ==========================================
FINAL_PROMPT = """
Bạn là chuyên gia pháp luật giao thông đường bộ Việt Nam.
Nhiệm vụ của bạn là phân tích các tài liệu luật trong context và trả lời câu hỏi của người dùng một cách chính xác, rõ ràng và dễ hiểu.

QUY TẮC:
1. CHỈ dùng thông tin được cung cấp trong context bên dưới. Tuyệt đối không tự bịa đặt hoặc dùng kiến thức ngoài context.
2. Nếu câu hỏi mang tính chất hỏi về quy định chung, thủ tục hành chính, thẩm quyền xử phạt, nguyên tắc trừ điểm hoặc định nghĩa (ví dụ: "thủ tục nộp phạt như thế nào", "luật trừ điểm GPLX ra sao", "thẩm quyền xử phạt của công an",...):
   - Đặt "is_general_query" = true.
   - Viết câu trả lời chi tiết, mạch lạc, dễ hiểu bằng tiếng Việt dưới dạng markdown vào trường "general_explanation".
   - Trường "violations" có thể để trống [] hoặc chứa các thông tin tóm tắt nếu cần.
3. Nếu câu hỏi hỏi về hành vi vi phạm cụ thể (ví dụ: "vượt đèn đỏ phạt bao nhiêu", "không đội mũ bảo hiểm phạt thế nào",...):
   - Đặt "is_general_query" = false.
   - Đặt "general_explanation" = null.
   - Liệt kê toàn bộ các hành vi vi phạm và mức phạt tìm thấy vào mảng "violations".
4. Phân biệt rõ các hành vi như "không mang theo" (quên mang) vs "không có" (chưa cấp/hết hạn) giấy tờ.
5. Nếu thực sự không tìm thấy bất kỳ thông tin nào liên quan đến câu hỏi trong context → đặt "found" = false.

============================================================
CONTEXT:
{context}
============================================================

CÂU HỎI: {query}

Suy luận từng bước:
1. Xác định loại câu hỏi: Đây là câu hỏi về quy định chung/thủ tục (general query) hay hành vi vi phạm cụ thể (specific violation)?
2. Tìm kiếm trong CONTEXT các điều luật liên quan.
3. Tổng hợp thông tin để điền vào cấu trúc JSON phù hợp.

Format JSON trả về:
{{
    "found": true,
    "is_general_query": true, // hoặc false
    "general_explanation": "Nội dung giải thích chi tiết nếu là câu hỏi quy định/thủ tục, viết bằng tiếng Việt rõ ràng, trình bày đẹp bằng markdown",
    "violations": [
      {{
        "phuong_tien": ["xe mô tô", "xe gắn máy"],
        "hanh_vi": "mô tả hành vi vi phạm theo đúng thuật ngữ pháp lý",
        "can_cu": "Điều X, Khoản Y - Nghị định X",
        "phat_tien": {{"min": 400000, "max": 600000}},
        "phat_bo_sung": ["tước GPLX 1-3 tháng"],
        "luu_y": "ghi chú thêm nếu có"
      }}
    ]
}}

Nếu không tìm thấy thông tin liên quan:
{{
    "found": false,
    "is_general_query": false,
    "general_explanation": null,
    "violations": []
}}

CHỈ TRẢ VỀ JSON HỢP LỆ, KHÔNG CHỨA BẤT KỲ GIẢI THÍCH NÀO NGOÀI KHỐI JSON.
Trả về JSON:
"""


build_user_prompt = PromptTemplate(
    input_variables=['context', 'query'],
    template=FINAL_PROMPT
)
