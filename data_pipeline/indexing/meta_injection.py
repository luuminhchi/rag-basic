def build_meta_injection(meta: dict, chunk_text: str) -> str:
    """
    Chỉ inject các SEMANTIC fields.
    Các field None hoặc empty → bỏ qua, không tạo dòng thừa.
    """
    lines = []

    # --- Nhóm 1: Định danh ngữ nghĩa (tên, không phải số) ---
    if meta.get('muc_ten'):
        lines.append(f"[Nhóm vi phạm: {meta['muc_ten']}]")

    if meta.get('tieu_de'):
        lines.append(f"[Điều khoản: {meta['tieu_de']}]")

    # --- Nhóm 2: Phương tiện ---
    if meta.get('vehicle_types'):
        vt = ', '.join(meta['vehicle_types'])
        lines.append(f"[Phương tiện: {vt}]")

    # --- Nhóm 3: Hành vi và đối tượng ---
    if meta.get('violation_category'):
        lines.append(f"[Loại vi phạm: {meta['violation_category']}]")

    if meta.get('hanh_vi_vi_pham'):
        lines.append(f"[Hành vi: {meta['hanh_vi_vi_pham']}]")

    if meta.get('doi_tuong_ap_dung'):
        lines.append(f"[Đối tượng: {meta['doi_tuong_ap_dung']}]")

    # --- Nhóm 4: Chế tài (format thân thiện, không phải số raw) ---
    pmin = meta.get('penalty_min')
    pmax = meta.get('penalty_max')
    if pmin and pmax:
        lines.append(
            f"[Phạt tiền: {pmin:,} - {pmax:,} đồng]"
            .replace(',', '.')   # format VN: 2.000.000
        )

    if meta.get('tru_diem_gplx'):
        lines.append(f"[Trừ điểm GPLX: {meta['tru_diem_gplx']} điểm]")

    if meta.get('hinh_thuc_phat_bo_sung'):
        lines.append(f"[Hình thức phạt bổ sung: {meta['hinh_thuc_phat_bo_sung']}]")

    gplx_min = meta.get('tuoc_gplx_min')
    gplx_max = meta.get('tuoc_gplx_max')
    if gplx_min and gplx_max:
        lines.append(f"[Tước GPLX: {gplx_min} - {gplx_max} tháng]")

    # --- Ghép header + text gốc ---
    if lines:
        header = '\n'.join(lines)
        return f"{header}\n\n{chunk_text}"
    return chunk_text