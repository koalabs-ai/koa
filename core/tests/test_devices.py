import re

import pytest

from koa_core import db as dbmod
from koa_core import devices as devicesmod


@pytest.fixture(autouse=True)
def _clean_brute_force():
    """El contador de fuerza bruta es global al proceso: limpialo entre casos."""
    devicesmod._reset_failures_for_tests()
    yield
    devicesmod._reset_failures_for_tests()


def test_start_claim_authenticate_revoke(conn):
    code, expires_at = devicesmod.start_pairing(conn, created_by="agente-x")
    assert re.match(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$", code)
    assert expires_at

    device_id, token = devicesmod.claim(conn, code, "mi telefono", "android")
    assert token.startswith("kd_")

    device = devicesmod.authenticate(conn, token)
    assert device is not None
    assert device["id"] == device_id
    assert device["name"] == "mi telefono"
    assert device["admin"] == 0

    assert devicesmod.revoke(conn, device_id) is True
    assert devicesmod.authenticate(conn, token) is None
    # revocar de nuevo: ya no hay nada que revocar
    assert devicesmod.revoke(conn, device_id) is False


def test_authenticate_unknown_token_is_none(conn):
    assert devicesmod.authenticate(conn, "kd_lo-que-sea") is None
    assert devicesmod.authenticate(conn, "") is None


def test_claim_expired_code(conn):
    code, _ = devicesmod.start_pairing(conn, ttl_s=-1)
    with pytest.raises(devicesmod.PairingError):
        devicesmod.claim(conn, code, "x")


def test_claim_reused_code(conn):
    code, _ = devicesmod.start_pairing(conn)
    devicesmod.claim(conn, code, "primero")
    with pytest.raises(devicesmod.PairingError):
        devicesmod.claim(conn, code, "segundo")


def test_claim_wrong_code(conn):
    devicesmod.start_pairing(conn)
    with pytest.raises(devicesmod.PairingError):
        devicesmod.claim(conn, "ZZZZ-ZZZZ", "x")


def test_claim_errors_are_generic(conn):
    """Codigo malo, expirado o usado dan el mismo tipo de error, sin decir cual."""
    expired, _ = devicesmod.start_pairing(conn, ttl_s=-1)
    used, _ = devicesmod.start_pairing(conn)
    devicesmod.claim(conn, used, "primero")
    messages = set()
    for bad in ("ZZZZ-ZZZZ", expired, used):
        with pytest.raises(devicesmod.PairingError) as exc:
            devicesmod.claim(conn, bad, "x")
        messages.add(str(exc.value))
    assert len(messages) == 1  # un solo mensaje generico para los tres casos


def test_claim_accepts_lowercase_spaces_and_dashes(conn):
    code, _ = devicesmod.start_pairing(conn)
    messy = code.lower().replace("-", " ")
    device_id, token = devicesmod.claim(conn, messy, "x")
    assert device_id and token


def test_admin_flag_propagates_from_code_to_device(conn):
    code, _ = devicesmod.start_pairing(conn, admin=True)
    _, token = devicesmod.claim(conn, code, "laptop admin")
    device = devicesmod.authenticate(conn, token)
    assert device["admin"] == 1


def test_brute_force_guard_returns_too_many_attempts(conn):
    for _ in range(devicesmod.BRUTE_FORCE_MAX_FAILURES):
        with pytest.raises(devicesmod.PairingError):
            devicesmod.claim(conn, "ZZZZ-ZZZZ", "x")
    with pytest.raises(devicesmod.TooManyAttempts):
        devicesmod.claim(conn, "ZZZZ-ZZZZ", "x")
    # incluso un codigo valido queda bloqueado mientras la ventana no pase
    code, _ = devicesmod.start_pairing(conn)
    with pytest.raises(devicesmod.TooManyAttempts):
        devicesmod.claim(conn, code, "x")


def test_tokens_and_codes_never_stored_in_plaintext(tmp_path):
    db_path = tmp_path / "koa-core.sqlite"
    conn = dbmod.connect(db_path)
    try:
        code, _ = devicesmod.start_pairing(conn)
        device_id, token = devicesmod.claim(conn, code, "x")
    finally:
        conn.close()
    raw = db_path.read_bytes()
    assert code.replace("-", "").encode() not in raw
    assert token.encode() not in raw


def test_list_devices_excludes_token_hash(conn):
    code, _ = devicesmod.start_pairing(conn)
    devicesmod.claim(conn, code, "x")
    rows = devicesmod.list_devices(conn)
    assert len(rows) == 1
    assert "token_hash" not in rows[0]


def test_count_active_excludes_revoked(conn):
    code, _ = devicesmod.start_pairing(conn)
    device_id, _ = devicesmod.claim(conn, code, "x")
    assert devicesmod.count_active(conn) == 1
    assert devicesmod.has_active_devices(conn) is True
    devicesmod.revoke(conn, device_id)
    assert devicesmod.count_active(conn) == 0
    assert devicesmod.has_active_devices(conn) is False


def test_claim_is_single_use_under_concurrency(tmp_path):
    """Dos canjes simultáneos del mismo código: sólo uno obtiene token."""
    import threading
    from koa_core import db as dbmod, devices as dv

    dbp = tmp_path / "k.sqlite"
    c0 = dbmod.connect(dbp) if hasattr(dbmod, "connect") else None
    if c0 is None:
        import pytest
        pytest.skip("db.connect no disponible")
    dbmod.migrate(c0) if hasattr(dbmod, "migrate") else None
    code, _ = dv.start_pairing(c0)
    results, barrier = [], threading.Barrier(8)

    def worker():
        c = dbmod.connect(dbp)
        barrier.wait()
        try:
            results.append(dv.claim(c, code, "x"))
        except dv.PairingError:
            results.append(None)
        except dv.TooManyAttempts:
            results.append(None)

    ts = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(1 for r in results if r) == 1


def test_token_file_is_born_private(tmp_path, monkeypatch):
    import os, stat
    from koa_core import config as cf
    monkeypatch.setattr(os, "umask", os.umask)
    old = os.umask(0o022)
    try:
        f = tmp_path / "s" / "koa-core.token"
        cf.write_token_file(f, "abc")
        assert stat.S_IMODE(f.stat().st_mode) == 0o600
    finally:
        os.umask(old)
