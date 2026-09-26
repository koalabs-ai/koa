from koa_core import secrets as secretsmod


def test_write_key_has_0600_permissions(tmp_path):
    path = secretsmod.secrets_path(tmp_path, "anthropic")
    secretsmod.write_key(path, "ANTHROPIC_API_KEY", "test-anthropic-key")
    assert (path.stat().st_mode & 0o777) == 0o600
    assert (path.parent.stat().st_mode & 0o777) == 0o700
    assert path.parent.name == "secrets"
    assert path.parent.parent.name == "10_personal"


def test_read_key_roundtrip(tmp_path):
    path = secretsmod.secrets_path(tmp_path, "anthropic")
    secretsmod.write_key(path, "ANTHROPIC_API_KEY", "test-anthropic-key")
    assert secretsmod.read_key(path, "ANTHROPIC_API_KEY") == "test-anthropic-key"


def test_read_key_missing_file_is_empty(tmp_path):
    path = secretsmod.secrets_path(tmp_path, "anthropic")
    assert secretsmod.read_key(path, "ANTHROPIC_API_KEY") == ""


def test_resolve_api_key_env_wins_over_file(tmp_path, monkeypatch):
    path = secretsmod.secrets_path(tmp_path, "anthropic")
    secretsmod.write_key(path, "ANTHROPIC_API_KEY", "from-file")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert secretsmod.resolve_api_key(tmp_path, "anthropic") == "from-env"


def test_resolve_api_key_falls_back_to_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    path = secretsmod.secrets_path(tmp_path, "anthropic")
    secretsmod.write_key(path, "ANTHROPIC_API_KEY", "from-file")
    assert secretsmod.resolve_api_key(tmp_path, "anthropic") == "from-file"


def test_resolve_api_key_empty_when_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert secretsmod.resolve_api_key(tmp_path, "openai-compatible") == ""


def test_resolve_api_key_unknown_provider_is_empty(tmp_path):
    assert secretsmod.resolve_api_key(tmp_path, "ollama-does-not-need-one") == ""


def test_openai_key_never_goes_to_another_host(tmp_path, monkeypatch):
    """An ambient OPENAI_API_KEY must not be sent to Ollama or a third party."""
    from koa_core import secrets as s
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-real")
    monkeypatch.delenv("KOA_LLM_API_KEY", raising=False)
    assert s.resolve_openai_compatible_key(tmp_path, "https://api.openai.com/v1") == "sk-openai-real"
    assert s.resolve_openai_compatible_key(tmp_path, "http://127.0.0.1:11434/v1") == ""
    assert s.resolve_openai_compatible_key(tmp_path, "https://openrouter.ai/api/v1") == ""


def test_saved_key_is_bound_to_its_host(tmp_path, monkeypatch):
    from koa_core import secrets as s
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("KOA_LLM_API_KEY", raising=False)
    s.write_key(s.secrets_path(tmp_path, "openai-compatible"), "OPENAI_API_KEY", "k-router", host="openrouter.ai")
    assert s.resolve_openai_compatible_key(tmp_path, "https://openrouter.ai/api/v1") == "k-router"
    assert s.resolve_openai_compatible_key(tmp_path, "https://evil.example.com/v1") == ""
    monkeypatch.setenv("KOA_LLM_API_KEY", "explicit")
    assert s.resolve_openai_compatible_key(tmp_path, "https://evil.example.com/v1") == "explicit"
