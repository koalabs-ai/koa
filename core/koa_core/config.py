"""Carga de configuración: koa.toml + variables de entorno.

Prioridad del token: ``KOA_TOKEN`` (env) > archivo de token > ``[api] token``
en koa.toml (compatibilidad; ``koa-core doctor`` avisa si lo encuentra ahi).
El resto: variable de entorno > koa.toml > default. Todo relativo a
KOA_HOME (env ``KOA_HOME``, default ``~/koa``).
"""
from __future__ import annotations

import getpass
import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:  # pragma: no cover - sólo en 3.10
    from koa_core import _toml as tomllib  # type: ignore[no-redef]

from koa_core import i18n as i18nmod


def default_toml(lang: str = i18nmod.DEFAULT_LANG) -> str:
    """koa.toml written by ``koa-core init`` when there isn't one yet, in
    the language ``koa-core init`` resolved for the run. Keep it in sync
    with the repo's ``koa.toml.example`` if you change something here."""
    return i18nmod.t("config.default_toml", lang=lang)


# Compatibilidad: constante en inglés para quien importaba el valor viejo.
DEFAULT_TOML = default_toml("en")


def default_agent() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "agent"
    host = socket.gethostname().split(".")[0] or "local"
    return f"{user}@{host}"


@dataclass
class Config:
    home: Path
    host: str = "127.0.0.1"
    port: int = 8700
    token: str = ""
    db_path: Path | None = None
    agent: str = ""
    token_source: str = "none"  # "env" | "file" | "toml" | "none"
    code_ttl_s: int = 600
    lang: str = i18nmod.DEFAULT_LANG  # "en" | "es", resolved by load_config()
    llm_provider: str = ""            # "" | "anthropic" | "openai-compatible"
    llm_model: str = ""
    llm_base_url: str = ""            # openai-compatible only

    def __post_init__(self):
        self.home = Path(self.home).expanduser().resolve()
        if self.db_path is None:
            self.db_path = self.home / "06_data" / "koa-core.sqlite"
        else:
            self.db_path = Path(self.db_path)
            if not self.db_path.is_absolute():
                self.db_path = self.home / self.db_path
        if not self.agent:
            self.agent = os.environ.get("KOA_AGENT", default_agent())

    @property
    def toml_path(self) -> Path:
        return self.home / "koa.toml"

    @property
    def memory_dir(self) -> Path:
        return self.home / "06_data" / "memory"

    @property
    def plans_dir(self) -> Path:
        return self.home / "99_docs" / "plans"

    @property
    def activity_log_path(self) -> Path:
        return self.home / "04_llm" / "activity.jsonl"

    @property
    def agents_md_path(self) -> Path:
        return self.home / "AGENTS.md"

    @property
    def token_path(self) -> Path:
        return self.home / "10_personal" / "secrets" / "koa-core.token"


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_token_file(path: Path) -> str:
    """Lee la primera linea de un archivo de token. Vacio si no existe o esta vacio."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def write_token_file(path: Path, token: str) -> None:
    """Escribe el token en ``path`` con permisos 0600 (dirs 0700)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    # Nace 0600: write_text + chmod lo dejaba legible (umask 022) un instante.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(token.strip() + "\n")
    try:
        os.chmod(path, 0o600)  # por si el archivo ya existía con otros permisos
    except OSError:
        pass


_TOKEN_LINE = re.compile(r'^(?P<pre>\s*token\s*=\s*)(?P<val>"(?:[^"\\]|\\.)*"|\S+)(?P<post>.*)$')


def strip_toml_token(toml_path: Path) -> bool:
    """Vacia el valor de ``[api].token`` en koa.toml si tenia algo (deja la llave
    para no romper el archivo). Devuelve True si cambio algo."""
    toml_path = Path(toml_path)
    if not toml_path.exists():
        return False
    text = toml_path.read_text(encoding="utf-8")
    section = ""
    changed = False
    out_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            out_lines.append(line)
            continue
        if section == "api":
            body = line[:-1] if line.endswith("\n") else line
            m = _TOKEN_LINE.match(body)
            if m and m.group("val") != '""':
                newline = f'{m.group("pre")}""{m.group("post")}'
                if line.endswith("\n"):
                    newline += "\n"
                out_lines.append(newline)
                changed = True
                continue
        out_lines.append(line)
    if changed:
        toml_path.write_text("".join(out_lines), encoding="utf-8")
    return changed


def write_llm_config(toml_path: Path, provider: str, model: str, base_url: str) -> None:
    """Rewrites (or creates) the ``[llm]`` section of ``koa.toml`` — the
    provider, model and base_url only. The API key itself never goes here
    (see :mod:`koa_core.secrets`); this is the one place ``koa-core llm
    setup`` touches the config file."""
    toml_path = Path(toml_path)
    lines = toml_path.read_text(encoding="utf-8").splitlines(keepends=True) if toml_path.exists() else []
    block = (
        "[llm]\n"
        f'provider = "{provider}"\n'
        f'model = "{model}"\n'
        f'base_url = "{base_url}"\n'
    )
    start = end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[llm]":
            start = i
        elif start is not None and end is None and stripped.startswith("[") and stripped.endswith("]"):
            end = i
    if start is not None:
        lines[start : (end if end is not None else len(lines))] = [block]
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines:
            lines.append("\n")
        lines.append(block)
    toml_path.write_text("".join(lines), encoding="utf-8")


def load_config(home: str | Path | None = None) -> Config:
    """Arma la config final: env > koa.toml > default.

    El token es la excepcion: ``KOA_TOKEN`` (env) > archivo de token en
    ``10_personal/secrets/koa-core.token`` > ``[api] token`` en koa.toml (solo
    por compatibilidad; ``doctor`` avisa si lo encuentra ahi).
    """
    home = Path(home or os.environ.get("KOA_HOME", "~/koa")).expanduser()
    data = _read_toml((home / "koa.toml"))
    api = data.get("api", {})
    db = data.get("db", {})
    pairing = data.get("pairing", {})
    ui = data.get("ui", {})
    llm = data.get("llm", {})

    def env_or(name: str, current):
        return os.environ.get(name, current)

    host = env_or("KOA_HOST", api.get("host", "127.0.0.1"))
    port = int(env_or("KOA_PORT", api.get("port", 8700)))
    db_path = env_or("KOA_DB_PATH", db.get("path", "06_data/koa-core.sqlite"))
    agent = os.environ.get("KOA_AGENT", "")
    code_ttl_s = int(env_or("KOA_PAIRING_CODE_TTL_S", pairing.get("code_ttl_s", 600)))
    lang = i18nmod.resolve_lang(ui.get("lang"))

    cfg = Config(
        home=home, host=host, port=port, db_path=db_path, agent=agent,
        code_ttl_s=code_ttl_s, lang=lang,
        llm_provider=llm.get("provider", "") or "",
        llm_model=llm.get("model", "") or "",
        llm_base_url=llm.get("base_url", "") or "",
    )

    env_token = os.environ.get("KOA_TOKEN", "")
    toml_token = api.get("token", "") or ""
    if env_token:
        cfg.token, cfg.token_source = env_token, "env"
    else:
        file_token = read_token_file(cfg.token_path)
        if file_token:
            cfg.token, cfg.token_source = file_token, "file"
        elif toml_token:
            cfg.token, cfg.token_source = toml_token, "toml"
        else:
            cfg.token, cfg.token_source = "", "none"
    return cfg
