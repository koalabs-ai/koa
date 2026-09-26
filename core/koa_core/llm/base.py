"""Shared contract for LLM providers.

``Turn`` is what every provider's ``chat()`` returns; ``Provider`` is the
interface both :mod:`koa_core.llm.anthropic_provider` and
:mod:`koa_core.llm.openai_compatible` implement. Errors are
:class:`koa_core.i18n.LocalizedError` so callers (CLI, HTTP API, the agent
loop) show them in the active language without each provider knowing which
one that is.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from koa_core.i18n import LocalizedError


@dataclass
class Turn:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # [{"id","name","input"}]
    stop_reason: str = "end_turn"
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw_assistant: Any = None  # appended to history verbatim, provider-native shape
    error: LocalizedError | None = None


class Provider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict], system: str) -> Turn: ...

    def format_tools(self, specs: dict) -> list[dict]: ...

    def tool_result_messages(self, results: list[dict]) -> list[dict]: ...


class ProviderUnavailable(LocalizedError):
    """Nothing usable is configured: no provider chosen, the SDK isn't
    importable, or there's no key. Never raised for a mid-conversation
    provider error (that's :class:`Turn.error` instead)."""
