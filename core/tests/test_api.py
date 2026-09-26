import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from koa_core import api as apimod
from koa_core import config as configmod
from koa_core import devices as devicesmod


@pytest.fixture(autouse=True)
def _clean_brute_force():
    devicesmod._reset_failures_for_tests()
    yield
    devicesmod._reset_failures_for_tests()


def _request(url, method="GET", body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


@pytest.fixture
def server(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="127.0.0.1", port=0)
    srv = apimod.make_server(cfg)
    cfg.port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    yield cfg
    srv.shutdown()



def _local_pair(cfg, admin=False):
    """Código creado como lo hace `koa-core pair`: directo en la BD (dueño local).
    Por HTTP, en modo abierto, /v1/pair/start responde 403 a propósito."""
    from koa_core import db as dbmod, devices as dv
    conn = dbmod.connect(cfg.db_path)
    try:
        dbmod.migrate(conn)
        code, expires_at = dv.start_pairing(conn, admin=admin)
    finally:
        conn.close()
    return 201, {"code": code, "expires_at": expires_at}


def base(cfg):
    return f"http://{cfg.host}:{cfg.port}"


def test_health(server):
    status, body = _request(base(server) + "/v1/health")
    assert status == 200 and body["ok"] is True


def test_items_crud(server):
    status, item = _request(base(server) + "/v1/items", "POST", {"title": "Uno"})
    assert status == 201
    status, rows = _request(base(server) + "/v1/items?status=open")
    assert status == 200 and len(rows) == 1
    status, updated = _request(
        base(server) + f"/v1/items/{item['id']}", "PATCH",
        {"status": "done", "evidence": "listo"},
    )
    assert status == 200 and updated["status"] == "done"


def test_items_done_without_evidence_is_400(server):
    status, item = _request(base(server) + "/v1/items", "POST", {"title": "Uno"})
    status, body = _request(base(server) + f"/v1/items/{item['id']}", "PATCH", {"status": "done"})
    assert status == 400 and "error" in body


def test_memory_and_activity(server):
    status, entry = _request(
        base(server) + "/v1/memory", "POST",
        {"type": "reference", "name": "algo", "description": "d", "body": "cuerpo"},
    )
    assert status == 201
    status, hits = _request(base(server) + "/v1/memory?q=cuerpo")
    assert status == 200 and len(hits) == 1
    status, acts = _request(base(server) + "/v1/activity?limit=10")
    assert status == 200 and len(acts) >= 1  # memory_add quedo logueado


def test_claims_conflict_returns_409(server):
    status, _ = _request(base(server) + "/v1/claims", "POST", {"target": "t1", "agent": "a1"})
    assert status == 201
    status, body = _request(base(server) + "/v1/claims", "POST", {"target": "t1", "agent": "a2"})
    assert status == 409 and "holder" in body


def test_context_endpoint(server):
    status, ctx = _request(base(server) + "/v1/context")
    assert status == 200
    assert "agents_md" in ctx and "open_items_count" in ctx


def test_pair_page_served_without_token_even_if_configured(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="127.0.0.1", port=0, token="secreto")
    srv = apimod.make_server(cfg)
    cfg.port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    try:
        with urllib.request.urlopen(base(cfg) + "/pair") as resp:
            assert resp.status == 200
            assert b"<title>KOA" in resp.read()
    finally:
        srv.shutdown()


def test_ui_served_at_root(server):
    status, _ = 200, None
    with urllib.request.urlopen(base(server) + "/") as resp:
        assert resp.status == 200
        assert b"<title>KOA" in resp.read()


def test_token_required_when_set(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="127.0.0.1", port=0, token="secreto")
    srv = apimod.make_server(cfg)
    cfg.port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    try:
        status, _ = _request(base(cfg) + "/v1/health")
        assert status == 200  # health nunca pide token
        status, _ = _request(base(cfg) + "/v1/items")
        assert status == 401
        status, _ = _request(base(cfg) + "/v1/items", token="secreto")
        assert status == 200
    finally:
        srv.shutdown()


def test_refuses_non_loopback_without_token(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="0.0.0.0", port=0)
    with pytest.raises(RuntimeError):
        apimod.make_server(cfg)


def test_non_loopback_allowed_with_token(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="0.0.0.0", port=0, token="algo")
    srv = apimod.make_server(cfg)
    srv.server_close()


# ── emparejamiento ───────────────────────────────────────────────────

def test_me_is_open_when_nothing_configured(server):
    status, body = _request(base(server) + "/v1/me")
    assert status == 200 and body["kind"] == "open" and body["admin"] is True


def test_pair_start_claim_authenticate_revoke(server):
    status, started = _local_pair(server, admin=True)
    assert status == 201
    assert "-" in started["code"]

    status, admin_claimed = _request(
        base(server) + "/v1/pair/claim", "POST",
        {"code": started["code"], "name": "mi laptop admin", "platform": "linux"},
    )
    assert status == 201
    admin_token = admin_claimed["token"]
    assert admin_token.startswith("kd_")

    # antes de que hubiera dispositivos esto era abierto; ahora exige token
    status, _ = _request(base(server) + "/v1/items")
    assert status == 401
    status, _ = _request(base(server) + "/v1/items", token=admin_token)
    assert status == 200

    status, me = _request(base(server) + "/v1/me", token=admin_token)
    assert (
        status == 200 and me["kind"] == "device"
        and me["device_id"] == admin_claimed["device_id"] and me["admin"] is True
    )

    # un segundo dispositivo no-admin: el admin lo puede revocar
    status, started2 = _request(base(server) + "/v1/pair/start", "POST", {}, token=admin_token)
    assert started2["pair_url"].endswith(f"/pair#code={started2['code']}")
    status, claimed2 = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": started2["code"], "name": "otro"},
    )
    other_token = claimed2["token"]
    status, _ = _request(base(server) + "/v1/items", token=other_token)
    assert status == 200

    status, _ = _request(
        base(server) + f"/v1/devices/{claimed2['device_id']}", "DELETE", token=admin_token,
    )
    assert status == 200
    status, _ = _request(base(server) + "/v1/items", token=other_token)
    assert status == 401


def test_pair_claim_wrong_code_is_400(server):
    status, body = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": "ZZZZ-ZZZZ", "name": "x"},
    )
    assert status == 400 and "error" in body


def test_pair_claim_reused_code_is_400(server):
    _, started = _local_pair(server)
    _request(base(server) + "/v1/pair/claim", "POST", {"code": started["code"], "name": "uno"})
    status, body = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": started["code"], "name": "dos"},
    )
    assert status == 400 and "error" in body


def test_pair_claim_brute_force_returns_429(server):
    for _ in range(devicesmod.BRUTE_FORCE_MAX_FAILURES):
        _request(base(server) + "/v1/pair/claim", "POST", {"code": "ZZZZ-ZZZZ", "name": "x"})
    status, body = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": "ZZZZ-ZZZZ", "name": "x"},
    )
    assert status == 429 and "error" in body


def test_devices_requires_admin_once_a_non_admin_device_exists(server):
    _, started = _local_pair(server)
    _, claimed = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": started["code"], "name": "no admin"},
    )
    token = claimed["token"]

    status, _ = _request(base(server) + "/v1/devices", token=token)
    assert status == 403
    status, _ = _request(base(server) + "/v1/pair/start", "POST", {}, token=token)
    assert status == 403


def test_admin_device_can_administer(server):
    _, started = _local_pair(server, admin=True)
    _, claimed = _request(
        base(server) + "/v1/pair/claim", "POST", {"code": started["code"], "name": "admin"},
    )
    token = claimed["token"]

    status, rows = _request(base(server) + "/v1/devices", token=token)
    assert status == 200 and len(rows) == 1
    assert "token_hash" not in rows[0]

    status, started2 = _request(base(server) + "/v1/pair/start", "POST", {}, token=token)
    assert status == 201


def test_master_token_reflected_in_me(tmp_path):
    home = tmp_path / "koa"
    home.mkdir()
    cfg = configmod.Config(home=home, host="127.0.0.1", port=0, token="secreto")
    srv = apimod.make_server(cfg)
    cfg.port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    try:
        status, body = _request(base(cfg) + "/v1/me", token="secreto")
        assert status == 200 and body["kind"] == "master" and body["admin"] is True
    finally:
        srv.shutdown()


def test_llm_status_unconfigured(server):
    status, body = _request(base(server) + "/v1/llm/status")
    assert status == 200 and body == {"configured": False, "provider": "", "model": ""}


def test_chat_without_a_model_configured_is_400(server):
    status, body = _request(base(server) + "/v1/chat", "POST", {"message": "hola"})
    assert status == 400 and "koa-core llm setup" in body["error"]


def test_chat_needs_a_non_empty_message(server):
    status, body = _request(base(server) + "/v1/chat", "POST", {"message": "  "})
    assert status == 400 and "error" in body


def test_chat_list_is_empty_by_default(server):
    status, body = _request(base(server) + "/v1/chat")
    assert status == 200 and body == []


def test_chat_missing_conversation_is_404(server):
    status, body = _request(base(server) + "/v1/chat/does-not-exist")
    assert status == 404 and "error" in body


def test_chat_round_trip_with_a_fake_provider(server, monkeypatch):
    from koa_core import agent as agentmod
    from koa_core.llm.base import Turn

    server.llm_provider = "fake"
    server.llm_model = "fake-model"

    class _Fake:
        name = "fake"
        model = "fake-model"

        def format_tools(self, specs):
            return list(specs)

        def tool_result_messages(self, results):
            return [{"role": "user", "content": results}]

        def chat(self, messages, tools, system):
            return Turn(text="hola humano", tool_calls=[], stop_reason="end_turn",
                        usage={"input_tokens": 1, "output_tokens": 1},
                        raw_assistant={"role": "assistant", "content": "hola humano"})

    monkeypatch.setattr(agentmod, "for_config", lambda cfg: _Fake())

    status, body = _request(base(server) + "/v1/chat", "POST", {"message": "hola"})
    assert status == 200
    assert body["reply"] == "hola humano"
    assert body["tool_calls"] == []
    conv_id = body["conversation_id"]

    status, rows = _request(base(server) + "/v1/chat")
    assert status == 200 and len(rows) == 1 and rows[0]["id"] == conv_id

    status, messages = _request(base(server) + f"/v1/chat/{conv_id}")
    assert status == 200
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_pair_start_over_http_is_refused_in_open_mode(server):
    """Sin token maestro ni dispositivos, crear códigos por HTTP no se permite:
    un proxy enfrente dejaría a cualquiera emparejarse."""
    status, body = _request(base(server) + "/v1/pair/start", "POST", {})
    assert status == 403 and "koa-core pair" in body["error"]
