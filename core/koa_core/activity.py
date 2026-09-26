"""Bitácora de actividad: sqlite (para consultar) + activity.jsonl (append-only)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from koa_core.items import now_iso


def log(
    conn: sqlite3.Connection,
    log_path: Path,
    agent: str,
    text: str,
    kind: str = "log",
    data: dict | None = None,
) -> dict:
    ts = now_iso()
    payload = data or {}
    conn.execute(
        "INSERT INTO activity (ts, agent, kind, text, data) VALUES (?,?,?,?,?)",
        (ts, agent, kind, text, json.dumps(payload)),
    )
    conn.commit()
    entry = {"ts": ts, "agent": agent, "kind": kind, "text": text, "data": payload}
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["data"] = json.loads(d.get("data") or "{}")
        except json.JSONDecodeError:
            d["data"] = {}
        out.append(d)
    return out


def heartbeat(conn: sqlite3.Connection, agent: str, note: str = "") -> dict:
    ts = now_iso()
    conn.execute(
        "INSERT INTO agents (agent, last_seen, note) VALUES (?,?,?) "
        "ON CONFLICT(agent) DO UPDATE SET last_seen=excluded.last_seen, note=excluded.note",
        (agent, ts, note),
    )
    conn.commit()
    return {"agent": agent, "last_seen": ts, "note": note}


def list_agents(conn: sqlite3.Connection, active_seconds: int = 300) -> list[dict]:
    from datetime import datetime, timedelta, timezone

    rows = conn.execute("SELECT * FROM agents ORDER BY last_seen DESC").fetchall()
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        d = dict(r)
        try:
            seen = datetime.strptime(d["last_seen"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            d["active"] = (now - seen) <= timedelta(seconds=active_seconds)
        except ValueError:
            d["active"] = False
        out.append(d)
    return out
