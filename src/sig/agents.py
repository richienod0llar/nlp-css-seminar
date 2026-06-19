from pathlib import Path
from typing import Dict, Any
from src.sig.schema import AssertionResult, QuestionResult
from src.sig.llm_client import get_client

class BaseAgent:
    def __init__(self, config: Dict[str, Any], prompt_path: str):
        self.config = config
        self.client = get_client(config, mock=config["llm"].get("mock", False))
        self.system_prompt = Path(prompt_path).read_text(encoding="utf-8")

class Assertion_Developer(BaseAgent):
    def run(self, input_indicator: str) -> AssertionResult:
        user_prompt = f"Develop an assertion for this indicator: {input_indicator}"
        response = self.client.chat_completion(self.system_prompt, user_prompt)

        return AssertionResult(
            predicted_concept=response.get("concept", ""),
            predicted_structure_code=response.get("structure_code", ""),
            predicted_assertion=response.get("assertion", ""),
            raw_response=str(response)
        )
    
class Question_Developer(BaseAgent):
    def run(self, assertion: str) -> QuestionResult:
        user_prompt = f"Develop a survey question and options for this assertion: {assertion}"
        response = self.client.chat_completion(self.system_prompt, user_prompt)
        
        return QuestionResult(
            predicted_question=response.get("question", ""),
            predicted_options=response.get("answer_options", ""),
            question_format=response.get("question_format", ""),
            raw_response=str(response)
        )