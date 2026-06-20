import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.sig.evaluation.metrics import (
    calculate_assertion_scores,
    calculate_question_scores,
    calculate_summary,
)
from src.sig.loader import DataManager
from src.sig.pipeline import SurveyPipeline


def main():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    eval_cfg = config.get("eval", {})
    max_rows = eval_cfg.get("max_rows")  # None = all rows
    output_dir = Path(eval_cfg.get("output_dir", config["output"]["dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    dm = DataManager(config["data"]["gold_set"], config["data"]["concepts"])
    dm.load_all()
    valid_concepts = list(dm.concepts.keys())

    rows = dm.gold_data if max_rows is None else dm.gold_data[: int(max_rows)]
    mock = config["llm"].get("mock", False)
    mode = "mock" if mock else "vllm"

    print(f"Starting evaluation ({mode}) on {len(rows)} rows...")

    pipeline = SurveyPipeline(config)
    all_results = []

    for gold_row in rows:
        print(f"Processing ID {gold_row.example_id}...")
        output = pipeline.evaluate_row(gold_row)

        assertion_scores = calculate_assertion_scores(
            gold_row, output["assertion_stage"], valid_concepts
        )
        question_scores = calculate_question_scores(gold_row, output["question_stage"])

        all_results.append(
            {
                "example_id": gold_row.example_id,
                "input_indicator": gold_row.input_indicator,
                **assertion_scores,
                **question_scores,
            }
        )

    summary = calculate_summary(all_results)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"eval_report_{mode}_{stamp}.csv"
    summary_path = output_dir / f"eval_summary_{mode}_{stamp}.json"

    pd.DataFrame(all_results).to_csv(report_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 40)
    print(f"EVALUATION SUMMARY ({mode.upper()})")
    print("=" * 40)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nPer-row report: {report_path.resolve()}")
    print(f"Summary JSON:   {summary_path.resolve()}")


if __name__ == "__main__":
    main()
