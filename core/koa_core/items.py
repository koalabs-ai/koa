"""Pendientes (items): la lista de tareas que agentes y persona comparten."""
from __future__ import annotations

from koa_core import i18n

import json
import sqlite3
import uuid
from datetime import datetime, timezone

STATUSES = ("open", "doing", "done", "dropped")


class ItemError(i18n.LocalizedError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    return d


def create(
    conn: sqlite3.Connection,
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    plan: str | None = None,
    source_id: str | None = None,
    status: str = "open",
) -> dict:
    if not title or not title.strip():
        raise ItemError("err.item_title")
    if status not in STATUSES:
        raise ItemError("err.item_status", status=status)
    if source_id:
        existing = conn.execute(
            "SELECT * FROM items WHERE source_id = ?", (source_id,)
        ).fetchone()
        if existing:
            return _row_to_dict(existing)
    item_id = str(uuid.uuid4())
    ts = now_iso()
    conn.execute(
        "INSERT INTO items (id, title, body, status, tags, plan, source_id, "
        "evidence, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (item_id, title.strip(), body, status, json.dumps(tags or []), plan,
         source_id, None, ts, ts),
    )
    conn.commit()
    return get(conn, item_id)


def get(conn: sqlite3.Connection, item_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_items(
    conn: sqlite3.Connection,
    status: str | None = None,
    tag: str | None = None,
    plan: str | None = None,
    q: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM items WHERE 1=1"
    args: list = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if plan:
        sql += " AND plan = ?"
        args.append(plan)
    if q:
        sql += " AND (title LIKE ? OR body LIKE ?)"
        like = f"%{q}%"
        args.extend([like, like])
    sql += " ORDER BY created_at DESC"
    rows = [_row_to_dict(r) for r in conn.execute(sql, args).fetchall()]
    if tag:
        rows = [r for r in rows if tag in r["tags"]]
    return rows


def update(
    conn: sqlite3.Connection,
    item_id: str,
    *,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    plan: str | None = None,
    evidence: str | None = None,
) -> dict:
    current = get(conn, item_id)
    if current is None:
        raise ItemError("err.item_missing", id=item_id)
    if status is not None and status not in STATUSES:
        raise ItemError("err.item_status", status=status)
    new_status = status if status is not None else current["status"]
    new_evidence = evidence if evidence is not None else current["evidence"]
    if new_status in ("done", "dropped") and not (new_evidence and new_evidence.strip()):
        raise ItemError("err.item_evidence")
    fields = {
        "title": title if title is not None else current["title"],
        "body": body if body is not None else current["body"],
        "status": new_status,
        "tags": json.dumps(tags if tags is not None else current["tags"]),
        "plan": plan if plan is not None else current["plan"],
        "evidence": new_evidence,
        "updated_at": now_iso(),
    }
    conn.execute(
        "UPDATE items SET title=?, body=?, status=?, tags=?, plan=?, evidence=?, "
        "updated_at=? WHERE id=?",
        (*fields.values(), item_id),
    )
    conn.commit()
    return get(conn, item_id)


def count_open(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM items WHERE status IN ('open','doing')"
    ).fetchone()
    return row["n"]
