import re
from typing import List, Optional

def normalize_string(text: str) -> str:
    """Standardize strings for matching (lowercase, strip, remove extra internal spaces)"""
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    return re.sub(r'\s+','',text)
    
def match_concept(raw_name: str, valid_concepts: List[str]) -> Optional[str]:
    """Finds the correct concept name from the YAML list based on a raw Excel string"""
    norm_raw = normalize_string(raw_name)
    for concept in valid_concepts:
        if normalize_string(concept) == norm_raw:
            return concept
    return None