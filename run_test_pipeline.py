import yaml
from src.sig.pipeline import SurveyPipeline

# 1. Load Config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# 2. Start Pipeline
pipeline = SurveyPipeline(config)

# 3. Test on an indicator
result = pipeline.process_indicator("Overall satisfaction with medical care")

print("--- ASSERTION STAGE ---")
print(f"Concept: {result['assertion_stage'].predicted_concept}")
print(f"Assertion: {result['assertion_stage'].predicted_assertion}")

print("\n--- QUESTION STAGE ---")
print(f"Question: {result['question_stage'].predicted_question}")
print(f"Options: {result['question_stage'].predicted_options}")