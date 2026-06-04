INTENT_TO_SECTION = {
    'query_muc_phat': {
        'doc_section':   'xu_phat',
        'doc_subsection': None,      # cần tầng 3 để xác định subsection
        'filter_fields': ['penalty_min', 'penalty_max', 'vehicle_types']
    },
    'query_hanh_vi': {
        'doc_section':   'xu_phat',
        'doc_subsection': None,
        'filter_fields': ['violation_category', 'hanh_vi_vi_pham', 'vehicle_types']
    },
    'query_che_tai': {
        'doc_section':   'xu_phat',
        'doc_subsection': None,
        'filter_fields': ['tru_diem_gplx', 'tuoc_gplx_min', 'has_tru_diem']
    },
    'query_thu_tuc': {
        'doc_section':   'tham_quyen_thu_tuc',
        'doc_subsection': 'thu_tuc_xu_phat',
        'filter_fields': []
    },
   
    'query_tong_hop': {
        'doc_section':   'xu_phat',
        'doc_subsection': None,
        'filter_fields': ['vehicle_types', 'violation_category']
    },
}