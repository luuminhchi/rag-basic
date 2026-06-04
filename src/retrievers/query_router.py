import re

from src.retrievers.intent_classifier import INTENT_TYPES
from src.retrievers.section_resolver import INTENT_TO_SECTION
from src.retrievers.filter_builder import extract_entities

def classify_query(query: str) -> dict:
    """
    Output đầy đủ để routing + filter cho hybrid search
    """
    query_lower = query.lower()

    # Tầng 1: detect intent
    intent = 'query_muc_phat'  # default
    for intent_type, patterns in INTENT_TYPES.items():
        if any(re.search(p, query_lower) for p in patterns):
            intent = intent_type
            break

    # Tầng 2: section từ intent
    section_info = INTENT_TO_SECTION[intent]

    # Tầng 3: entity extraction
    entities = extract_entities(query)

    # Merge subsection: entity override intent nếu có
    final_subsection = entities['doc_subsection'] or section_info['doc_subsection']

    return {
        # Routing
        'intent':         intent,
        'doc_section':    section_info['doc_section'],
        'doc_subsection': final_subsection,

        # Filter cho hybrid search
        'filter': {
            'doc_section':    section_info['doc_section'],
            'doc_subsection': final_subsection,
            'vehicle_groups': entities['vehicle_group'],
            **entities['special']
        },

        # Rewrite hint — truyền vào query rewriter
        'rewrite_context': {
            'intent':       intent,
            'vehicle':      entities['vehicle_group'],
            'filter_fields': section_info['filter_fields']
        }
    }