import pytest

from koa_core import items


def test_create_and_get(conn):
    it = items.create(conn, "Primer pendiente", tags=["bug"])
    assert it["status"] == "open"
    assert it["tags"] == ["bug"]
    assert items.get(conn, it["id"])["title"] == "Primer pendiente"


def test_create_requires_title(conn):
    with pytest.raises(items.ItemError):
        items.create(conn, "  ")


def test_source_id_is_idempotent(conn):
    a = items.create(conn, "Uno", source_id="x1")
    b = items.create(conn, "Uno de nuevo", source_id="x1")
    assert a["id"] == b["id"]


def test_done_requires_evidence(conn):
    it = items.create(conn, "Algo")
    with pytest.raises(items.ItemError):
        items.update(conn, it["id"], status="done")
    updated = items.update(conn, it["id"], status="done", evidence="lo probe")
    assert updated["status"] == "done"
    assert updated["evidence"] == "lo probe"


def test_list_filters(conn):
    items.create(conn, "A", tags=["x"], status="open")
    items.create(conn, "B", tags=["y"], plan="miplan")
    assert len(items.list_items(conn, tag="x")) == 1
    assert len(items.list_items(conn, plan="miplan")) == 1
    assert len(items.list_items(conn, status="open")) == 2
    assert len(items.list_items(conn, q="A")) == 1
