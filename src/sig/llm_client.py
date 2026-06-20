import json
import random
import re
from typing import Any, Dict, Literal

from openai import OpenAI

ResponseSchema = Literal["assertion", "question"]

ASSERTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "concept": {"type": "string"},
        "structure_code": {"type": "string"},
        "assertion": {"type": "string"},
    },
    "required": ["concept", "structure_code", "assertion"],
}

QUESTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer_options": {"type": "string"},
        "question_format": {"type": "string"},
    },
    "required": ["question", "answer_options", "question_format"],
}


def parse_json_response(content: str) -> Dict[str, Any]:
    """Parse model output; tolerate thinking text before/after JSON."""
    if not content:
        return {}
    content = content.strip()
    # Strip Qwen3 thinking blocks if present
    content = re.sub(
        r"^Thinking Process:.*?(?=\{|\Z)",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()
    think_close = "</" + "redacted_thinking" + ">"
    if think_close in content:
        content = content.split(think_close, 1)[-1].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass
    if content.lower().startswith("thinking process"):
        print("Error decoding JSON response: model returned thinking text only (no JSON).")
        return {}
    print(f"Error decoding JSON response: {content[:500]}")
    return {}


def _build_user_prompt(user_prompt: str, enable_thinking: bool) -> str:
    suffix = (
        "\n\nRespond with a single JSON object only. "
        "No markdown, no explanation, no thinking process."
    )
    if not enable_thinking:
        user_prompt = f"{user_prompt.rstrip()} /no_think"
    return user_prompt + suffix


class vLLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "EMPTY",
        enable_thinking: bool = False,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.enable_thinking = enable_thinking

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: ResponseSchema = "assertion",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        schema = ASSERTION_SCHEMA if response_schema == "assertion" else QUESTION_SCHEMA
        user_prompt = _build_user_prompt(user_prompt, self.enable_thinking)
        extra_body: Dict[str, Any] = {"guided_json": schema}
        if not self.enable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        msg = response.choices[0].message
        content = msg.content or ""
        if not content.strip():
            reasoning = getattr(msg, "reasoning_content", None)
            if reasoning:
                content = reasoning
        return parse_json_response(content)


class MockLLMClient:
    """Fake responses for local wiring tests (no vLLM server)."""

    _ASSERTION_RESPONSES = [
        {"concept": "Evaluation", "structure_code": "xIe", "assertion": "I am satisfied with this product."},
        {"concept": "Behavior", "structure_code": "rDy", "assertion": "I exercise regularly each week."},
        {"concept": "Preference", "structure_code": "xPRy", "assertion": "I prefer online communication over in-person meetings."},
        {"concept": "Feelings", "structure_code": "xFy", "assertion": "I feel anxious in crowded environments."},
        {"concept": "Demographics", "structure_code": "xId", "assertion": "My current employment status is employed."},
    ]

    _QUESTION_RESPONSES = [
        {
            "question": "How satisfied are you with this product?",
            "answer_options": "Rating scale (1–5)",
            "question_format": "Direct interrogative (with WH word)",
        },
        {
            "question": "How often do you exercise each week?",
            "answer_options": "Never, Rarely, Sometimes, Often, Always",
            "question_format": "Direct interrogative (with WH word)",
        },
        {
            "question": "What is your preferred method of communication?",
            "answer_options": "Open-ended",
            "question_format": "Direct interrogative (with WH word)",
        },
        {
            "question": "How anxious do you feel in crowded environments?",
            "answer_options": "Not at all–Extremely",
            "question_format": "Direct interrogative (with WH word)",
        },
        {
            "question": "What is your current employment status?",
            "answer_options": "Employed, Unemployed, Student, Retired, Other",
            "question_format": "Direct interrogative (with WH word)",
        },
    ]

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: ResponseSchema = "assertion",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        del system_prompt, user_prompt, temperature, max_tokens
        if response_schema == "assertion":
            return random.choice(self._ASSERTION_RESPONSES)
        return random.choice(self._QUESTION_RESPONSES)


def get_client(config: Dict[str, Any], mock: bool = False):
    if mock:
        return MockLLMClient()
    llm = config["llm"]
    return vLLMClient(
        base_url=llm["base_url"],
        model=llm["model"],
        api_key=llm.get("api_key", "EMPTY"),
        enable_thinking=llm.get("enable_thinking", False),
    )
