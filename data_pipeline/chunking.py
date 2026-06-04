import re
from typing import List
import logging
import json
from pathlib import Path
from data_pipeline.parser import ParserArticle
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.contains import STANDARD_VEHICLES, VEHICLE_ALIASES, VEHICLE_GROUPS, CHUONG_TO_SECTION, DIEU_TO_SUBSECTION_FALLBACK, MUC_TO_SUBSECTION
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
        ),
    'tuoc_gplx': re.compile(
    r'tước quyền sử dụng giấy phép.*?(?:từ\s+)' # Thêm .*? để bắt mọi từ xen giữa (như "lái xe", "hạng A1")
    r'(\d+)\s*tháng\s*'                        # group(1): Số tháng min (đã bỏ [] cho gọn code)
    r'đến\s+'
    r'(\d+)\s*tháng',                          # group(2): Số tháng max
    re.IGNORECASE
)
}


STANDARD_VEHICLES_SORTED = sorted(STANDARD_VEHICLES, key=len, reverse=True)

def extract_vehicles(ten_dieu: str, text: str)-> dict:
    combined = f"{ten_dieu} {text}".lower()

    for alias, std in VEHICLE_ALIASES.items():
        combined = combined.replace(alias, std if isinstance(std, str) else std[0])
    
    matched = []
    temp = combined
    for vehicel in STANDARD_VEHICLES_SORTED:
        pattern = re.escape(vehicel.lower())
        if re.search(pattern, temp):
            matched.append(vehicel)
            temp = re.sub(pattern, '', temp)
    
    groups = set()
    for v in matched:
        for group, members in VEHICLE_GROUPS.items():
            if v in members:
                groups.add(group)

    in_ten_dieu = any(v.lower() in ten_dieu.lower() for v in matched)
    in_text     = any(v.lower() in text.lower()     for v in matched)
    source = 'both' if (in_ten_dieu and in_text) else \
             'ten_dieu' if in_ten_dieu else 'text'

    return {
        'vehicle_types':  matched,   # ['xe ô tô', 'xe chở hàng bốn bánh...']
        'vehicle_groups': list(groups),  # ['nhom_o_to']
        'vehicle_source': source,        # để debug sau này
    } 
def normalize(text: str) -> str:
    """Lowercase + bỏ dấu để match robust hơn"""
    import unicodedata
    text = text.lower()
    # Giữ dấu tiếng Việt vì pattern viết có dấu
    return text.strip()

def derive_sections(parsed_node: dict) -> dict:
    """
    Input:  node đã parse có ten_chuong, ten_muc, ten_dieu
    Output: {'doc_section': ..., 'doc_subsection': ...}
    """
    ten_chuong = normalize(parsed_node.get('ten_chuong', ''))
    ten_muc    = normalize(parsed_node.get('ten_muc', ''))
    ten_dieu   = normalize(parsed_node.get('ten_dieu', ''))

    # --- Tầng 1: doc_section từ tên chương ---
    doc_section = 'unknown'
    for pattern, section in CHUONG_TO_SECTION:
        if re.search(pattern, ten_chuong):
            doc_section = section
            break

    # --- Tầng 2: doc_subsection ---
    doc_subsection = 'unknown'

    if ten_muc:  # Ưu tiên 1: có tên mục → match tên mục
        for pattern, subsection in MUC_TO_SUBSECTION:
            if re.search(pattern, ten_muc):
                doc_subsection = subsection
                break
    else:        # Ưu tiên 2: không có mục → fallback tên điều
        for pattern, subsection in DIEU_TO_SUBSECTION_FALLBACK:
            if re.search(pattern, ten_dieu):
                doc_subsection = subsection
                break

    return {
        'doc_section':    doc_section,
        'doc_subsection': doc_subsection,
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

def parse_tuoc_gplx(text: str) -> tuple[int, int]:
    match = PATTERNS['tuoc_gplx'].search(text)
    if not match:
        return None, None
    def to_int(s: str) -> int:
        return s
    return to_int(match.group(1)), to_int(match.group(2))

def chunk_article(article: ParserArticle) -> list[dict]:
    """
    Từ một ParserArticle, tạo ra các chunk:
      1. Chunk cấp Điều (toàn bộ text)
      2. Chunk cấp Khoản (tách theo số 1., 2., 3., ...)
      3. Chunk cấp Điểm (tách theo a), b), c), ... nếu Khoản quá dài)
    """
    # doc_meta = registry.get(article.doc_id, {})
    section_info = derive_sections({
    'ten_chuong': article.chuong_name,
    'ten_muc': article.muc_name,
    'ten_dieu': article.tieu_de,
})
    # Metadata dùng chung cho mọi chunk của Điều này
    base = {
        'doc_id':            article.doc_id,
        'chuong':            article.chuong,
        'chuong_ten':        article.chuong_name,
        'muc':               article.muc,
        'muc_ten':           article.muc_name,
        'dieu':              article.so,
        'tieu_de':           article.tieu_de,
        'doc_section':       section_info['doc_section'],
        'doc_subsection':    section_info['doc_subsection'],
    }
    vehicle_info = extract_vehicles(article.tieu_de, article.text)
    parent_id  = f'{article.doc_id}_d{article.so}'
    chunks     = []
    pmin, pmax = parse_penalty(article.text)
    tuoc_gplx_min, tuoc_gplx_max = parse_tuoc_gplx(article.text)

    # ── CHUNK CẤP ĐIỀU 
    chunks.append({
        'chunk_id': parent_id,
        'text':     _strip_markdown(article.text),
        'metadata': {
            **base,
            'loai':        'dieu',
            'khoan':       None,
            'diem':        None,
            'parent_id':   None,
            'penalty_min': pmin,
            'penalty_max': pmax,

            'vehicle_types': vehicle_info['vehicle_types'],
            'vehicle_groups': vehicle_info['vehicle_groups'],
            'vehicle_source': vehicle_info['vehicle_source'],
            'tuoc_gplx_min':  tuoc_gplx_min,               # tháng, None nếu không có
            'tuoc_gplx_max':  tuoc_gplx_max,

            'violation_category':  None,
            'hanh_vi_vi_pham': None,
            'hinh_thuc_phat_bo_sung': None,
            'doi_tuong_ap_dung': None,
            'tru_diem_gplx':  None,            # số điểm trừ
            'la_tai_pham': False,
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

                'vehicle_types': vehicle_info['vehicle_types'],
                'vehicle_groups': vehicle_info['vehicle_groups'],
                'vehicle_source': vehicle_info['vehicle_source'],
                'tuoc_gplx_min':  tuoc_gplx_min,               # tháng, None nếu không có
                'tuoc_gplx_max':  tuoc_gplx_max,

                'violation_category':  None,
                'hanh_vi_vi_pham': None,
                'hinh_thuc_phat_bo_sung': None,
                'doi_tuong_ap_dung': None,
                'tru_diem_gplx':  None,            # số điểm trừ
                'la_tai_pham': False,
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

                    'vehicle_types': vehicle_info['vehicle_types'],
                    'vehicle_groups': vehicle_info['vehicle_groups'],
                    'vehicle_source': vehicle_info['vehicle_source'],
                    'tuoc_gplx_min':  tuoc_gplx_min,               # tháng, None nếu không có
                    'tuoc_gplx_max':  tuoc_gplx_max,

                    'violation_category':  None,
                    'hanh_vi_vi_pham': None,
                    'hinh_thuc_phat_bo_sung': None,
                    'doi_tuong_ap_dung': None,
                    'tru_diem_gplx':  None,            # số điểm trừ
                    'la_tai_pham': False,
                },
            })

    return chunks


def chunk_all(articles: list[ParserArticle]) -> list[dict]:
    chunks = []
    for a in articles:
        chunks.extend(chunk_article(a))
    parent_count = sum(1 for c in chunks if c["metadata"]["loai"] == "dieu")
    child_count = sum(1 for c in chunks if c["metadata"]["loai"] in ["khoan", "diem"])
    log.info(f"Chunking hoàn tất: {parent_count} Parent + {child_count} Child = {len(chunks)} Chunks.")
    return chunks


    