"""LLM providers for the built-in agent. Importing this package (and its
submodules) must never fail even when no provider SDK is installed — only
*building* a provider via :func:`for_config` does, and it always fails with
a localized :class:`ProviderUnavailable` instead of crashing.
"""
from __future__ import annotations

from koa_core.llm.base import Provider, ProviderUnavailable, Turn

__all__ = ["Provider", "ProviderUnavailable", "Turn", "for_config"]


def for_config(cfg) -> Provider:
    """Builds the provider configured in ``koa.toml``'s ``[llm]`` section,
    reading its key from the environment or the secrets file. Raises
    :class:`ProviderUnavailable` (a localized error, never a bare
    exception) if nothing usable is configured."""
    from koa_core import secrets as secretsmod

    provider = cfg.llm_provider
    if not provider:
        raise ProviderUnavailable("llm.error.not_configured")

    if provider == "anthropic":
        from koa_core.llm import anthropic_provider

        if not anthropic_provider.available():
            raise ProviderUnavailable("llm.error.sdk_missing")
        key = secretsmod.resolve_api_key(cfg.home, "anthropic")
        if not key:
            raise ProviderUnavailable("llm.error.key_missing", provider="Anthropic", env="ANTHROPIC_API_KEY")
        return anthropic_provider.AnthropicProvider(key, model=cfg.llm_model or anthropic_provider.DEFAULT_MODEL)

    if provider == "openai-compatible":
        from koa_core.llm import openai_compatible

        if not cfg.llm_model:
            raise ProviderUnavailable("llm.error.model_missing")
        base_url = cfg.llm_base_url or openai_compatible.DEFAULT_BASE_URL
        key = secretsmod.resolve_openai_compatible_key(cfg.home, base_url)
        return openai_compatible.OpenAICompatibleProvider(
            base_url=base_url,
            model=cfg.llm_model, api_key=key,
        )

    raise ProviderUnavailable("llm.error.unknown_provider", provider=provider)
