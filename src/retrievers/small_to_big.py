

def expand_chunks(chunks: list, vectorDB):
    expanded = []
    for doc in chunks:
        meta = doc.get('metadata')
        loai = meta.get('loai')
        if loai == 'diem':
            parent = _fetch_by_id(meta.get('parent_id'), vectorDB)
            expanded.append({
                'child': doc,
                'parent': parent,
                'dieu': None
            })
            # khoan thì không cần leo thêm
        elif loai == 'khoan':
            expanded.append({
                'child': doc,
                'parent': None,
                'dieu': None
            })
        else:  # điều
            expanded.append({
                'child': doc,
                'parent': None,
                'dieu': None
            })
    return expanded

def expand_full_to_dieu(chunks: list, vectorDB) -> list:
    '''dùng khi câu hỏi phức tạp - leo lên tận điều
    Gọi khi rerank thấy kết quả chưa đủ ngữ cảnh 
    '''
    expanded = []
    for doc in chunks:
        meta = doc.get('metadata')
        loai = meta.get('loai')
        parent = meta.get('parent_id')
        
        khoan = None
        dieu = None
        if loai == 'diem':
            dieu = _fetch_by_id(meta.get(parent), vectorDB)
            
        elif loai == 'khoan':
            dieu = _fetch_by_id(meta.get('parent_id'), vectorDB)
           
        
        expanded.append({
            'child': doc,
            'parent': khoan,
            'dieu': dieu
        })

def _fetch_by_id(chunk_id: str, vectorDB):
    if not chunk_id:
        return None
    result = vectorDB.search_similarity(
        query='',
        k=1,
        filter={'id': chunk_id}
    )
    return result[0] if result else None
