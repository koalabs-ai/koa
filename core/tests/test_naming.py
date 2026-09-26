import subprocess
from pathlib import Path

from koa_core import naming as n


def rules_of(vs):
    return [v.rule for v in vs]


def test_root_only_admits_numbered_dirs_and_entry_files():
    assert n.check_path("05_services/x/app.py") == []
    assert n.check_path("AGENTS.md") == []
    assert n.check_path("koa.toml") == []
    assert n.check_path(".gitignore") == []
    assert rules_of(n.check_path("b8.json")) == ["root"]
    assert rules_of(n.check_path("diagrams/a.png")) == ["root"]
    assert rules_of(n.check_path("Services/x")) == ["root"]


def test_level1_dirs_are_kebab():
    assert n.check_path("11_work/panaderia-luz/README.md") == []
    assert n.check_path("99_docs/_archive/x.md") == []
    v = n.check_path("11_work/Proyecto/README.md")
    assert rules_of(v) == ["level1"] and v[0].suggestion == "proyecto"
    assert rules_of(n.check_path("07_tools/koa_search/x.py")) == ["level1"]


def test_level1_files_and_canonical_caps_are_free():
    assert n.check_path("99_docs/2026-09-25-reporte.md") == []
    assert n.check_path("04_llm/README.md") == []
    assert n.check_path("05_services/Caddyfile") == []


def test_deny_any_level():
    assert rules_of(n.check_path("99_docs/plans/foo.md.orig.123")) == ["deny"]
    assert rules_of(n.check_path("02_emacs/lisp/ui.sync-conflict-20260514-1-AB.org")) == ["deny"]
    assert rules_of(n.check_path("11_work/menu/Menú simple.pdf")) == ["deny"]
    assert rules_of(n.check_path("05_services/x/x.egg-info/PKG-INFO")) == ["deny"]
    assert rules_of(n.check_path("06_data/redash (1).pem")) == ["deny"]
    assert rules_of(n.check_path("99_docs/plans/slug-cortado-.md")) == ["deny"]


def test_deep_code_names_are_not_policed():
    assert n.check_path("05_services/hub/src/routes/[slug]/+page.svelte") == []
    assert n.check_path("05_services/hub/src/lib/Button.svelte") == []
    assert n.check_path("07_tools/x/koa_x/__init__.py") == []


def test_skip_private_and_vendored():
    assert n.check_path("10_personal/Documentos/Carta (1).pdf") == []
    assert n.check_path("05_services/hub/node_modules/A B/x.js") == []


def test_ratchet_ignores_inherited_paths():
    existing = {"11_work", "11_work/Proyecto"}
    assert n.check_path("11_work/Proyecto/nuevo.md", existing=existing) == []
    # pero lo nuevo dentro de lo heredado sí se revisa
    assert rules_of(n.check_path("11_work/Proyecto/copia (1).md", existing=existing)) == ["deny"]


def test_suggest():
    assert n.suggest("Menú Simple (1).pdf") == "menu-simple.pdf"
    assert n.suggest("koa_search") == "koa-search"
    assert n.suggest("CamelCase") == "camel-case"


def test_scan_reports_each_bad_dir_once(tmp_path: Path):
    (tmp_path / "11_work" / "Mala Carpeta").mkdir(parents=True)
    (tmp_path / "11_work" / "Mala Carpeta" / "a.md").write_text("x")
    (tmp_path / "11_work" / "buena").mkdir()
    (tmp_path / "suelto.json").write_text("{}")
    vs = n.scan(tmp_path)
    paths = sorted(v.path for v in vs)
    assert paths == ["11_work/Mala Carpeta", "suelto.json"]


def test_staged_only_checks_new_paths(tmp_path: Path):
    def g(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (tmp_path / "Viejo.txt").write_text("x")
    g("add", ".")
    g("commit", "-qm", "init")
    (tmp_path / "Viejo.txt").write_text("y")          # modificado: no cuenta
    (tmp_path / "otro nuevo.txt").write_text("z")     # nuevo y malo
    g("add", ".")
    vs = n.staged(tmp_path, n.Rules(skip=[]))
    assert [v.path for v in vs] == ["otro nuevo.txt"]


def test_staged_with_prefix_evaluates_workspace_rules(tmp_path: Path):
    def g(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (tmp_path / "Legacy").mkdir()
    (tmp_path / "Legacy" / "a").write_text("x")
    g("add", ".")
    g("commit", "-qm", "init")
    (tmp_path / "Legacy" / "b").write_text("x")
    (tmp_path / "NuevoServicio").mkdir()
    (tmp_path / "NuevoServicio" / "a").write_text("x")
    g("add", ".")
    vs = n.staged(tmp_path, prefix="05_services/")
    assert [v.path for v in vs] == ["05_services/NuevoServicio"]
