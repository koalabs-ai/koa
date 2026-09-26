"""Shared tool table: the domain tools that MCP and the built-in agent both
expose. One source of truth so their behavior can't drift apart — mcp.py and
agent.py both import :data:`TOOL_SPECS` and :class:`ToolBox` from here.

``TOOL_SPECS`` uses a provider-neutral ``schema`` key (a JSON Schema
object); each surface adapts the shape it needs (MCP wants ``inputSchema``,
Anthropic ``input_schema``, an OpenAI-compatible provider wraps it in
``{"type":"function","function":{...,"parameters":...}}``).
"""
from __future__ import annotations

from typing import Any, Callable

from koa_core import activity as activitymod
from koa_core import claims as claimsmod
from koa_core import config as configmod
from koa_core import db as dbmod
from koa_core import items as itemsmod
from koa_core import memory as memorymod
from koa_core import plans as plansmod


def _schema(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


TOOL_SPECS: dict[str, dict] = {
    "context": {
        "description": "Workspace context: AGENTS.md, recent activity, and open items.",
        "schema": _schema({}),
    },
    "todo_list": {
        "description": "Lists items, with optional filters.",
        "schema": _schema({
            "status": {"type": "string"}, "tag": {"type": "string"},
            "plan": {"type": "string"}, "q": {"type": "string"},
        }),
    },
    "todo_add": {
        "description": "Creates a new item.",
        "schema": _schema({
            "title": {"type": "string"}, "body": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "plan": {"type": "string"},
        }, ["title"]),
    },
    "todo_update": {
        "description": "Changes status/evidence (or other fields) of an item.",
        "schema": _schema({
            "id": {"type": "string"}, "status": {"type": "string"},
            "evidence": {"type": "string"}, "title": {"type": "string"},
            "body": {"type": "string"},
        }, ["id"]),
    },
    "memory_recall": {
        "description": "Searches persistent memory.",
        "schema": _schema({"query": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]),
    },
    "memory_add": {
        "description": "Adds a new memory (.md file + index).",
        "schema": _schema({
            "type": {"type": "string", "enum": list(memorymod.TYPES)},
            "name": {"type": "string"}, "description": {"type": "string"},
            "body": {"type": "string"},
        }, ["type", "name"]),
    },
    "plans_list": {
        "description": "Lists synced plans (from 99_docs/plans/*.md).",
        "schema": _schema({}),
    },
    "claim_acquire": {
        "description": "Takes a lock on a target so agents don't step on each other.",
        "schema": _schema({
            "target": {"type": "string"}, "agent": {"type": "string"},
            "intent": {"type": "string"},
        }, ["target"]),
    },
    "claim_release": {
        "description": "Releases a lock by id.",
        "schema": _schema({"id": {"type": "string"}}, ["id"]),
    },
    "activity_log": {
        "description": "Writes a line to the activity log.",
        "schema": _schema({
            "text": {"type": "string"}, "kind": {"type": "string"}, "agent": {"type": "string"},
        }, ["text"]),
    },
    "heartbeat": {
        "description": "Marks this agent as active.",
        "schema": _schema({"agent": {"type": "string"}, "note": {"type": "string"}}),
    },
}

# Tools the built-in agent (koa_core.agent) is allowed to call. No shell, no
# file writes outside these, no network: "heartbeat" is for MCP clients
# identifying themselves, not something a chat turn needs.
AGENT_TOOL_NAMES: tuple[str, ...] = (
    "context", "todo_list", "todo_add", "todo_update", "memory_recall",
    "memory_add", "plans_list", "claim_acquire", "claim_release", "activity_log",
)


class ToolBox:
    """Executes tool calls against sqlite. Cheap to build; one per request/turn."""

    def __init__(self, cfg: configmod.Config):
        self.cfg = cfg

    def _conn(self):
        return dbmod.connect(self.cfg.db_path)

    def _agent(self, args: dict) -> str:
        return args.get("agent") or self.cfg.agent

    # ── handlers ───────────────────────────────────────────
    def _t_context(self, args):
        conn = self._conn()
        try:
            try:
                agents_md = self.cfg.agents_md_path.read_text(encoding="utf-8")
            except OSError:
                agents_md = ""
            return {
                "agents_md": agents_md,
                "recent_activity": activitymod.recent(conn, 20),
                "open_items_count": itemsmod.count_open(conn),
            }
        finally:
            conn.close()

    def _t_todo_list(self, args):
        conn = self._conn()
        try:
            return itemsmod.list_items(
                conn, status=args.get("status"), tag=args.get("tag"),
                plan=args.get("plan"), q=args.get("q"),
            )
        finally:
            conn.close()

    def _t_todo_add(self, args):
        conn = self._conn()
        try:
            return itemsmod.create(
                conn, title=args["title"], body=args.get("body", ""),
                tags=args.get("tags"), plan=args.get("plan"),
            )
        finally:
            conn.close()

    def _t_todo_update(self, args):
        conn = self._conn()
        try:
            fields = {k: v for k, v in args.items() if k in ("status", "evidence", "title", "body")}
            return itemsmod.update(conn, args["id"], **fields)
        finally:
            conn.close()

    def _t_memory_recall(self, args):
        conn = self._conn()
        try:
            return memorymod.recall(conn, args["query"], int(args.get("limit", 10)))
        finally:
            conn.close()

    def _t_memory_add(self, args):
        conn = self._conn()
        try:
            return memorymod.add(
                conn, self.cfg.memory_dir, args["type"], args["name"],
                args.get("description", ""), args.get("body", ""),
            )
        finally:
            conn.close()

    def _t_plans_list(self, args):
        conn = self._conn()
        try:
            return plansmod.list_plans(conn)
        finally:
            conn.close()

    def _t_claim_acquire(self, args):
        conn = self._conn()
        try:
            return claimsmod.acquire(conn, args["target"], self._agent(args), args.get("intent", ""))
        finally:
            conn.close()

    def _t_claim_release(self, args):
        conn = self._conn()
        try:
            return {"released": claimsmod.release(conn, args["id"])}
        finally:
            conn.close()

    def _t_activity_log(self, args):
        conn = self._conn()
        try:
            return activitymod.log(
                conn, self.cfg.activity_log_path, self._agent(args),
                args["text"], args.get("kind", "log"),
            )
        finally:
            conn.close()

    def _t_heartbeat(self, args):
        conn = self._conn()
        try:
            return activitymod.heartbeat(conn, self._agent(args), args.get("note", ""))
        finally:
            conn.close()

    def call(self, name: str, args: dict) -> Any:
        handler: Callable | None = getattr(self, f"_t_{name}", None)
        if handler is None:
            raise KeyError(f"unknown tool: {name}")
        return handler(args or {})
