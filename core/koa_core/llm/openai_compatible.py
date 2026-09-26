"""Generic OpenAI-compatible provider: OpenAI itself, Ollama, LM Studio,
OpenRouter, anything speaking ``/v1/chat/completions`` with function
calling. stdlib ``urllib`` only — no SDK, no dependency. Never used for
Anthropic models; that path always goes through the real SDK instead.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from koa_core.i18n import LocalizedError
from koa_core.llm.base import Turn

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"  # Ollama: local, no key needed
TIMEOUT_S = 300  # local CPU inference (Ollama) can be slow to load/answer


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model
        self.api_key = api_key

    def format_tools(self, specs: dict) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {"name": name, "description": spec["description"], "parameters": spec["schema"]},
            }
            for name, spec in specs.items()
        ]

    def tool_result_messages(self, results: list[dict]) -> list[dict]:
        # OpenAI's shape: one "tool" role message per call, in order (no
        # combined message like Anthropic's).
        return [{"role": "tool", "tool_call_id": r["id"], "content": r["content"]} for r in results]

    def chat(self, messages: list[dict], tools: list[dict], system: str) -> Turn:
        body = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages]}
        if tools:
            body["tools"] = tools
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"), headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = _read_error_body(e)
            by_status = {401: "llm.error.auth", 403: "llm.error.permission",
                         404: "llm.error.not_found", 429: "llm.error.rate_limit"}
            if e.code in by_status:
                return _error_turn(by_status[e.code])
            if e.code >= 500:
                return _error_turn("llm.error.server")
            return _error_turn("llm.error.http", status=e.code, detail=detail)
        except TimeoutError:
            return _error_turn("llm.error.timeout")
        except urllib.error.URLError:
            return _error_turn("llm.error.connection")
        return _turn_from_payload(payload)


def _read_error_body(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:300]
    except Exception:
        return ""


def _error_turn(key: str, **params) -> Turn:
    return Turn(error=LocalizedError(key, **params))


def _turn_from_payload(payload: dict) -> Turn:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    tool_calls = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        try:
            # Unlike Anthropic, arguments come back as a JSON *string*.
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({"id": call.get("id", ""), "name": fn.get("name", ""), "input": args})
    usage = payload.get("usage") or {}
    finish_reason = choice.get("finish_reason") or "stop"
    stop_reason = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use"}.get(
        finish_reason, finish_reason
    )
    raw_assistant = {"role": "assistant", "content": text}
    if message.get("tool_calls"):
        raw_assistant["tool_calls"] = message["tool_calls"]
    return Turn(
        text=text, tool_calls=tool_calls, stop_reason=stop_reason,
        raw_assistant=raw_assistant,
        usage={
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    )
