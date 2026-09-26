"""Anthropic provider: the official ``anthropic`` Python SDK, never raw HTTP
and never an OpenAI-compatible shim. Importing this module must never fail
even if the SDK isn't installed — only building a provider does.
"""
from __future__ import annotations

from koa_core.i18n import LocalizedError
from koa_core.llm.base import ProviderUnavailable, Turn

try:
    import anthropic
except Exception:  # pragma: no cover - exercised by test_llm_anthropic's skip
    anthropic = None

DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000
# Only these two models get the server-side-fallback beta + `fallbacks`;
# every other model omits both, per the spec's exact request shape.
FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5-1")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def available() -> bool:
    return anthropic is not None


def _block_to_dict(block) -> dict:
    """Content blocks come back as SDK (pydantic) objects; store them as
    plain dicts so a conversation can be persisted to sqlite and fed back
    into a later ``messages.create`` call unchanged."""
    if isinstance(block, dict):
        return block
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_none=True)
    return dict(block)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base_url: str | None = None):
        if anthropic is None:
            raise ProviderUnavailable("llm.error.sdk_missing")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)
        self.model = model

    def format_tools(self, specs: dict) -> list[dict]:
        return [
            {"name": name, "description": spec["description"], "input_schema": spec["schema"]}
            for name, spec in specs.items()
        ]

    def tool_result_messages(self, results: list[dict]) -> list[dict]:
        # Anthropic wants every tool_result for a turn in ONE user message.
        blocks = [
            {
                "type": "tool_result", "tool_use_id": r["id"],
                "content": r["content"], "is_error": bool(r.get("is_error", False)),
            }
            for r in results
        ]
        return [{"role": "user", "content": blocks}]

    def chat(self, messages: list[dict], tools: list[dict], system: str) -> Turn:
        kwargs = dict(
            model=self.model, max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=system, tools=tools, messages=messages,
        )
        if self.model in FALLBACK_MODELS:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        try:
            response = self._client.beta.messages.create(**kwargs)
        # Most specific first: an AuthenticationError/PermissionDeniedError/
        # NotFoundError/RateLimitError are also APIStatusError subclasses.
        except anthropic.AuthenticationError:
            return _error_turn("llm.error.auth")
        except anthropic.PermissionDeniedError:
            return _error_turn("llm.error.permission")
        except anthropic.NotFoundError:
            return _error_turn("llm.error.not_found")
        except anthropic.RateLimitError:
            return _error_turn("llm.error.rate_limit")
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                return _error_turn("llm.error.server")
            return _error_turn("llm.error.unexpected", detail=str(e))
        except anthropic.APIConnectionError:
            return _error_turn("llm.error.connection")
        return _turn_from_response(response)


def _error_turn(key: str, **params) -> Turn:
    return Turn(error=LocalizedError(key, **params))


def _turn_from_response(response) -> Turn:
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    content = [_block_to_dict(b) for b in response.content]
    for block in content:
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            # `input` is already a dict as the SDK parsed it: never
            # string-match serialized JSON.
            tool_calls.append({"id": block["id"], "name": block["name"], "input": block.get("input") or {}})
    usage = {
        "input_tokens": getattr(response.usage, "input_tokens", 0),
        "output_tokens": getattr(response.usage, "output_tokens", 0),
    }
    stop_reason = response.stop_reason
    error = None
    if stop_reason == "refusal":
        stop_details = getattr(response, "stop_details", None)
        category = getattr(stop_details, "category", None) if stop_details else None
        error = LocalizedError("llm.error.refusal", category=category or "")
    return Turn(
        text="\n".join(p for p in text_parts if p), tool_calls=tool_calls,
        stop_reason=stop_reason, usage=usage,
        raw_assistant={"role": "assistant", "content": content}, error=error,
    )
