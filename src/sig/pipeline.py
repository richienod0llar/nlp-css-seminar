from typing import Any, Dict

from src.sig.agents import Assertion_Developer, Question_Developer
from src.sig.schema import GoldRow


class SurveyPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.assertion_dev = Assertion_Developer(config, "src/sig/prompts/assertion_developer.md")
        self.question_dev = Question_Developer(config, "src/sig/prompts/question_developer.md")

    def process_indicator(self, input_indicator: str) -> Dict[str, Any]:
        """Chained demo: indicator -> assertion -> question (uses predicted assertion)."""
        assertion_res = self.assertion_dev.run(input_indicator)
        question_res = self.question_dev.run(assertion_res.predicted_assertion)
        return {"assertion_stage": assertion_res, "question_stage": question_res}

    def evaluate_row(self, gold_row: GoldRow) -> Dict[str, Any]:
        """Isolated eval per protocol: assertion from indicator; question from gold assertion."""
        assertion_res = self.assertion_dev.run(gold_row.input_indicator)
        question_res = self.question_dev.run(gold_row.assertion)
        return {"assertion_stage": assertion_res, "question_stage": question_res}
