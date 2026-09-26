"""Parser mínimo de TOML para cuando ``tomllib`` no existe (Python 3.10).

Sólo entiende el subconjunto que escribimos nosotros mismos en koa.toml:
tablas ``[seccion]``, claves ``clave = valor`` con valor string, int, bool
o lista de strings. Nada de tablas anidadas, fechas, floats con exponente,
strings multilínea, etc. Si el árbol tiene ``tomllib`` (3.11+) se usa ese
en su lugar; este módulo es sólo el respaldo para 3.10.
"""
from __future__ import annotations

import re

_STR = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
_ARR = re.compile(r"^\[(.*)\]$", re.DOTALL)


def _unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n").replace("\\t", "\t")


def _parse_scalar(raw: str):
    raw = raw.strip()
    m = _STR.match(raw)
    if m:
        return _unescape(m.group(1))
    if raw == "true":
        return True
    if raw == "false":
        return False
    m = _ARR.match(raw)
    if m:
        inner = m.group(1).strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_top_level(inner)]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _split_top_level(s: str) -> list[str]:
    out, depth, cur, in_str = [], 0, "", False
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            cur += c
            if c == "\\":
                i += 1
                if i < len(s):
                    cur += s[i]
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            cur += c
        elif c == "[":
            depth += 1
            cur += c
        elif c == "]":
            depth -= 1
            cur += c
        elif c == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        out.append(cur.strip())
    return out


def loads(text: str) -> dict:
    """Parsea texto TOML plano a un dict de dicts (tablas de un solo nivel)."""
    root: dict = {}
    table = root
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]") and "=" not in line.split("]")[0]:
            name = line[1:-1].strip()
            table = root.setdefault(name, {})
            continue
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip().strip('"')
        # una línea puede seguir en la siguiente si el array no cerró
        value_text = rest.strip()
        if value_text.count("[") > value_text.count("]"):
            buf = [value_text]
            # (no lo necesitamos en la práctica: nuestros arrays van en una línea)
            value_text = " ".join(buf)
        table[key] = _parse_scalar(value_text)
    return root
