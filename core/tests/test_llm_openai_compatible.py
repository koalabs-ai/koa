"""OpenAI-compatible provider tests: stdlib http.server as the fake
backend (this path uses only ``urllib``, no SDK, no real network)."""
import http.server
import json
import threading

import pytest

from koa_core.llm.openai_compatible import OpenAICompatibleProvider


class _FakeHandler(http.server.BaseHTTPRequestHandler):
    responder = None
    captured: list = []

    def log_message(self, *a):
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
    yield server, f"http://127.0.0.1:{port}/v1"
    server.shutdown()


def _completion(message, finish_reason="stop", usage=None):
    return {
        "id": "chatcmpl-test", "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": usage or {"prompt_tokens": 7, "completion_tokens": 3},
    }


def test_text_answer(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (
        200, _completion({"role": "assistant", "content": "hola"}),
    )
    provider = OpenAICompatibleProvider(base_url=base_url, model="test-model")
    turn = provider.chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is None
    assert turn.text == "hola"
    assert turn.tool_calls == []
    assert turn.usage == {"input_tokens": 7, "output_tokens": 3}
    req = _FakeHandler.captured[-1]
    assert req["path"] == "/v1/chat/completions"
    assert req["body"]["messages"][0] == {"role": "system", "content": "system"}


def test_tool_calls_round_trip(fake_server):
    _, base_url = fake_server
    responses = [
        _completion({
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "call_1", "type": "function",
                             "function": {"name": "todo_add", "arguments": '{"title": "x"}'}}],
        }, finish_reason="tool_calls"),
        _completion({"role": "assistant", "content": "listo"}),
    ]

    def responder(body, headers):
        return 200, responses.pop(0)

    _FakeHandler.responder = responder
    provider = OpenAICompatibleProvider(base_url=base_url, model="test-model", api_key="k")
    tools = provider.format_tools({"todo_add": {"description": "d", "schema": {"type": "object", "properties": {}}}})
    history = [{"role": "user", "content": "add x"}]
    turn = provider.chat(history, tools, "system")
    assert turn.tool_calls == [{"id": "call_1", "name": "todo_add", "input": {"title": "x"}}]
    history.append(turn.raw_assistant)

    tool_msgs = provider.tool_result_messages([{"id": "call_1", "content": "{}", "is_error": False}])
    assert tool_msgs == [{"role": "tool", "tool_call_id": "call_1", "content": "{}"}]
    history.extend(tool_msgs)

    turn2 = provider.chat(history, tools, "system")
    assert turn2.text == "listo"
    sent = _FakeHandler.captured[-1]["body"]["messages"][-1]
    assert sent == {"role": "tool", "tool_call_id": "call_1", "content": "{}"}
    # la llave se manda como Bearer, nunca en el cuerpo
    assert _FakeHandler.captured[-1]["headers"].get("Authorization") == "Bearer k"


def test_http_error_maps_to_localized_error(fake_server):
    _, base_url = fake_server
    _FakeHandler.responder = lambda body, headers: (401, {"error": "nope"})
    provider = OpenAICompatibleProvider(base_url=base_url, model="test-model")
    turn = provider.chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is not None
    assert turn.error.key == "llm.error.auth"


def test_connection_error_when_nothing_is_listening():
    provider = OpenAICompatibleProvider(base_url="http://127.0.0.1:1", model="m")
    turn = provider.chat([{"role": "user", "content": "hi"}], [], "system")
    assert turn.error is not None
    assert turn.error.key == "llm.error.connection"
