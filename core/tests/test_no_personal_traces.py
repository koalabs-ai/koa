"""The seed carries nothing that points at one concrete machine or account.

If this test fails, something machine-specific (home path, server path, private
IP, API key) slipped into what gets published. Fix it by removing it, not by adding exceptions.
"""
import re
from pathlib import Path

SEED = Path(__file__).resolve().parents[2]
THIS = Path(__file__).resolve()

# Generic shapes: anything that points at one concrete machine or account.
FORBIDDEN = [
    (r"/home/(?!<)[a-z]", "a specific user's home path"),
    (r"/srv/[a-z]", "a specific server path"),
    (r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+", "tailnet (CGNAT) IP"),
    (r"\b192\.168\.\d+\.\d+", "LAN IP"),
    (r"\b10\.(?!0\.2\.)\d+\.\d+\.\d+", "LAN IP (10.0.2.x is QEMU's own network)"),
    (r"(sk-ant-|sk-proj-|sk-api-|sk-cp-|ghp_|AKIA|APP_USR-)[A-Za-z0-9]", "API key shape"),
]


TEXT_SUFFIXES = {".py", ".sh", ".md", ".toml", ".example", ".html", ".js", ".css",
                 ".json", ".webmanifest", ".svg", ".txt", ".gitignore", ""}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def _files():
    for p in SEED.rglob("*"):
        if p.is_dir() or p == THIS or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in TEXT_SUFFIXES or p.name.endswith(".example"):
            yield p


def test_seed_has_no_traces_of_its_author():
    hits = []
    for f in _files():
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for rx, why in FORBIDDEN:
            for m in re.finditer(rx, text, flags=re.IGNORECASE):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{f.relative_to(SEED)}:{line}: {why} ({m.group(0)!r})")
    assert not hits, "author traces in the seed:\n" + "\n".join(hits[:50])
