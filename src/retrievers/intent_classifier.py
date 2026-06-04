INTENT_TYPES = {
    # Hỏi về mức phạt tiền
    'query_muc_phat': [
        r'phạt bao nhiêu', r'mức phạt', r'bị phạt',
        r'tiền phạt', r'phạt tiền', r'nộp phạt bao nhiêu',
        r'phạt \d+', r'bao nhiêu tiền'
    ],

    # Hỏi về hành vi cụ thể
    'query_hanh_vi': [
        r'lỗi gì', r'vi phạm gì', r'hành vi nào',
        r'được phép không', r'có bị phạt không',
        r'có vi phạm không'
    ],

    # Hỏi về chế tài bổ sung
    'query_che_tai': [
        r'tước bằng', r'tước giấy phép', r'tước gplx',
        r'trừ điểm', r'bị trừ mấy điểm', r'mất điểm',
        r'tịch thu', r'bị giữ xe'
    ],

    # Hỏi về thủ tục
    'query_thu_tuc': [
        r'thủ tục', r'nộp phạt ở đâu', r'quy trình',
        r'lấy lại', r'phục hồi điểm', r'nộp phạt như thế nào'
    ],

    # Hỏi tổng hợp — nguy hiểm nhất, cần xử lý riêng
    'query_tong_hop': [
        r'tất cả các lỗi', r'các mức phạt',
        r'vi phạm.*và.*bị', r'ngoài phạt tiền còn'
    ],
}