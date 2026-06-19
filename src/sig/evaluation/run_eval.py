import pandas as pd
import yaml
from src.sig.loader import DataManager
from src.sig.pipeline import SurveyPipeline
from src.sig.evaluation.metrics import calculate_assertion_scores, calculate_summary

def main():
    # 1. Load config data
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    dm = DataManager(config["data"]["gold_set"], config["data"]["concepts"])
    dm.load_all()

    pipeline = SurveyPipeline(config)
    all_results = []
    
    print(f"Starting eveluation on {len(dm.gold_data)} rows...")
    
    # 2. Run through a slice of rows
    for gold_row in dm.gold_data[:10]: # Testing on first 10 rows
        print(f"Processing ID {gold_row.example_id}...")
        
        # Run the AI pipeline
        output = pipeline.process_indicator(gold_row.input_indicator)

        # Score the Assertion Stage
        scores = calculate_assertion_scores(gold_row, output["assertion_stage"])

        # Store for report
        all_results.append({
            "id":gold_row.example_id,
            **scores
        })
        
    # 3. Print Final Report
    summary = calculate_summary(all_results)
    print("\n" + "="*30)
    print("EVALUATION SUMMARY (MOCK)")
    print("\n" + "="*30)
    for key, value in summary.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()