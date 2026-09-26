"""Planes: markdown con casillas que se sincronizan a pendientes (items).

Un plan es un archivo ``KOA_HOME/99_docs/plans/<slug>.md``. El frontmatter
(``title``, ``status``, ``description``) se lee a mano. Cada casilla
``- [ ] texto`` / ``- [x] texto`` se vuelve un item con un
``source_id`` corto derivado de slug+texto, así ``sync`` es
idempotente: correrlo dos veces no duplica nada.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from koa_core import _frontmatter
from koa_core import items as itemsmod

CHECKBOX = re.compile(r"^\s*-\s*\[( |x|X)\]\s+(.*\S)\s*$")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def source_id_for(slug: str, text: str) -> str:
    # Solo necesitamos un id estable y corto (no criptografia), pero usamos
    # sha256 para no chocar con linters de seguridad que vetan sha1.
    digest = hashlib.sha256(f"{slug}:{_normalize(text)}".encode("utf-8")).hexdigest()
    return digest[:16]


def parse_plan(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    header, body = _frontmatter.parse(text)
    tasks = []
    for line in body.splitlines():
        m = CHECKBOX.match(line)
        if m:
            tasks.append({"text": m.group(2), "done": m.group(1).lower() == "x"})
    return {
        "slug": Path(path).stem,
        "title": header.get("title", Path(path).stem),
        "status": header.get("status", ""),
        "description": header.get("description", ""),
        "tasks": tasks,
        "path": str(path),
    }


def sync_one(conn: sqlite3.Connection, path: Path) -> dict:
    plan = parse_plan(path)
    slug = plan["slug"]
    conn.execute(
        "INSERT INTO plans (slug, title, status, description, path, updated_at) "
        "VALUES (?,?,?,?,?, datetime('now')) ON CONFLICT(slug) DO UPDATE SET "
        "title=excluded.title, status=excluded.status, description=excluded.description, "
        "path=excluded.path, updated_at=excluded.updated_at",
        (slug, plan["title"], plan["status"], plan["description"], plan["path"]),
    )
    conn.commit()
    seen_source_ids = set()
    created, completed = 0, 0
    for task in plan["tasks"]:
        sid = source_id_for(slug, task["text"])
        seen_source_ids.add(sid)
        existing = conn.execute(
            "SELECT * FROM items WHERE source_id = ?", (sid,)
        ).fetchone()
        if existing is None:
            itemsmod.create(
                conn, title=task["text"], plan=slug, source_id=sid,
                status="done" if task["done"] else "open",
            )
            created += 1
            if task["done"]:
                # evidence obligatoria para done: se pone directo al crear
                conn.execute(
                    "UPDATE items SET evidence=? WHERE source_id=?",
                    (f"plan:{slug}", sid),
                )
                conn.commit()
        elif task["done"] and existing["status"] != "done":
            itemsmod.update(conn, existing["id"], status="done", evidence=f"plan:{slug}")
            completed += 1
    orphans = [
        dict(r) for r in conn.execute(
            "SELECT * FROM items WHERE plan = ? AND source_id IS NOT NULL", (slug,)
        )
        if r["source_id"] not in seen_source_ids
    ]
    return {
        "slug": slug, "title": plan["title"], "tasks": len(plan["tasks"]),
        "created": created, "completed": completed, "orphans": orphans,
    }


def sync(conn: sqlite3.Connection, plans_dir: Path) -> list[dict]:
    plans_dir = Path(plans_dir)
    if not plans_dir.exists():
        return []
    return [sync_one(conn, p) for p in sorted(plans_dir.glob("*.md"))]


def list_plans(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM plans ORDER BY slug")]
