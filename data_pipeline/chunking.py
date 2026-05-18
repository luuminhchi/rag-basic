import re
import logging
import json
from pathlib import Path
from data_pipeline.parser import ParserArticle

log = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent.parent / 'docs/docs_registry.json'

# Cắt tại dòng bắt đầu bằng "1.", "2.", ... (Khoản)
RE_KHOAN = re.compile(r'(?=\n\s*\d+\.\s+)')
# Cắt tại dòng bắt đầu bằng "a)", "b)", "đ)", ... (Điểm)
RE_DIEM  = re.compile(r'(?=\n\s*[a-zđ]\)\s+)', re.IGNORECASE)

# Nếu một Khoản dài hơn ngưỡng này → tách tiếp xuống cấp Điểm
MAX_CHILD_LENGTH = 1500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        log.warning('docs_registry.json không tồn tại tại %s — metadata sẽ rỗng.', REGISTRY_PATH)
        return {}
    raw = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    return {k: v for k, v in raw.items() if not k.startswith('_')}


def _strip_markdown(text: str) -> str:
    """Bỏ ký hiệu Markdown (#, *, _) và chuẩn hóa khoảng trắng."""
    text = re.sub(r'[\#\*\_]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_tags(text: str) -> dict:
    """
    Trích xuất các tag ngữ nghĩa từ nội dung:
      - Loại phương tiện được đề cập
      - Mức phạt tiền (min, max)
    """
    vehicles = []
    if re.search(r'ô\s*tô|xe\s*kéo', text, re.IGNORECASE):
        vehicles.append('ô tô')
    if re.search(r'mô\s*tô|xe\s*gắn\s*máy|xe\s*máy', text, re.IGNORECASE):
        vehicles.append('xe máy')
    if re.search(r'xe\s*đạp|xe\s*thô\s*sơ', text, re.IGNORECASE):
        vehicles.append('xe đạp')
    if re.search(r'người\s*đi\s*bộ', text, re.IGNORECASE):
        vehicles.append('người đi bộ')

    p_min, p_max = 0, 0
    # Bắt mẫu "từ X.000 đồng đến Y.000 đồng"
    penalty_match = re.search(
        r'từ\s+([\d\.]+)\s*(?:đồng)?\s*đến\s+([\d\.]+)\s*(?:đồng)?',
        text, re.IGNORECASE
    )
    if penalty_match:
        try:
            p_min = int(penalty_match.group(1).replace('.', ''))
            p_max = int(penalty_match.group(2).replace('.', ''))
        except ValueError:
            pass

    return {
        'vehicle_types': vehicles,
        'penalty_min': p_min,
        'penalty_max': p_max,
    }


# Core chunker

def chunk_article(article: ParserArticle, registry: dict) -> list[dict]:
    """
    Từ một ParserArticle, tạo ra các chunk:
      1. Chunk cấp Điều (toàn bộ text)
      2. Chunk cấp Khoản (tách theo số 1., 2., 3., ...)
      3. Chunk cấp Điểm (tách theo a), b), c), ... nếu Khoản quá dài)
    """
    doc_meta = registry.get(article.doc_id, {})

    # Metadata dùng chung cho mọi chunk của Điều này
    base = {
        'doc_id':            article.doc_id,
        'source':            doc_meta.get('ten_day_du', article.doc_id),
        'co_quan_ban_hanh':  doc_meta.get('co_quan_ban_hanh', ''),
        'ngay_ban_hanh':     doc_meta.get('ngay_ban_hanh', ''),
        'linh_vuc':          doc_meta.get('linh_vuc', ''),
        'loai_van_ban':      doc_meta.get('loai_van_ban', ''),
        'chuong':            article.chuong,
        'chuong_ten':        article.chuong_name,
        'muc':               article.muc,
        'muc_ten':           article.muc_name,
        'dieu':              article.so,
        'tieu_de':           article.tieu_de,
    }

    parent_id  = f'{article.doc_id}_d{article.so}'
    dieu_tags  = _extract_tags(article.text)
    chunks     = []

    # ── CHUNK CẤP ĐIỀU ──────────────────────────────────────────────────────
    chunks.append({
        'chunk_id': parent_id,
        'text':     _strip_markdown(article.text),
        'metadata': {
            **base,
            'loai':        'dieu_phang',
            'khoan':       None,
            'diem':        None,
            'parent_id':   None,
            **dieu_tags,
        },
    })

    # ── TÁCH KHOẢN ──────────────────────────────────────────────────────────
    # Thêm \n vào đầu để RE_KHOAN (lookbehind \n) hoạt động đúng ở khoản 1
    raw_sections = RE_KHOAN.split('\n' + article.text)

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

        khoan_tags = _extract_tags(body)

        # ── CHUNK CẤP KHOẢN ─────────────────────────────────────────────────
        chunks.append({
            'chunk_id': khoan_id,
            'text':     _strip_markdown(body),
            'metadata': {
                **base,
                'loai':      'khoan',
                'khoan':     khoan_no,
                'diem':      None,
                'parent_id': parent_id,
                **khoan_tags,
            },
        })

        if len(body) <= MAX_CHILD_LENGTH:
            continue

        # ── TÁCH ĐIỂM (nếu Khoản dài) ───────────────────────────────────────
        diem_sections = RE_DIEM.split('\n' + body)

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

            diem_tags = _extract_tags(diem_body)

            chunks.append({
                'chunk_id': diem_id,
                'text':     _strip_markdown(diem_body),
                'metadata': {
                    **base,
                    'loai':      'diem',
                    'khoan':     khoan_no,
                    'diem':      diem_chr,
                    'parent_id': khoan_id,
                    **diem_tags,
                },
            })

    return chunks


def chunk_all(articles: list[ParserArticle]) -> list[dict]:
    registry = _load_registry()
    chunks = []
    for a in articles:
        chunks.extend(chunk_article(a, registry))
        
    parent_count = sum(1 for c in chunks if c["metadata"]["loai"] == "dieu_phang")
    child_count = sum(1 for c in chunks if c["metadata"]["loai"] in ["khoan", "diem"])
    log.info(f"Chunking hoàn tất: {parent_count} Parent + {child_count} Child = {len(chunks)} Chunks.")
    return chunks