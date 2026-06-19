import json
import random
from typing import Dict, Any, Optional
from openai import OpenAI

class vLLMClient:
    def __init__(self, base_url: str, model: str, api_key: str = 'EMPTY'):
        self.client = OpenAI(base_url, api_key=api_key)
        self.model = model

    def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Sends a request to vLLM and expects a JSON response"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
              {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}  
            ],
            temperature=temperature,
            # vLLM supports guided JSON output
            extra_body={"guided_json": self._get_assertion_schema()}
        )

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Error decoding JSON response: {content}")
            return {}
    def _get_assertion_schema(self) -> Dict[str, Any]:
        """Schema for forced JSON output (Assertion Developer)"""
        return{
            "type": "object",
            "properties": {
                "concept": {"type": "string"},
                "structure_code": {"type": "string"},
                "assertion": {"type": "string"}
            },
            "required": ["concept", "structure_code", "assertion"]
        }
    
class MockLLMClient:
    """
    A mock client for local development without a running vLLM server.
    Returns plausible-looking fake responses so you can test the full pipeline.
    """

    # A small pool of fake responses per agent type
    _ASSERTION_RESPONSES = [
        {"concept": "Evaluation", "structure_code": "xIe", "assertion": "I am satisfied with this product."},
        {"concept": "Behavior", "structure_code": "rDy", "assertion": "I exercise regularly each week."},
        {"concept": "Preference", "structure_code": "xPRy", "assertion": "I prefer online communication over in-person meetings."},
        {"concept": "Feelings", "structure_code": "xFy", "assertion": "I feel anxious in crowded environments."},
        {"concept": "Demographics", "structure_code": "xId", "assertion": "My current employment status is employed."},
    ]

    _QUESTION_RESPONSES = [
        {"question": "How satisfied are you with this product?", "answer_options": "Rating scale (1–5)", "question_format": "Direct interrogative (with WH word)"},
        {"question": "How often do you exercise each week?", "answer_options": "Never, Rarely, Sometimes, Often, Always", "question_format": "Direct interrogative (with WH word)"},
        {"question": "What is your preferred method of communication?", "answer_options": "Open-ended", "question_format": "Direct interrogative (with WH word)"},
        {"question": "How anxious do you feel in crowded environments?", "answer_options": "Not at all–Extremely", "question_format": "Direct interrogative (with WH word)"},
        {"question": "What is your current employment status?", "answer_options": "Employed, Unemployed, Student, Retired, Other", "question_format": "Direct interrogative (with WH word)"},
    ]

    def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Returns a random fake response based on which agent is calling."""
        if "assertion" in system_prompt.lower():
            return random.choice(self._ASSERTION_RESPONSES)
        else:
            return random.choice(self._QUESTION_RESPONSES)


def get_client(config: Dict[str, Any], mock: bool = False):
    """
    Factory function — returns MockLLMClient locally, vLLMClient on LRZ.
    Usage:
        client = get_client(config, mock=True)   # local
        client = get_client(config, mock=False)  # LRZ
    """
    if mock:
        return MockLLMClient()
    return vLLMClient(
        base_url=config["llm"]["base_url"],
        model=config["llm"]["model"],
        api_key=config["llm"].get("api_key", "EMPTY")
    )