
import json
import pickle
from rank_bm25 import BM25Okapi
def build_bm25_index(chunks_path: str, bm25_save_path: str):
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)
    
    corpus = []
    ids = []
    for chunk in chunks_data:
        text = chunk['text'].lower().split()
        corpus.append(text)
        ids.append(chunk['chunk_id'])
        
    bm25_index = BM25Okapi(corpus)
    # Lưu index và ids để truy xuất sau này
    with open(bm25_save_path, 'wb') as f:
        pickle.dump({'index': bm25_index, 'ids': ids}, f)