import json
import os

import pytest

from koa_core import cli
from koa_core import devices as devicesmod


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "koa"
    h.mkdir()
    monkeypatch.setenv("KOA_HOME", str(h))
    monkeypatch.delenv("KOA_TOKEN", raising=False)
    monkeypatch.delenv("KOA_HOST", raising=False)
    monkeypatch.delenv("KOA_PORT", raising=False)
    return h


def run(argv):
    return cli.main(argv)


def test_version(capsys):
    assert run(["version"]) == 0
    assert capsys.readouterr().out.strip() != ""


def test_todo_add_list_done(home, capsys):
    assert run(["todo", "add", "Probar la cli", "--tag", "bug", "--json"]) == 0
    out = capsys.readouterr().out
    item = json.loads(out)
    assert item["title"] == "Probar la cli"

    assert run(["todo", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1

    assert run(["todo", "done", item["id"], "--evidence", "lo revise"]) == 0
    capsys.readouterr()
    rows = json.loads(run_and_capture(["todo", "list", "--status", "done", "--json"], capsys))
    assert rows[0]["status"] == "done"


def run_and_capture(argv, capsys):
    run(argv)
    return capsys.readouterr().out


def test_mem_add_and_recall(home, capsys):
    assert run([
        "mem", "add", "--type", "user", "--name", "mi-perfil",
        "--description", "quien soy", "--body", "trabajo con agentes", "--json",
    ]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert (home / "06_data" / "memory" / "user-mi-perfil.md").exists()
    assert entry["name"] == "mi-perfil"

    run(["mem", "recall", "agentes", "--json"])
    hits = json.loads(capsys.readouterr().out)
    assert len(hits) == 1


def test_claim_conflict_exit_code(home):
    os.environ["KOA_AGENT"] = "agent-a"
    assert run(["claim", "acquire", "ruta/x", "--intent", "trabajar"]) == 0
    os.environ["KOA_AGENT"] = "agent-b"
    assert run(["claim", "acquire", "ruta/x"]) == 9
    del os.environ["KOA_AGENT"]


def test_log_and_heartbeat(home, capsys):
    assert run(["log", "paso algo", "--kind", "deploy"]) == 0
    assert run(["heartbeat"]) == 0


def test_doctor_json_has_checks(home, capsys):
    run(["doctor", "--json"])
    checks = json.loads(capsys.readouterr().out)
    names = {c["check"] for c in checks}
    assert {"python", "koa_home", "db", "puerto"} <= names


def test_names_scan_on_home(home, capsys):
    assert run(["names", "--scan", "--path", str(home), "--json"]) == 0


def test_token_rotate_writes_file_and_never_prints_token(home, capsys):
    assert run(["token", "rotate"]) == 0
    out = capsys.readouterr().out
    token_path = home / "10_personal" / "secrets" / "koa-core.token"
    assert token_path.exists()
    token = token_path.read_text().strip()
    assert token not in out
    assert (token_path.stat().st_mode & 0o777) == 0o600


def test_token_rotate_show_prints_token(home, capsys):
    assert run(["token", "rotate", "--show"]) == 0
    out = capsys.readouterr().out
    token_path = home / "10_personal" / "secrets" / "koa-core.token"
    token = token_path.read_text().strip()
    assert token in out


def test_token_rotate_empties_toml_token(home, capsys):
    (home / "koa.toml").write_text('[api]\nhost = "127.0.0.1"\ntoken = "viejo"\n[db]\npath = "x"\n')
    assert run(["token", "rotate"]) == 0
    text = (home / "koa.toml").read_text()
    assert "viejo" not in text
    assert 'token = ""' in text


def test_pair_prints_code_and_url(home, capsys):
    assert run(["pair"]) == 0
    out = capsys.readouterr().out
    assert "/pair#code=" in out
    assert "expires" in out


def test_pair_json_output(home, capsys):
    assert run(["pair", "--json"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert set(body) == {"code", "expires_at", "pair_url"}
    assert body["pair_url"].endswith(f"/pair#code={body['code']}")


def test_devices_list_and_revoke(home, capsys):
    from koa_core import config as configmod
    from koa_core import db as dbmod

    cfg = configmod.load_config(home)
    conn = dbmod.connect(cfg.db_path)
    code, _ = devicesmod.start_pairing(conn)
    device_id, _ = devicesmod.claim(conn, code, "un telefono")
    conn.close()

    assert run(["devices", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1 and rows[0]["id"] == device_id

    assert run(["devices", "revoke", device_id]) == 0
    capsys.readouterr()
    assert run(["devices", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["revoked_at"] is not None


def test_doctor_reports_token_and_dispositivos_checks(home, capsys):
    run(["doctor", "--json"])
    checks = json.loads(capsys.readouterr().out)
    names = {c["check"] for c in checks}
    assert {"token", "dispositivos"} <= names


def test_llm_status_none_when_unconfigured(home, capsys):
    assert run(["llm", "status", "--json"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body == {"provider": "", "model": "", "base_url": "", "key_present": False}


def test_llm_setup_ollama_writes_config_without_a_secrets_file(home, capsys):
    # --base-url apunta a un puerto cerrado: la llamada de prueba final falla
    # (localizada) sin depender de si esta maquina tiene Ollama corriendo.
    # Lo que importa aqui es que koa.toml SI quedo escrito y que no se creo
    # ningun archivo de secretos (Ollama no necesita llave).
    assert run([
        "llm", "setup", "--provider", "ollama", "--model", "qwen2.5:3b",
        "--base-url", "http://127.0.0.1:1", "--yes",
    ]) != 0
    capsys.readouterr()
    assert run(["llm", "status", "--json"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["provider"] == "openai-compatible"
    assert body["model"] == "qwen2.5:3b"
    assert body["key_present"] is False
    assert not (home / "10_personal" / "secrets" / "openai-compatible.env").exists()


def test_llm_setup_needs_provider_without_yes_in_scripts(home, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(EOFError()))
    assert run(["llm", "setup", "--yes"]) == 1


def test_chat_uses_llm_error_when_not_configured(home, capsys):
    assert run(["chat", "-m", "hola"]) == 1
    err = capsys.readouterr().err
    assert "koa-core llm setup" in err


def test_chat_list_empty(home, capsys):
    assert run(["chat", "--list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_ensure_anthropic_sdk_skips_when_already_available(monkeypatch):
    from koa_core import cli as climod
    from koa_core.llm import anthropic_provider

    monkeypatch.setattr(anthropic_provider, "available", lambda: True)
    assert climod._ensure_anthropic_sdk("en") is True


def test_ensure_anthropic_sdk_reports_missing_venv_module(monkeypatch, capsys):
    from koa_core import cli as climod
    from koa_core.llm import anthropic_provider

    monkeypatch.setattr(anthropic_provider, "available", lambda: False)

    class _Fail:
        returncode = 1
        stderr = "The virtual environment was not created successfully because ensurepip is not available"

    monkeypatch.setattr(climod.subprocess, "run", lambda *a, **k: _Fail())
    assert climod._ensure_anthropic_sdk("en") is False
    assert "python3-venv" in capsys.readouterr().err


def test_ensure_anthropic_sdk_installs_and_asks_to_rerun_without_reexec(tmp_path, monkeypatch, capsys):
    from koa_core import cli as climod
    from koa_core.llm import anthropic_provider

    monkeypatch.setattr(anthropic_provider, "available", lambda: False)
    monkeypatch.setenv("KOA_LLM_NO_REEXEC", "1")

    class _Ok:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(climod.subprocess, "run", lambda *a, **k: _Ok())
    monkeypatch.setattr(climod, "__file__", str(tmp_path / "share" / "koa-core" / "koa_core" / "cli.py"))
    assert climod._ensure_anthropic_sdk("en") is False
    out = capsys.readouterr().out
    assert "run `koa-core llm setup` again" in out


def test_doctor_warns_when_core_hookspath_hides_the_hook(tmp_path, monkeypatch):
    """Con core.hooksPath (p. ej. global) git ignora .git/hooks: doctor debe decirlo."""
    import subprocess as sp
    from koa_core import cli as climod

    home = tmp_path / "k"
    home.mkdir()
    sp.run(["git", "init", "-q", str(home)], check=True)
    sp.run(["git", "-C", str(home), "config", "core.hooksPath", str(tmp_path / "otros-hooks")], check=True)
    assert climod._hooks_path_override(home) == str(tmp_path / "otros-hooks")
    sp.run(["git", "-C", str(home), "config", "core.hooksPath", ".git/hooks"], check=True)
    assert climod._hooks_path_override(home) is None
