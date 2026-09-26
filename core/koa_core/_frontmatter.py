"""Frontmatter a mano: ``clave: valor`` entre dos líneas ``---``. Sin YAML."""
from __future__ import annotations


def parse(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    header: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        if ":" in line:
            key, _, val = line.partition(":")
            header[key.strip().lower()] = val.strip()
        i += 1
    body = "\n".join(lines[i + 1 :]).lstrip("\n")
    return header, body
