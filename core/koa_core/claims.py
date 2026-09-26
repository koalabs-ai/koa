"""Candados entre agentes: evitar que dos agentes trabajen la misma cosa a la vez."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from koa_core.items import now_iso

DEFAULT_TTL_MINUTES = 60


class ClaimHeld(Exception):
    """Otro agente ya tiene un candado vigente sobre ese target."""

    def __init__(self, holder: dict):
        self.holder = holder
        super().__init__(f"target held by {holder['agent']} until {holder['expires_at']}")


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _active_holder(conn: sqlite3.Connection, target: str) -> sqlite3.Row | None:
    now = datetime.now(timezone.utc)
    for row in conn.execute("SELECT * FROM claims WHERE target = ?", (target,)):
        if _parse(row["expires_at"]) > now:
            return row
    return None


def acquire(
    conn: sqlite3.Connection,
    target: str,
    agent: str,
    intent: str = "",
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> dict:
    holder = _active_holder(conn, target)
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if holder is not None and holder["agent"] != agent:
        raise ClaimHeld(dict(holder))
    if holder is not None and holder["agent"] == agent:
        conn.execute(
            "UPDATE claims SET intent=?, expires_at=? WHERE id=?",
            (intent, expires, holder["id"]),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM claims WHERE id=?", (holder["id"],)).fetchone())
    claim_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO claims (id, target, agent, intent, created_at, expires_at) "
        "VALUES (?,?,?,?,?,?)",
        (claim_id, target, agent, intent, now_iso(), expires),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone())


def release(conn: sqlite3.Connection, claim_id: str) -> bool:
    cur = conn.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
    conn.commit()
    return cur.rowcount > 0


def list_claims(conn: sqlite3.Connection, include_expired: bool = False) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM claims ORDER BY created_at DESC")]
    if include_expired:
        return rows
    now = datetime.now(timezone.utc)
    return [r for r in rows if _parse(r["expires_at"]) > now]
