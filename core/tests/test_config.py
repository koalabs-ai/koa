from koa_core import config as configmod


def test_token_from_file_wins_over_toml(tmp_path):
    (tmp_path / "koa.toml").write_text('[api]\ntoken = "del-toml"\n')
    configmod.write_token_file(tmp_path / "10_personal" / "secrets" / "koa-core.token", "del-archivo")
    cfg = configmod.load_config(tmp_path)
    assert cfg.token == "del-archivo"
    assert cfg.token_source == "file"


def test_token_file_has_0600_permissions(tmp_path):
    path = tmp_path / "10_personal" / "secrets" / "koa-core.token"
    configmod.write_token_file(path, "un-token")
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600
    assert (path.parent.stat().st_mode & 0o777) == 0o700


def test_token_from_toml_when_no_file(tmp_path):
    (tmp_path / "koa.toml").write_text('[api]\ntoken = "del-toml"\n')
    cfg = configmod.load_config(tmp_path)
    assert cfg.token == "del-toml"
    assert cfg.token_source == "toml"


def test_env_token_wins_over_file_and_toml(tmp_path, monkeypatch):
    (tmp_path / "koa.toml").write_text('[api]\ntoken = "del-toml"\n')
    configmod.write_token_file(tmp_path / "10_personal" / "secrets" / "koa-core.token", "del-archivo")
    monkeypatch.setenv("KOA_TOKEN", "del-env")
    cfg = configmod.load_config(tmp_path)
    assert cfg.token == "del-env"
    assert cfg.token_source == "env"


def test_no_token_anywhere(tmp_path):
    cfg = configmod.load_config(tmp_path)
    assert cfg.token == ""
    assert cfg.token_source == "none"


def test_strip_toml_token_empties_value_but_keeps_key(tmp_path):
    toml_path = tmp_path / "koa.toml"
    toml_path.write_text('[api]\nhost = "127.0.0.1"\ntoken = "secreto"\n\n[db]\npath = "x"\n')
    changed = configmod.strip_toml_token(toml_path)
    assert changed is True
    text = toml_path.read_text()
    assert 'token = ""' in text
    assert "secreto" not in text
    assert 'host = "127.0.0.1"' in text  # el resto del archivo no se toca


def test_strip_toml_token_noop_when_already_empty(tmp_path):
    toml_path = tmp_path / "koa.toml"
    toml_path.write_text('[api]\ntoken = ""\n')
    assert configmod.strip_toml_token(toml_path) is False


def test_pairing_code_ttl_default_and_override(tmp_path):
    cfg = configmod.load_config(tmp_path)
    assert cfg.code_ttl_s == 600
    (tmp_path / "koa.toml").write_text("[pairing]\ncode_ttl_s = 120\n")
    cfg = configmod.load_config(tmp_path)
    assert cfg.code_ttl_s == 120


def test_defaults(tmp_path):
    cfg = configmod.load_config(tmp_path)
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8700
    assert cfg.db_path == tmp_path.resolve() / "06_data" / "koa-core.sqlite"


def test_reads_toml(tmp_path):
    (tmp_path / "koa.toml").write_text(
        '[api]\nhost = "0.0.0.0"\nport = 9000\ntoken = "abc"\n[db]\npath = "otro.sqlite"\n'
    )
    cfg = configmod.load_config(tmp_path)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9000
    assert cfg.token == "abc"
    assert cfg.db_path == tmp_path.resolve() / "otro.sqlite"


def test_env_overrides_toml(tmp_path, monkeypatch):
    (tmp_path / "koa.toml").write_text('[api]\nport = 9000\n')
    monkeypatch.setenv("KOA_PORT", "7777")
    cfg = configmod.load_config(tmp_path)
    assert cfg.port == 7777
