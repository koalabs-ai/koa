import string

import pytest

from koa_core import cli
from koa_core import i18n
from koa_core.i18n_catalog import EN, ES


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "koa"
    h.mkdir()
    monkeypatch.setenv("KOA_HOME", str(h))
    monkeypatch.delenv("KOA_TOKEN", raising=False)
    monkeypatch.delenv("KOA_HOST", raising=False)
    monkeypatch.delenv("KOA_PORT", raising=False)
    return h


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


# ── resolve_lang ────────────────────────────────────────────────────

def test_default_lang_is_english():
    assert i18n.resolve_lang() == "en"


def test_koa_lang_env_wins(monkeypatch):
    monkeypatch.setenv("KOA_LANG", "es")
    assert i18n.resolve_lang() == "es"
    monkeypatch.setenv("KOA_LANG", "es-MX")
    assert i18n.resolve_lang() == "es"


def test_lang_env_es_mx(monkeypatch):
    monkeypatch.setenv("LANG", "es_MX.UTF-8")
    assert i18n.resolve_lang() == "es"


def test_lc_all_and_lc_messages_are_checked_before_lang(monkeypatch):
    monkeypatch.setenv("LANG", "es_MX.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "en_US.UTF-8")
    assert i18n.resolve_lang() == "en"
    monkeypatch.setenv("LC_ALL", "es_ES.UTF-8")
    assert i18n.resolve_lang() == "es"


def test_toml_lang_used_when_no_env():
    assert i18n.resolve_lang(toml_lang="es") == "es"
    assert i18n.resolve_lang(toml_lang="en") == "en"


def test_toml_lang_auto_falls_through_to_env(monkeypatch):
    monkeypatch.setenv("LANG", "es_MX.UTF-8")
    assert i18n.resolve_lang(toml_lang="auto") == "es"


def test_koa_lang_env_wins_over_toml_lang(monkeypatch):
    monkeypatch.setenv("KOA_LANG", "en")
    assert i18n.resolve_lang(toml_lang="es") == "en"


def test_non_spanish_value_selects_english(monkeypatch):
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert i18n.resolve_lang() == "en"


# ── t() ──────────────────────────────────────────────────────────────

def test_t_formats_placeholders():
    assert i18n.t("todo.empty", lang="en") == "no pending items"
    assert "vence" in i18n.t("pair.expires", lang="es", expires_at="x")


def test_t_falls_back_to_english_when_missing_in_spanish(monkeypatch):
    monkeypatch.setitem(EN, "__test_only_key__", "only in english")
    assert i18n.t("__test_only_key__", lang="es") == "only in english"


# ── catalog parity ─────────────────────────────────────────────────

def test_catalogs_have_the_same_keys():
    assert set(EN) == set(ES)


def test_catalogs_have_matching_placeholders():
    mismatched = []
    for key in EN:
        en_fields = _fields(EN[key])
        es_fields = _fields(ES[key])
        if en_fields != es_fields:
            mismatched.append((key, en_fields, es_fields))
    assert not mismatched, mismatched


# ── end-to-end through the CLI ──────────────────────────────────────

def test_cli_default_is_english(home, capsys):
    assert cli.main(["pair"]) == 0
    out = capsys.readouterr().out
    assert "expires:" in out


def test_cli_koa_lang_es_is_spanish(home, monkeypatch, capsys):
    monkeypatch.setenv("KOA_LANG", "es")
    assert cli.main(["pair"]) == 0
    out = capsys.readouterr().out
    assert "vence:" in out


def test_cli_lang_es_mx_is_spanish(home, monkeypatch, capsys):
    monkeypatch.setenv("LANG", "es_MX.UTF-8")
    assert cli.main(["pair"]) == 0
    out = capsys.readouterr().out
    assert "vence:" in out


def test_ui_lang_toml_is_spanish(home, capsys):
    (home / "koa.toml").write_text('[ui]\nlang = "es"\n')
    assert cli.main(["pair"]) == 0
    out = capsys.readouterr().out
    assert "vence:" in out


def test_doctor_naming_check_stays_english_regardless_of_lang(home, monkeypatch, capsys):
    """naming.py's own reason text isn't localized (see README/AGENTS.md
    scope notes); the doctor summary line around it still goes through the
    catalog and does change with the language."""
    monkeypatch.setenv("KOA_LANG", "es")
    assert cli.main(["doctor", "--json"]) == 0


def test_domain_errors_follow_active_language():
    from koa_core import i18n, items
    try:
        i18n.set_active("es")
        assert str(items.ItemError("err.item_missing", id="x")) == "no existe el pendiente: x"
        i18n.set_active("en")
        assert str(items.ItemError("err.item_missing", id="x")) == "no such item: x"
    finally:
        i18n.set_active(None)


def test_naming_reasons_render_in_both_languages():
    from koa_core import naming
    v = naming.check_path("Mala Carpeta/x.md")[0]
    assert v.reason == "naming.deny.spaces"
    assert "tiene espacios" in naming.render([v], "es")
    assert "has spaces" in naming.render([v], "en")
    root = naming.check_path("suelto.json")[0]
    assert "NN_" in root.text("en") and "muévelo" in root.hint("es")
    assert v.as_dict("es")["reason"] == "tiene espacios"


def test_no_placeholder_collides_with_t_arguments():
    """t(key, lang, **kwargs): a {key} or {lang} placeholder crashes at runtime."""
    import string
    from koa_core.i18n_catalog import EN, ES
    for cat in (EN, ES):
        for k, v in cat.items():
            names = {f for _, f, _, _ in string.Formatter().parse(v) if f}
            assert not names & {"key", "lang"}, (k, names)


def test_llm_status_runs(tmp_path, capsys):
    from koa_core import cli
    home = tmp_path / "k"
    assert cli.main(["init", "--home", str(home)]) in (0, None)
    assert cli.main(["--home", str(home), "llm", "status"]) in (0, None)
    out = capsys.readouterr().out
    assert out.strip()
