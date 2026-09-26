"""Esquema sqlite y migraciones. Una conexión por hilo/petición, WAL on.

Las migraciones son una lista de scripts SQL; ``PRAGMA user_version``
guarda cuál fue la última aplicada. Añadir una migración nueva = agregar
un elemento al final de ``MIGRATIONS``; nunca edites una ya publicada.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS: list[str] = [
    # v1: esquema inicial
    """
    CREATE TABLE items (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        body TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open',
        tags TEXT NOT NULL DEFAULT '[]',
        plan TEXT,
        source_id TEXT UNIQUE,
        evidence TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX idx_items_status ON items(status);
    CREATE INDEX idx_items_plan ON items(plan);

    CREATE TABLE plans (
        slug TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        path TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE memory (
        name TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '',
        path TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE claims (
        id TEXT PRIMARY KEY,
        target TEXT NOT NULL,
        agent TEXT NOT NULL,
        intent TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    CREATE INDEX idx_claims_target ON claims(target);

    CREATE TABLE activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        agent TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'log',
        text TEXT NOT NULL DEFAULT '',
        data TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX idx_activity_ts ON activity(ts);

    CREATE TABLE agents (
        agent TEXT PRIMARY KEY,
        last_seen TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT ''
    );
    """,
    # v2: emparejamiento de dispositivos (docs/mobile-and-desktop.md paso 2)
    """
    CREATE TABLE devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL DEFAULT '',
        platform TEXT NOT NULL DEFAULT '',
        token_hash TEXT NOT NULL UNIQUE,
        admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        last_seen_at TEXT,
        revoked_at TEXT
    );
    CREATE INDEX idx_devices_revoked ON devices(revoked_at);

    CREATE TABLE pairing_codes (
        code_hash TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        admin INTEGER NOT NULL DEFAULT 0,
        failed_attempts INTEGER NOT NULL DEFAULT 0,
        created_by TEXT NOT NULL DEFAULT ''
    );
    """,
    # v3: conversaciones del agente integrado (koa_core.agent)
    """
    CREATE TABLE conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        provider TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        context_open_items INTEGER NOT NULL DEFAULT 0,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL REFERENCES conversations(id),
        role TEXT NOT NULL,
        content_json TEXT NOT NULL,
        render_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX idx_messages_conversation ON messages(conversation_id);
    """,
]


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def connect(db_path: Path) -> sqlite3.Connection:
    """Abre (y si hace falta crea/migra) la base en ``db_path``."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> int:
    """Aplica migraciones pendientes. Devuelve la versión final."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    fts = has_fts5(conn)
    for i in range(version, len(MIGRATIONS)):
        conn.executescript(MIGRATIONS[i])
        _set_user_version(conn, i + 1)
    if fts and version < len(MIGRATIONS):
        _ensure_fts_table(conn)
    conn.commit()
    return len(MIGRATIONS)


def _set_user_version(conn: sqlite3.Connection, value: int) -> None:
    # PRAGMA no acepta parámetros ligados; value siempre es un contador
    # interno (len(MIGRATIONS)), nunca dato externo.
    assert isinstance(value, int) and 0 <= value < 100000
    # PRAGMA no admite parametros ligados (?); value ya se valido arriba
    # como int interno (nunca dato externo), asi que un literal es seguro.
    digits = str(value)
    assert digits.isdigit()
    conn.execute("PRAGMA user_version=" + digits)


_FTS_CHECKED: dict[int, bool] = {}


def has_fts5(conn: sqlite3.Connection) -> bool:
    key = id(conn)
    if key not in _FTS_CHECKED:
        _FTS_CHECKED[key] = _fts5_available(conn)
    return _FTS_CHECKED[key]


def _ensure_fts_table(conn: sqlite3.Connection) -> None:
    # Tabla FTS5 independiente (no "external content"): se re-llena a mano en
    # cada add/reindex. Más simple que sincronizar rowids con la tabla memory.
    conn.executescript(
        "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(name, type, description, body);"
    )
