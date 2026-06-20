import json
import random
import re
from typing import Any, Dict, Literal, List, Optional

from openai import OpenAI

ResponseSchema = Literal["assertion", "question", "judge"]

ASSERTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "concept": {"type": "string"},
        "structure_code": {"type": "string"},
        "assertion": {"type": "string"},
    },
    "required": ["concept", "structure_code", "assertion"],
}


def build_assertion_schema(valid_concepts: Optional[List[str]] = None) -> Dict[str, Any]:
    """Build assertion JSON schema; constrain concept to allowed names when provided."""
    schema = json.loads(json.dumps(ASSERTION_SCHEMA))
    if valid_concepts:
        schema["properties"]["concept"] = {"type": "string", "enum": valid_concepts}
    return schema


QUESTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer_options": {"type": "string"},
        "question_format": {"type": "string"},
    },
    "required": ["question", "answer_options", "question_format"],
}

JUDGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "rationale": {"type": "string"},
    },
    "required": ["score"],
}


def _repair_broken_question_json(content: str) -> Dict[str, Any]:
    """Extract question fields when answer_options breaks JSON quoting."""
    result: Dict[str, Any] = {}
    question_match = re.search(r'"question"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
    if question_match:
        result["question"] = question_match.group(1)
    format_match = re.search(r'"question_format"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
    if format_match:
        result["question_format"] = format_match.group(1)
    block_match = re.search(
        r'"answer_options"\s*:\s*(.+?),\s*"question_format"',
        content,
        re.DOTALL,
    )
    if block_match:
        block = block_match.group(1).strip()
        single = re.match(r'^"((?:[^"\\]|\\.)*)"$', block)
        if single:
            result["answer_options"] = single.group(1)
        else:
            parts = re.findall(r'"((?:[^"\\]|\\.)*)"', block)
            if parts:
                result["answer_options"] = ", ".join(parts)
    return result


def parse_json_response(content: str, schema: Optional[ResponseSchema] = None) -> Dict[str, Any]:
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
    if schema == "question":
        repaired = _repair_broken_question_json(content)
        if repaired.get("question"):
            return repaired
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
        valid_concepts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if response_schema == "assertion":
            schema = build_assertion_schema(valid_concepts)
        elif response_schema == "judge":
            schema = JUDGE_SCHEMA
        else:
            schema = QUESTION_SCHEMA
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
        return parse_json_response(content, schema=response_schema)


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
        valid_concepts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        del system_prompt, user_prompt, temperature, max_tokens, valid_concepts
        if response_schema == "judge":
            return {"score": random.randint(3, 5), "rationale": "Mock judge score."}
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


def get_judge_client(config: Dict[str, Any], mock: bool = False):
    if mock:
        return MockLLMClient()
    judge_cfg = config.get("judge", {})
    llm_cfg = config["llm"]
    return vLLMClient(
        base_url=judge_cfg.get("base_url", llm_cfg["base_url"]),
        model=judge_cfg.get("model", llm_cfg["model"]),
        api_key=judge_cfg.get("api_key", llm_cfg.get("api_key", "EMPTY")),
        enable_thinking=judge_cfg.get("enable_thinking", llm_cfg.get("enable_thinking", False)),
    )
