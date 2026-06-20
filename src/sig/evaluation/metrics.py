from typing import Any, Dict, List

from src.sig.normalize import concepts_match, normalize_string, structures_match
from src.sig.schema import AssertionResult, GoldRow, QuestionResult


def calculate_assertion_scores(
    gold: GoldRow,
    pred: AssertionResult,
    valid_concepts: List[str],
) -> Dict[str, Any]:
    return {
        "concept_accuracy": concepts_match(
            gold.basic_concept, pred.predicted_concept, valid_concepts
        ),
        "structure_accuracy": structures_match(
            gold.semantic_structure, pred.predicted_structure_code
        ),
        "gold_concept": gold.basic_concept,
        "pred_concept": pred.predicted_concept,
        "gold_structure": gold.semantic_structure,
        "pred_structure": pred.predicted_structure_code,
        "pred_assertion": pred.predicted_assertion,
    }


def calculate_question_scores(
    gold: GoldRow,
    pred: QuestionResult,
) -> Dict[str, Any]:
    pred_q = normalize_string(pred.predicted_question)
    gold_q = normalize_string(gold.question)
    return {
        "question_non_empty": bool(pred_q),
        "question_exact_match": pred_q == gold_q and bool(pred_q),
        "pred_question": pred.predicted_question,
        "pred_options": pred.predicted_options,
        "pred_format": pred.question_format,
        "gold_question": gold.question,
    }


def calculate_summary(results: List[Dict[str, Any]]) -> Dict[str, float]:
    total = len(results)
    if total == 0:
        return {}

    def pct(key: str) -> float:
        hits = sum(1 for r in results if r.get(key))
        return round((hits / total) * 100, 2)

    return {
        "total_rows": total,
        "concept_accuracy_pct": pct("concept_accuracy"),
        "structure_accuracy_pct": pct("structure_accuracy"),
        "question_non_empty_pct": pct("question_non_empty"),
        "question_exact_match_pct": pct("question_exact_match"),
    }
