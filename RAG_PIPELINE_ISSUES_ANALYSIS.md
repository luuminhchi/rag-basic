# RAG Pipeline Issues Analysis - Complete Diagnosis

**Date**: June 3, 2026  
**Question**: "Điều 15 của văn bản quy phạm pháp luật về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ quy định về hành vi vi phạm nào?"

---

## Executive Summary

Your RAG pipeline has **4 critical issues** that prevent article-level semantic matching. The system can retrieve relevant documents, but:
1. **Cannot preserve article-level context** through query rewriting
2. **Cannot verify metadata integrity** (shows as missing in debug)
3. **Cannot distinguish between articles** in the same section
4. **Cannot filter retrieval by specific article** even when router identifies it

---

## Critical Issues with Root Causes

### ⚠️ ISSUE 1: Query Rewriting Destroys Article Specificity

**Problem Statement**:
- User asks: "Điều 15 của văn bản... nói về hành vi vi phạm nào?"
- Router correctly identifies: `section = xu_phat`
- But then `rewrite_and_inject()` transforms query to: "xử phạt thiết bị an toàn" or generic semantics
- **Result**: Lost the "Article 15" constraint

**Code Flow**:
```
1. User Query: "Điều 15 của văn bản... quy định về hành vi vi phạm nào?"
   ↓
2. Query Router: doc_section = xu_phat ✓ Correct
   ↓
3. Query Processor (LLM rewrite): 
   "Điều 15" → "xử phạt thiết bị an toàn" 
   ✗ Lost article number!
   ↓
4. Hybrid Search: Finds articles 11-20 about safety equipment
   ↓
5. Rerank: Chooses best match semantically
   ↓
6. Result: May return Article 13, 17, 19 instead of specifically Article 15
```

**Why This Happens**:
- `query_processor.py` passes query to LLM rewrite WITHOUT article context
- LLM only sees: "xử phạt vi phạm hành chính... hành vi vi phạm nào?"
- LLM doesn't have instruction: "Keep article number in mind"
- Result: Pure semantic matching without structure preservation

**Impact**:
- **Severity**: HIGH
- **User Impact**: When asking "What does Article X say?", user gets answers about the same topic but from different article
- **Example**: "Article 15" question → Answer from Article 18 (both about safety)

**Evidence in Code** (`src/retrievers/query_processor.py`):
```python
# Issue: Article number lost during rewrite
def rewrite_and_inject(query: str, llm) -> dict:
    rewrite_query = llm.invoke(f"Rewrite: {query}")  
    # ↑ No mention of article preservation!
    
    injected_query = inject_metadata(rewrite_query, ...)
    # ↑ Can't inject article if already lost
```

---

### ⚠️ ISSUE 2: Metadata Display/Retrieval Inconsistency

**Problem Statement**:
- Your debug output shows: `[section=?]` (metadata missing)
- But chunks JSON clearly have: `"doc_section": "xu_phat"`
- Something breaks metadata between storage and display

**Current Code** (`src/retrievers/retriever.py` lines 90-105):
```python
# This SHOULD show [section=xu_phat]
section = doc.metadata.get('doc_section', '?')
violation_cat = doc.metadata.get('violation_category', '?')
print(f"   Top {i+1}: [section={section}] [dieu={dieu}] [loai={chunk_type}] [cat={violation_cat}]")
```

**If showing `[section=?]`, it means**:
- `doc.metadata.get('doc_section')` returned `None`
- Metadata dict exists, but `doc_section` key is missing

**Metadata Loss Chain**:
```
Raw Chunks (JSON)
  ↓ ✓ Has: doc_section = "xu_phat"
  
FAISS Indexing (meta_injection.py)
  ↓ ? May lose keys during vector encoding
  
FAISS Retrieval (hybrid_search.py)
  ↓ ? Returns Document objects with metadata?
  
RRF Fusion (hybrid_search.py)
  ↓ ? Merges BM25 + FAISS results
  ↓ ? Where does metadata come from?
  
Reranking (rerank.py)
  ↓ ? CrossEncoder reranking preserves metadata?
  
Article Expansion (retriever.py:68-92)
  ↓ ? Replaces page_content but keeps metadata?
  
Debug Output (retriever.py:90-105)
  ↓ ✗ Shows [section=?]
```

**Why This Happens**:
Without seeing FAISS integration code, the likely culprit is:
- **RRF Fusion**: When BM25 results merge with FAISS results, metadata might not be copied correctly
- **Document Creation**: If new Document objects are created during fusion, metadata keys might not transfer
- **FAISS Storage**: Metadata might not be stored in FAISS if using faiss-only storage without LangChain wrapper

**Impact**:
- **Severity**: CRITICAL
- **User Impact**: Can't display article/category info; can't filter by metadata
- **Debugging**: Impossible to verify retrieval quality without metadata

---

### ⚠️ ISSUE 3: No Article-Level Filtering in Retrieval

**Problem Statement**:
- Router correctly identifies: "Question is about Article 15, section = xu_phat"
- But hybrid_search doesn't filter results to ONLY Article 15
- Result: Top 5 may include Articles 11, 13, 16, 18, 20

**Current Flow**:
```python
# retriever.py
section = classify_query(user_query)  # ← Gets "xu_phat" ✓
# But only returns section, not article number!

hybrid_results = hybrid_search(
    processed_query=processed,
    vectordb=vector_db,
    bm25_path=bm25,
    top_k=10,
    target_section=section,  # ← Only filters to xu_phat (Articles 6-38)
)
# ↑ No article-level filtering!
```

**Compare to**:
```python
# What SHOULD happen:
article_num = extract_article_number(user_query)  # 15
section = extract_doc_section(article_num)  # xu_phat
# Pass article_num to hybrid_search for hard filtering
hybrid_results = hybrid_search(..., target_article=article_num)
```

**Why This Happens**:
- Router returns only 1 of 4 sections (broad categories)
- Each section has 10-15 articles
- No downstream code extracts article number from router
- hybrid_search only filters by section, not article

**Impact**:
- **Severity**: HIGH
- **User Impact**: "Tell me about Article 15" → Returns mix of Articles 6-38
- **Ranking**: Reranker may prefer Article 11 (higher semantic score) over Article 15

---

### ⚠️ ISSUE 4: Query Rewrite Ignores Semantic Categories

**Problem Statement**:
- Query: "Điều 15 quy định về hành vi vi phạm nào?"
- Expected metadata headers in injection:
  ```
  [Danh mục lỗi]: thiết_bị_an_toàn
  [Mức phạt]: 100,000đ đến 200,000đ
  [Đối tượng]: người lái xe
  ```
- But LLM rewrite might ignore these metadata hints

**Code** (`meta_injection.py` + `query_processor.py`):
```python
# What's injected for embedding
injected_text = """
[Nhóm tài liệu]: xử phạt vi phạm giao thông
[Đối tượng áp dụng]: người lái xe
[Danh mục lỗi]: thiết bị an toàn
[Các hành vi cụ thể]: không mang mũ bảo hiểm
[Mức phạt]: 100,000đ đến 200,000đ
Điều 15. Không mang mũ bảo hiểm...
"""

# But rewrite_query removes article number!
rewrite_query = "xử phạt vi phạm thiết bị an toàn không mang mũ bảo hiểm"
# ↑ Lost: "Điều 15", Lost: article-specific context
```

**Why This Happens**:
- LLM rewrite is semantic-only
- No instruction to preserve article structure
- Metadata headers only help EMBEDDING, not REWRITING

**Impact**:
- **Severity**: MEDIUM
- **User Impact**: Generic results instead of article-specific
- **Retrieval Quality**: FAISS may return Articles 11-20 equally well

---

## Summary Table

| Issue | Location | Root Cause | Symptom | Fix Priority |
|-------|----------|-----------|---------|--------------|
| **Query loses article** | `query_processor.py` | LLM rewrite ignores article context | "Điều 15" → generic | HIGH |
| **Metadata missing in debug** | `hybrid_search.py` or `rerank.py` | Metadata not preserved through pipeline | `[section=?]` | CRITICAL |
| **No article filtering** | `hybrid_search.py` | Only section-level filtering | Results include 6-38 | HIGH |
| **Rewrite ignores semantics** | `query_processor.py` | No instruction to preserve structure | Loses category info | MEDIUM |

---

## Why These Issues Compound

The problems **interact negatively**:

1. **User asks**: "Điều 15 nói về hành vi vi phạm nào?"
2. **Router identifies**: Article 15 ✓
3. **Query rewrite forgets**: Article 15 → "xử phạt thiết bị an toàn"
4. **Hybrid search finds**: Articles 11, 13, 16, 18, 20 (all about safety)
5. **Rerank chooses**: Article 13 (highest semantic match)
6. **Metadata missing**: Can't verify Article 13 ≠ Article 15
7. **User sees**: Wrong article with no warning

---

## Architecture Weakness

```
Current Flow:
Query → Router → Processor → Hybrid Search → Rerank → Output
         ↓
         Returns: section only
                  (1 of 4 categories, 10+ articles each)
         
Missing:
- Article-level extraction
- Article-level filtering
- Article-level constraint in rewriting
- Metadata verification
- Semantic preservation through rewriting
```

**What's Needed**:
```
Improved Flow:
Query → Router → Processor → Hybrid Search → Rerank → Output
         ↓        ↓          ↓               ↓
        Extract  Rewrite    Filter by      Verify
        article  WITH       article        metadata
        number   article    number         returned
```

---

## Recommendations (Before Fixing)

### For Understanding the Issues Better:

1. **Run this debug query**:
   ```python
   user_query = "Điều 15 nói về hành vi vi phạm nào?"
   
   # Step 1: Check router
   section = classify_query(user_query)
   print(f"Router result: {section}")
   # Expected: xu_phat ✓
   
   # Step 2: Check article extraction
   from src.retrievers.query_router import extract_article_for_routing
   article = extract_article_for_routing(user_query)
   print(f"Article extracted: {article}")
   # Expected: xu_phat (Article 15 maps to xu_phat) ✓
   
   # Step 3: Check rewrite
   processed = rewrite_and_inject(user_query, llm)
   print(f"Rewritten query: {processed['rewrite_query']}")
   # Warning: Article number lost?
   
   # Step 4: Check hybrid search metadata
   results = hybrid_search(processed, vector_db, bm25, top_k=5, target_section=section)
   for doc in results:
       print(f"doc_section: {doc.metadata.get('doc_section', 'MISSING')}")
   # Alert: If MISSING, metadata lost in hybrid_search!
   
   # Step 5: Check after rerank
   final = rerank(processed['rewrite_query'], results, k=5)
   for doc in final:
       print(f"Article: {doc.metadata.get('dieu')}, Section: {doc.metadata.get('doc_section')}")
   # Alert: If section missing, lost during rerank!
   ```

2. **Check FAISS metadata storage**:
   - How are metadata stored in FAISS?
   - Are they using LangChain's Document wrapper?
   - Or raw FAISS with separate metadata?

3. **Trace metadata through RRF fusion**:
   - When BM25 and FAISS results merge, which metadata wins?
   - Is metadata from top FAISS result preserved?

---

## Next Steps

Once you understand these issues:
1. **Fix CRITICAL first**: Verify metadata preservation
2. **Fix HIGH**: Add article-level filtering
3. **Fix HIGH**: Preserve article number in rewrite
4. **Fix MEDIUM**: Add semantic preservation to rewrite prompt
