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
  // "tuoc_gplx_3_6_thang", "tam_giu_xe", "tich_thu_phuong_tien"
  // [] nếu không có
  
  "doi_tuong_ap_dung": "",
  // "nguoi_dieu_khien" | "chu_xe" | "ca_hai" | "khac"

  "tru_diem_gplx": null,
  // hãy liệt kê chính xác tập trung ở các điểm điền số điểm trừ nếu có phù hợp với các điều khoản, null nếu không có
  "lai_tai_pham": false
  // true nếu có cụm từ "Tái phạm hành vi" hoặc "tái phạm hành vi"
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

SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn pháp luật giao thông đường bộ Việt Nam.
Nhiệm vụ: Trả lời câu hỏi DỰA TRÊN các quy định pháp luật được cung cấp.

Nguyên tắc:
- Chỉ trả lời dựa trên thông tin trong phần [QUY ĐỊNH PHÁP LUẬT]
- Trích dẫn rõ Điều, Khoản khi trả lời
- Nếu không đủ thông tin → nói rõ không tìm thấy quy định phù hợp
- Không suy đoán hoặc bịa đặt số liệu"""


# Mỗi intent → nhấn mạnh khác nhau trong câu trả lời
INTENT_INSTRUCTION = {
    'query_muc_phat': "Tập trung trả lời: mức tiền phạt cụ thể (min-max), "
                      "hình thức phạt bổ sung nếu có.",

    'query_che_tai':  "Tập trung trả lời: số điểm trừ GPLX, "
                      "thời gian tước GPLX, tịch thu phương tiện nếu có.",

    'query_hanh_vi':  "Tập trung trả lời: hành vi nào bị coi là vi phạm, "
                      "điều kiện áp dụng.",

    'query_thu_tuc':  "Tập trung trả lời: trình tự thủ tục, "
                      "cơ quan có thẩm quyền, thời hạn.",

    'query_tong_hop': "Trả lời đầy đủ: hành vi vi phạm, mức phạt tiền, "
                      "hình thức phạt bổ sung, trừ điểm GPLX nếu có.",
}

USER_PROMPT_TEMPLATE = """{intent_instruction}

[CÂU HỎI]
{query}

[QUY ĐỊNH PHÁP LUẬT]
{context}

[YÊU CẦU TRẢ LỜI]
Trả lời ngắn gọn, rõ ràng. Trích dẫn số Điều, Khoản cụ thể."""


