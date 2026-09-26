"""Memoria persistente: la fuente de verdad son archivos .md; sqlite es el índice.

Cada recuerdo vive en ``KOA_HOME/06_data/memory/<type>-<slug>.md`` con un
frontmatter simple (``name:``, ``type:``, ``description:`` entre ``---``)
y el cuerpo libre debajo. El índice (FTS5 si hay, si no LIKE) se reconstruye
con ``reindex`` y se actualiza en cada ``add``.
"""
from __future__ import annotations

from koa_core import i18n

import re
import sqlite3
from pathlib import Path

from koa_core import _frontmatter
from koa_core import db as dbmod
from koa_core import naming
from koa_core.items import now_iso

TYPES = ("user", "feedback", "project", "reference")


class MemoryError(i18n.LocalizedError):
    pass


def slugify(name: str) -> str:
    s = naming.suggest(name.strip())
    return s or "note"


def _render(name: str, type_: str, description: str, body: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"type: {type_}\n"
        f"description: {description}\n"
        "---\n\n"
        f"{body}\n"
    )


def path_for(memory_dir: Path, type_: str, name: str) -> Path:
    return Path(memory_dir) / f"{type_}-{slugify(name)}.md"


def add(
    conn: sqlite3.Connection,
    memory_dir: Path,
    type_: str,
    name: str,
    description: str = "",
    body: str = "",
) -> dict:
    if type_ not in TYPES:
        raise MemoryError("err.mem_type", type=type_, types=", ".join(TYPES))
    if not name or not name.strip():
        raise MemoryError("err.mem_name")
    memory_dir = Path(memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)
    path = path_for(memory_dir, type_, name)
    path.write_text(_render(name.strip(), type_, description, body), encoding="utf-8")
    entry = _index_file(conn, path)
    _update_index_md(memory_dir)
    return entry


def _index_file(conn: sqlite3.Connection, path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    header, body = _frontmatter.parse(text)
    name = header.get("name") or header.get("title") or path.stem
    type_ = header.get("type") or path.stem.split("-", 1)[0]
    description = header.get("description", "")
    updated_at = now_iso()
    conn.execute(
        "INSERT INTO memory (name, type, description, body, path, updated_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET "
        "type=excluded.type, description=excluded.description, body=excluded.body, "
        "path=excluded.path, updated_at=excluded.updated_at",
        (name, type_, description, body, str(path), updated_at),
    )
    if dbmod.has_fts5(conn):
        conn.execute("DELETE FROM memory_fts WHERE name = ?", (name,))
        conn.execute(
            "INSERT INTO memory_fts (name, type, description, body) VALUES (?,?,?,?)",
            (name, type_, description, body),
        )
    conn.commit()
    return {"name": name, "type": type_, "description": description, "path": str(path)}


def reindex(conn: sqlite3.Connection, memory_dir: Path) -> int:
    memory_dir = Path(memory_dir)
    conn.execute("DELETE FROM memory")
    if dbmod.has_fts5(conn):
        conn.execute("DELETE FROM memory_fts")
    conn.commit()
    n = 0
    if memory_dir.exists():
        for path in sorted(memory_dir.glob("*.md")):
            if path.name.upper() == "MEMORY.MD":
                continue
            _index_file(conn, path)
            n += 1
    return n


def recall(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    query = (query or "").strip()
    if not query:
        rows = conn.execute(
            "SELECT name, type, description, body FROM memory ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_snippet_row(r) for r in rows]
    if dbmod.has_fts5(conn):
        try:
            rows = conn.execute(
                "SELECT name, type, description, snippet(memory_fts, 3, '[', ']', '...', 12) "
                "AS snippet FROM memory_fts WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
                (_fts_query(query), limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            pass  # query rara para FTS5: cae al LIKE
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT name, type, description, body FROM memory WHERE name LIKE ? OR "
        "description LIKE ? OR body LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (like, like, like, limit),
    ).fetchall()
    return [_snippet_row(r) for r in rows]


def _fts_query(query: str) -> str:
    # Cada palabra como término independiente con prefijo, para que
    # "proyecto x" encuentre "proyecto-x-cosa" igual que LIKE %proyecto%.
    words = re.findall(r"\w+", query)
    if not words:
        return '""'
    return " ".join(f'{w}*' for w in words)


def _snippet_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    body = d.pop("body", "") or ""
    d["snippet"] = (body[:200] + "...") if len(body) > 200 else body
    return d


def list_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT name, type, description, path, updated_at FROM memory ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def _update_index_md(memory_dir: Path) -> None:
    """Reescribe MEMORY.md: una línea por recuerdo, más nuevo primero."""
    entries = []
    for path in sorted(memory_dir.glob("*.md")):
        if path.name.upper() == "MEMORY.MD":
            continue
        header, _ = _frontmatter.parse(path.read_text(encoding="utf-8"))
        name = header.get("name") or header.get("title") or path.stem
        desc = header.get("description", "")
        entries.append(f"- [{name}]({path.name}) — {desc}" if desc else f"- [{name}]({path.name})")
    lines = ["# MEMORY.md — memory index", "", *entries, ""]
    (memory_dir / "MEMORY.md").write_text("\n".join(lines), encoding="utf-8")
