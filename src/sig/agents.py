from pathlib import Path
from typing import Any, Dict

from src.sig.llm_client import get_client
from src.sig.loader import load_concept_names
from src.sig.normalize import match_concept
from src.sig.prompts.prompt_loader import load_prompt
from src.sig.schema import AssertionResult, QuestionResult


class BaseAgent:
    def __init__(self, config: Dict[str, Any], prompt_path: str):
        self.config = config
        self.client = get_client(config, mock=config["llm"].get("mock", False))
        self.llm_cfg = config["llm"]
        self.system_prompt = load_prompt(
            template_path=Path(prompt_path),
            yaml_path=config["data"]["concepts"],
        )

    def _llm_kwargs(self) -> Dict[str, Any]:
        return {
            "temperature": self.llm_cfg.get("temperature", 0.0),
            "max_tokens": self.llm_cfg.get("max_tokens", 1024),
        }


class Assertion_Developer(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "src/sig/prompts/assertion_developer.md")
        self.valid_concepts = load_concept_names(config["data"]["concepts"])

    def run(self, input_indicator: str) -> AssertionResult:
        user_prompt = f"Develop an assertion for this indicator: {input_indicator}"
        response = self.client.chat_completion(
            self.system_prompt,
            user_prompt,
            response_schema="assertion",
            valid_concepts=self.valid_concepts,
            **self._llm_kwargs(),
        )
        raw_concept = response.get("concept", "")
        canonical_concept = match_concept(raw_concept, self.valid_concepts)
        return AssertionResult(
            predicted_concept=canonical_concept or raw_concept,
            predicted_structure_code=response.get("structure_code", ""),
            predicted_assertion=response.get("assertion", ""),
            raw_response=str(response),
        )


class Question_Developer(BaseAgent):
    def run(self, assertion: str) -> QuestionResult:
        user_prompt = f"Develop a survey question and options for this assertion: {assertion}"
        response = self.client.chat_completion(
            self.system_prompt,
            user_prompt,
            response_schema="question",
            **self._llm_kwargs(),
        )
        return QuestionResult(
            predicted_question=response.get("question", ""),
            predicted_options=response.get("answer_options", ""),
            question_format=response.get("question_format", ""),
            raw_response=str(response),
        )
