"""Agent loop tests: a fake Provider double (no network, no provider SDK)
drives koa_core.agent.send_message the way koa_core.llm.for_config would.
"""
import json

import pytest

from koa_core import agent as agentmod
from koa_core import config as configmod
from koa_core.llm.base import Turn


def _cfg(tmp_path):
    # db_path matches the `conn` fixture (conftest.py) so ToolBox's own
    # connection and the test's assertions hit the same sqlite file.
    home = tmp_path / "koa"
    (home / "06_data" / "memory").mkdir(parents=True)
    (home / "04_llm").mkdir(parents=True)
    return configmod.Config(
        home=home, db_path=tmp_path / "koa-core.sqlite", llm_provider="fake", llm_model="fake-model",
    )


class _EchoProvider:
    """Answers once, no tool calls: end_turn immediately."""
    name = "fake"
    model = "fake-model"

    def __init__(self, reply="ok"):
        self.reply = reply
        self.calls = []

    def format_tools(self, specs):
        return list(specs)

    def tool_result_messages(self, results):
        return [{"role": "user", "content": [{"tool_result": r["id"]} for r in results]}]

    def chat(self, messages, tools, system):
        self.calls.append({"messages": [dict(m) for m in messages], "system": system})
        return Turn(
            text=self.reply, tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 3, "output_tokens": 2},
            raw_assistant={"role": "assistant", "content": self.reply},
        )


class _OneToolCallProvider:
    """Calls todo_add once, then answers with no more tool calls."""
    name = "fake"
    model = "fake-model"

    def format_tools(self, specs):
        return list(specs)

    def tool_result_messages(self, results):
        return [{"role": "tool", "tool_call_id": r["id"], "content": r["content"]} for r in results]

    def chat(self, messages, tools, system):
        # segunda vuelta: ya hay un tool_result en el historial
        if any(m.get("role") == "tool" for m in messages):
            return Turn(text="hecho", tool_calls=[], stop_reason="end_turn",
                        usage={"input_tokens": 1, "output_tokens": 1},
                        raw_assistant={"role": "assistant", "content": "hecho"})
        return Turn(
            text="", tool_calls=[{"id": "c1", "name": "todo_add", "input": {"title": "comprar cafe"}}],
            stop_reason="tool_use", usage={"input_tokens": 1, "output_tokens": 1},
            raw_assistant={"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "todo_add", "arguments": "{}"}}
            ]},
        )


class _AlwaysToolCallProvider:
    """Never stops on its own: exercises the iteration cap."""
    name = "fake"
    model = "fake-model"

    def __init__(self):
        self.calls = 0

    def format_tools(self, specs):
        return list(specs)

    def tool_result_messages(self, results):
        return [{"role": "user", "content": [{"tool_result": r["id"]} for r in results]}]

    def chat(self, messages, tools, system):
        self.calls += 1
        cid = f"c{self.calls}"
        return Turn(
            text="", tool_calls=[{"id": cid, "name": "context", "input": {}}],
            stop_reason="tool_use", usage={"input_tokens": 1, "output_tokens": 1},
            raw_assistant={"role": "assistant", "content": [{"type": "tool_use", "id": cid, "name": "context", "input": {}}]},
        )


@pytest.fixture(autouse=True)
def _default_lang_env(monkeypatch):
    for var in ("KOA_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)


def test_send_message_creates_conversation_and_persists(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    provider = _EchoProvider("hola, como estas")
    monkeypatch.setattr(agentmod, "for_config", lambda c: provider)

    result = agentmod.send_message(cfg, conn, None, "hola")
    assert result["reply"] == "hola, como estas"
    assert result["usage"] == {"input_tokens": 3, "output_tokens": 2}
    assert result["tool_calls"] == []

    conv = agentmod.get_conversation(conn, result["conversation_id"])
    assert conv["provider"] == "fake" and conv["model"] == "fake-model"
    assert conv["input_tokens"] == 3 and conv["output_tokens"] == 2

    history = agentmod._load_history(conn, result["conversation_id"])
    assert history == [{"role": "user", "content": "hola"}, {"role": "assistant", "content": "hola, como estas"}]


def test_conversation_continues_with_full_history(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    provider = _EchoProvider("respuesta")
    monkeypatch.setattr(agentmod, "for_config", lambda c: provider)

    first = agentmod.send_message(cfg, conn, None, "primero")
    second = agentmod.send_message(cfg, conn, first["conversation_id"], "segundo")
    assert second["conversation_id"] == first["conversation_id"]

    # el segundo chat() vio los 3 mensajes previos + el nuevo user
    assert len(provider.calls[-1]["messages"]) == 3
    conv = agentmod.get_conversation(conn, first["conversation_id"])
    assert conv["input_tokens"] == 6 and conv["output_tokens"] == 4  # sumado, no reemplazado


def test_tool_call_executes_and_is_visible_in_koa(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(agentmod, "for_config", lambda c: _OneToolCallProvider())

    result = agentmod.send_message(cfg, conn, None, "agrega comprar cafe")
    assert result["reply"] == "hecho"
    assert result["tool_calls"] == [{"name": "todo_add", "ok": True}]

    from koa_core import items as itemsmod
    items = itemsmod.list_items(conn)
    assert any(i["title"] == "comprar cafe" for i in items)


def test_tool_call_is_logged_to_activity_without_leaking_secrets(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(agentmod, "for_config", lambda c: _OneToolCallProvider())
    secret = "test-anthropic-key-totally-secret"
    (tmp_path / "koa" / "10_personal" / "secrets").mkdir(parents=True)
    (tmp_path / "koa" / "10_personal" / "secrets" / "anthropic.env").write_text(f"ANTHROPIC_API_KEY={secret}\n")

    agentmod.send_message(cfg, conn, None, "agrega comprar cafe")

    rows = [dict(r) for r in conn.execute("SELECT * FROM activity WHERE kind='agent_tool'")]
    assert len(rows) == 1
    assert rows[0]["text"].startswith("todo_add ")
    assert secret not in json.dumps(rows)
    log_bytes = cfg.activity_log_path.read_bytes()
    assert secret.encode() not in log_bytes
    db_bytes = cfg.db_path.read_bytes()
    assert secret.encode() not in db_bytes


def test_iteration_cap_stops_the_loop(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    provider = _AlwaysToolCallProvider()
    monkeypatch.setattr(agentmod, "for_config", lambda c: provider)

    result = agentmod.send_message(cfg, conn, None, "nunca pares")
    assert provider.calls == agentmod.MAX_TOOL_ITERATIONS + 1
    assert str(agentmod.MAX_TOOL_ITERATIONS) in result["reply"]
    assert len(result["tool_calls"]) == agentmod.MAX_TOOL_ITERATIONS


def test_send_message_to_missing_conversation_is_localized_error(tmp_path, conn, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(agentmod, "for_config", lambda c: _EchoProvider())
    from koa_core import i18n
    with pytest.raises(i18n.LocalizedError):
        agentmod.send_message(cfg, conn, "no-existe", "hola")


def test_provider_unavailable_propagates(tmp_path, conn, monkeypatch):
    from koa_core.llm import ProviderUnavailable

    cfg = _cfg(tmp_path)

    def _raise(c):
        raise ProviderUnavailable("llm.error.not_configured")

    monkeypatch.setattr(agentmod, "for_config", _raise)
    with pytest.raises(ProviderUnavailable):
        agentmod.send_message(cfg, conn, None, "hola")
    # no debe haber creado una conversacion a medias
    assert agentmod.list_conversations(conn) == []
