#!/usr/bin/env python3
"""Re-score an existing eval CSV with an external LLM judge (no pipeline rerun)."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Allow running as: python scripts/run_judge_only.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import yaml

from src.sig.evaluation.judge import AlignmentJudge
from src.sig.loader import DataManager


def _mean_score(rows: list[dict], key: str) -> float | None:
    scores = [r[key] for r in rows if r.get(key) is not None]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-score an eval report CSV with the configured external judge."
    )
    parser.add_argument(
        "report_csv",
        nargs="?",
        default="docs/baseline/eval_report_vllm_20260625_160020.csv",
        help="Path to eval_report_*.csv with predictions (default: Run 4 baseline)",
    )
    parser.add_argument("--config", default="config.yaml", help="Config with judge.* settings")
    parser.add_argument("--max-rows", type=int, default=None, help="Score only first N rows")
    parser.add_argument("--judge-model", help="Override judge.model (for the 2x2 judge control)")
    parser.add_argument("--judge-base-url", help="Override judge.base_url")
    parser.add_argument("--tag", help="Label embedded in the output filenames")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: outputs/)",
    )
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.judge_model:
        config.setdefault("judge", {})["model"] = args.judge_model
    if args.judge_base_url:
        config.setdefault("judge", {})["base_url"] = args.judge_base_url

    report_path = Path(args.report_csv)
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")

    df = pd.read_csv(report_path)
    if args.max_rows is not None:
        df = df.head(int(args.max_rows))

    dm = DataManager(config["data"]["gold_set"], config["data"]["concepts"])
    dm.load_all()
    gold_by_id = {row.example_id: row for row in dm.gold_data}

    judge_cfg = config.get("judge", {})
    judge_model = judge_cfg.get("model", config["llm"]["model"])
    print(f"External judge: {judge_model}")
    print(f"Rows to score: {len(df)}")

    judge = AlignmentJudge(config)
    results: list[dict] = []

    for _, row in df.iterrows():
        example_id = int(row["example_id"])
        gold = gold_by_id.get(example_id)
        if gold is None:
            raise SystemExit(f"No gold row for example_id={example_id}")

        print(f"Scoring ID {example_id}...")
        pred_assertion = row.get("pred_assertion", "")
        pred_concept = row.get("pred_concept")
        if pd.isna(pred_concept):
            pred_concept = None

        ia = judge.score_indicator_assertion(
            str(row["input_indicator"]),
            str(pred_assertion) if not pd.isna(pred_assertion) else "",
            str(pred_concept) if pred_concept is not None else None,
        )

        pred_question = row.get("pred_question", "")
        pred_options = row.get("pred_options")
        if pd.isna(pred_options):
            pred_options = None

        aq = judge.score_assertion_question(
            gold.assertion,
            str(pred_question) if not pd.isna(pred_question) else "",
            str(pred_options) if pred_options is not None else None,
        )

        out = row.to_dict()
        out["ext_indicator_assertion_score"] = ia["score"]
        out["ext_indicator_assertion_rationale"] = ia["rationale"]
        out["ext_assertion_question_score"] = aq["score"]
        out["ext_assertion_question_rationale"] = aq["rationale"]
        results.append(out)

    output_dir = Path(args.output_dir or config.get("eval", {}).get("output_dir", "outputs/"))
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_stamp = report_path.stem.replace("eval_report_", "")
    if args.tag:
        source_stamp = f"{args.tag}_{source_stamp}"
    report_out = output_dir / f"eval_report_ext_judge_{source_stamp}_{stamp}.csv"
    summary_out = output_dir / f"eval_summary_ext_judge_{source_stamp}_{stamp}.json"

    summary = {
        "source_report": str(report_path),
        "judge_model": judge_model,
        "total_rows": len(results),
        "mean_ext_indicator_assertion_score": _mean_score(results, "ext_indicator_assertion_score"),
        "mean_ext_assertion_question_score": _mean_score(results, "ext_assertion_question_score"),
    }
    if "indicator_assertion_score" in df.columns:
        summary["mean_self_indicator_assertion_score"] = _mean_score(
            results, "indicator_assertion_score"
        )
    if "assertion_question_score" in df.columns:
        summary["mean_self_assertion_question_score"] = _mean_score(
            results, "assertion_question_score"
        )

    pd.DataFrame(results).to_csv(report_out, index=False)
    summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 40)
    print("EXTERNAL JUDGE SUMMARY")
    print("=" * 40)
    for key, value in summary.items():
        if key != "source_report":
            print(f"{key}: {value}")
    print(f"\nReport:  {report_out.resolve()}")
    print(f"Summary: {summary_out.resolve()}")


if __name__ == "__main__":
    main()
