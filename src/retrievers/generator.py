# Build context từ RerankResult
# ─────────────────────────────────────────────
from src.retrievers.rerank import RerankResult
from src.llm import llm
from src.prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, INTENT_INSTRUCTION
SCORE_THRESHOLD = 0.0  # Loại chunk có rerank_score quá thấp

def _build_context(retrieved_docs: list[RerankResult]) -> str:
    """
    Dùng text_index (có meta_injection đầy đủ) cho LLM
    — không dùng text_rerank vì đó là text rút gọn cho CrossEncoder.
    Lọc chunk có score quá thấp.
    """
    blocks = []

    for i, r in enumerate(retrieved_docs, 1):
        # Bỏ qua chunk không liên quan
        if r.rerank_score < SCORE_THRESHOLD:
            continue

        meta     = r.chunk.get('metadata', {})
        chunk_id = meta.get('chunk_id', '?')
        dieu     = meta.get('dieu', '')
        khoan    = meta.get('khoan', '')

        # Label rõ nguồn để LLM trích dẫn được
        label = f"Tài liệu {i}"
        if dieu:
            label += f" — Điều {dieu}"
            if khoan:
                label += f" Khoản {khoan}"
        label += f" (ID: {chunk_id})"

        # Dùng text_index: đủ meta_injection + text gốc
        text = r.chunk.get('text') or r.chunk.get('text_index', '')

        blocks.append(f"[{label}]\n{text}")

    return '\n\n---\n\n'.join(blocks) if blocks else ''


# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def generate_final_answer(
    user_query:     str,
    retrieved_docs: list[RerankResult],
    classify_result: dict,
    llm,
) -> str:
    """
    Args:
        user_query      : câu hỏi gốc của người dùng
        retrieved_docs  : list[RerankResult] từ rerank()
        classify_result : dict từ classify_query() — dùng intent để chọn prompt
        llm             : LLM instance
    """
    if not retrieved_docs:
        return ("Xin lỗi, tôi không tìm thấy quy định pháp luật nào "
                "phù hợp với câu hỏi của bạn.")

    # Build context — lọc theo score, dùng text đầy đủ
    context = _build_context(retrieved_docs)

    if not context:
        return ("Các kết quả tìm được có độ liên quan thấp. "
                "Bạn có thể hỏi cụ thể hơn về loại phương tiện "
                "hoặc hành vi vi phạm không?")

    # Chọn instruction theo intent
    intent            = classify_result.get('intent', 'query_muc_phat')
    intent_instruction = INTENT_INSTRUCTION.get(intent, INTENT_INSTRUCTION['query_tong_hop'])

    # Build prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        intent_instruction = intent_instruction,
        query              = user_query,
        context            = context,
    )

    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ])

    return response.content