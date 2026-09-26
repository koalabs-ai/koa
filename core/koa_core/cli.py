"""CLI de koa-core: ``koa-core <comando> ...``."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from koa_core import __version__
from koa_core import activity as activitymod
from koa_core import claims as claimsmod
from koa_core import config as configmod
from koa_core import db as dbmod
from koa_core import devices as devicesmod
from koa_core import i18n
from koa_core import items as itemsmod
from koa_core import memory as memorymod
from koa_core import naming
from koa_core import plans as plansmod
from koa_core import secrets as secretsmod

HOOK_MARKER = "# koa-core-names-hook"
HOOK_BODY = f"""#!/bin/sh
{HOOK_MARKER} — installed by `koa-core hooks install`. Don't delete it by hand;
# run `koa-core hooks install` again if you need to regenerate it.
if [ "${{KOA_SKIP_NAMING:-0}}" != "1" ]; then
    koa-core names --staged || exit 1
fi
"""


# ─── helpers compartidos ────────────────────────────────────────────

def _out(args, payload, human: str) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(human)


def _cfg(args) -> configmod.Config:
    cfg = configmod.load_config(getattr(args, "home", None))
    i18n.set_active(cfg.lang)
    return cfg


def _conn(cfg):
    return dbmod.connect(cfg.db_path)


# ─── init ───────────────────────────────────────────────────────────

def _seed_dir() -> Path:
    env = os.environ.get("KOA_SEED_DIR")
    if env:
        return Path(env)
    # core/koa_core/cli.py -> core -> koa-semilla ; skeleton lives next to core/
    return Path(__file__).resolve().parent.parent.parent / "skeleton"


def _copy_seed(seed: Path, home: Path, force: bool) -> tuple[int, int]:
    copied, skipped = 0, 0
    for src in seed.rglob("*"):
        rel = src.relative_to(seed)
        dst = home / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if dst.exists() and not force:
            skipped += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    return copied, skipped


def _git_init_if_needed(home: Path, lang: str) -> str:
    if not shutil.which("git"):
        return i18n.t("init.git_missing", lang=lang)
    if (home / ".git").exists():
        return i18n.t("init.git_already", lang=lang)
    r = subprocess.run(["git", "init", "-q"], cwd=home, capture_output=True, text=True)
    if r.returncode == 0:
        return i18n.t("init.git_done", lang=lang)
    return i18n.t("init.git_failed", lang=lang, err=r.stderr.strip())


def cmd_init(args) -> int:
    lang = i18n.resolve_lang()
    home = Path(args.home or os.environ.get("KOA_HOME", "~/koa")).expanduser().resolve()
    seed = _seed_dir()
    if not seed.exists():
        print(i18n.t("init.no_seed", lang=lang, seed=seed), file=sys.stderr)
        return 1
    home.mkdir(parents=True, exist_ok=True)
    copied, skipped = _copy_seed(seed, home, args.force)
    toml_path = home / "koa.toml"
    wrote_toml = False
    if not toml_path.exists() or args.force:
        toml_path.write_text(configmod.default_toml(lang), encoding="utf-8")
        wrote_toml = True
    for sub in ("06_data/memory", "04_llm", "99_docs/plans"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    git_msg = _git_init_if_needed(home, lang)
    hook_msg = _install_hook(home, lang)
    print(i18n.t("init.done", lang=lang, home=home))
    print(i18n.t("init.seed_summary", lang=lang, copied=copied, skipped=skipped))
    toml_status = i18n.t("init.toml_written" if wrote_toml else "init.toml_kept", lang=lang)
    print(f"  koa.toml: {toml_status}")
    print(f"  {git_msg}")
    print(f"  {hook_msg}")
    return 0


# ─── doctor ─────────────────────────────────────────────────────────

def _check_port_or_health(cfg) -> tuple[str, str]:
    from koa_core import api as apimod

    lang = cfg.lang
    if apimod.port_is_free(cfg.host, cfg.port):
        return "PASS", i18n.t("doctor.port_free", lang=lang, port=cfg.port)
    import urllib.request

    url = f"http://{cfg.host}:{cfg.port}/v1/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read())
        if data.get("ok"):
            return "PASS", i18n.t("doctor.port_healthy", lang=lang, url=url)
        return "FAIL", i18n.t("doctor.port_unhealthy", lang=lang, url=url)
    except Exception as e:
        return "FAIL", i18n.t("doctor.port_busy", lang=lang, port=cfg.port, err=e)


def _check_token(cfg: configmod.Config) -> tuple[str, str]:
    lang = cfg.lang
    if cfg.token_source == "file":
        try:
            mode = cfg.token_path.stat().st_mode & 0o777
        except OSError as e:
            return "WARN", i18n.t("doctor.token_perm_unreadable", lang=lang, path=cfg.token_path, err=e)
        if mode == 0o600:
            return "PASS", str(cfg.token_path)
        return "WARN", i18n.t(
            "doctor.token_bad_perms", lang=lang, path=cfg.token_path, mode=oct(mode),
        )
    if cfg.token_source == "toml":
        return "WARN", i18n.t("doctor.token_in_toml", lang=lang)
    if cfg.token_source == "env":
        return "PASS", i18n.t("doctor.token_env", lang=lang)
    if cfg.host in ("127.0.0.1", "localhost", "::1"):
        return "PASS", i18n.t("doctor.token_open", lang=lang)
    return "FAIL", i18n.t("doctor.token_exposed", lang=lang)


def cmd_doctor(args) -> int:
    cfg = _cfg(args)
    lang = cfg.lang
    checks: list[dict] = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    if sys.version_info >= (3, 10):
        add("python", "PASS", sys.version.split()[0])
    else:
        add("python", "FAIL", i18n.t("doctor.python_fail", lang=lang, have=sys.version.split()[0]))

    add("koa_home", "PASS" if cfg.home.is_dir() else "FAIL", str(cfg.home))

    if cfg.toml_path.exists():
        try:
            configmod.load_config(cfg.home)
            add("koa_toml", "PASS", str(cfg.toml_path))
        except Exception as e:
            add("koa_toml", "FAIL", i18n.t("doctor.toml_parse_fail", lang=lang, err=e))
    else:
        add("koa_toml", "WARN", i18n.t("doctor.toml_missing", lang=lang))

    try:
        conn = _conn(cfg)
        version = dbmod.migrate(conn)
        conn.close()
        add("db", "PASS", i18n.t("doctor.db_pass", lang=lang, path=cfg.db_path, version=version))
    except Exception as e:
        add("db", "FAIL", str(e))

    status, detail = _check_port_or_health(cfg)
    add("puerto", status, detail)

    add(
        "git", "PASS" if shutil.which("git") else "WARN",
        shutil.which("git") or i18n.t("doctor.git_missing", lang=lang),
    )

    hook_path = cfg.home / ".git" / "hooks" / "pre-commit"
    override = _hooks_path_override(cfg.home) if (cfg.home / ".git").exists() else None
    if override:
        add("hook_nombres", "WARN", i18n.t("hooks.override_hint", lang=lang, value=override, home=cfg.home))
    elif hook_path.exists() and HOOK_MARKER in hook_path.read_text(encoding="utf-8", errors="ignore"):
        add("hook_nombres", "PASS", str(hook_path))
    else:
        add("hook_nombres", "WARN", i18n.t("doctor.hook_not_installed", lang=lang))

    try:
        violations = naming.scan(cfg.home)
        add("nombres", "PASS" if not violations else "WARN",
            i18n.t("doctor.naming_issues", lang=lang, n=len(violations)))
    except Exception as e:
        add("nombres", "WARN", str(e))

    status, detail = _check_token(cfg)
    add("token", status, detail)

    try:
        conn = _conn(cfg)
        n = devicesmod.count_active(conn)
        conn.close()
        add("dispositivos", "PASS", i18n.t("doctor.devices_active", lang=lang, n=n))
    except Exception as e:
        add("dispositivos", "WARN", str(e))

    if getattr(args, "json", False):
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        for c in checks:
            print(f"[{c['status']:4}] {c['check']}: {c['detail']}")
    return 1 if any(c["status"] == "FAIL" for c in checks) else 0


# ─── serve ──────────────────────────────────────────────────────────

def cmd_serve(args) -> int:
    from koa_core import api as apimod

    cfg = _cfg(args)
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port
    apimod.serve(cfg)
    return 0


# ─── todo ───────────────────────────────────────────────────────────

def cmd_todo(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        if args.todo_cmd == "list":
            rows = itemsmod.list_items(conn, status=args.status, tag=args.tag, plan=args.plan, q=args.q)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                if not rows:
                    print(i18n.t("todo.empty", lang=cfg.lang))
                for r in rows:
                    tags = f" #{' #'.join(r['tags'])}" if r["tags"] else ""
                    print(f"{r['id'][:8]}  [{r['status']:5}] {r['title']}{tags}")
            return 0
        if args.todo_cmd == "add":
            it = itemsmod.create(conn, args.title, body=args.body or "", tags=args.tag, plan=args.plan)
            activitymod.log(conn, cfg.activity_log_path, cfg.agent, it["title"], "todo_add")
            _out(args, it, i18n.t("todo.created", lang=cfg.lang, id=it["id"], title=it["title"]))
            return 0
        if args.todo_cmd in ("start", "done", "drop"):
            status = {"start": "doing", "done": "done", "drop": "dropped"}[args.todo_cmd]
            try:
                it = itemsmod.update(conn, args.id, status=status, evidence=args.evidence)
            except itemsmod.ItemError as e:
                print(i18n.t("common.error", lang=cfg.lang, err=e), file=sys.stderr)
                return 1
            activitymod.log(conn, cfg.activity_log_path, cfg.agent, it["title"], f"todo_{args.todo_cmd}")
            _out(args, it, f"{args.todo_cmd}: {it['id']}  {it['title']} -> {it['status']}")
            return 0
    finally:
        conn.close()
    return 1


# ─── plans ──────────────────────────────────────────────────────────

def cmd_plans(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        if args.plans_cmd == "sync":
            results = plansmod.sync(conn, cfg.plans_dir)
            if getattr(args, "json", False):
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                if not results:
                    print(i18n.t("plans.none", lang=cfg.lang, dir=cfg.plans_dir))
                for r in results:
                    print(i18n.t(
                        "plans.sync_line", lang=cfg.lang, slug=r["slug"], tasks=r["tasks"],
                        created=r["created"], completed=r["completed"], orphans=len(r["orphans"]),
                    ))
            return 0
        if args.plans_cmd == "list":
            rows = plansmod.list_plans(conn)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for r in rows:
                    status = r["status"] or i18n.t("plans.no_status", lang=cfg.lang)
                    print(i18n.t("plans.list_line", lang=cfg.lang, slug=r["slug"], title=r["title"], status=status))
            return 0
    finally:
        conn.close()
    return 1


# ─── mem ────────────────────────────────────────────────────────────

def cmd_mem(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        if args.mem_cmd == "add":
            try:
                entry = memorymod.add(conn, cfg.memory_dir, args.type, args.name, args.description or "", args.body or "")
            except memorymod.MemoryError as e:
                print(i18n.t("common.error", lang=cfg.lang, err=e), file=sys.stderr)
                return 1
            activitymod.log(conn, cfg.activity_log_path, cfg.agent, entry["name"], "memory_add")
            _out(args, entry, i18n.t("mem.saved", lang=cfg.lang, path=entry["path"]))
            return 0
        if args.mem_cmd == "recall":
            hits = memorymod.recall(conn, args.query, args.limit)
            if getattr(args, "json", False):
                print(json.dumps(hits, ensure_ascii=False, indent=2))
            else:
                if not hits:
                    print(i18n.t("common.no_results", lang=cfg.lang))
                for h in hits:
                    print(f"[{h['type']}] {h['name']} — {h['description']}\n    {h.get('snippet', '')}")
            return 0
        if args.mem_cmd == "list":
            rows = memorymod.list_all(conn)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for r in rows:
                    print(f"[{r['type']}] {r['name']} — {r['description']}")
            return 0
        if args.mem_cmd == "reindex":
            n = memorymod.reindex(conn, cfg.memory_dir)
            print(i18n.t("mem.reindexed", lang=cfg.lang, n=n))
            return 0
    finally:
        conn.close()
    return 1


# ─── claim ──────────────────────────────────────────────────────────

def cmd_claim(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        if args.claim_cmd == "acquire":
            try:
                claim = claimsmod.acquire(conn, args.target, cfg.agent, args.intent or "")
            except claimsmod.ClaimHeld as e:
                print(i18n.t("common.error", lang=cfg.lang, err=e), file=sys.stderr)
                return 9
            _out(args, claim, i18n.t(
                "claim.acquired", lang=cfg.lang, id=claim["id"], target=claim["target"],
                expires_at=claim["expires_at"],
            ))
            return 0
        if args.claim_cmd == "release":
            ok = claimsmod.release(conn, args.id)
            print(i18n.t("claim.released" if ok else "claim.not_found", lang=cfg.lang))
            return 0 if ok else 1
        if args.claim_cmd == "list":
            rows = claimsmod.list_claims(conn)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for r in rows:
                    print(i18n.t(
                        "claim.list_line", lang=cfg.lang, id=r["id"][:8], target=r["target"],
                        agent=r["agent"], expires_at=r["expires_at"],
                    ))
            return 0
    finally:
        conn.close()
    return 1


# ─── log / heartbeat ────────────────────────────────────────────────

def cmd_log(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        entry = activitymod.log(conn, cfg.activity_log_path, cfg.agent, args.text, args.kind)
    finally:
        conn.close()
    _out(args, entry, f"log: {entry['text']}")
    return 0


def cmd_heartbeat(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        hb = activitymod.heartbeat(conn, cfg.agent, args.note or "")
    finally:
        conn.close()
    _out(args, hb, f"heartbeat: {hb['agent']} @ {hb['last_seen']}")
    return 0


# ─── names ──────────────────────────────────────────────────────────

def cmd_names(args) -> int:
    cfg = _cfg(args)
    root = Path(args.path) if args.path else cfg.home
    if args.staged:
        violations = naming.staged(root)
    else:
        violations = naming.scan(root)
    if getattr(args, "json", False):
        print(json.dumps([v.as_dict() for v in violations], ensure_ascii=False, indent=2))
    else:
        print(naming.render(violations))
    return 1 if (args.staged and violations) else 0


# ─── hooks ──────────────────────────────────────────────────────────

def _hooks_path_override(home: Path) -> str | None:
    """core.hooksPath (local o global) hace que git ignore .git/hooks: el
    candado quedaría instalado pero sin correr nunca, en silencio."""
    if not shutil.which("git"):
        return None
    r = subprocess.run(["git", "-C", str(home), "config", "--get", "core.hooksPath"],
                       capture_output=True, text=True)
    value = r.stdout.strip()
    if not value:
        return None
    resolved = Path(value).expanduser()
    if not resolved.is_absolute():
        resolved = home / resolved
    if resolved.resolve() == (home / ".git" / "hooks").resolve():
        return None
    return value


def _install_hook(home: Path, lang: str) -> str:
    git_dir = home / ".git"
    if not git_dir.exists():
        return i18n.t("hooks.no_git", lang=lang)
    override = _hooks_path_override(home)
    if override:
        warning = i18n.t("common.warning_prefix", lang=lang) + i18n.t(
            "hooks.override_hint", lang=lang, value=override, home=home,
        )
        print(warning, file=sys.stderr)
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_commit = hooks_dir / "pre-commit"
    if pre_commit.exists():
        current = pre_commit.read_text(encoding="utf-8", errors="ignore")
        if HOOK_MARKER in current:
            pre_commit.write_text(HOOK_BODY, encoding="utf-8")
            msg = i18n.t("hooks.updated", lang=lang)
        else:
            pre_commit.write_text(current.rstrip("\n") + "\n\n" + HOOK_BODY, encoding="utf-8")
            msg = i18n.t("hooks.chained", lang=lang)
    else:
        pre_commit.write_text(HOOK_BODY, encoding="utf-8")
        msg = i18n.t("hooks.installed", lang=lang)
    pre_commit.chmod(0o755)
    return msg


def cmd_hooks(args) -> int:
    if args.hooks_cmd == "install":
        cfg = _cfg(args)
        print(_install_hook(cfg.home, cfg.lang))
        return 0
    return 1


# ─── pair / devices / token ─────────────────────────────────────────

def cmd_pair(args) -> int:
    """Genera un codigo de emparejamiento. Corre directo contra la base (el
    acceso local al archivo YA es ser el dueño de esta maquina)."""
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        code, expires_at = devicesmod.start_pairing(
            conn, admin=args.admin, created_by=cfg.agent, ttl_s=cfg.code_ttl_s,
        )
    finally:
        conn.close()
    base = (args.url or f"http://{cfg.host}:{cfg.port}").rstrip("/")
    pair_url = f"{base}/pair#code={code}"
    if getattr(args, "json", False):
        print(json.dumps({"code": code, "expires_at": expires_at, "pair_url": pair_url}, ensure_ascii=False))
        return 0
    print()
    print(f"    {code}")
    print()
    print(i18n.t("pair.expires", lang=cfg.lang, expires_at=expires_at))
    print(i18n.t("pair.open_url", lang=cfg.lang, url=pair_url))
    print()
    if shutil.which("qrencode"):
        subprocess.run(["qrencode", "-t", "ANSIUTF8", pair_url])
    else:
        print(i18n.t("pair.install_qrencode", lang=cfg.lang))
    return 0


def cmd_devices(args) -> int:
    cfg = _cfg(args)
    conn = _conn(cfg)
    try:
        if args.devices_cmd == "list":
            rows = devicesmod.list_devices(conn)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                if not rows:
                    print(i18n.t("devices.empty", lang=cfg.lang))
                for r in rows:
                    estado = i18n.t(
                        "devices.status_revoked" if r["revoked_at"] else "devices.status_active",
                        lang=cfg.lang,
                    )
                    admin = i18n.t("devices.admin_suffix", lang=cfg.lang) if r["admin"] else ""
                    platform = r["platform"] or i18n.t("devices.no_platform", lang=cfg.lang)
                    seen = r["last_seen_at"] or i18n.t("devices.never_seen", lang=cfg.lang)
                    print(i18n.t(
                        "devices.list_line", lang=cfg.lang, id=r["id"][:8], status=estado,
                        name=r["name"], admin=admin, platform=platform, seen=seen,
                    ))
            return 0
        if args.devices_cmd == "revoke":
            ok = devicesmod.revoke(conn, args.id)
            if ok:
                activitymod.log(conn, cfg.activity_log_path, cfg.agent, args.id, "device_revoke")
            print(i18n.t("devices.revoked" if ok else "devices.revoke_not_found", lang=cfg.lang))
            return 0 if ok else 1
    finally:
        conn.close()
    return 1


def cmd_token(args) -> int:
    cfg = _cfg(args)
    if args.token_cmd == "rotate":
        token = secrets.token_urlsafe(32)
        configmod.write_token_file(cfg.token_path, token)
        moved = configmod.strip_toml_token(cfg.toml_path)
        print(i18n.t("token.rotated", lang=cfg.lang, path=cfg.token_path))
        if moved:
            print(i18n.t("token.toml_cleared", lang=cfg.lang, path=cfg.toml_path))
        print(i18n.t("token.usage_hint", lang=cfg.lang))
        if args.show:
            print(i18n.t("token.value", lang=cfg.lang, token=token))
        return 0
    return 1


# ─── chat (built-in agent) ────────────────────────────────────────────

def cmd_chat(args) -> int:
    cfg = _cfg(args)
    from koa_core import agent as agentmod

    conn = _conn(cfg)
    try:
        if args.list:
            rows = agentmod.list_conversations(conn)
            if getattr(args, "json", False):
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                if not rows:
                    print(i18n.t("chat.list_empty", lang=cfg.lang))
                for r in rows:
                    title = r["title"] or i18n.t("chat.untitled", lang=cfg.lang)
                    print(i18n.t("chat.list_line", lang=cfg.lang, id=r["id"][:8], title=title,
                                 updated_at=r["updated_at"]))
            return 0
        if args.message:
            return _chat_send(cfg, conn, args, args.conversation, args.message)
        return _chat_repl(cfg, conn, args)
    finally:
        conn.close()


def _chat_send(cfg, conn, args, conversation_id, message) -> int:
    from koa_core import agent as agentmod
    from koa_core import llm as llmmod

    try:
        result = agentmod.send_message(cfg, conn, conversation_id, message)
    except llmmod.ProviderUnavailable as e:
        print(i18n.t("common.error", lang=cfg.lang, err=e.render(cfg.lang)), file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["reply"])
        print(i18n.t("chat.usage_line", lang=cfg.lang, **result["usage"]))
    return 0


def _chat_repl(cfg, conn, args) -> int:
    from koa_core import agent as agentmod
    from koa_core import llm as llmmod

    conversation_id = args.conversation
    print(i18n.t("chat.repl_hint", lang=cfg.lang))
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        line = line.strip()
        if not line:
            continue
        if line == "/exit":
            return 0
        if line == "/new":
            conversation_id = None
            print(i18n.t("chat.new_conversation", lang=cfg.lang))
            continue
        try:
            result = agentmod.send_message(cfg, conn, conversation_id, line)
        except llmmod.ProviderUnavailable as e:
            print(i18n.t("common.error", lang=cfg.lang, err=e.render(cfg.lang)))
            continue
        conversation_id = result["conversation_id"]
        print(result["reply"])


# ─── llm (connect a model) ──────────────────────────────────────────

OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"


def cmd_llm(args) -> int:
    if args.llm_cmd == "setup":
        return cmd_llm_setup(args)
    if args.llm_cmd == "status":
        return cmd_llm_status(args)
    if args.llm_cmd == "test":
        return cmd_llm_test(args)
    return 1


def _ask_provider(lang: str) -> str:
    choice = input(i18n.t("llm.setup.ask_provider_prompt", lang=lang)).strip()
    return {"1": "anthropic", "2": "openai", "3": "ollama", "4": "other"}.get(choice, "")


def _ensure_anthropic_sdk(lang: str) -> bool:
    """Installs the `anthropic` SDK into its own venv (never --user, never
    --break-system-packages) and re-execs this process with that venv's
    python so setup can finish in one shot. Returns True if `anthropic` is
    already importable (nothing to do)."""
    from koa_core.llm import anthropic_provider

    if anthropic_provider.available():
        return True
    share_dir = Path(__file__).resolve().parent.parent  # .../share/koa-core (parent of koa_core/)
    venv_dir = share_dir / "venv"
    print(i18n.t("llm.setup.installing_sdk", lang=lang, path=venv_dir))
    r = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], capture_output=True, text=True)
    if r.returncode != 0:
        if "ensurepip" in r.stderr.lower() or "venv" in r.stderr.lower():
            print(i18n.t("llm.setup.venv_missing_apt", lang=lang), file=sys.stderr)
        else:
            print(i18n.t("llm.setup.venv_failed", lang=lang, err=r.stderr.strip()), file=sys.stderr)
        return False
    pip = venv_dir / "bin" / "pip"
    r = subprocess.run([str(pip), "install", "anthropic"], capture_output=True, text=True)
    if r.returncode != 0:
        print(i18n.t("llm.setup.pip_failed", lang=lang, err=r.stderr.strip()), file=sys.stderr)
        return False
    _rewrite_wrapper_to_use_venv(share_dir, venv_dir)
    print(i18n.t("llm.setup.sdk_installed", lang=lang, path=venv_dir))
    if os.environ.get("KOA_LLM_NO_REEXEC") == "1":
        print(i18n.t("llm.setup.restart_hint", lang=lang))
        return False
    venv_python = str(venv_dir / "bin" / "python3")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(share_dir) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    os.execve(venv_python, [venv_python, "-m", "koa_core", *sys.argv[1:]], env)
    return False  # pragma: no cover - execve never returns on success


def _rewrite_wrapper_to_use_venv(share_dir: Path, venv_dir: Path) -> None:
    """Rewrites the installed `koa-core` wrapper (`$PREFIX/bin/koa-core`) so
    it runs with the new venv's python. A dev checkout has no such wrapper;
    nothing to do then."""
    prefix = share_dir.parent.parent  # $PREFIX/share/koa-core -> $PREFIX
    wrapper = prefix / "bin" / "koa-core"
    if not wrapper.exists():
        return
    text = wrapper.read_text(encoding="utf-8")
    venv_python = str(venv_dir / "bin" / "python3")
    new_text = re.sub(r'exec \S+ -m koa_core "\$@"', f'exec {venv_python} -m koa_core "$@"', text)
    wrapper.write_text(new_text, encoding="utf-8")


def cmd_llm_setup(args) -> int:
    cfg = _cfg(args)
    lang = cfg.lang
    provider_choice = args.provider
    if not provider_choice:
        if args.yes:
            print(i18n.t("llm.setup.needs_provider", lang=lang), file=sys.stderr)
            return 1
        provider_choice = _ask_provider(lang)
        if not provider_choice:
            print(i18n.t("llm.setup.invalid_choice", lang=lang), file=sys.stderr)
            return 1

    if provider_choice == "anthropic":
        if not _ensure_anthropic_sdk(lang):
            return 1
        model = args.model or "claude-opus-5"
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key and not args.yes:
            key = getpass.getpass(i18n.t("llm.setup.key_prompt", lang=lang, provider="Anthropic"))
        if not key:
            print(i18n.t("llm.setup.key_missing", lang=lang, env="ANTHROPIC_API_KEY"), file=sys.stderr)
            return 1
        secretsmod.write_key(secretsmod.secrets_path(cfg.home, "anthropic"), "ANTHROPIC_API_KEY", key)
        configmod.write_llm_config(cfg.toml_path, "anthropic", model, "")
        return _llm_test(configmod.load_config(cfg.home))

    if provider_choice not in ("openai", "ollama", "other"):
        return 1

    if provider_choice == "ollama":
        base_url = args.base_url or OLLAMA_BASE_URL
        env_name = ""
    elif provider_choice == "openai":
        base_url = args.base_url or OPENAI_BASE_URL
        env_name = "OPENAI_API_KEY"
    else:
        base_url = args.base_url or ""
        if not base_url:
            print(i18n.t("llm.setup.needs_base_url", lang=lang), file=sys.stderr)
            return 1
        # Otro servidor: nunca se toma OPENAI_API_KEY (es la llave de OpenAI).
        env_name = "KOA_LLM_API_KEY"

    model = args.model or ""
    if not model:
        print(i18n.t("llm.setup.needs_model", lang=lang), file=sys.stderr)
        return 1

    key = os.environ.get(env_name, "") if env_name else ""
    if env_name and not key and not args.yes:
        key = getpass.getpass(i18n.t("llm.setup.key_prompt", lang=lang, provider=provider_choice))
    if key:
        from urllib.parse import urlparse
        secretsmod.write_key(
            secretsmod.secrets_path(cfg.home, "openai-compatible"), "OPENAI_API_KEY", key,
            host=(urlparse(base_url).hostname or "").lower(),
        )
    configmod.write_llm_config(cfg.toml_path, "openai-compatible", model, base_url)
    return _llm_test(configmod.load_config(cfg.home))


def _llm_test(cfg: configmod.Config) -> int:
    from koa_core import llm as llmmod

    try:
        provider = llmmod.for_config(cfg)
    except llmmod.ProviderUnavailable as e:
        print(i18n.t("common.error", lang=cfg.lang, err=e.render(cfg.lang)), file=sys.stderr)
        return 1
    turn = provider.chat(
        [{"role": "user", "content": i18n.t("llm.setup.test_prompt", lang=cfg.lang)}],
        [], i18n.t("llm.setup.test_system", lang=cfg.lang),
    )
    if turn.error is not None:
        print(i18n.t("common.error", lang=cfg.lang, err=turn.error.render(cfg.lang)), file=sys.stderr)
        return 1
    print(i18n.t(
        "llm.setup.test_ok", lang=cfg.lang, model=provider.model,
        input_tokens=turn.usage.get("input_tokens", 0), output_tokens=turn.usage.get("output_tokens", 0),
    ))
    return 0


def cmd_llm_test(args) -> int:
    return _llm_test(_cfg(args))


def cmd_llm_status(args) -> int:
    cfg = _cfg(args)
    provider = cfg.llm_provider
    key_present = bool(secretsmod.resolve_api_key(cfg.home, provider)) if provider else False
    if getattr(args, "json", False):
        print(json.dumps({
            "provider": provider, "model": cfg.llm_model, "base_url": cfg.llm_base_url,
            "key_present": key_present,
        }, ensure_ascii=False))
        return 0
    if not provider:
        print(i18n.t("llm.status.none", lang=cfg.lang))
        return 0
    key_label = i18n.t("llm.status.key_yes" if key_present else "llm.status.key_no", lang=cfg.lang)
    print(i18n.t("llm.status.line", lang=cfg.lang, provider=provider, model=cfg.llm_model or "-", key_state=key_label))
    return 0


# ─── mcp ────────────────────────────────────────────────────────────

def cmd_mcp(args) -> int:
    from koa_core import mcp as mcpmod

    cfg = _cfg(args)
    mcpmod.run_stdio(cfg)
    return 0


# ─── unit install ───────────────────────────────────────────────────

UNIT_TEMPLATE = """[Unit]
Description={description}
After=network.target

[Service]
Type=simple
Environment=KOA_HOME={home}
Environment=PYTHONPATH={pythonpath}
ExecStart={python} -m koa_core serve
Restart=on-failure

[Install]
WantedBy=default.target
"""


def cmd_unit(args) -> int:
    if args.unit_cmd != "install":
        return 1
    cfg = _cfg(args)
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    pythonpath = str(Path(__file__).resolve().parent.parent)
    content = UNIT_TEMPLATE.format(
        description=i18n.t("unit.description", lang=cfg.lang),
        home=cfg.home, pythonpath=pythonpath, python=sys.executable,
    )
    unit_path = unit_dir / "koa-core.service"
    unit_path.write_text(content, encoding="utf-8")
    print(i18n.t("unit.written", lang=cfg.lang, path=unit_path))
    print(i18n.t("unit.enable_hint", lang=cfg.lang))
    return 0


# ─── parser ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    # --home aún no se conoce aquí (es el propio argumento), así que el idioma
    # del parser sólo mira variables de entorno, no [ui] lang en koa.toml.
    lang = i18n.resolve_lang()
    p = argparse.ArgumentParser(prog="koa-core", description=i18n.t("cli.description", lang=lang))
    p.add_argument("--home", help=i18n.t("cli.home_help", lang=lang))
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("version")

    sp = sub.add_parser("init")
    sp.add_argument("--force", action="store_true")
    # --home tambien se acepta despues de "init" (no solo antes, como global);
    # SUPPRESS evita que pise el valor global si no se repite aqui.
    sp.add_argument("--home", default=argparse.SUPPRESS)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("doctor")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("serve")
    sp.add_argument("--host")
    sp.add_argument("--port", type=int)
    sp.set_defaults(func=cmd_serve)

    todo = sub.add_parser("todo")
    todo_sub = todo.add_subparsers(dest="todo_cmd", required=True)
    tl = todo_sub.add_parser("list")
    tl.add_argument("--status")
    tl.add_argument("--tag")
    tl.add_argument("--plan")
    tl.add_argument("--q")
    tl.add_argument("--json", action="store_true")
    ta = todo_sub.add_parser("add")
    ta.add_argument("title")
    ta.add_argument("--body")
    ta.add_argument("--tag", action="append")
    ta.add_argument("--plan")
    ta.add_argument("--json", action="store_true")
    for name in ("start", "done", "drop"):
        t = todo_sub.add_parser(name)
        t.add_argument("id")
        t.add_argument("--evidence")
        t.add_argument("--json", action="store_true")
    todo.set_defaults(func=cmd_todo)

    plansp = sub.add_parser("plans")
    plans_sub = plansp.add_subparsers(dest="plans_cmd", required=True)
    for name in ("sync", "list"):
        pp = plans_sub.add_parser(name)
        pp.add_argument("--json", action="store_true")
    plansp.set_defaults(func=cmd_plans)

    mem = sub.add_parser("mem")
    mem_sub = mem.add_subparsers(dest="mem_cmd", required=True)
    ma = mem_sub.add_parser("add")
    ma.add_argument("--type", required=True, choices=list(memorymod.TYPES))
    ma.add_argument("--name", required=True)
    ma.add_argument("--description")
    ma.add_argument("--body")
    ma.add_argument("--json", action="store_true")
    mr = mem_sub.add_parser("recall")
    mr.add_argument("query")
    mr.add_argument("--limit", type=int, default=10)
    mr.add_argument("--json", action="store_true")
    ml = mem_sub.add_parser("list")
    ml.add_argument("--json", action="store_true")
    mem_sub.add_parser("reindex")
    mem.set_defaults(func=cmd_mem)

    claim = sub.add_parser("claim")
    claim_sub = claim.add_subparsers(dest="claim_cmd", required=True)
    ca = claim_sub.add_parser("acquire")
    ca.add_argument("target")
    ca.add_argument("--intent")
    ca.add_argument("--json", action="store_true")
    cr = claim_sub.add_parser("release")
    cr.add_argument("id")
    cl = claim_sub.add_parser("list")
    cl.add_argument("--json", action="store_true")
    claim.set_defaults(func=cmd_claim)

    sp = sub.add_parser("log")
    sp.add_argument("text")
    sp.add_argument("--kind", default="log")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("heartbeat")
    sp.add_argument("--note")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_heartbeat)

    sp = sub.add_parser("names")
    group = sp.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true")
    group.add_argument("--scan", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--path")
    sp.set_defaults(func=cmd_names)

    hooks = sub.add_parser("hooks")
    hooks_sub = hooks.add_subparsers(dest="hooks_cmd", required=True)
    hooks_sub.add_parser("install")
    hooks.set_defaults(func=cmd_hooks)

    sp = sub.add_parser("pair")
    sp.add_argument("--admin", action="store_true", help=i18n.t("cli.pair.admin_help", lang=lang))
    sp.add_argument("--url", help=i18n.t("cli.pair.url_help", lang=lang))
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_pair)

    devices = sub.add_parser("devices")
    devices_sub = devices.add_subparsers(dest="devices_cmd", required=True)
    dl = devices_sub.add_parser("list")
    dl.add_argument("--json", action="store_true")
    dr = devices_sub.add_parser("revoke")
    dr.add_argument("id")
    devices.set_defaults(func=cmd_devices)

    token = sub.add_parser("token")
    token_sub = token.add_subparsers(dest="token_cmd", required=True)
    tr = token_sub.add_parser("rotate")
    tr.add_argument("--show", action="store_true", help=i18n.t("cli.token.show_help", lang=lang))
    token.set_defaults(func=cmd_token)

    chat = sub.add_parser("chat")
    chat.add_argument("-m", "--message")
    chat.add_argument("--conversation")
    chat.add_argument("--list", action="store_true")
    chat.add_argument("--json", action="store_true")
    chat.set_defaults(func=cmd_chat)

    llm = sub.add_parser("llm")
    llm_sub = llm.add_subparsers(dest="llm_cmd", required=True)
    ls = llm_sub.add_parser("setup")
    ls.add_argument("--provider", choices=["anthropic", "openai", "ollama", "other"])
    ls.add_argument("--model")
    ls.add_argument("--base-url")
    ls.add_argument("--yes", action="store_true")
    lst = llm_sub.add_parser("status")
    lst.add_argument("--json", action="store_true")
    llm_sub.add_parser("test")
    llm.set_defaults(func=cmd_llm)

    sp = sub.add_parser("mcp")
    sp.set_defaults(func=cmd_mcp)

    unit = sub.add_parser("unit")
    unit_sub = unit.add_subparsers(dest="unit_cmd", required=True)
    unit_sub.add_parser("install")
    unit.set_defaults(func=cmd_unit)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
