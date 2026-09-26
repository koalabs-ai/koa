"""Per-provider secret files for the built-in agent's LLM keys.

Same discipline as the pairing token (``koa_core.config.write_token_file``):
``KOA_HOME/10_personal/secrets/<provider>.env``, dir 0700, file 0600,
created with ``os.open`` so it is never briefly world-readable. One line,
``ENV_VAR=value``. Keys never go in ``koa.toml`` or in any log; an
environment variable always wins over the file so a shell session (or a
container secret) can override without touching disk.
"""
from __future__ import annotations

import os
from pathlib import Path

# Which environment variable overrides the file, per ``[llm] provider``.
ENV_VAR_FOR_PROVIDER = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai-compatible": "OPENAI_API_KEY",
}


def secrets_path(home: Path, provider: str) -> Path:
    return Path(home) / "10_personal" / "secrets" / f"{provider}.env"


def write_key(path: Path, env_var: str, value: str, host: str = "") -> None:
    """Writes ``ENV_VAR=value`` to ``path`` with permissions 0600 (dir 0700).
    ``host``: the only host this key may be sent to (OpenAI-compatible keys)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    # Nace 0600: write_text + chmod dejaría el archivo legible un instante.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(f"{env_var}={value.strip()}\n")
        if host:
            fh.write(f"KOA_LLM_KEY_HOST={host}\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def read_key(path: Path, env_var: str) -> str:
    """Reads ``ENV_VAR=value`` out of ``path``. Empty string if missing."""
    if not env_var:
        return ""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == env_var:
            return val.strip()
    return ""


def resolve_api_key(home: Path, provider: str) -> str:
    """Env var (``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``) > secrets file.
    Ollama and other keyless OpenAI-compatible servers simply have neither."""
    env_var = ENV_VAR_FOR_PROVIDER.get(provider, "")
    if env_var:
        env_val = os.environ.get(env_var, "")
        if env_val:
            return env_val
    return read_key(secrets_path(home, provider), env_var)


OPENAI_HOST = "api.openai.com"


def resolve_openai_compatible_key(home: Path, base_url: str) -> str:
    """A key only ever goes to the host it was entered for.

    An ambient ``OPENAI_API_KEY`` is a key for OpenAI: sending it to Ollama,
    OpenRouter or any other server configured here would hand it to a third
    party. So the env var applies only when the endpoint is api.openai.com,
    ``KOA_LLM_API_KEY`` is the explicit override for other hosts, and a saved
    key is used only if its ``KOA_LLM_KEY_HOST`` matches the configured host.
    """
    from urllib.parse import urlparse

    host = (urlparse(base_url or "").hostname or "").lower()
    if not host:
        return ""
    explicit = os.environ.get("KOA_LLM_API_KEY", "")
    if explicit:
        return explicit
    if host == OPENAI_HOST and os.environ.get("OPENAI_API_KEY", ""):
        return os.environ["OPENAI_API_KEY"]
    path = secrets_path(home, "openai-compatible")
    stored_host = read_key(path, "KOA_LLM_KEY_HOST").lower()
    if stored_host != host:
        return ""
    return read_key(path, "OPENAI_API_KEY")
