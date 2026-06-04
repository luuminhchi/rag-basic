import json
import re
from langchain_core.messages import HumanMessage
from data_pipeline.indexing.meta_injection import build_meta_injection

VIOLATION_CATEGORIES = [
    "thiet_bi_an_toan",  # mũ bảo hiểm, đèn xe, còi, dây an toàn
    "toc_do",            # quá tốc độ, chạy dưới tốc độ tối thiểu
    "nong_do_con",       # rượu bia, nồng độ cồn, ma tuý
    "giay_to_quen",      # CÓ giấy tờ nhưng không mang theo
    "giay_to_khong_co",  # KHÔNG CÓ / hết hạn giấy tờ
    "tin_hieu_den",      # vượt đèn đỏ, không chấp hành tín hiệu
    "lan_duong",         # sai làn, ngược chiều
    "vuot_xe",           # vượt xe sai quy định
    "do_xe",             # dừng đỗ sai quy định
    "tai_trong",         # quá tải, quá số người
    "giao_xe_sai",       # giao xe cho người không đủ điều kiện
    "phu_hieu",          # phù hiệu kinh doanh vận tải
    "hanh_trinh",        # sai tuyến đường, lịch trình
    "thiet_bi_giam_sat", # camera, thiết bị giám sát hành trình
]

REWRITE_PROMPT = """Bạn là chuyên gia pháp luật giao thông Việt Nam.

Nhiệm vụ: Trích xuất thông tin từ câu hỏi và viết lại bằng thuật ngữ pháp lý chuẩn.

Ngữ cảnh tìm kiếm:
- Nhóm văn bản: {doc_section}
- Nhóm vi phạm: {doc_subsection}

Chuẩn hoá phương tiện theo văn bản pháp luật:
- xe máy / tay ga / xe số → ["xe mô tô", "xe gắn máy"]
- ô tô / xe hơi / xe con  → ["xe ô tô"]
- không đề cập            → []

Danh sách violation_category (chọn 1):
{categories}

Phân biệt giấy tờ:
- "quên mang" / "không mang theo" → giay_to_quen
- "không có"  / "hết hạn"         → giay_to_khong_co

Câu hỏi: {query}

Trả về JSON, không markdown:
{{
    "rewrite_query": "viết lại câu hỏi bằng thuật ngữ pháp lý",
    "vehicle_types": [],
    "violation_category": "",
    "hanh_vi_vi_pham": []
}}"""


def rewrite_query(user_query: str, classify_result: dict, llm) -> dict:
    """
    classify_result: output từ bước classify_query() trước đó
    {
        'doc_section':    'xu_phat',
        'doc_subsection': 'vi_pham_quy_tac_gt',
        'filter': {...}
    }
    """
    # ── Bước 1: Gọi LLM rewrite ──────────────────────────
    prompt = REWRITE_PROMPT.format(
        query         = user_query,
        doc_section   = classify_result.get('doc_section', ''),
        doc_subsection= classify_result.get('doc_subsection', ''),
        categories    = '\n'.join(f'- "{c}"' for c in VIOLATION_CATEGORIES),
    )

    raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()

    # Strip markdown nếu LLM vẫn trả về
    raw = re.sub(r'^```json|```$', '', raw, flags=re.MULTILINE).strip()
    rewrite = json.loads(raw)

    # ── Bước 2: Build injected query — CÙNG format với chunk ─
    # Tái dụng build_meta_injection bằng cách tạo fake chunk
    fake_chunk = {
        'text': rewrite['rewrite_query'],
        'metadata': {
            'vehicle_types':      rewrite.get('vehicle_types', []),
            'violation_category': rewrite.get('violation_category', ''),
            'hanh_vi_vi_pham':    rewrite.get('hanh_vi_vi_pham', []),
            'penalty_min':        None,
            'penalty_max':        None,
            'tru_diem_gplx':      None,
        }
    }
    injected_query = build_meta_injection(fake_chunk['metadata'], fake_chunk['text'])
    # ── Bước 3: Merge filter từ classify + rewrite ───────────
    final_filter = {
        **classify_result.get('filter', {}),        # doc_section, doc_subsection, vehicle_groups từ classify
        'violation_category': rewrite.get('violation_category') or None,
    }
    # Loại bỏ None để tránh over-filter
    final_filter = {k: v for k, v in final_filter.items() if v}

    return {
        'original_query': user_query,
        'rewrite_query':  rewrite['rewrite_query'],
        'injected_query': injected_query,   # → đưa vào FAISS search
        'filter':         final_filter,     # → đưa vào metadata filter
    }