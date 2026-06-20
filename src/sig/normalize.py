import re
from typing import List, Optional

# Structure codes in gold/predictions: xIe, xPRy, rDy, etc.
_STRUCTURE_CODE_RE = re.compile(r"\b([xrgoc][A-Za-z]+)\b")


def normalize_string(text: str) -> str:
    """Lowercase, strip, remove whitespace for fuzzy string match."""
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    return re.sub(r"\s+", "", text)


def extract_structure_code(text: str) -> str:
    """Pull bare structure code from gold label or model output."""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.strip()
    match = _STRUCTURE_CODE_RE.search(text)
    if match:
        return match.group(1)
    return normalize_string(text)


def match_concept(raw_name: str, valid_concepts: List[str]) -> Optional[str]:
    """Map raw concept string to canonical name from concepts.yaml."""
    norm_raw = normalize_string(raw_name)
    if not norm_raw:
        return None
    for concept in valid_concepts:
        if normalize_string(concept) == norm_raw:
            return concept
    return None


def concepts_match(gold_concept: str, predicted_concept: str, valid_concepts: List[str]) -> bool:
    """Compare concepts after normalization; also accept canonical YAML names."""
    gold = match_concept(gold_concept, valid_concepts) or gold_concept
    pred = match_concept(predicted_concept, valid_concepts) or predicted_concept
    return normalize_string(gold) == normalize_string(pred)


def structures_match(gold_structure: str, predicted_structure: str) -> bool:
    return extract_structure_code(gold_structure) == extract_structure_code(predicted_structure)
