from koa_core import items, plans

PLAN_TEXT = """\
---
title: Ordenar mi KOA
status: wip
description: primer plan
---

## Tareas

- [ ] Leer AGENTS.md
- [x] Correr doctor
"""


def test_sync_creates_items_and_marks_done(conn, tmp_path):
    pdir = tmp_path / "plans"
    pdir.mkdir()
    (pdir / "ordenar-mi-koa.md").write_text(PLAN_TEXT)
    [result] = plans.sync(conn, pdir)
    assert result["tasks"] == 2
    assert result["created"] == 2
    rows = items.list_items(conn, plan="ordenar-mi-koa")
    by_title = {r["title"]: r for r in rows}
    assert by_title["Leer AGENTS.md"]["status"] == "open"
    assert by_title["Correr doctor"]["status"] == "done"
    assert by_title["Correr doctor"]["evidence"] == "plan:ordenar-mi-koa"


def test_sync_is_idempotent(conn, tmp_path):
    pdir = tmp_path / "plans"
    pdir.mkdir()
    (pdir / "ordenar-mi-koa.md").write_text(PLAN_TEXT)
    plans.sync(conn, pdir)
    [result] = plans.sync(conn, pdir)
    assert result["created"] == 0
    assert len(items.list_items(conn, plan="ordenar-mi-koa")) == 2


def test_sync_detects_checked_box_added_later(conn, tmp_path):
    pdir = tmp_path / "plans"
    pdir.mkdir()
    f = pdir / "ordenar-mi-koa.md"
    f.write_text(PLAN_TEXT.replace("- [x] Correr doctor", "- [ ] Correr doctor"))
    plans.sync(conn, pdir)
    f.write_text(PLAN_TEXT)
    [result] = plans.sync(conn, pdir)
    assert result["completed"] == 1


def test_sync_reports_orphans(conn, tmp_path):
    pdir = tmp_path / "plans"
    pdir.mkdir()
    f = pdir / "ordenar-mi-koa.md"
    f.write_text(PLAN_TEXT)
    plans.sync(conn, pdir)
    f.write_text(PLAN_TEXT.replace("- [ ] Leer AGENTS.md\n", ""))
    [result] = plans.sync(conn, pdir)
    assert len(result["orphans"]) == 1
    assert result["orphans"][0]["title"] == "Leer AGENTS.md"
