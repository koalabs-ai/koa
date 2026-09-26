import pytest

from koa_core import claims


def test_acquire_and_conflict(conn):
    claims.acquire(conn, "target-a", "agent-1", intent="hacer algo")
    with pytest.raises(claims.ClaimHeld):
        claims.acquire(conn, "target-a", "agent-2")


def test_same_agent_extends(conn):
    c1 = claims.acquire(conn, "target-b", "agent-1")
    c2 = claims.acquire(conn, "target-b", "agent-1", intent="ahora esto")
    assert c1["id"] == c2["id"]
    assert c2["intent"] == "ahora esto"


def test_release_frees_target(conn):
    c1 = claims.acquire(conn, "target-c", "agent-1")
    assert claims.release(conn, c1["id"]) is True
    claims.acquire(conn, "target-c", "agent-2")  # ya no truena


def test_expired_claim_is_ignored(conn):
    claims.acquire(conn, "target-d", "agent-1", ttl_minutes=-1)
    claims.acquire(conn, "target-d", "agent-2")  # no debe explotar
