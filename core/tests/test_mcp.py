import io
import json

from koa_core import config as configmod
from koa_core import mcp as mcpmod


def _send(cfg, requests):
    inp = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
    out = io.StringIO()
    mcpmod.run_stdio(cfg, in_stream=inp, out_stream=out)
    lines = [l for l in out.getvalue().splitlines() if l]
    return [json.loads(l) for l in lines]


def test_initialize_echoes_known_protocol(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    [resp] = _send(cfg, [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2025-03-26"}}])
    assert resp["result"]["protocolVersion"] == "2025-03-26"
    assert resp["result"]["serverInfo"]["name"] == "koa-core"


def test_initialize_unknown_protocol_falls_back(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    [resp] = _send(cfg, [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "1999-01-01"}}])
    assert resp["result"]["protocolVersion"] == mcpmod.DEFAULT_PROTOCOL


def test_notifications_initialized_has_no_response(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    resps = _send(cfg, [{"jsonrpc": "2.0", "method": "notifications/initialized"}])
    assert resps == []


def test_tools_list_and_call_roundtrip(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "todo_add", "arguments": {"title": "desde mcp"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "todo_list", "arguments": {}}},
    ]
    resps = _send(cfg, reqs)
    tool_names = {t["name"] for t in resps[0]["result"]["tools"]}
    assert "todo_add" in tool_names and "memory_recall" in tool_names

    added = json.loads(resps[1]["result"]["content"][0]["text"])
    assert added["title"] == "desde mcp"
    assert resps[1]["result"]["isError"] is False

    listed = json.loads(resps[2]["result"]["content"][0]["text"])
    assert any(i["title"] == "desde mcp" for i in listed)


def test_tools_call_unknown_tool_is_iserror(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    [resp] = _send(cfg, [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "no_existe", "arguments": {}}}])
    assert resp["result"]["isError"] is True


def test_ping(tmp_path):
    cfg = configmod.Config(home=tmp_path)
    [resp] = _send(cfg, [{"jsonrpc": "2.0", "id": 5, "method": "ping"}])
    assert resp["result"] == {}
