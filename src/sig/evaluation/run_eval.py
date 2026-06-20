import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.sig.evaluation.judge import AlignmentJudge
from src.sig.evaluation.metrics import (
    build_concept_confusion_matrix,
    build_structure_confusion_matrix,
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
    run_judge = eval_cfg.get("run_judge", False)
    output_dir = Path(eval_cfg.get("output_dir", config["output"]["dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    dm = DataManager(config["data"]["gold_set"], config["data"]["concepts"])
    dm.load_all()
    valid_concepts = list(dm.concepts.keys())

    rows = dm.gold_data if max_rows is None else dm.gold_data[: int(max_rows)]
    mock = config["llm"].get("mock", False)
    mode = "mock" if mock else "vllm"

    print(f"Starting evaluation ({mode}) on {len(rows)} rows...")
    if run_judge:
        print("LLM-as-judge enabled (2 extra calls per row).")

    pipeline = SurveyPipeline(config)
    judge = AlignmentJudge(config) if run_judge else None
    all_results = []

    for gold_row in rows:
        print(f"Processing ID {gold_row.example_id}...")
        output = pipeline.evaluate_row(gold_row)

        assertion_scores = calculate_assertion_scores(
            gold_row, output["assertion_stage"], valid_concepts
        )
        question_scores = calculate_question_scores(gold_row, output["question_stage"])

        row_result = {
            "example_id": gold_row.example_id,
            "input_indicator": gold_row.input_indicator,
            **assertion_scores,
            **question_scores,
        }

        if judge:
            ia = judge.score_indicator_assertion(
                gold_row.input_indicator,
                output["assertion_stage"].predicted_assertion,
                output["assertion_stage"].predicted_concept,
            )
            aq = judge.score_assertion_question(
                gold_row.assertion,
                output["question_stage"].predicted_question,
                output["question_stage"].predicted_options,
            )
            row_result["indicator_assertion_score"] = ia["score"]
            row_result["indicator_assertion_rationale"] = ia["rationale"]
            row_result["assertion_question_score"] = aq["score"]
            row_result["assertion_question_rationale"] = aq["rationale"]

        all_results.append(row_result)

    summary = calculate_summary(all_results)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"eval_report_{mode}_{stamp}.csv"
    summary_path = output_dir / f"eval_summary_{mode}_{stamp}.json"
    concept_cm_path = output_dir / f"concept_confusion_{mode}_{stamp}.csv"
    structure_cm_path = output_dir / f"structure_confusion_{mode}_{stamp}.csv"

    pd.DataFrame(all_results).to_csv(report_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    build_concept_confusion_matrix(all_results).to_csv(concept_cm_path, index=False)
    build_structure_confusion_matrix(all_results).to_csv(structure_cm_path, index=False)

    print("\n" + "=" * 40)
    print(f"EVALUATION SUMMARY ({mode.upper()})")
    print("=" * 40)
    for key, value in summary.items():
        if key in ("per_concept", "per_structure", "question_format_distribution"):
            continue
        print(f"{key}: {value}")
    print(f"\nPer-row report:       {report_path.resolve()}")
    print(f"Summary JSON:         {summary_path.resolve()}")
    print(f"Concept confusion:    {concept_cm_path.resolve()}")
    print(f"Structure confusion:  {structure_cm_path.resolve()}")


if __name__ == "__main__":
    main()
