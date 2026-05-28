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

QUERY_UNDERSTANDING_TEMPLATE = """Bạn là chuyên gia chuyển đổi ngôn ngữ hằng ngày sang thuật ngữ pháp lý Việt Nam.
Nhiệm vụ: viết lại câu hỏi thành cụm từ khóa pháp lý để tìm kiếm trong 3 văn bản:
- NĐ 168/2024/NĐ-CP: mức xử phạt vi phạm hành chính giao thông (phạt tiền, tước GPLX, trừ điểm GPLX)
- Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15: quy tắc giao thông, hành vi bị cấm, điều kiện phương tiện và người lái
- Luật Giao thông đường bộ 26/2001/QH10: định nghĩa và quy tắc nền tảng về giao thông đường bộ

Ánh xạ từ ngữ hằng ngày → thuật ngữ pháp lý:
| Ngôn ngữ thường dùng | Thuật ngữ pháp lý |
|---|---|
| vượt đèn đỏ | không chấp hành hiệu lệnh đèn tín hiệu giao thông |
| đi ngược chiều | đi ngược chiều đường một chiều |
| không xi nhan / không bật đèn xi nhan | chuyển hướng không có tín hiệu báo hướng rẽ |
| say rượu / uống rượu lái xe / nồng độ cồn | vi phạm nồng độ cồn khi điều khiển phương tiện |
| quá tốc độ / phóng nhanh / chạy nhanh | chạy quá tốc độ quy định |
| phơi lúa / phơi nông sản trên đường | phơi thóc lúa rơm rạ nông sản trên đường bộ |
| đỗ xe sai / đậu xe sai chỗ | dừng đỗ xe không đúng nơi quy định |
| chạy vào làn ưu tiên / vào làn xe buýt | đi vào làn đường không được phép |
| không đội mũ bảo hiểm | không đội mũ bảo hiểm cho người ngồi trên xe mô tô xe gắn máy |
| dùng điện thoại khi lái xe | sử dụng điện thoại di động khi điều khiển phương tiện |
| lái xe không bằng lái / không có GPLX | điều khiển phương tiện không có giấy phép lái xe |
| xe không đăng ký / xe không biển số | phương tiện không có đăng ký xe |
| chở quá người / chở quá số người | chở người quá số lượng quy định |
| chở hàng cồng kềnh / hàng quá khổ | chở hàng hóa quá kích thước giới hạn |
| không thắt dây an toàn | không sử dụng dây đai an toàn khi ngồi trên ô tô |
| vượt phải / vượt bên phải | vượt xe không đúng quy định |
| rẽ sai làn / chuyển làn sai | chuyển làn đường không đúng nơi quy định |
| lấn tuyến / đi sai làn | không đi đúng làn đường phần đường quy định |
| bấm còi quá mức / bấm còi inh ỏi | sử dụng còi xe không đúng quy định |
| xe hết hạn đăng kiểm / không đăng kiểm | phương tiện không có giấy chứng nhận kiểm định an toàn kỹ thuật |
| trẻ em ngồi ghế trước / trẻ em không có ghế an toàn | chở trẻ em không đúng quy định |
| lùi xe sai / lùi ẩu | lùi xe không đúng quy định |
| dừng xe trên cầu / đỗ xe trên cầu | dừng đỗ xe trên cầu không đúng quy định |
| tước bằng lái / bị giữ GPLX | tước quyền sử dụng giấy phép lái xe |
| trừ điểm bằng lái | trừ điểm giấy phép lái xe |
| phạt nguội | xử phạt vi phạm giao thông qua hình ảnh camera |

Quy tắc xác định loại câu hỏi và viết từ khóa:
1. Hỏi MỨC PHẠT / bị phạt bao nhiêu → bắt đầu bằng "xử phạt" + hành vi pháp lý + loại phương tiện
2. Hỏi QUY ĐỊNH / có được phép không / điều kiện → dùng từ khóa mô tả hành vi + "quy tắc giao thông"
3. Hỏi ĐIỀU KIỆN PHƯƠNG TIỆN / đăng ký / đăng kiểm → "điều kiện phương tiện tham gia giao thông" + đối tượng
4. Hỏi ĐIỀU KIỆN NGƯỜI LÁI / bằng lái / tuổi → "điều kiện người điều khiển" + loại phương tiện
5. Hỏi SO SÁNH / khác nhau / phân biệt → liệt kê cả hai đối tượng trong từ khóa
6. Hỏi THỦ TỤC / cách / làm gì khi → "thủ tục" + đối tượng pháp lý
7. Hỏi ĐỊNH NGHĨA / là gì → tên thuật ngữ pháp lý cần tra cứu
- Giữ nguyên số Điều/Khoản/Điểm nếu câu hỏi đề cập đến
- Giữ nguyên loại phương tiện cụ thể (xe mô tô, xe ô tô, xe tải, xe khách...)
- CHỈ trả về câu tìm kiếm, không giải thích, không thêm dấu câu cuối

Ví dụ:
Câu hỏi: vượt đèn đỏ xe máy bị phạt bao nhiêu
Câu tìm kiếm: xử phạt không chấp hành hiệu lệnh đèn tín hiệu giao thông xe mô tô xe gắn máy

Câu hỏi: say rượu lái ô tô phạt bao nhiêu
Câu tìm kiếm: xử phạt vi phạm nồng độ cồn điều khiển xe ô tô

Câu hỏi: xe đạp có phải đội mũ bảo hiểm không
Câu tìm kiếm: điều kiện người điều khiển xe đạp mũ bảo hiểm quy tắc giao thông

Câu hỏi: xe tải chở hàng quá tải bị phạt bao nhiêu
Câu tìm kiếm: xử phạt chở hàng hóa quá tải trọng xe tải

Câu hỏi: bằng lái xe máy hạng A1 được điều khiển xe gì
Câu tìm kiếm: điều kiện người điều khiển giấy phép lái xe hạng A1 loại xe mô tô

Câu hỏi: ô tô không có bảo hiểm bắt buộc phạt bao nhiêu
Câu tìm kiếm: xử phạt phương tiện không có bảo hiểm trách nhiệm dân sự xe ô tô

Câu hỏi: trẻ em ngồi xe máy có cần đội mũ không
Câu tìm kiếm: điều kiện chở trẻ em trên xe mô tô xe gắn máy mũ bảo hiểm

Câu hỏi: {question}
Câu tìm kiếm:"""

query_understanding_prompt = PromptTemplate(
    input_variables=['question'],
    template=QUERY_UNDERSTANDING_TEMPLATE
)


# ==========================================
# PROMPT 3: Trả lời câu hỏi dựa trên tài liệu đã tìm được
# ==========================================

SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật giao thông đường bộ Việt Nam.

NGUYÊN TẮC BẮT BUỘC:
- Chỉ dùng thông tin trong <TÀI_LIỆU> để trả lời. Không suy đoán, không bịa số liệu.
- Mỗi thông tin trích dẫn phải ghi nguồn [Nguồn X, Điều Y, Khoản Z] ngay sau câu đó.
- Nếu tài liệu không đủ thông tin → trả lời "Tài liệu hiện tại không có quy định về vấn đề này."
- Không thêm lời khuyên cá nhân, cảnh báo an toàn, hay nội dung ngoài phạm vi câu hỏi.

NGUỒN TÀI LIỆU:
- NĐ 168/2024/NĐ-CP: mức phạt tiền, tước GPLX, trừ điểm GPLX theo từng loại phương tiện
- Luật 36/2024/QH15: quy tắc giao thông, hành vi bị cấm, điều kiện phương tiện và người lái
- Luật 26/2001/QH10: định nghĩa và quy tắc nền tảng giao thông đường bộ

<TÀI_LIỆU>
{context}
</TÀI_LIỆU>

<CÂU_HỎI>{question}</CÂU_HỎI>

CÁCH TRẢ LỜI THEO TỪNG DẠNG CÂU HỎI:

**Dạng 1 – Hỏi mức phạt:**
- Nêu mức phạt tiền theo từng loại phương tiện (nếu câu hỏi không chỉ rõ loại xe).
- Nêu hình thức phạt bổ sung: tước GPLX (bao nhiêu tháng), trừ điểm GPLX (bao nhiêu điểm) nếu có.
- Ghi [Nguồn X, Điều Y, Khoản Z] ngay sau mỗi mức phạt.
- Ví dụ định dạng:
  - Xe mô tô, xe gắn máy: phạt [X] – [Y] triệu đồng [Nguồn 1, Điều 6, Khoản 4]
  - Ô tô: phạt [X] – [Y] triệu đồng, tước GPLX [Z] tháng [Nguồn 1, Điều 5, Khoản 8]

**Dạng 2 – Hỏi quy định / có được phép không:**
- Trích dẫn trực tiếp điều khoản quy định hành vi đó.
- Nếu có quy định cấm → trả lời "Không được phép. [trích dẫn quy định] [Nguồn X, Điều Y]"
- Nếu không tìm thấy quy định cấm → "Tài liệu không có điều khoản cấm hành vi này."

**Dạng 3 – Hỏi điều kiện phương tiện / người lái:**
- Liệt kê đầy đủ các điều kiện bắt buộc được quy định trong tài liệu.
- Ghi [Nguồn X, Điều Y] sau mỗi nhóm điều kiện.

**Dạng 4 – Hỏi định nghĩa / giải thích khái niệm:**
- Trích dẫn định nghĩa trong tài liệu và ghi [Nguồn X, Điều Y].
- Nếu không có định nghĩa chính thức → nêu rõ điều đó.

**Dạng 5 – Hỏi so sánh / phân biệt hai đối tượng:**
- Trình bày theo từng đối tượng riêng, ghi nguồn sau mỗi phần.

Dừng ngay sau khi trả lời xong. Không thêm phần "Lưu ý", "Tóm lại", hay bất kỳ nội dung nào khác."""

build_user_prompt = PromptTemplate(
    input_variables=['context', 'question'],
    template=SYSTEM_PROMPT
)
