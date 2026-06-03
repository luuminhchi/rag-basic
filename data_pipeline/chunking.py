import re
import logging
import json
from pathlib import Path
from data_pipeline.parser import ParserArticle

log = logging.getLogger(__name__)

# REGISTRY_PATH = Path(__file__).parent.parent / 'docs/docs_registry.json'

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

STANDARD_VEHICLES = [
    "xe ô tô", "xe chở người bốn bánh có gắn động cơ", "xe chở hàng bốn bánh có gắn động cơ", "các loại xe tương tự xe ô tô",
    "xe mô tô", "xe gắn máy", "xe máy điện", "các loại xe tương tự xe mô tô",
    "máy kéo", "xe máy chuyên dùng",
    "xe đạp", "xe đạp máy", "xe thô sơ",
    "người đi bộ", "người điều khiển, dẫn dắt súc vật", "kéo xe súc vật", "xe chở xác"
]

def extract_vehicles_from_text(text: str) -> list[str]:
    """Hàm quét tìm MỌI loại phương tiện có xuất hiện trong một đoạn text bất kỳ"""
    if not text:
        return []
        
    text_lower = text.lower()
    found_vehicles = []
    
    for vehicle in STANDARD_VEHICLES:
        if vehicle in text_lower:
            found_vehicles.append(vehicle)
            
    return found_vehicles

def _strip_markdown(text: str) -> str:
    """Bỏ ký hiệu Markdown (#, *, _) và chuẩn hóa khoảng trắng."""
    text = re.sub(r'[\#\*\_]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _assign_doc_section(chuong: str, dieu: int | None) -> str:
    """
    Gán nhóm tài liệu (doc_section) dựa trên Chương và số Điều.
    """
    if chuong == "II" or (dieu and 6 <= dieu <= 38):
        return "xu_phat"
    if chuong == "V" or (dieu and 56 <= dieu <= 58):
        return "tru_diem"
    if chuong in ("IV", "VI") or (dieu and (39 <= dieu <= 55 or 59 <= dieu <= 70)):
        return "thu_tuc"
    return "quy_dinh_chung"


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
        'doc_section':       _assign_doc_section(article.chuong, article.so),
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

            'vehicle_types': [],
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

                'vehicle_types': [],
                'violation_category':  None,
                'hanh_vi_vi_pham': None,
                'hinh_thuc_phat_bo_sung': None,
                'doi_tuong_ap_dung': None,
                'has_penalty': pmin > 0
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

                    'vehicle_types': [],  # Kế thừa xe từ Điều cha
                    'violation_category':  None,
                    'hanh_vi_vi_pham': None,
                    'hinh_thuc_phat_bo_sung': None,
                    'doi_tuong_ap_dung': None,
                    'has_penalty': pmin > 0
                },
            })

    return chunks


def _apply_smart_vehicle_inheritance(chunks: list[dict]) -> list[dict]:
    """
    Gán vehicle_types
    - Cấp Điều: chỉ dùng xe tìm thấy trong text của Điều đó.
    - Cấp Khoản/Điểm: union xe của Điều cha + xe tìm thấy trong text của chính nó.
    """
    current_vehicles: list[str] = []

    for chunk in chunks:
        meta = chunk.get('metadata', {})
        loai = meta.get('loai')
        local_vehicles = extract_vehicles_from_text(chunk.get('text', ''))

        if loai in ('dieu_phang', 'dieu'):
            current_vehicles = local_vehicles
            meta['vehicle_types'] = current_vehicles
        else:
            meta['vehicle_types'] = list(set(current_vehicles + local_vehicles))

        chunk['metadata'] = meta

    return chunks


def chunk_all(articles: list[ParserArticle]) -> list[dict]:
    chunks = []
    for a in articles:
        chunks.extend(chunk_article(a))

    chunks = _apply_smart_vehicle_inheritance(chunks)

    parent_count = sum(1 for c in chunks if c["metadata"]["loai"] == "dieu_phang")
    child_count = sum(1 for c in chunks if c["metadata"]["loai"] in ["khoan", "diem"])
    log.info(f"Chunking hoàn tất: {parent_count} Parent + {child_count} Child = {len(chunks)} Chunks.")
    return chunks


    