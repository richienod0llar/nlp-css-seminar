#!/usr/bin/env python3
"""Offline analysis of an eval report CSV (no LLM calls)."""

import argparse
import json
import sys
from pathlib import Path

# Allow running as: python scripts/analyze_eval.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.sig.evaluation.metrics import (
    build_concept_confusion_matrix,
    build_structure_confusion_matrix,
    calculate_summary,
)


def main():
    parser = argparse.ArgumentParser(description="Analyze an eval report CSV.")
    parser.add_argument(
        "report_csv",
        nargs="?",
        help="Path to eval_report_*.csv (default: latest in outputs/)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for analysis JSON (default: same as report)",
    )
    args = parser.parse_args()

    if args.report_csv:
        report_path = Path(args.report_csv)
    else:
        candidates = sorted(Path("outputs").glob("eval_report_*.csv"))
        if not candidates:
            raise SystemExit("No eval_report_*.csv found in outputs/")
        report_path = candidates[-1]

    df = pd.read_csv(report_path)
    results = df.to_dict(orient="records")
    summary = calculate_summary(results)

    out_dir = Path(args.output_dir) if args.output_dir else report_path.parent
    stamp = report_path.stem.replace("eval_report_", "")
    analysis_path = out_dir / f"eval_analysis_{stamp}.json"
    concept_cm_path = out_dir / f"concept_confusion_{stamp}.csv"
    structure_cm_path = out_dir / f"structure_confusion_{stamp}.csv"

    analysis_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    build_concept_confusion_matrix(results).to_csv(concept_cm_path, index=False)
    build_structure_confusion_matrix(results).to_csv(structure_cm_path, index=False)

    print(f"Report:              {report_path.resolve()}")
    print(f"Analysis JSON:       {analysis_path.resolve()}")
    print(f"Concept confusion:   {concept_cm_path.resolve()}")
    print(f"Structure confusion: {structure_cm_path.resolve()}")
    print()
    for key in (
        "total_rows",
        "concept_accuracy_pct",
        "structure_accuracy_pct",
        "both_correct_pct",
        "question_non_empty_pct",
        "question_exact_match_pct",
    ):
        if key in summary:
            print(f"{key}: {summary[key]}")


if __name__ == "__main__":
    main()
