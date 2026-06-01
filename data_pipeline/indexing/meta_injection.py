CATEGORY_MAP = {
    'thiet_bi_an_toan':  'thiết bị an toàn',
    'toc_do': 'tốc độ',
    'nong_do_con': 'nồng độ cồn',
    'giay_to_quen': 'giấy tờ không mang theo',
    'giay_to_khong_co': 'không có giấy tờ',
    'tin_hieu_den': 'tín hiệu đèn giao thông',
    'lan_duong': 'làn đường',
    'do_xe': 'dừng độ xe',
    'tai_trong': 'tải trọng',
    'giao_xe_sai': 'giao xe sai',
}

SECTION_MAP = {
    'xu_phat':        'xử phạt vi phạm giao thông theo phương tiện',
    'tru_diem':       'trừ điểm giấy phép lái xe',
    'thu_tuc':        'thủ tục thẩm quyền xử phạt giao thông',
    'quy_dinh_chung': 'quy định chung nguyên tắc giao thông',
}

def build_injection_text(chunk: dict) -> str:
    meta = chunk['metadata']
    original_text = chunk['text']
    parts = []

    # [MOI] Them nhom tai lieu vao dau header
    section = meta.get('doc_section', '')
    if section:
        section_label = SECTION_MAP.get(section, section)
        parts.append(f'[Nhóm tài liệu]: {section_label}')

    if meta.get('vehicle_types'):
        vehicles_str = ', '.join(meta['vehicle_types'])
        parts.append(f'[Đối tượng áp dụng]: {vehicles_str}')
    
    if meta.get('violation_category'):
        violations_str = CATEGORY_MAP.get(
            meta['violation_category'],
            meta['violation_category']
        )
        parts.append(f'[Danh mục lỗi]: {violations_str}')
    
    if meta.get('hanh_vi_vi_pham'):
        behiviors = ', '.join(meta['hanh_vi_vi_pham'])
        parts.append(f'[Các hành vi cụ thể]: {behiviors}')
    if meta.get('penalty_min') and meta.get('penalty_max'):
        pmin = f'{meta["penalty_min"]:,}'
        pmax = f'{meta["penalty_max"]:,}'
        parts.append(f'[Mức phạt]: {pmin}đ đến {pmax}đ')
    
    injectied_header = '\n'.join(parts)
    if not injectied_header:
        return original_text
    return f'{injectied_header}\n{original_text}'