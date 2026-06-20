from typing import Any, Dict, List, Optional

import pandas as pd

from src.sig.normalize import concepts_match, extract_structure_code, normalize_string, structures_match
from src.sig.schema import AssertionResult, GoldRow, QuestionResult

VALID_QUESTION_FORMATS = [
    "direct interrogative (with wh word)",
    "direct interrogative (without wh word)",
    "direct imperative",
    "indirect interrogative",
    "indirect imperative",
]


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


def normalize_question_format(raw_format: str) -> str:
    """Normalize predicted question format for reporting."""
    if not isinstance(raw_format, str) or not raw_format.strip():
        return ""
    fmt = raw_format.strip().lower()
    fmt = fmt.replace("direct interrogative", "direct interrogative")
    for valid in VALID_QUESTION_FORMATS:
        if valid in fmt or fmt in valid:
            return valid
    if "interrogative" in fmt and "wh" in fmt:
        return VALID_QUESTION_FORMATS[0]
    if "interrogative" in fmt:
        return VALID_QUESTION_FORMATS[1]
    if "imperative" in fmt and "indirect" in fmt:
        return VALID_QUESTION_FORMATS[4]
    if "imperative" in fmt:
        return VALID_QUESTION_FORMATS[2]
    return fmt


def calculate_question_scores(
    gold: GoldRow,
    pred: QuestionResult,
) -> Dict[str, Any]:
    pred_q = normalize_string(pred.predicted_question)
    gold_q = normalize_string(gold.question)
    pred_format = normalize_question_format(pred.question_format)
    return {
        "question_non_empty": bool(pred_q),
        "question_exact_match": pred_q == gold_q and bool(pred_q),
        "question_format_non_empty": bool(pred_format),
        "pred_question": pred.predicted_question,
        "pred_options": pred.predicted_options,
        "pred_format": pred.question_format,
        "pred_format_normalized": pred_format,
        "gold_question": gold.question,
    }


def calculate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {}

    def pct(key: str) -> float:
        hits = sum(1 for r in results if r.get(key))
        return round((hits / total) * 100, 2)

    summary: Dict[str, Any] = {
        "total_rows": total,
        "concept_accuracy_pct": pct("concept_accuracy"),
        "structure_accuracy_pct": pct("structure_accuracy"),
        "both_correct_pct": round(
            sum(1 for r in results if r.get("concept_accuracy") and r.get("structure_accuracy"))
            / total
            * 100,
            2,
        ),
        "question_non_empty_pct": pct("question_non_empty"),
        "question_exact_match_pct": pct("question_exact_match"),
        "question_format_non_empty_pct": pct("question_format_non_empty"),
    }

    for key in ("indicator_assertion_score", "assertion_question_score"):
        scores = [r[key] for r in results if r.get(key) is not None]
        if scores:
            summary[f"mean_{key}"] = round(sum(scores) / len(scores), 2)
            summary[f"{key}_n"] = len(scores)

    summary["per_concept"] = per_concept_breakdown(results)
    summary["per_structure"] = per_structure_breakdown(results)
    summary["question_format_distribution"] = question_format_distribution(results)
    return summary


def per_concept_breakdown(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    df = pd.DataFrame(results)
    if df.empty or "gold_concept" not in df.columns:
        return {}
    breakdown: Dict[str, Dict[str, float]] = {}
    for concept, group in df.groupby("gold_concept"):
        n = len(group)
        breakdown[str(concept)] = {
            "n": int(n),
            "concept_accuracy_pct": round(group["concept_accuracy"].mean() * 100, 1),
            "structure_accuracy_pct": round(group["structure_accuracy"].mean() * 100, 1),
        }
    return breakdown


def per_structure_breakdown(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    df = pd.DataFrame(results)
    if df.empty or "gold_structure" not in df.columns:
        return {}
    df = df.copy()
    df["gold_structure_code"] = df["gold_structure"].apply(extract_structure_code)
    breakdown: Dict[str, Dict[str, float]] = {}
    for code, group in df.groupby("gold_structure_code"):
        if not code:
            continue
        n = len(group)
        breakdown[str(code)] = {
            "n": int(n),
            "structure_accuracy_pct": round(group["structure_accuracy"].mean() * 100, 1),
        }
    return breakdown


def question_format_distribution(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in results:
        fmt = row.get("pred_format_normalized") or ""
        if not fmt:
            fmt = "(empty)"
        counts[fmt] = counts.get(fmt, 0) + 1
    return counts


def build_concept_confusion_matrix(results: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(results)
    if df.empty:
        return pd.DataFrame()
    wrong = df[~df["concept_accuracy"]].copy()
    if wrong.empty:
        return pd.DataFrame(columns=["gold_concept", "pred_concept", "count"])
    matrix = (
        wrong.groupby(["gold_concept", "pred_concept"])
        .size()
        .reset_index(name="count")
        .sort_values(["count", "gold_concept"], ascending=[False, True])
    )
    return matrix


def build_structure_confusion_matrix(results: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(results)
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["gold_code"] = df["gold_structure"].apply(extract_structure_code)
    df["pred_code"] = df["pred_structure"].apply(extract_structure_code)
    wrong = df[~df["structure_accuracy"]]
    if wrong.empty:
        return pd.DataFrame(columns=["gold_structure", "pred_structure", "count"])
    matrix = (
        wrong.groupby(["gold_code", "pred_code"])
        .size()
        .reset_index(name="count")
        .sort_values(["count", "gold_code"], ascending=[False, True])
    )
    return matrix
