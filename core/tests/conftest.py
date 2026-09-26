import sqlite3

import pytest

from koa_core import db as dbmod


@pytest.fixture(autouse=True)
def _default_lang_env(monkeypatch):
    """Deterministic language across the suite: English unless a test sets
    one of these itself. Without this, a sandbox with LANG=es_* would flip
    every "assert English text" test."""
    for var in ("KOA_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _no_ambient_llm_keys(monkeypatch):
    """A dev machine's own shell may export ANTHROPIC_API_KEY/OPENAI_API_KEY
    for unrelated tools (a local gateway, another project); the llm tests
    must not silently "see" a key nobody configured for this KOA."""
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def conn(tmp_path):
    c = dbmod.connect(tmp_path / "koa-core.sqlite")
    yield c
    c.close()
