"""Minimal i18n: no gettext, no .mo compilation, no runtime dependency.

Resolution order for the active language: env ``KOA_LANG`` > ``[ui] lang``
in ``koa.toml`` > ``LC_ALL`` > ``LC_MESSAGES`` > ``LANG`` > default
``"en"``. Any value starting with ``"es"`` (case-insensitive) selects
Spanish; anything else (including an unset/empty value or ``"auto"``)
falls through to the next source, and English if none matches.

Messages live in :mod:`koa_core.i18n_catalog` as two flat dicts (``EN``,
``ES``) keyed by a dotted name, with ``str.format`` placeholders. A
message missing from ``ES`` falls back to ``EN`` at runtime; the test
suite checks both catalogs have the same keys and placeholders so that
never happens in practice.
"""
from __future__ import annotations

import os

from koa_core.i18n_catalog import EN, ES

DEFAULT_LANG = "en"


def _from_value(value: str | None) -> str | None:
    """"es*" (any case) -> "es"; any other non-empty, non-"auto" value ->
    "en"; empty/None/"auto" -> None (keep looking)."""
    if not value:
        return None
    v = value.strip().lower()
    if not v or v == "auto":
        return None
    return "es" if v.startswith("es") else "en"


def resolve_lang(toml_lang: str | None = None) -> str:
    """Resolve the active language. ``toml_lang`` is the already-read
    ``[ui] lang`` value from koa.toml (the caller reads the file; this
    function stays free of any file I/O so it also works before a
    KOA_HOME is known, e.g. building the argparse parser)."""
    for value in (
        os.environ.get("KOA_LANG"),
        toml_lang,
        os.environ.get("LC_ALL"),
        os.environ.get("LC_MESSAGES"),
        os.environ.get("LANG"),
    ):
        lang = _from_value(value)
        if lang:
            return lang
    return DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Translate ``key`` into ``lang`` ("en" or "es"), formatting
    placeholders with ``kwargs``."""
    catalog = ES if lang == "es" else EN
    template = catalog.get(key)
    if template is None:
        template = EN[key]  # missing in ES: fall back to EN (raises if missing there too)
    return template.format(**kwargs) if kwargs else template


# Idioma activo del proceso: lo fija la CLI/API tras leer la config, para que
# los errores del dominio (items, memory, naming) salgan en el idioma correcto
# sin que cada módulo tenga que recibir ``lang``.
_active: str | None = None


def set_active(lang: str | None) -> None:
    global _active
    _active = lang if lang in ("en", "es") else None


def active() -> str:
    return _active or resolve_lang()


class LocalizedError(ValueError):
    """Error con clave de catálogo: se muestra en el idioma activo."""

    def __init__(self, key: str, **params):
        self.key = key
        self.params = params
        super().__init__(key)

    def render(self, lang: str | None = None) -> str:
        return t(self.key, lang or active(), **self.params)

    def __str__(self) -> str:
        return self.render()
