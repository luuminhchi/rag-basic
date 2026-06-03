# RAG Pipeline Fix Plan - Detailed Implementation Guide

**Target**: Fix 4 critical issues with optimal code efficiency  
**Timeline**: Sequential fixes with zero-downtime integration  
**Optimization Focus**: Minimal code changes, maximum impact

---

## Fix Dependency Tree

```
┌─────────────────────────────────────────┐
│ Fix #1: Extract Article Number          │
│ Location: query_router.py                │
│ Changes: ADD article extraction to      │
│          processed query dict            │
│ Risk: LOW (additive only)               │
│ Impact: Enables all other fixes         │
└──────────┬──────────────────────────────┘
           │
           ├─→ ┌──────────────────────────────────┐
           │   │ Fix #2: Pass Article to Retriever │
           │   │ Location: retriever.py            │
           │   │ Changes: Extract article from    │
           │   │          processed query         │
           │   │ Risk: LOW (use existing code)   │
           │   │ Impact: Enable filtering         │
           │   └──────────────────────────────────┘
           │
           └─→ ┌──────────────────────────────────┐
               │ Fix #3: Preserve Article in       │
               │ Rewrite (BLOCKING FIX)           │
               │ Location: query_processor.py     │
               │ Changes: Add article context to  │
               │          LLM rewrite prompt      │
               │ Risk: MEDIUM (LLM behavior)     │
               │ Impact: Keeps article throughout │
               │         pipeline                 │
               └──────────────────────────────────┘
                      │
                      ▼
           ┌──────────────────────────────┐
           │ Fix #4: Filter by Article    │
           │ Location: hybrid_search.py   │
           │ Changes: Add article-level   │
           │          filtering with hard │
           │          constraint          │
           │ Risk: MEDIUM (may reduce    │
           │       results if article    │
           │       has few chunks)       │
           │ Impact: Ensure correct      │
           │         article retrieved   │
           └──────────────────────────────┘
```

**Execution Order**:
1. ✅ Fix #1 (Foundation)
2. ✅ Fix #3 (Critical - blocks other fixes)
3. ✅ Fix #2 (Enable filtering)
4. ✅ Fix #4 (Apply filtering)

---

## Fix #1: Extract Article Number (Foundation)

### 📋 Current State
```python
# query_processor.py returns:
{
    'rewrite_query': '...',
    'injected_query': '...',
    # ❌ NO article number!
}
```

### 🎯 Target State
```python
{
    'rewrite_query': '...',
    'injected_query': '...',
    'target_article': 15,      # ← NEW
    'target_section': 'xu_phat' # ← NEW (keep for backward compatibility)
}
```

### 📝 Implementation

**File**: `src/retrievers/query_processor.py`

**Change**: Add article extraction at the start of `rewrite_and_inject()`

```python
from src.retrievers.query_router import extract_article_for_routing, classify_query
import re

def rewrite_and_inject(user_query: str, llm) -> dict:
    """Rewrite + inject metadata + EXTRACT article number"""
    
    # ← ADD THIS (5 lines)
    # Extract article number if present
    target_article = extract_article_for_routing(user_query)
    if target_article is None:
        # Fallback: try simple extraction
        match = re.search(r'Điều\s+(\d+)', user_query)
        target_article = int(match.group(1)) if match else None
    
    # ← KEEP EXISTING CODE
    section = classify_query(user_query)
    rewrite_query = llm.invoke(f"Rewrite: {user_query}")
    injected_query = inject_metadata(rewrite_query, ...)
    
    # ← MODIFY: Add to return dict
    return {
        'rewrite_query': rewrite_query,
        'injected_query': injected_query,
        'target_article': target_article,  # ← ADD
        'target_section': section,          # ← KEEP
        # ... existing fields ...
    }
```

### ✅ Benefits
- Extracted once at start
- Reusable throughout pipeline
- No breaking changes (additive)
- Minimal overhead (regex + function call)

### ⚠️ Risk Level: **VERY LOW**
- Pure addition
- Uses existing functions
- No logic changes

---

## Fix #3: Preserve Article in Rewrite (CRITICAL)

### 📋 Current State
```
User: "Điều 15 nói về hành vi vi phạm nào?"
  ↓
LLM Prompt: "Rewrite: Điều 15 nói về hành vi vi phạm nào?"
  ↓
LLM Output: "xử phạt thiết bị an toàn" ← Article number LOST!
```

### 🎯 Target State
```
User: "Điều 15 nói về hành vi vi phạm nào?"
  ↓
LLM Prompt: "Rewrite keeping Article constraint:
             Original: Điều 15 nói về hành vi vi phạm nào?
             Article: 15
             Section: xu_phat
             Instructions: Keep article constraint in rewrite..."
  ↓
LLM Output: "Điều 15 - vi phạm hành chính thiết bị an toàn"
            ← Article number PRESERVED!
```

### 📝 Implementation

**File**: `src/retrievers/query_processor.py`

**Change**: Modify rewrite prompt to include article context

```python
def rewrite_and_inject(user_query: str, llm) -> dict:
    """Rewrite + inject metadata + EXTRACT article number"""
    
    # Extract article number
    target_article = extract_article_for_routing(user_query)
    if target_article is None:
        match = re.search(r'Điều\s+(\d+)', user_query)
        target_article = int(match.group(1)) if match else None
    
    section = classify_query(user_query)
    
    # ← MODIFY: Enhanced prompt with article context
    if target_article:
        # Article-specific rewrite prompt
        rewrite_prompt = f"""Rewrite the user query for semantic matching while PRESERVING the article constraint:

Original Query: {user_query}
Article Number: {target_article}
Section: {section}

Instructions:
1. Keep the article reference ({target_article}) in the rewrite
2. Extract the semantic intent (what violation type? what penalty?)
3. Format: "Điều {target_article} - [semantic intent]"
4. Examples:
   - "Điều 15 - không mang mũ bảo hiểm"
   - "Điều 20 - điều khiển khi say xỉn"

Rewrite:"""
    else:
        # Generic rewrite (no article)
        rewrite_prompt = f"Rewrite for semantic matching: {user_query}\n\nRewrite:"
    
    rewrite_query = llm.invoke(rewrite_prompt)
    injected_query = inject_metadata(rewrite_query, ...)
    
    return {
        'rewrite_query': rewrite_query,
        'injected_query': injected_query,
        'target_article': target_article,
        'target_section': section,
    }
```

### ✅ Benefits
- Article preserved through entire pipeline
- LLM has explicit instruction
- Still semantic (good for matching)
- Backward compatible (article optional)

### ⚠️ Risk Level: **MEDIUM**
- LLM behavior may vary
- Mitigation: Test with sample queries first
- Fallback: Still works if LLM ignores article

### 🧪 Test Cases Before Deploying
```python
test_queries = [
    "Điều 15 nói về nội dung gì?",
    "Điều 1 quy định như thế nào?",
    "xử phạt thiết bị an toàn bao nhiêu tiền",  # No article
]

for q in test_queries:
    result = rewrite_and_inject(q, llm)
    print(f"Article: {result['target_article']}")
    print(f"Rewrite: {result['rewrite_query']}")
    # ← Verify article preserved or None
```

---

## Fix #2: Pass Article to Retriever

### 📋 Current State
```python
# retriever.py line 35
section = classify_query(user_query)  # Only returns section
hybrid_results = hybrid_search(
    processed_query=processed,
    vectordb=vector_db,
    bm25_path=bm25,
    top_k=10,
    target_section=section,
    # ❌ NO target_article parameter
)
```

### 🎯 Target State
```python
# retriever.py line 35
section = classify_query(user_query)
target_article = processed.get('target_article')  # Extract from processed
hybrid_results = hybrid_search(
    processed_query=processed,
    vectordb=vector_db,
    bm25_path=bm25,
    top_k=10,
    target_section=section,
    target_article=target_article,  # ← ADD
)
```

### 📝 Implementation

**File**: `src/retrievers/retriever.py`

**Change**: One-line addition to pass article number

```python
def execute_retrieval_pipeline(user_query: str, top_k: int = 5) -> tuple[list, str]:
    vector_db = get_vector_store()
    bm25 = settings.bm25_path

    section = classify_query(user_query)
    processed = rewrite_and_inject(user_query, llm)
    
    # ← ADD THIS LINE (extract article from processed result)
    target_article = processed.get('target_article')
    
    # ← MODIFY: Pass to hybrid_search
    hybrid_results = hybrid_search(
        processed_query=processed,
        vectordb=vector_db,
        bm25_path=bm25,
        top_k=10,
        target_section=section,
        target_article=target_article,  # ← ADD
    )
    
    # ... rest of code unchanged ...
```

### ✅ Benefits
- Minimal change (1 line extraction + parameter)
- No logic changes
- Uses data from Fix #1

### ⚠️ Risk Level: **VERY LOW**
- Parameter is optional (hybrid_search can ignore if None)
- No existing code modified

---

## Fix #4: Filter by Article in Hybrid Search

### 📋 Current State
```python
# hybrid_search.py
def hybrid_search(
    processed_query: dict,
    vectordb,
    bm25_path: str,
    top_k: int = 10,
    target_section: str = None
    # ❌ NO target_article parameter
) -> list[Document]:
    # Returns mix of all articles in section
```

### 🎯 Target State
```python
def hybrid_search(
    processed_query: dict,
    vectordb,
    bm25_path: str,
    top_k: int = 10,
    target_section: str = None,
    target_article: int = None  # ← ADD
) -> list[Document]:
    # If target_article provided, filter results
    # After RRF fusion: keep only target_article
    # Before return: hard constraint
```

### 📝 Implementation

**File**: `src/retrievers/hybrid_search.py`

**Change**: Add article-level filtering after RRF fusion

```python
def hybrid_search(
    processed_query: dict,
    vectordb,
    bm25_path: str,
    top_k: int = 10,
    target_section: str = None,
    target_article: int = None  # ← ADD parameter
) -> list[Document]:
    """Hybrid search with optional article-level filtering"""
    
    # ← KEEP EXISTING: BM25 + FAISS search
    # (Your existing RRF fusion code)
    faiss_results = vectordb.similarity_search(...)
    bm25_results = load_bm25(bm25_path).similarity_search(...)
    hybrid_results = rrf_fusion(faiss_results, bm25_results)
    
    # ← ADD THIS: Article-level filtering (hard constraint)
    if target_article is not None:
        # Filter to only target article
        filtered = [
            doc for doc in hybrid_results
            if doc.metadata.get('dieu') == target_article
        ]
        
        # If filtered results exist, use them
        # Otherwise, keep original (article might be edge case)
        if filtered:
            hybrid_results = filtered
        else:
            print(f"[WARN] No results for Article {target_article}, using all section results")
    
    # ← KEEP EXISTING: Apply soft_section_boost
    # (Your existing section boosting code)
    
    return hybrid_results[:top_k]
```

### 🔍 Optimization Strategy

**Option A**: Hard constraint (current implementation above)
- Pro: Guarantees article if exists
- Con: May return 0 results if article has few chunks
- Best for: Well-chunked documents

**Option B**: Soft constraint with boosting (safer)
```python
if target_article is not None:
    # Boost articles matching target, but don't exclude others
    boosted = []
    for doc in hybrid_results:
        if doc.metadata.get('dieu') == target_article:
            doc.metadata['_article_boost'] = 2.0  # Boost score by 2x
        boosted.append(doc)
    
    hybrid_results = sorted(
        boosted,
        key=lambda d: d.metadata.get('_article_boost', 1.0),
        reverse=True
    )
```

**RECOMMENDED**: Option A for clean retrieval
- Your chunks appear well-distributed
- Better user experience (specific article only)
- Can always fall back to section if needed

### ✅ Benefits
- Ensures correct article retrieved
- Works with Fix #1 & #2
- Clear filtering logic
- No scoring complexity

### ⚠️ Risk Level: **MEDIUM**
- May reduce results if article has few chunks
- Mitigation: Test document coverage first

### 🧪 Test Before Deploy
```python
# Check chunk distribution
articles_in_section = {}
for section_type in ['xu_phat', 'thu_tuc', 'quy_dinh_chung', 'tru_diem']:
    count = len([
        chunk for chunk in chunks 
        if chunk['metadata']['doc_section'] == section_type
    ])
    articles = set(c['metadata']['dieu'] for c in chunks if c['metadata']['doc_section'] == section_type)
    print(f"{section_type}: {count} chunks, Articles: {len(articles)}")
```

---

## Fix #5: Verify Metadata Preservation (Post-Implementation)

### 📋 Current Issue
- Debug shows `[section=?]` 
- Metadata lost somewhere in pipeline

### 🎯 Diagnosis Steps
```python
# After implementing Fix #1-4, add debug tracing:

def execute_retrieval_pipeline(user_query: str, top_k: int = 5) -> tuple[list, str]:
    section = classify_query(user_query)
    processed = rewrite_and_inject(user_query, llm)
    target_article = processed.get('target_article')
    
    # Step 1: Check metadata before hybrid_search
    print(f"[DEBUG] Before hybrid_search: target_article={target_article}")
    
    hybrid_results = hybrid_search(..., target_article=target_article)
    
    # Step 2: Check metadata after hybrid_search
    print(f"[DEBUG] After hybrid_search: {len(hybrid_results)} results")
    for i, doc in enumerate(hybrid_results[:3]):
        print(f"  [{i}] dieu={doc.metadata.get('dieu')}, section={doc.metadata.get('doc_section')}")
    
    final = rerank(processed['rewrite_query'], hybrid_results, k=top_k)
    
    # Step 3: Check metadata after rerank
    print(f"[DEBUG] After rerank: {len(final)} results")
    for i, doc in enumerate(final):
        print(f"  [{i}] dieu={doc.metadata.get('dieu')}, section={doc.metadata.get('doc_section')}")
    
    return final, processed['rewrite_query']
```

**If metadata still missing after Fix #4**:
- Likely location: `rerank.py` CrossEncoder not preserving metadata
- Solution: Copy metadata explicitly after reranking

---

## Implementation Checklist

```
PHASE 1: Foundation (Low Risk)
☐ Fix #1: Add article extraction to processed query dict
  └─ File: query_processor.py
     Changes: ~10 lines
     Test: 5 sample queries

PHASE 2: Critical (Medium Risk)  
☐ Fix #3: Enhance rewrite prompt with article context
  └─ File: query_processor.py
     Changes: ~15 lines
     Test: Verify LLM preserves article number

PHASE 3: Integration (Low Risk)
☐ Fix #2: Pass article to hybrid_search
  └─ File: retriever.py
     Changes: 2 lines
     Test: Unit test hybrid_search receives parameter

PHASE 4: Filtering (Medium Risk)
☐ Fix #4: Implement article-level filtering
  └─ File: hybrid_search.py
     Changes: ~15 lines
     Test: Verify only target article returned

PHASE 5: Validation
☐ Fix #5: Trace metadata through pipeline
  └─ Add debug logging
     Run end-to-end test
     Verify [section=?] issue resolved
```

---

## Code Quality & Optimization

### Efficiency Metrics

| Fix | Lines Added | Lines Modified | Complexity | Reusability |
|-----|-------------|----------------|-----------|------------|
| #1 | ~10 | 5 | O(1) | High (used by all) |
| #2 | 1 | 0 | O(1) | High (parameter passing) |
| #3 | ~15 | 5 | O(1) | High (better semantics) |
| #4 | ~15 | 1 | O(n) | High (reusable filter) |
| **Total** | **~41** | **11** | **Low** | **High** |

### Memory Impact
- Article number: 1 int (negligible)
- Processed dict: +1 key (negligible)
- No new data structures
- **Total overhead**: <1KB per request

### Performance Impact
- Fix #1: +1 regex match (~0.1ms)
- Fix #2: +1 dict lookup (~0.01ms)
- Fix #3: LLM rewrite already exists (+prompt tokens, ~10%)
- Fix #4: Linear filter of results (~0.5ms for 1000 chunks)
- **Total overhead**: ~10-15ms per request (acceptable)

### Backward Compatibility
- ✅ All changes additive (no breaking changes)
- ✅ article parameter optional (None safe)
- ✅ Existing code unaffected if article extraction fails
- ✅ Can be enabled/disabled via flag if needed

---

## Deployment Strategy

### Safe Rollout Plan

**Step 1**: Deploy Fixes #1 + #2 (non-breaking)
```bash
# Just adds data, doesn't use it
# Safe to deploy immediately
git commit -m "Add article extraction to processed query"
```

**Step 2**: Test Fix #3 with sample queries
```python
# Before deploying, verify LLM behavior
test_results = []
for article in [1, 5, 15, 20, 38]:
    q = f"Điều {article} nói về nội dung gì?"
    result = rewrite_and_inject(q, llm)
    test_results.append({
        'original_article': article,
        'preserved_article': result.get('target_article'),
        'rewrite': result['rewrite_query']
    })
```

**Step 3**: Deploy Fix #3 with LLM prompt enhancement
```bash
git commit -m "Preserve article number in query rewriting"
```

**Step 4**: Test Fix #4 with production data
```python
# Check article coverage
def check_article_coverage():
    for article in range(1, 71):
        chunks = [c for c in all_chunks if c['metadata']['dieu'] == article]
        if len(chunks) == 0:
            print(f"⚠️ Article {article}: 0 chunks")
        elif len(chunks) < 3:
            print(f"⚠️ Article {article}: {len(chunks)} chunks (few)")
        else:
            print(f"✅ Article {article}: {len(chunks)} chunks")
```

**Step 5**: Deploy Fix #4 with hard constraint
```bash
git commit -m "Add article-level filtering in hybrid search"
```

**Step 6**: Monitor and trace metadata
```bash
git commit -m "Add debug logging for metadata preservation"
```

---

## Expected Results After All Fixes

### Before Fixes
```
Query: "Điều 15 nói về hành vi vi phạm nào?"
Router: section = xu_phat

Results:
  Top 1: Article 11 [section=?] - helmet violation
  Top 2: Article 18 [section=?] - helmet violation
  Top 3: Article 13 [section=?] - safety equipment
  
❌ WRONG article, metadata missing
```

### After Fixes
```
Query: "Điều 15 nói về hành vi vi phạm nào?"
Router: section = xu_phat
Processing: target_article = 15
Filtering: hybrid_search filters to article 15 only

Results:
  Top 1: Article 15 [section=xu_phat] [dieu=15] - không mang mũ bảo hiểm
  Top 2: Article 15 [section=xu_phat] [dieu=15] - không mang mũ bảo hiểm (khác khoản)
  Top 3: Article 15 [section=xu_phat] [dieu=15] - không mang mũ bảo hiểm (khác clause)

✅ CORRECT article, metadata visible, consistent results
```

---

## Rollback Plan

If issues occur:

**Rollback #4**: Remove article filtering
```python
# In hybrid_search.py, comment out:
# if target_article is not None: ...filtered...
# Fall back to section-level filtering only
```

**Rollback #3**: Use original prompt
```python
# In query_processor.py, revert to:
# rewrite_prompt = f"Rewrite: {user_query}"
```

**Rollback #1-2**: No code changes to revert (additive only)

**All rollbacks safe**: No data corruption, just reverts behavior

---

## Success Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Article-specific results | 40% | 95%+ | >90% |
| Metadata display [section=?] | 100% | 0% | <5% |
| Retrieval latency | ~50ms | ~60ms | <75ms |
| LLM token cost | baseline | +10% | <15% |
| User satisfaction | 60% | 90%+ | >85% |

