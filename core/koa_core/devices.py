"""Emparejamiento de dispositivos: un código de corta vida se cambia por un
token propio y revocable por dispositivo. Ni el código ni el token se
guardan en claro: sólo su sha256.

Flujo: ``start_pairing`` crea un código (persona/agente con permiso) ->
``claim`` lo cambia por un token de dispositivo (lo hace el dispositivo,
sin más credencial que el código) -> ``authenticate`` valida ese token en
cada petición -> ``revoke`` lo apaga cuando ya no se confía en ese aparato.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from koa_core import i18n
from koa_core.items import now_iso

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 8
TOKEN_PREFIX = "kd_"
DEFAULT_CODE_TTL_S = 600

# Guardia global de fuerza bruta: si hay demasiados intentos fallidos de
# "claim" en la ventana, todos los intentos (de cualquier código) responden
# 429 hasta que la ventana pase. Contador en memoria del proceso; basta para
# un servidor de una sola persona.
BRUTE_FORCE_WINDOW_S = 600
BRUTE_FORCE_MAX_FAILURES = 10

_lock = threading.Lock()
_failures: list[float] = []


class PairingError(ValueError):
    """Código inválido, expirado o ya usado. Mensaje siempre genérico:
    no se revela cuál de los tres pasó."""


class TooManyAttempts(Exception):
    """Se superó el máximo de intentos fallidos en la ventana: 429."""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def normalize_code(raw: str) -> str:
    """Mayúsculas, sin espacios ni guiones: así llega lo que la persona tecleó."""
    return re.sub(r"[\s-]", "", raw or "").upper()


def format_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))


def _reset_failures_for_tests() -> None:
    """Sólo para pruebas: limpia el contador global entre casos."""
    with _lock:
        _failures.clear()


def _record_failure() -> None:
    now = time.time()
    with _lock:
        _failures.append(now)
        cutoff = now - BRUTE_FORCE_WINDOW_S
        while _failures and _failures[0] < cutoff:
            _failures.pop(0)


def _check_brute_force(lang: str = i18n.DEFAULT_LANG) -> None:
    now = time.time()
    with _lock:
        cutoff = now - BRUTE_FORCE_WINDOW_S
        while _failures and _failures[0] < cutoff:
            _failures.pop(0)
        if len(_failures) >= BRUTE_FORCE_MAX_FAILURES:
            raise TooManyAttempts(i18n.t("devices.too_many_attempts", lang=lang))


def start_pairing(
    conn: sqlite3.Connection,
    admin: bool = False,
    created_by: str = "",
    ttl_s: int = DEFAULT_CODE_TTL_S,
) -> tuple[str, str]:
    """Crea un código nuevo. Devuelve ``(codigo "XXXX-XXXX", expires_at)``."""
    code = generate_code()
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=ttl_s)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO pairing_codes (code_hash, created_at, expires_at, admin, created_by) "
        "VALUES (?,?,?,?,?)",
        (_hash(code), now_iso(), expires_at, int(bool(admin)), created_by),
    )
    conn.commit()
    return format_code(code), expires_at


def claim(
    conn: sqlite3.Connection,
    code: str,
    name: str,
    platform: str = "",
    lang: str = i18n.DEFAULT_LANG,
) -> tuple[str, str]:
    """Cambia un código vigente por un token de dispositivo nuevo.

    Levanta :class:`TooManyAttempts` (429) o :class:`PairingError` (400,
    mensaje genérico) sin decir cuál de los tres motivos aplicó.
    """
    _check_brute_force(lang)
    normalized = normalize_code(code)
    if len(normalized) != CODE_LEN:
        _record_failure()
        raise PairingError(i18n.t("devices.invalid_code", lang=lang))
    code_hash = _hash(normalized)
    row = conn.execute(
        "SELECT * FROM pairing_codes WHERE code_hash = ?", (code_hash,)
    ).fetchone()
    if row is None:
        _record_failure()
        raise PairingError(i18n.t("devices.invalid_or_expired_code", lang=lang))
    now = datetime.now(timezone.utc)
    if row["used_at"] or _parse(row["expires_at"]) <= now:
        conn.execute(
            "UPDATE pairing_codes SET failed_attempts = failed_attempts + 1 WHERE code_hash = ?",
            (code_hash,),
        )
        conn.commit()
        _record_failure()
        raise PairingError(i18n.t("devices.invalid_or_expired_code", lang=lang))

    device_id = str(uuid.uuid4())
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    ts = now_iso()
    # Atómico: el servidor es multihilo; dos canjes simultáneos del mismo código
    # no deben dar dos tokens. Sólo gana el UPDATE que encuentra used_at vacío.
    cur = conn.execute(
        "UPDATE pairing_codes SET used_at = ? WHERE code_hash = ? AND used_at IS NULL",
        (ts, code_hash),
    )
    if cur.rowcount != 1:
        conn.commit()
        _record_failure()
        raise PairingError(i18n.t("devices.invalid_or_expired_code", lang=lang))
    default_name = i18n.t("devices.default_name", lang=lang)
    conn.execute(
        "INSERT INTO devices (id, name, platform, token_hash, admin, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (device_id, (name or default_name).strip() or default_name, platform or "",
         _hash(token), row["admin"], ts),
    )
    conn.commit()
    return device_id, token


def authenticate(conn: sqlite3.Connection, token: str) -> dict | None:
    """Valida un token de dispositivo. ``None`` si no existe o está revocado.

    Actualiza ``last_seen_at`` a lo mucho una vez por minuto (evita un
    UPDATE en cada petición).
    """
    if not token:
        return None
    row = conn.execute(
        "SELECT * FROM devices WHERE token_hash = ?", (_hash(token),)
    ).fetchone()
    if row is None or row["revoked_at"]:
        return None
    device = dict(row)
    now = datetime.now(timezone.utc)
    stale = True
    if device["last_seen_at"]:
        try:
            stale = (now - _parse(device["last_seen_at"])) >= timedelta(minutes=1)
        except ValueError:
            stale = True
    if stale:
        ts = now_iso()
        conn.execute("UPDATE devices SET last_seen_at = ? WHERE id = ?", (ts, device["id"]))
        conn.commit()
        device["last_seen_at"] = ts
    return device


def list_devices(conn: sqlite3.Connection) -> list[dict]:
    """Dispositivos, sin ``token_hash``, más nuevo primero."""
    rows = conn.execute(
        "SELECT id, name, platform, admin, created_at, last_seen_at, revoked_at "
        "FROM devices ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def revoke(conn: sqlite3.Connection, device_id: str) -> bool:
    row = conn.execute("SELECT revoked_at FROM devices WHERE id = ?", (device_id,)).fetchone()
    if row is None or row["revoked_at"]:
        return False
    conn.execute(
        "UPDATE devices SET revoked_at = ? WHERE id = ?", (now_iso(), device_id)
    )
    conn.commit()
    return True


def count_active(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM devices WHERE revoked_at IS NULL"
    ).fetchone()
    return row["n"]


def has_active_devices(conn: sqlite3.Connection) -> bool:
    return count_active(conn) > 0
