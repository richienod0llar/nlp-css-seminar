from typing import Dict, List, Any
from src.sig.schema import GoldRow, AssertionResult

def calculate_assertion_scores(gold: GoldRow, pred: AssertionResult) -> Dict[str, bool]:
    """
    Compares the predicted assertion details against the gold set.
    """
    
    # Normalize strings
    concept_match = gold.basic_concept.strip().lower() == pred.predicted_concept.strip().lower()
    
    # Check if the structure code matches
    structure_match = gold.semantic_structure.strip().lower() == pred.predicted_structure_code.strip().lower()
    
    return{
        "concept_accuracy": concept_match,
        "structure_accuracy": structure_match
    }
def calculate_summary(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregates all rows into percentage scores"""
    total = len(results)
    if total == 0:
        return{}

    concept_hits = sum(1 for r in results if r["concept_accuracy"])
    struct_hits = sum(1 for r in results if r["structure_accuracy"])
    
    return{
        "total rows": total,
        "concept_accuracy_pct": round((concept_hits/total)*100, 2),
        "structure_accuracy_pct": round((struct_hits/total)*100, 2),
    }