"""Anthropic provider tests: the real SDK against a local fake server (no
network, no real API call — never the owner's money). Skipped with a clear
reason when `anthropic` isn't importable; see AGENTS.md for how to get a
throwaway venv with it installed.
"""
import json
import threading

import pytest

anthropic = pytest.importorskip(
    "anthropic", reason="anthropic SDK not installed (create a throwaway venv: "
    "python3 -m venv /tmp/v && /tmp/v/bin/pip install anthropic pytest, then run "
    "pytest with /tmp/v/bin/python3 -m pytest)",
)

import http.server

from koa_core.llm import anthropic_provider


class _FakeHandler(http.server.BaseHTTPRequestHandler):
    # set per-test via _make_server(): a callable(body: dict, headers) -> (status, body)
    responder = None
    captured: list = []

    def log_message(self, *a):  # silencio en la salida de pytest
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).captured.append({"path": self.path, "body": body, "headers": dict(self.headers)})
        status, payload = type(self).responder(body, self.headers)
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakeHandler)
    _FakeHandler.captured = []
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    port = server.server_address[1]
    yield server, f"http://127.0.0.1:{port}"
    server.shutdown()


def _message(content, stop_reason="end_turn", stop_details=None, usage=None):
    body = {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5",
        "content": content, "stop_reason": stop_reason,
        "usage": usage or {"input_tokens": 10, "output_tokens": 5},
    }
    if stop_details:
        body["stop_details"] = stop_details
    return body


def _provider(base_url):
    return anthropic_provider.AnthropicProvider("test-key", model="claude-opus-5", base_url=base_url)


def test_text_answer(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (200, _message([{"type": "text", "text": "hola"}]))
    turn = _provider(base_url).chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is None
    assert turn.text == "hola"
    assert turn.tool_calls == []
    assert turn.stop_reason == "end_turn"
    assert turn.usage == {"input_tokens": 10, "output_tokens": 5}
    assert turn.raw_assistant == {"role": "assistant", "content": [{"type": "text", "text": "hola"}]}


def test_tool_use_then_tool_result_in_one_user_message(fake_server):
    _, base_url = fake_server
    responses = [
        _message([{"type": "tool_use", "id": "call_1", "name": "todo_add", "input": {"title": "x"}}],
                 stop_reason="tool_use"),
        _message([{"type": "text", "text": "listo"}]),
    ]

    def responder(body, headers):
        return 200, responses.pop(0)

    _FakeHandler.responder = responder
    provider = _provider(base_url)
    history = [{"role": "user", "content": "add x"}]
    turn = provider.chat(history, [{"name": "todo_add", "description": "d", "input_schema": {}}], "system")
    assert turn.tool_calls == [{"id": "call_1", "name": "todo_add", "input": {"title": "x"}}]
    history.append(turn.raw_assistant)

    tool_msgs = provider.tool_result_messages([{"id": "call_1", "content": "{}", "is_error": False}])
    assert len(tool_msgs) == 1  # UN solo mensaje de usuario con los tool_result
    assert tool_msgs[0]["role"] == "user"
    assert tool_msgs[0]["content"] == [
        {"type": "tool_result", "tool_use_id": "call_1", "content": "{}", "is_error": False}
    ]
    history.extend(tool_msgs)

    turn2 = provider.chat(history, [], "system")
    assert turn2.text == "listo"
    # el segundo request llevo el tool_result en un solo mensaje de usuario
    sent = _FakeHandler.captured[-1]["body"]["messages"][-1]
    assert sent["role"] == "user"
    assert sent["content"][0]["type"] == "tool_result"


def test_refusal_stop_reason(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (
        200, _message([], stop_reason="refusal", stop_details={"type": "refusal", "category": "cyber"}),
    )
    turn = _provider(base_url).chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is not None
    assert turn.error.key == "llm.error.refusal"
    assert turn.error.render("en")  # no revienta al formatear


def test_401_maps_to_localized_auth_error(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (
        401, {"type": "error", "error": {"type": "authentication_error", "message": "bad key"}},
    )
    turn = _provider(base_url).chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is not None
    assert turn.error.key == "llm.error.auth"


def test_fallbacks_and_beta_header_only_for_fallback_models(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (200, _message([{"type": "text", "text": "ok"}]))

    _provider(base_url).chat([{"role": "user", "content": "hi"}], [], "system")
    req = _FakeHandler.captured[-1]
    assert req["body"].get("fallbacks") == "default"
    assert "anthropic-beta" in req["headers"]
    assert anthropic_provider.FALLBACK_BETA in req["headers"]["anthropic-beta"]

    other = anthropic_provider.AnthropicProvider("test-key", model="claude-haiku-not-a-fallback-model", base_url=base_url)
    other.chat([{"role": "user", "content": "hi"}], [], "system")
    req2 = _FakeHandler.captured[-1]
    assert "fallbacks" not in req2["body"]
    assert "anthropic-beta" not in req2["headers"]
