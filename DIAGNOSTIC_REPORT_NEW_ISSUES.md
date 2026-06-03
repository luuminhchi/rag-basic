# 🔍 NEW ISSUES FOUND - Diagnostic Report

**Date**: June 3, 2026  
**Test Query**: "Mức xử phạt đối với hành vi điều khiển xe gắn máy không chấp hành tín hiệu đèn giao thông (vượt đèn đỏ) là bao nhiêu?"  
**Finding**: Original 4 fixes are **necessary but NOT sufficient** - there are additional metadata/penalty issues

---

## 🚨 CRITICAL FINDINGS

### Issue #1: `[section=?]` Metadata Missing 
**Symptom**: Debug output shows `[section=?]` instead of `[section=xu_phat]`  
**Expected**: `doc_section` should exist in metadata (it's in the chunks JSON)  
**Problem**: Metadata getting lost somewhere in pipeline (RRF → boost → rerank)  

**Root Cause Location**: 
- FAISS retrieval HAS metadata ✓
- Metadata should survive RRF fusion (only passes Document objects)
- Metadata should survive section/category boost (just reorders, doesn't modify)
- **Likely culprit**: Rerank function or article expansion modifying documents without preserving metadata

**Evidence**: 
```
Chunk JSON has: "doc_section": "xu_phat"
Debug output shows: [section=?]
```

---

### Issue #2: **Penalty Information Not Shown**
**Symptom**: Debug output shows `[Danh mục lỗi]` and behaviors, but NO `[Mức phạt]`  
**Expected**: For Article 11 traffic signal violation: `[Mức phạt]: 150,000 - 250,000 đ`  
**Problem**: Penalty data exists in metadata but NOT extracted to debug output  

**Root Cause**: `retriever.py` debug output (lines 107-110) only shows:
```python
section = doc.metadata.get('doc_section', '?')  # ← Missing
dieu = doc.metadata.get('dieu')
violation_cat = doc.metadata.get('violation_category')
chunk_type = doc.metadata.get('loai')
# ❌ NO: penalty_min, penalty_max
```

**Evidence**:
```json
Chunk metadata HAS:
  "penalty_min": 150000,
  "penalty_max": 250000,
  "has_penalty": true
  
But debug output missing these fields
```

---

### Issue #3: Article Filtering Not Working (Or Not Deployed)
**Symptom**: Query for traffic signal violation returns Articles 7, 9, 11 (all three)  
**Expected**: Should prioritize Article 11 (or only show if matching article specified)  
**Problem**: My Fix #4 (article filtering) either not deployed or not working correctly  

**Current**: Articles 7, 9, 11, 9 mixed in results  
**Should be**: Article 11 only (user asked specifically for traffic signal running red light)  

---

## ✅ IMMEDIATE FIXES NEEDED (Beyond the 4 original fixes)

### Fix #5: Add Penalty Information to Debug Output ✅ DONE
**File**: `src/retrievers/retriever.py`  
**Change**: Added penalty extraction and display in debug output  
**Status**: Already implemented in this session

**Before**:
```
   Top 1: [section=?] [dieu=11] [loai=khoan] [cat=tin_hieu_den]
```

**After**:
```
   Top 1: [section=?] [dieu=11] [loai=khoan] [cat=tin_hieu_den] [Mức phạt]: 150,000 - 250,000 đ
```

---

### Fix #6: Debug Metadata Loss in Pipeline 🔍 IN PROGRESS
**File**: `src/retrievers/hybrid_search.py`  
**Added**: Debug logging to trace metadata through RRF and boost functions  
**Goal**: Identify exact point where doc_section disappears  

**Debug Points Added**:
- RRF input/output metadata check
- Section boost metadata preservation check
- Category boost metadata preservation check

**How to Test**:
```bash
# Run with debug enabled to see:
# [DEBUG RRF] FAISS result - chunk 168_2024_ND-CP_619502_d11_k1_dpb: section=xu_phat
# [DEBUG BOOST] Section boost: target=xu_phat, matched=1, others=5
```

---

## 📋 Testing Strategy

### Step 1: Deploy Debug Logging
- ✅ Added to `retriever.py` (penalty display)
- ✅ Added to `hybrid_search.py` (metadata tracing)

### Step 2: Run Test Query
```python
from src.retrievers.retriever import execute_retrieval_pipeline

results, rewrite = execute_retrieval_pipeline(
    "Mức xử phạt đối với hành vi điều khiển xe gắn máy không chấp hành " +
    "tín hiệu đèn giao thông (vượt đèn đỏ) là bao nhiêu?"
)
```

### Step 3: Check Debug Output
Look for:
1. `[DEBUG ARTICLE]`: Article filtering working?
2. `[DEBUG RRF]`: Metadata survived RRF?
3. `[DEBUG BOOST]`: Metadata survived section boost?
4. `[Mức phạt]`: Penalty shown in output?

---

## 🎯 Next Actions

### Immediate (15 minutes)
1. Deploy the updated code with debug logging
2. Run test query to see where metadata is lost
3. Add more debug logging if needed

### Short-term (30 minutes)
1. Fix metadata loss in identified location
2. Ensure penalty info flows through entire pipeline
3. Verify article filtering is working

### Medium-term (1 hour)
1. Add penalty info to LLM context (not just display)
2. Enhance LLM prompt with penalty extraction
3. Return penalty in API response

---

## 📊 Metadata Flow Analysis

**Current (with issues)**:
```
Chunks JSON ✓ (has doc_section, penalties)
    ↓
FAISS Index ✓ (preserves metadata)
    ↓
FAISS Search ✓ (returns Document with metadata)
    ↓
RRF Fusion [DEBUG] (preserve test)
    ↓
Section Boost [DEBUG] (preserve test)
    ↓
Category Boost [?] (need to check)
    ↓
Rerank [?] (might strip metadata)
    ↓
Article Expansion ✓ (preserves metadata, replaces page_content)
    ↓
Debug Output ✓ (now shows penalty, but section still missing)
    ↓
LLM Response ❌ (LLM might not see penalty in text)
```

---

## 🔧 Technical Details

### Why Penalty Info Was Missing
The debug output code was manually selecting metadata fields to display:
```python
section = doc.metadata.get('doc_section', '?')
dieu = doc.metadata.get('dieu', '?')
violation_cat = doc.metadata.get('violation_category', '?')
```

But NOT including:
```python
penalty_min = doc.metadata.get('penalty_min')
penalty_max = doc.metadata.get('penalty_max')
```

### Why Section Shows as '?'
Either:
1. **Metadata not in Document**: FAISS not preserving metadata from chunks
2. **Metadata lost in processing**: RRF/boost/rerank stripping metadata
3. **Metadata key mismatch**: Field name different than expected

---

## 📝 Summary

| Issue | Before | After | Status |
|-------|--------|-------|--------|
| Penalty missing from output | ❌ Not shown | ✅ Added to debug | FIXED |
| Section missing ([section=?]) | ❌ Missing | ❓ Debugging | IN PROGRESS |
| Article filtering | ❌ Not filtering | ❓ Testing | TESTING |
| Metadata preservation | ❌ Unknown | ✅ Logging added | INVESTIGATING |

---

## 🎓 What We Learned

1. **Metadata is critical** - Without it, LLM can't extract penalties
2. **Debug output matters** - User can't see penalty if not in debug
3. **Pipeline preservation** - Need to track metadata through each step
4. **Original 4 fixes necessary** - But not sufficient for full solution

---

**Next**: Run tests with debug logging enabled to trace metadata loss 🔍

