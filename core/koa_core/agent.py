"""The built-in agent: system prompt + tool loop + conversation persistence.

Provider-agnostic — it only knows the :class:`koa_core.llm.Provider`
interface (``chat()`` -> Turn, ``tool_result_messages()``). Tools are the
domain tools in :mod:`koa_core.toolbox` (``AGENT_TOOL_NAMES``): no shell, no
file writes outside those, no network beyond whatever the chosen provider
does. Importing this module never touches a provider SDK; only
:func:`send_message` (via ``koa_core.llm.for_config``) does.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from koa_core import activity as activitymod
from koa_core import i18n
from koa_core import items as itemsmod
from koa_core.config import Config
from koa_core.items import now_iso
from koa_core.llm import ProviderUnavailable, for_config
from koa_core.toolbox import AGENT_TOOL_NAMES, TOOL_SPECS, ToolBox

MAX_TOOL_ITERATIONS = 12
_AGENT_TOOL_SPECS = {name: TOOL_SPECS[name] for name in AGENT_TOOL_NAMES}
_ARGS_SUMMARY_MAX = 200


def _read(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _koa_work_skill_path(cfg: Config) -> Path:
    return cfg.home / "04_llm" / "skills" / "koa-work" / "SKILL.md"


def _stable_system_prefix(cfg: Config) -> str:
    """AGENTS.md + constitution + the koa-work skill, in that fixed order.
    Doesn't change within a KOA_HOME, which is what keeps the prompt
    byte-stable turn to turn (good for provider-side prompt caching)."""
    sections = [
        s for s in (
            _read(cfg.agents_md_path),
            _read(cfg.home / "04_llm" / "constitution.md"),
            _read(_koa_work_skill_path(cfg)),
        )
        if s
    ]
    return "\n\n---\n\n".join(sections)


def system_prompt(cfg: Config, conversation: dict) -> str:
    """Byte-stable across the whole conversation except the date line at
    the end: the open-items count is a snapshot taken once, when the
    conversation was created (see :func:`create_conversation`), not
    recomputed every turn."""
    prefix = _stable_system_prefix(cfg)
    live = i18n.t(
        "agent.system.live_context", lang=cfg.lang,
        today=now_iso()[:10], open_items=conversation["context_open_items"],
    )
    return f"{prefix}\n\n---\n\n{live}" if prefix else live


# ── persistencia ─────────────────────────────────────────────────────

def create_conversation(cfg: Config, conn: sqlite3.Connection, title: str = "") -> dict:
    conv_id = str(uuid.uuid4())
    ts = now_iso()
    open_items = itemsmod.count_open(conn)
    conn.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at, provider, model, "
        "context_open_items, input_tokens, output_tokens) VALUES (?,?,?,?,?,?,?,0,0)",
        (conv_id, title.strip()[:80], ts, ts, cfg.llm_provider, cfg.llm_model, open_items),
    )
    conn.commit()
    return get_conversation(conn, conv_id)


def get_conversation(conn: sqlite3.Connection, conversation_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    return dict(row) if row else None


def list_conversations(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at, provider, model, input_tokens, output_tokens "
        "FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def render_messages(conn: sqlite3.Connection, conversation_id: str) -> list[dict]:
    """Render-friendly transcript for GET /v1/chat/{id}: role + text + tool
    summaries, no thinking content, no provider-native shape."""
    rows = conn.execute(
        "SELECT render_json, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = json.loads(r["render_json"])
        d["created_at"] = r["created_at"]
        out.append(d)
    return out


def _load_history(conn: sqlite3.Connection, conversation_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT content_json FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    return [json.loads(r["content_json"]) for r in rows]


def _save_message(conn: sqlite3.Connection, conversation_id: str, message: dict, render: dict) -> None:
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content_json, render_json, created_at) "
        "VALUES (?,?,?,?,?)",
        (
            conversation_id, message.get("role", ""),
            json.dumps(message, ensure_ascii=False), json.dumps(render, ensure_ascii=False),
            now_iso(),
        ),
    )
    conn.commit()


def _update_conversation_usage(conn: sqlite3.Connection, conversation_id: str, usage: dict) -> None:
    conn.execute(
        "UPDATE conversations SET input_tokens = input_tokens + ?, output_tokens = output_tokens + ?, "
        "updated_at = ? WHERE id = ?",
        (usage["input_tokens"], usage["output_tokens"], now_iso(), conversation_id),
    )
    conn.commit()


# ── ejecución de tools ───────────────────────────────────────────────

def _args_summary(args: dict) -> str:
    """Short, loggable summary of a tool call's arguments. The domain tools
    never take secrets as arguments, so this is safe to put in the activity
    log verbatim (just capped in length)."""
    try:
        s = json.dumps(args, ensure_ascii=False)
    except TypeError:
        s = str(args)
    return s if len(s) <= _ARGS_SUMMARY_MAX else s[:_ARGS_SUMMARY_MAX] + "…"


def _log_tool_call(cfg: Config, conn: sqlite3.Connection, name: str, args: dict, ok: bool) -> None:
    status = "ok" if ok else "error"
    activitymod.log(
        conn, cfg.activity_log_path, cfg.agent,
        f"{name} {_args_summary(args)} ({status})", "agent_tool",
    )


def _run_tool(cfg: Config, conn: sqlite3.Connection, box: ToolBox, call: dict) -> dict:
    name, args = call["name"], call.get("input") or {}
    try:
        if name not in AGENT_TOOL_NAMES:
            raise KeyError(name)
        result = box.call(name, args)
        content = json.dumps(result, ensure_ascii=False)
        ok = True
    except Exception as e:
        content = i18n.t("common.error", lang=cfg.lang, err=e)
        ok = False
    _log_tool_call(cfg, conn, name, args, ok)
    return {"id": call["id"], "name": name, "content": content, "is_error": not ok}


# ── el turno ─────────────────────────────────────────────────────────

def send_message(cfg: Config, conn: sqlite3.Connection, conversation_id: str | None, text: str) -> dict:
    """Runs one user turn end to end: creates a conversation if needed,
    drives the provider+tool loop (<= MAX_TOOL_ITERATIONS), persists every
    message, and returns ``{conversation_id, reply, tool_calls, usage}``.

    Raises :class:`koa_core.llm.ProviderUnavailable` (localized) instead of
    crashing when no model is connected — callers (CLI, HTTP API) show it
    as a normal, translated message.
    """
    if conversation_id:
        conv = get_conversation(conn, conversation_id)
        if conv is None:
            raise i18n.LocalizedError("llm.error.conversation_missing", id=conversation_id)

    provider = for_config(cfg)  # ProviderUnavailable propagates: nothing written yet

    if not conversation_id:
        conv = create_conversation(cfg, conn, title=text)
        conversation_id = conv["id"]

    box = ToolBox(cfg)
    tools = provider.format_tools(_AGENT_TOOL_SPECS)
    history = _load_history(conn, conversation_id)

    user_message = {"role": "user", "content": text}
    history.append(user_message)
    _save_message(conn, conversation_id, user_message, {"role": "user", "text": text, "tool_calls": []})

    tool_summaries: list[dict] = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    reply_text = ""
    iterations = 0

    while True:
        system = system_prompt(cfg, conv)
        turn = provider.chat(history, tools, system)
        total_usage["input_tokens"] += turn.usage.get("input_tokens", 0)
        total_usage["output_tokens"] += turn.usage.get("output_tokens", 0)

        if turn.error is not None:
            reply_text = turn.error.render(cfg.lang)
            break

        history.append(turn.raw_assistant)
        _save_message(
            conn, conversation_id, turn.raw_assistant,
            {"role": "assistant", "text": turn.text, "tool_calls": [{"name": c["name"]} for c in turn.tool_calls]},
        )
        if turn.text:
            reply_text = turn.text

        if not turn.tool_calls:
            if turn.stop_reason == "max_tokens":
                cut = i18n.t("llm.error.max_tokens_cut", lang=cfg.lang)
                reply_text = f"{reply_text}\n\n{cut}" if reply_text else cut
            break

        iterations += 1
        if iterations > MAX_TOOL_ITERATIONS:
            reply_text = i18n.t("llm.error.iteration_cap", lang=cfg.lang, n=MAX_TOOL_ITERATIONS)
            break

        results = [_run_tool(cfg, conn, box, call) for call in turn.tool_calls]
        tool_summaries.extend({"name": r["name"], "ok": not r["is_error"]} for r in results)

        tool_msgs = provider.tool_result_messages(results)
        # Anthropic returns ONE combined message for every result; an
        # OpenAI-compatible provider returns one per result. Either way,
        # zip against the matching slice of `results` for the render summary.
        if len(tool_msgs) == 1 and len(results) > 1:
            groups = [results]
        else:
            groups = [[r] for r in results]
        for msg, group in zip(tool_msgs, groups):
            history.append(msg)
            render = {"role": "tool_result", "text": "", "tool_calls": [
                {"name": r["name"], "ok": not r["is_error"]} for r in group
            ]}
            _save_message(conn, conversation_id, msg, render)

    _update_conversation_usage(conn, conversation_id, total_usage)
    return {
        "conversation_id": conversation_id, "reply": reply_text,
        "tool_calls": tool_summaries, "usage": total_usage,
    }
