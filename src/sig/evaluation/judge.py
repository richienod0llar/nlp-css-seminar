"""LLM-as-judge for indicator-assertion and assertion-question alignment."""

from typing import Any, Dict, Optional

from src.sig.llm_client import get_judge_client

INDICATOR_ASSERTION_JUDGE_PROMPT = """You are an expert survey methodologist evaluating whether an assertion faithfully represents an input indicator.

Score 1-5:
5 = Perfect alignment; assertion captures the indicator meaning precisely
4 = Good alignment; minor wording differences only
3 = Partial alignment; related but misses nuance or scope
2 = Poor alignment; significant mismatch
1 = No alignment; assertion does not represent the indicator

Respond with JSON: {"score": <1-5>, "rationale": "<brief explanation>"}"""

ASSERTION_QUESTION_JUDGE_PROMPT = """You are an expert survey methodologist evaluating whether a survey question faithfully represents an assertion.

Score 1-5:
5 = Perfect alignment; question captures the assertion meaning precisely
4 = Good alignment; minor wording or format differences only
3 = Partial alignment; related but misses nuance or scope
2 = Poor alignment; significant mismatch
1 = No alignment; question does not represent the assertion

Respond with JSON: {"score": <1-5>, "rationale": "<brief explanation>"}"""


class AlignmentJudge:
    def __init__(self, config: Dict[str, Any]):
        mock = config["llm"].get("mock", False)
        self.client = get_judge_client(config, mock=mock)
        judge_cfg = config.get("judge", {})
        llm_cfg = config["llm"]
        self.temperature = judge_cfg.get("temperature", llm_cfg.get("temperature", 0.0))
        self.max_tokens = judge_cfg.get("max_tokens", 256)

    def _score(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        response = self.client.chat_completion(
            system_prompt,
            user_prompt,
            response_schema="judge",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        score = response.get("score")
        if not isinstance(score, int) or score < 1 or score > 5:
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = None
        return {
            "score": score,
            "rationale": response.get("rationale", ""),
        }

    def score_indicator_assertion(
        self,
        input_indicator: str,
        predicted_assertion: str,
        predicted_concept: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not predicted_assertion or not predicted_assertion.strip():
            return {"score": None, "rationale": "Empty assertion."}
        concept_note = f"\nPredicted concept: {predicted_concept}" if predicted_concept else ""
        user_prompt = (
            f"Input indicator: {input_indicator}\n"
            f"Assertion: {predicted_assertion}{concept_note}\n\n"
            "Rate alignment (1-5)."
        )
        return self._score(INDICATOR_ASSERTION_JUDGE_PROMPT, user_prompt)

    def score_assertion_question(
        self,
        assertion: str,
        predicted_question: str,
        predicted_options: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not predicted_question or not predicted_question.strip():
            return {"score": None, "rationale": "Empty question."}
        options_note = f"\nAnswer options: {predicted_options}" if predicted_options else ""
        user_prompt = (
            f"Assertion: {assertion}\n"
            f"Question: {predicted_question}{options_note}\n\n"
            "Rate alignment (1-5)."
        )
        return self._score(ASSERTION_QUESTION_JUDGE_PROMPT, user_prompt)
