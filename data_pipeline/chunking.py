import re
import logging
import json
from pathlib import Path
from data_pipeline.parser import ParserArticle

log = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent.parent / 'docs/docs_registry.json'

PATTERNS = {
    # Cắt tại dòng bắt đầu bằng "1.", "2.", ... (Khoản)
    'khoan': re.compile(r'(?=\n\s*\d+\.\s+)'),
    # Cắt tại dòng bắt đầu bằng "a)", "b)", "đ)", ... (Điểm)
    'diem'  : re.compile(r'(?=\n\s*[a-zđ]\)\s+)', re.IGNORECASE),

    "penalty": re.compile(
            r"Phạt tiền từ\s+"
            r"([\d\.]+)\s*(?:đồng)?\s*"
            r"đến\s+"
            r"([\d\.]+)\s*(?:đồng)?",
            re.IGNORECASE
        )
}


def _strip_markdown(text: str) -> str:
    """Bỏ ký hiệu Markdown (#, *, _) và chuẩn hóa khoảng trắng."""
    text = re.sub(r'[\#\*\_]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_penalty(text: str) -> tuple[int, int]:
    match = PATTERNS['penalty'].search(text)
    if not match:
        return 0, 0
    def to_int(s: str) -> int:
        return int(s.replace('.', '').replace(',', ''))
    return to_int(match.group(1)), to_int(match.group(2))

# Core chunker

def chunk_article(article: ParserArticle) -> list[dict]:
    """
    Từ một ParserArticle, tạo ra các chunk:
      1. Chunk cấp Điều (toàn bộ text)
      2. Chunk cấp Khoản (tách theo số 1., 2., 3., ...)
      3. Chunk cấp Điểm (tách theo a), b), c), ... nếu Khoản quá dài)
    """
    # doc_meta = registry.get(article.doc_id, {})

    # Metadata dùng chung cho mọi chunk của Điều này
    base = {
        'doc_id':            article.doc_id,
        'chuong':            article.chuong,
        'chuong_ten':        article.chuong_name,
        'muc':               article.muc,
        'muc_ten':           article.muc_name,
        'dieu':              article.so,
        'tieu_de':           article.tieu_de,
    }

    parent_id  = f'{article.doc_id}_d{article.so}'
    chunks     = []
    pmin, pmax = parse_penalty(article.text)
    # ── CHUNK CẤP ĐIỀU 
    chunks.append({
        'chunk_id': parent_id,
        'text':     _strip_markdown(article.text),
        'metadata': {
            **base,
            'loai':        'dieu_phang',
            'khoan':       None,
            'diem':        None,
            'parent_id':   None,
            'penalty_min': pmin,
            'penalty_max': pmax,

            'vehicle_types': None,
            'violation_category':  None,
            'hanh_vi_vi_pham': None,
            'hinh_thuc_phat_bo_sung': None,
            'doi_tuong_ap_dung': None,
            'has_penalty': pmin > 0
        },
    })

    # ── TÁCH KHOẢN 
    # Thêm \n vào đầu để RE_KHOAN (lookbehind \n) hoạt động đúng ở khoản 1
    raw_sections = PATTERNS['khoan'].split('\n' + article.text)

    # Bỏ phần đầu nếu không phải khoản (phần mô tả tổng quát của Điều)
    if raw_sections and not re.match(r'^\s*\d+\.', raw_sections[0].strip()):
        raw_sections.pop(0) 

    if not raw_sections:
        # Điều không có khoản → chỉ trả về chunk cấp Điều
        return chunks

    for body in raw_sections:
        body = body.strip()
        if not body:
            continue

        # Lấy số khoản
        k_match  = re.match(r'^(\d+)\.', body)
        khoan_no = int(k_match.group(1)) if k_match else 0
        khoan_id = f'{parent_id}_k{khoan_no}'

        # ── CHUNK CẤP KHOẢN
        chunks.append({
            'chunk_id': khoan_id,
            'text':     _strip_markdown(body),
            'metadata': {
                **base,
                'loai':      'khoan',
                'khoan':     khoan_no,
                'diem':      None,
                'parent_id': parent_id,
                'penalty_min': pmin,
                'penalty_max': pmax,

                # 'vehicle_types': None,
                # 'violation_category':  None,
                # 'hanh_vi_vi_pham': None,
                # 'hinh_thuc_phat_bo_sung': None,
                # 'doi_tuong_ap_dung': None,
                # 'has_penalty': pmin > 0
            },
        })

        # ── TÁCH ĐIỂM (nếu Khoản dài)
        diem_sections = PATTERNS['diem'].split('\n' + body)

        # Bỏ phần mở đầu khoản (trước điểm a)
        if diem_sections and not re.match(r'^\s*[a-zđ]\)', diem_sections[0].strip(), re.IGNORECASE):
            diem_sections.pop(0)

        for diem_body in diem_sections:
            diem_body = diem_body.strip()
            if not diem_body:
                continue

            d_match  = re.match(r'^([a-zđ])\)', diem_body, re.IGNORECASE)
            diem_chr = d_match.group(1).lower() if d_match else '?'
            diem_id  = f'{khoan_id}_dp{diem_chr}'


            chunks.append({
                'chunk_id': diem_id,
                'text':     _strip_markdown(diem_body),
                'metadata': {
                    **base,
                    'loai':      'diem',
                    'khoan':     khoan_no,
                    'diem':      diem_chr,
                    'parent_id': khoan_id,
                    'penalty_min': pmin,
                    'penalty_max': pmax,

                    'vehicle_types': None,
                    'violation_category':  None,
                    'hanh_vi_vi_pham': None,
                    'hinh_thuc_phat_bo_sung': None,
                    'doi_tuong_ap_dung': None,
                    'has_penalty': pmin > 0
                },
            })

    return chunks


def chunk_all(articles: list[ParserArticle]) -> list[dict]:
    chunks = []
    for a in articles:
        chunks.extend(chunk_article(a))
        
    parent_count = sum(1 for c in chunks if c["metadata"]["loai"] == "dieu_phang")
    child_count = sum(1 for c in chunks if c["metadata"]["loai"] in ["khoan", "diem"])
    log.info(f"Chunking hoàn tất: {parent_count} Parent + {child_count} Child = {len(chunks)} Chunks.")
    return chunks


    