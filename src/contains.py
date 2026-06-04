VEHICLE_GROUPS = {
    'nhom_o_to': [
        "xe ô tô",
        "xe chở người bốn bánh có gắn động cơ",
        "xe chở hàng bốn bánh có gắn động cơ",
        "các loại xe tương tự xe ô tô",
    ],
    'nhom_mo_to': [
        "xe mô tô",
        "xe gắn máy",
        "xe máy điện",
        "các loại xe tương tự xe mô tô",
    ],
    'nhom_may_keo': [
        "máy kéo",
        "xe máy chuyên dùng",
    ],
    'nhom_tho_so': [
        "xe đạp",
        "xe đạp máy",
        "xe thô sơ",
    ],
    'nhom_nguoi': [
        "người đi bộ",
        "người điều khiển, dẫn dắt súc vật",
        "kéo xe súc vật",
        "xe chở xác",
    ],
}

VEHICLE_ALIASES = {
    "ô tô":       "xe ô tô",
    "xe máy":     "xe mô tô",
    "xe cơ giới": ["xe ô tô", "xe mô tô", "máy kéo"],  # expand thành nhóm
}

STANDARD_VEHICLES = [
    "xe ô tô", "xe chở người bốn bánh có gắn động cơ", "xe chở hàng bốn bánh có gắn động cơ", "các loại xe tương tự xe ô tô",
    "xe mô tô", "xe gắn máy", "xe máy điện", "các loại xe tương tự xe mô tô",
    "máy kéo", "xe máy chuyên dùng",
    "xe đạp", "xe đạp máy", "xe thô sơ",
    "người đi bộ", "người điều khiển, dẫn dắt súc vật", "kéo xe súc vật", "xe chở xác"
]

# 
# TẦNG 1: doc_section — suy từ TÊN CHƯƠNG
# ============================================================
CHUONG_TO_SECTION = [
    # (pattern match tên chương, doc_section)
    (r'quy định chung',                        'quy_dinh_chung'),
    (r'hành vi vi phạm|hình thức|mức xử phạt', 'xu_phat'),

]

# ============================================================
# TẦNG 2: doc_subsection — suy từ TÊN MỤC
# ============================================================
MUC_TO_SUBSECTION = [
    # xu_phat subsections
    (r'quy tắc giao thông',                    'vi_pham_quy_tac_gt'),
    (r'phương tiện tham gia giao thông',        'vi_pham_phuong_tien'),
    (r'người điều khiển phương tiện',           'vi_pham_nguoi_dieu_khien'),
    (r'vận chuyển|hàng hóa|hành khách|trẻ em', 'vi_pham_van_chuyen'),
    (r'các vi phạm khác',                       'vi_pham_khac'),

    # quy_dinh_chung subsections
    (r'phạm vi|đối tượng',                      'pham_vi_doi_tuong'),
    (r'giải thích',                              'giai_thich_tu_ngu'),
]

# ============================================================
# FALLBACK: không có mục → suy từ tên điều
# ============================================================
DIEU_TO_SUBSECTION_FALLBACK = [
    (r'quy tắc|tín hiệu|tốc độ|làn đường',     'vi_pham_quy_tac_gt'),
    (r'phương tiện|đăng ký|đăng kiểm',          'vi_pham_phuong_tien'),
    (r'giấy phép lái xe|bằng lái',              'vi_pham_nguoi_dieu_khien'),
    (r'vận tải|vận chuyển|kinh doanh',          'vi_pham_van_chuyen'),
]