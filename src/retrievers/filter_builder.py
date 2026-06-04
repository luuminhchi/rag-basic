import re
ENTITY_EXTRACTORS = {

    # Loại phương tiện
    'vehicle': {
        'xe máy|mô tô|tay ga|xe số':  'nhom_mo_to',
        'ô tô|xe hơi|xe con|xe tải':  'nhom_o_to',
        'xe đạp|xe thô sơ':           'nhom_tho_so',
        'máy kéo|xe chuyên dùng':     'nhom_may_keo',
        'người đi bộ':                'nhom_nguoi',
    },

    # Loại vi phạm → map về subsection
    'violation_type': {
        r'đèn đỏ|tín hiệu|đèn tín hiệu':    'vi_pham_quy_tac_gt',
        r'tốc độ|quá tốc|chạy nhanh':        'vi_pham_quy_tac_gt',
        r'nồng độ cồn|uống rượu|bia':        'vi_pham_quy_tac_gt',
        r'đăng kiểm|đăng ký|biển số':        'vi_pham_phuong_tien',
        r'bằng lái|giấy phép lái xe|gplx':   'vi_pham_nguoi_dieu_khien',
        r'chở hàng|vận chuyển|quá tải':      'vi_pham_van_chuyen',
        r'phù hiệu|kinh doanh vận tải':      'vi_pham_van_chuyen',
    },

    # Điều kiện đặc thù
    'special_condition': {
        r'nồng độ cồn\s*([\d.]+)':  'nong_do_con',   # extract số
        r'quá\s*(\d+)\s*km':        'nguong_toc_do',  # extract số
        r'tái phạm|lần \d+':        'la_tai_pham',
    }
}

def extract_entities(query: str) -> dict:
    query_lower = query.lower()
    result = {
        'vehicle_group':  None,
        'doc_subsection': None,
        'special':        {}
    }

    for pattern, group in ENTITY_EXTRACTORS['vehicle'].items():
        if re.search(pattern, query_lower):
            result['vehicle_group'] = group
            break

    for pattern, subsection in ENTITY_EXTRACTORS['violation_type'].items():
        if re.search(pattern, query_lower):
            result['doc_subsection'] = subsection
            break

    for pattern, key in ENTITY_EXTRACTORS['special_condition'].items():
        m = re.search(pattern, query_lower)
        if m:
            result['special'][key] = m.group(1) if m.lastindex else True

    return result