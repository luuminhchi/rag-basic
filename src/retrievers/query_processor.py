from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from langchain_core.messages import HumanMessage
from data_pipeline.indexing.meta_injection import build_injection_text

def rewrite_and_inject(user_query: str, llm) -> str:
    prompt = f'''Viết lại câu hỏi bằng thuật ngữ pháp lý giao thông Việt Nam.
Chỉ trả về JSON hợp lệ, không giải thích, không markdown, không code block.

Danh sách violation_category (chọn 1 phù hợp nhất):
- "thiet_bi_an_toan": mũ bảo hiểm, gương chiếu hậu, đèn xe, còi, dây an toàn
- "toc_do": chạy quá tốc độ, vượt tốc độ quy định
- "nong_do_con": uống rượu bia khi lái xe, nồng độ cồn
- "giay_to_quen": có giấy tờ nhưng không mang theo khi lái xe (quên mang GPLX, đăng ký xe, bảo hiểm)
- "giay_to_khong_co": không có giấy phép lái xe, không có đăng ký xe (chưa từng được cấp hoặc hết hạn)
- "tin_hieu_den": vượt đèn đỏ, không chấp hành tín hiệu đèn giao thông
- "lan_duong": đi sai làn, vượt xe sai quy định, đi ngược chiều
- "do_xe": dừng đỗ sai quy định, đỗ xe trên vỉa hè
- "tai_trong": chở quá tải, quá số người quy định
- "giao_xe_sai": giao xe cho người không đủ điều kiện

LƯU Ý QUAN TRỌNG:
- "không mang theo" / "quên mang" giấy tờ → dùng "giay_to_quen"
- "không có" / "chưa có" / "hết hạn" giấy tờ → dùng "giay_to_khong_co"

Format trả về:
{{
    "rewrite_query": "câu viết lại bằng thuật ngữ pháp lý",
    "vehicle_types": ["xe mô tô", "xe gắn máy"],
    "violation_category": "giay_to_quen",
    "hanh_vi_vi_pham": ["hành vi 1", "hành vi 2"],
    "penalty_min": null,
    "penalty_max": null
}}
Câu hỏi: {user_query}'''

    rewriter_result = llm.invoke([HumanMessage(content=prompt)])    
    raw = rewriter_result.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    rewrite = json.loads(raw.strip())

    # ── Inject query — cùng format với chunk ──────────
    # Tạo fake chunk từ rewrite result để dùng lại hàm inject
    fake_chunk = {
        'text': rewrite['rewrite_query'],
        'metadata': {
            'vehicle_types': rewrite.get('vehicle_types', []),
            'violation_category': rewrite.get('violation_category', ''),
            'hanh_vi_vi_pham': rewrite.get('hanh_vi_vi_pham', []),
            'penalty_min': rewrite.get('penalty_min'),
            'penalty_max': rewrite.get('penalty_max'),
        }
    }

    injected_query = build_injection_text(fake_chunk)

    return {
        'original_query': user_query,
        'rewrite_query': rewrite['rewrite_query'],
        'injected_query': injected_query,
        'filter': {
            'vehicle_types': rewrite.get('vehicle_types', []),
            'violation_category': rewrite.get('violation_category', '')
            }
    }
