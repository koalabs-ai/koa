"""Candado de nombres: reglas de nombrado para archivos y carpetas de un KOA.

Motor sin dependencias (sólo stdlib). Lo usan dos lados:

* la semilla (``koa-core names``), con las reglas por defecto de una
  instancia nueva (:data:`DEFAULT_RULES`);
* un KOA ya en uso (con su propio lint de estructura), que le pasa sus
  propias reglas y el árbol que ya existe para no castigar lo heredado.

Idea central — **trinquete**: una ruta que ya existe en ``HEAD`` no se
revisa; sólo lo que nace. Así el candado entra hoy sin exigir migrar años
de nombres viejos de golpe, y lo viejo se arregla con ``scan`` a su ritmo.

Las rutas siempre son relativas a la raíz del workspace, con ``/``.
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from koa_core import i18n

KEBAB = r"[a-z0-9]+(?:-[a-z0-9]+)*"

# Nombres con mayúsculas que la convención de casi todas las herramientas
# espera tal cual. Se aceptan en cualquier nivel.
CANONICAL_CAPS = re.compile(
    r"^(README|AGENTS|CLAUDE|GEMINI|LICENSE|NOTICE|CHANGELOG|CONTRIBUTING|"
    r"SECURITY|CONTEXT|SPEC|Makefile|Dockerfile|Containerfile|Caddyfile|"
    r"Justfile|Procfile|Gemfile|Pipfile)(\.[A-Za-z0-9.]+)?$"
)

# Basura que nunca debe entrar a git, en cualquier nivel.
DENY_ANY: list[tuple[str, str]] = [
    (r"\s", "naming.deny.spaces"),
    (r"[^\x00-\x7f]", "naming.deny.ascii"),
    (r"sync-conflict", "naming.deny.syncthing"),
    (r"\.orig(\.|$)", "naming.deny.orig"),
    (r"\.(bak|backup)(\b|$|[-.])", "naming.deny.bak"),
    (r"~$", "naming.deny.tilde"),
    (r"^#.*#$", "naming.deny.autosave"),
    (r"^\.#", "naming.deny.lock"),
    (r"\.egg-info$", "naming.deny.egg"),
    (r"\(\d+\)", "naming.deny.copy"),
    (r"-(\.[A-Za-z0-9]+)?$", "naming.deny.dash"),
]


@dataclass(frozen=True)
class Violation:
    path: str
    component: str
    rule: str
    reason: str               # clave de catálogo (koa_core.i18n_catalog)
    suggestion: str = ""
    params: tuple = ()        # ((nombre, valor), …) para el texto de ``reason``

    def text(self, lang: str | None = None) -> str:
        return i18n.t(self.reason, lang or i18n.active(), **dict(self.params))

    def hint(self, lang: str | None = None) -> str:
        if self.rule == "root":
            return i18n.t("naming.root_hint", lang or i18n.active())
        return self.suggestion if self.suggestion and self.suggestion != self.component else ""

    def as_dict(self, lang: str | None = None) -> dict:
        return {
            "path": self.path,
            "component": self.component,
            "rule": self.rule,
            "reason_key": self.reason,
            "reason": self.text(lang),
            "suggestion": self.hint(lang),
        }


@dataclass
class Rules:
    """Reglas de nombrado.

    ``root``: regex que debe cumplir cada entrada de la raíz del workspace.
    ``level1``: {glob del padre: regex} para carpetas de primer nivel dentro
    de ese padre (p. ej. ``"05_services": KEBAB``).
    ``skip``: globs de rutas que no se revisan (vendoreado, privado, builds).
    ``allow``: globs de rutas aceptadas aunque rompan una regla (excepciones
    documentadas, p. ej. alias de módulos Python).
    """

    root: list[str] = field(default_factory=list)
    level1: dict[str, str] = field(default_factory=dict)
    level1_files_free: bool = True
    skip: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    deny_any: list[tuple[str, str]] = field(default_factory=lambda: list(DENY_ANY))
    max_len: int = 80

    def _match_any(self, path: str, globs: list[str]) -> bool:
        return any(fnmatch.fnmatchcase(path, g) or fnmatch.fnmatchcase(path + "/", g) for g in globs)

    def skipped(self, path: str) -> bool:
        return self._match_any(path, self.skip)

    def allowed(self, path: str) -> bool:
        return self._match_any(path, self.allow)


# Reglas de una instancia nueva creada desde la semilla.
DEFAULT_RULES = Rules(
    root=[
        rf"^\d{{2}}_{KEBAB}$",           # 01_dotfiles, 99_docs …
        r"^\.[a-z0-9][a-z0-9._-]*$",     # .gitignore, .git, .claude …
        r"^(AGENTS|CLAUDE|README|LICENSE)\.md$",
        r"^koa\.toml$",
        r"^flake\.(nix|lock)$",
    ],
    level1={
        "[0-9][0-9]_*": rf"^([_.]?{KEBAB})$",  # _archive, .github
    },
    skip=[
        "10_personal/*",
        "*/node_modules/*", "*/.venv/*", "*/__pycache__/*", "*/.git/*",
        "*/build/*", "*/dist/*", "*/.svelte-kit/*", "*/target/*",
        "*/_vendor/*",
    ],
)


def suggest(name: str) -> str:
    """Propone un nombre kebab-case ASCII conservando la extensión."""
    stem, dot, ext = name.partition(".") if not name.startswith(".") else (name, "", "")
    s = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    s = re.sub(r"\(\d+\)", "", s)
    s = re.sub(r"sync-conflict-[0-9-]+-[A-Z0-9]+", "", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    ext = ext.lower()
    return f"{s}{dot}{ext}" if s else name


def _is_dir_component(idx: int, parts: list[str], is_dir: bool) -> bool:
    return idx < len(parts) - 1 or is_dir


def check_path(
    path: str,
    rules: Rules = DEFAULT_RULES,
    existing: set[str] | None = None,
    is_dir: bool = False,
) -> list[Violation]:
    """Revisa una ruta relativa a la raíz del workspace.

    ``existing``: conjunto de rutas (carpetas y archivos) que ya existen en
    ``HEAD``. Un componente cuyo prefijo ya existe se considera heredado y no
    se revisa. ``None`` = revisar todo (modo ``scan``).
    """
    path = path.strip("/").replace(os.sep, "/")
    if not path or rules.skipped(path) or rules.allowed(path):
        return []
    parts = path.split("/")
    out: list[Violation] = []
    for i, comp in enumerate(parts):
        prefix = "/".join(parts[: i + 1])
        if existing is not None and prefix in existing:
            continue  # heredado: el trinquete no mira hacia atrás
        if rules.skipped(prefix) or rules.allowed(prefix):
            return out
        comp_is_dir = _is_dir_component(i, parts, is_dir)
        for rx, why in rules.deny_any:
            if re.search(rx, comp):
                out.append(Violation(prefix, comp, "deny", why, suggest(comp)))
                break
        else:
            if len(comp) > rules.max_len:
                out.append(Violation(prefix, comp, "length", "naming.length",
                                     params=(("n", len(comp)), ("max", rules.max_len))))
            if i == 0 and rules.root:
                if not any(re.match(rx, comp) for rx in rules.root):
                    out.append(Violation(
                        prefix, comp, "root",
                        "naming.root", "",
                    ))
            elif i == 1:
                for parent_glob, rx in rules.level1.items():
                    if fnmatch.fnmatchcase(parts[0], parent_glob):
                        if not comp_is_dir and rules.level1_files_free:
                            break
                        if CANONICAL_CAPS.match(comp):
                            break
                        if not re.match(rx, comp):
                            out.append(Violation(
                                prefix, comp, "level1",
                                "naming.level1",
                                suggest(comp),
                            ))
                        break
        if out:
            # Un componente malo basta; lo de abajo hereda el problema.
            return out
    return out


# ─── Fuentes de rutas ────────────────────────────────────────────────

SKIP_WALK = {".git", "node_modules", ".venv", "__pycache__", "build", "dist",
             ".svelte-kit", "target", ".pytest_cache", ".ruff_cache", ".mypy_cache"}


def scan(root: Path, rules: Rules = DEFAULT_RULES, max_depth: int = 6) -> list[Violation]:
    """Revisa el árbol completo bajo ``root`` (sin trinquete)."""
    root = Path(root)
    out: list[Violation] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        dirnames[:] = [d for d in dirnames if d not in SKIP_WALK]
        if depth >= max_depth:
            dirnames[:] = []
        for name in dirnames:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if rules.skipped(rel):
                continue
            v = check_path(rel, rules, existing=_parents(rel), is_dir=True)
            out.extend(v)
        for name in filenames:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if rules.skipped(rel):
                continue
            out.extend(check_path(rel, rules, existing=_parents(rel)))
    return out


def _parents(rel: str) -> set[str]:
    """En scan cada carpeta se reporta una vez: sus padres cuentan como vistos."""
    parts = rel.split("/")
    return {"/".join(parts[:i]) for i in range(1, len(parts))}


def _git(repo: Path, *args: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [l for l in r.stdout.splitlines() if l]


def staged(repo: Path, rules: Rules = DEFAULT_RULES, prefix: str = "") -> list[Violation]:
    """Revisa sólo lo que nace en el commit (``git diff --cached``, A y R).

    ``prefix``: ruta del repo dentro del workspace (p. ej. ``"05_services/"``
    para un submódulo), para evaluar contra las reglas del workspace.
    """
    repo = Path(repo)
    new = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=AR", "-z")
    if new and "\x00" in new[0]:
        new = [p for p in new[0].split("\x00") if p]
    existing_raw = _git(repo, "ls-tree", "-r", "-t", "--name-only", "HEAD")
    existing = {prefix + p for p in existing_raw}
    if prefix:
        # los ancestros del prefijo existen por definición
        pp = prefix.strip("/").split("/")
        existing |= {"/".join(pp[: i + 1]) for i in range(len(pp))}
    out: list[Violation] = []
    seen: set[str] = set()
    for p in new:
        for v in check_path(prefix + p, rules, existing=existing):
            if v.path not in seen:
                seen.add(v.path)
                out.append(v)
    return out


def render(violations: list[Violation], lang: str | None = None) -> str:
    lang = lang or i18n.active()
    if not violations:
        return i18n.t("naming.ok", lang)
    lines = [i18n.t("naming.count", lang, n=len(violations))]
    for v in violations:
        hint = v.hint(lang)
        lines.append(f"  · {v.path}: {v.text(lang)}" + (f"  → {hint}" if hint else ""))
    return "\n".join(lines)
