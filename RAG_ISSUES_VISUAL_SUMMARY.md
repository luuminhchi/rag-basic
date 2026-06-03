# RAG Pipeline Issues - Visual Summary

## The Core Problem

When you ask: **"Điều 15 của văn bản quy phạm pháp luật về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ quy định về hành vi vi phạm nào?"**

### What SHOULD Happen
```
Input: "Điều 15 nói về hành vi vi phạm nào?"
        ↓
Router: "This is about Article 15, section = xu_phat" ✓
        ↓
Search: "Find SPECIFICALLY Article 15 chunks" ✓
        ↓
Output: "Article 15: Không mang mũ bảo hiểm (Safety equipment violation)" ✓
```

### What ACTUALLY Happens
```
Input: "Điều 15 nói về hành vi vi phạm nào?"
        ↓
Router: "This is about section = xu_phat" ⚠️ (Loses article number!)
        ↓
Rewrite: "xử phạt thiết bị an toàn" ❌ (Lost "Article 15"!)
        ↓
Search: "Find ANY article about safety equipment" ❌
        ↓
Results: Articles 11, 13, 16, 18 (also about safety) ❌
        ↓
Output: "Article 13 violates safety equipment..." ❌ (Wrong article!)
```

---

## Four Critical Failures

### 1️⃣ ARTICLE SPECIFICITY LOST IN REWRITING

**The Problem**:
```
┌─────────────────────────────────────┐
│ User Query                          │
│ "Điều 15 nói về hành vi nào?"      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Query Router (classify_query)       │
│ ✓ Correctly identifies: xu_phat    │
│ ✓ Has extract_article_for_routing()│
│ ✓ Can extract "15"                 │
└──────────────┬──────────────────────┘
               │
               ▼
          ❌ LOST HERE!
               │
      ┌────────▼────────┐
      │ Query Processor │
      │ (LLM Rewrite)   │
      │ Input: Query    │
      │ ❌ NO article   │
      │    context!     │
      └────────┬────────┘
               │
               ▼
    "xử phạt thiết bị an toàn"
    (Lost: "Điều 15")
```

**Why**:
- `query_processor.py` calls LLM rewrite WITHOUT article number
- LLM has no instruction to preserve article structure
- Result: Pure semantic rewriting loses structure

---

### 2️⃣ METADATA DISAPPEARS IN PIPELINE

**The Problem**:
```
Chunks (JSON):
{
  "doc_section": "xu_phat",        ✓ Present
  "violation_category": "thiet_bi_an_toan",  ✓ Present
  "dieu": 15                        ✓ Present
}
        │
        ▼
    FAISS Index ─→ RRF Fusion ─→ Reranking ─→ Expansion
        │            │              │           │
        ?            ?              ?           ▼
        │            │              │     Debug Output
        ▼            ▼              ▼     [section=?]
    Metadata?   Metadata?      Metadata?    ❌ MISSING!
```

**Result**: Debug shows `[section=?]` even though chunks have it

**Why**: Unknown (needs code trace through FAISS integration)
- Likely: Metadata not copied during RRF fusion
- Or: Document objects created without metadata dict

---

### 3️⃣ NO ARTICLE-LEVEL FILTERING

**The Problem**:
```
Router returns:  section = "xu_phat"
                 (Articles 6-38: 32 articles!)
                 
Hybrid Search:   ✓ Filters to xu_phat section
                 ❌ No filter for Article 15
                 
Result:          Top 5 includes:
                 • Article 11 (helmet violations)
                 • Article 13 (helmet violations)
                 • Article 16 (helmet violations)
                 • Article 18 (helmet violations)
                 • Article 20 (helmet violations)
                 
                 ❌ Article 15 may rank 5th or lower!
```

**Why**:
- `classify_query()` returns only 1 of 4 sections
- Each section has multiple articles
- `hybrid_search()` doesn't receive article number
- No downstream filtering by article

---

### 4️⃣ SEMANTIC METADATA IGNORED IN REWRITE

**The Problem**:
```
Raw Chunk with Metadata:
┌─────────────────────────────────────────┐
│ [Danh mục lỗi]: thiết_bị_an_toàn      │  ← Helpful semantic hint
│ [Mức phạt]: 100,000đ - 200,000đ       │  ← Helpful context
│ [Đối tượng]: người lái xe              │  ← Helpful context
│                                        │
│ Điều 15. Không mang mũ bảo hiểm...    │
└─────────────────────────────────────────┘
        │
        │ (Metadata injected for FAISS)
        ▼
    FAISS Embedding
        │
        ▼
    Semantic search result ✓
        │
        │
        ▼
    BUT: Query rewrite ignores all this!
        │
        ├→ "xử phạt thiết bị an toàn"
        │  (Metadata hints lost in LLM rewrite)
        │
        └→ Generic semantic search
           (No structure from metadata)
```

---

## Impact Table

| Issue | Consequence | Severity |
|-------|-------------|----------|
| Article lost in rewrite | "Điều 15" → "Điều 13" (wrong answer) | **CRITICAL** |
| Metadata missing | Can't verify article in output | **CRITICAL** |
| No article filtering | Top 5 is mix of Articles 6-38 | **HIGH** |
| Ignore semantic hints | Generic results instead of specific | **HIGH** |

---

## Real Example: Your Question

### Question
**"Điều 15 của văn bản quy phạm pháp luật về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ quy định về hành vi vi phạm nào?"**

### What You Should Get
```
Top 1: Article 15 - Không mang mũ bảo hiểm
       [section=xu_phat] [dieu=15] [cat=thiet_bi_an_toan]
       "Người lái xe, người ngồi trên xe mô tô, xe gắn máy, xe đạp 
       điện không mang mũ bảo hiểm..."
```

### What You Might Get (Due to Issues)
```
Top 1: [section=?] [dieu=?] [cat=?]
       "Người điều khiển xe không mang mũ bảo hiểm..."
       (Article 11, 13, 16, or 18 - same topic!)
       
       ❌ Can't verify which article it is
       ❌ Not specifically Article 15
```

---

## Diagnostic Commands

To verify each issue:

### Test 1: Does router extract article?
```python
from src.retrievers.query_router import extract_article_for_routing
result = extract_article_for_routing("Điều 15 nói về nội dung gì?")
print(result)  # Should output: "xu_phat" (Article 15 is in xu_phat range)
```

### Test 2: Does rewrite preserve article?
```python
from src.retrievers.query_processor import rewrite_and_inject
processed = rewrite_and_inject("Điều 15 nói về nội dung gì?", llm)
print(processed['rewrite_query'])  # Does it mention "Article 15"? 
# Expected: ❌ Probably NOT (Issue #1)
```

### Test 3: Does metadata survive hybrid_search?
```python
docs = hybrid_search(processed, vector_db, bm25, top_k=5, target_section="xu_phat")
for doc in docs:
    print(f"doc_section: {doc.metadata.get('doc_section')}")
# Expected: ❌ If None, metadata lost (Issue #2)
```

### Test 4: Are results article-specific?
```python
docs = hybrid_search(...)
articles = [doc.metadata.get('dieu') for doc in docs]
print(f"Articles found: {articles}")
# Expected: ❌ Mix of [11, 13, 15, 16, 18] - not specifically 15 (Issue #3)
```

---

## Summary: What's Broken

| Step | Status | Issue |
|------|--------|-------|
| 1. User asks about Article 15 | ✓ Clear input | None |
| 2. Router identifies section | ✓ Correct | Doesn't extract article number |
| 3. Rewrite query for semantics | ❌ LOST | Article specificity gone |
| 4. Search for matching articles | ❌ BROAD | Section-level only, not article-level |
| 5. Retrieve documents | ✓ Working | But... |
| 6. Preserve metadata | ❌ LOST | Metadata disappears somewhere |
| 7. Rerank results | ✓ Working | But with missing metadata |
| 8. Display answer | ❌ BROKEN | Can't show which article it is |

**Result**: System can retrieve RELEVANT documents, but:
- ❌ Can't guarantee SPECIFIC article
- ❌ Can't verify what article was retrieved
- ❌ Can't filter by article even when asked

---

## Architecture Vision (What's Needed)

```
                    User Query
                        │
                        ▼
              ┌──────────────────────┐
              │ Route & Extract      │
              │ • Identify section   │
              │ • Extract article #  │
              │ • Check metadata     │
              └──────────┬───────────┘
                        │
        ┌───────────────┴──────────────┐
        │ For "Điều 15" question:      │
        │ section = "xu_phat"          │
        │ article = 15                 │
        │ preserve_article = True      │
        └───────────────┬──────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │ Rewrite WITH Context │
              │ "Rewrite but keep    │
              │ article constraint"  │
              └──────────┬───────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │ Search + Filter      │
              │ • Hybrid search      │
              │ • Filter article=15  │
              │ • Hard constraint    │
              └──────────┬───────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │ Verify & Display     │
              │ • Check metadata     │
              │ • Verify article     │
              │ • Display with info  │
              └──────────┬───────────┘
                        │
                        ▼
                  Final Answer
```

This ensures Article 15 question → Article 15 answer ✓
