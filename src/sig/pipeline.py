from typing import Dict, Any
from src.sig.agents import Assertion_Developer, Question_Developer

class SurveyPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.assertion_dev = Assertion_Developer(config, "src/sig/prompts/assertion_developer.md")
        self.question_dev = Question_Developer(config, "src/sig/prompts/question_developer.md")
        
    def process_indicator(self, input_indicator: str):
        # Step 1: Develop Assertion
        assertion_res = self.assertion_dev.run(input_indicator)
        
        # Step 2: Develop Question from that Assertion
        question_res = self.question_dev.run(assertion_res.predicted_assertion)
        
        return{
            "assertion_stage": assertion_res,
            "question_stage": question_res
        }