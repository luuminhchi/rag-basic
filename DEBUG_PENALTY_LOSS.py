#!/usr/bin/env python3
"""
Debug script to trace where penalty metadata is lost in the pipeline
"""
import json
from pathlib import Path

# Load chunks
chunks_file = Path("data/final_chunks/168_2024_ND-CP_619502_chunks.json")
with open(chunks_file) as f:
    chunks = json.load(f)

# Find Article 11 chunks with penalties
article_11_chunks = [
    c for c in chunks 
    if c["metadata"].get("dieu") == 11 and c["metadata"].get("has_penalty")
]

print(f"Found {len(article_11_chunks)} Article 11 chunks with penalties\n")

# Show what information exists in chunks
print("=" * 80)
print("CHUNK METADATA - What Should Be Preserved")
print("=" * 80)

for i, chunk in enumerate(article_11_chunks[:3], 1):
    meta = chunk["metadata"]
    print(f"\nChunk {i}: {chunk['chunk_id']}")
    print(f"  Article:           {meta.get('dieu')}")
    print(f"  Section:           {meta.get('doc_section')}")
    print(f"  Violation Type:    {meta.get('violation_category')}")
    print(f"  Penalty Min:       {meta.get('penalty_min'):,} đ" if meta.get('penalty_min') else "  Penalty Min:       None")
    print(f"  Penalty Max:       {meta.get('penalty_max'):,} đ" if meta.get('penalty_max') else "  Penalty Max:       None")
    print(f"  Behavior:          {meta.get('hanh_vi_vi_pham', [])[:1]}")
    print(f"  Content Length:    {len(chunk['text'])} chars")

print("\n" + "=" * 80)
print("WHAT THE HYBRID SEARCH OUTPUT CURRENTLY SHOWS")
print("=" * 80)
print("""
Current debug output:
   Top 1: [section=?] [dieu=11] [loai=khoan] [cat=tin_hieu_den]
           [Danh mục lỗi]: tín hiệu đèn giao thông
[Các hành vi cụ thể]: Không nhường đường theo quy định, không báo hiệu bằng tay ...

Missing:
   ❌ [section=xu_phat]           <- doc_section missing  
   ❌ [Mức phạt]: 150.000-250.000  <- penalty_min/max missing
   ❌ [Mức trừ điểm]: ?            <- no points deduction shown
""")

print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print("""
Issue 1: Metadata Loss [section=?]
  Location: Between hybrid_search retrieval and debug output
  Likely cause: Document metadata not preserved in RRF fusion or rerank
  
Issue 2: Penalty Not Shown
  Location: Debug output formatting (rerank.py)
  Likely cause: LLM prompt extraction only uses text, not metadata
  
Issue 3: Article Filtering Not Working
  Expected: Only Article 11 results
  Actual: Articles 7, 9, 11 (all shown)
  Likely cause: Fix #4 not deployed yet, OR target_article not passed correctly
""")

print("\n" + "=" * 80)
print("WHAT NEEDS TO BE FIXED (Beyond the 4 fixes)")
print("=" * 80)
print("""
PRIMARY (Blocking penalty info):
  1. Extract penalty from metadata during rerank
  2. Add to debug output: [Mức phạt]: {penalty_min}-{penalty_max}
  3. Preserve doc_section metadata through pipeline

SECONDARY (Article filtering):
  1. Verify Fix #4 is deployed correctly
  2. Check target_article is passed to hybrid_search
  3. Confirm article filtering is working

TERTIARY (Data completeness):
  1. Ensure all chunks have doc_section metadata
  2. Add metadata to LLM context (not just text)
  3. Extract multiple metadata fields for display
""")
