"""Servidor MCP por stdio: JSON-RPC 2.0, un objeto JSON por línea.

Trabaja directo contra sqlite (no necesita el servidor HTTP corriendo).
Logs sólo a stderr: stdout es exclusivamente para las respuestas JSON-RPC.

Las tools son las mismas que usa el agente integrado (``koa_core.agent``):
:mod:`koa_core.toolbox` es la única fuente de verdad para su descripción y
su ejecución.
"""
from __future__ import annotations

import json
import sys

from koa_core import config as configmod
from koa_core import toolbox
from koa_core import __version__

SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26")
DEFAULT_PROTOCOL = "2025-06-18"

TOOLS: dict[str, dict] = {
    name: {"description": spec["description"], "inputSchema": spec["schema"]}
    for name, spec in toolbox.TOOL_SPECS.items()
}


class McpServer(toolbox.ToolBox):
    """Alias con el nombre histórico de este módulo; el trabajo real vive en
    :class:`koa_core.toolbox.ToolBox` (compartida con el agente)."""


def _rpc_result(id_, result) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _rpc_error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_request(server: McpServer, req: dict) -> dict | None:
    method = req.get("method")
    id_ = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        requested = params.get("protocolVersion")
        protocol = requested if requested in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
        return _rpc_result(id_, {
            "protocolVersion": protocol,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "koa-core", "version": __version__},
        })
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _rpc_result(id_, {})
    if method == "tools/list":
        tools = [{"name": name, **spec} for name, spec in TOOLS.items()]
        return _rpc_result(id_, {"tools": tools})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            result = server.call(name, args)
            text = json.dumps(result, ensure_ascii=False)
            return _rpc_result(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as e:
            text = json.dumps({"error": str(e)}, ensure_ascii=False)
            return _rpc_result(id_, {"content": [{"type": "text", "text": text}], "isError": True})
    if id_ is None:
        return None  # notificación desconocida: se ignora
    return _rpc_error(id_, -32601, f"unsupported method: {method}")


def run_stdio(cfg: configmod.Config, in_stream=None, out_stream=None) -> None:
    server = McpServer(cfg)
    in_stream = in_stream or sys.stdin
    out_stream = out_stream or sys.stdout
    print(f"koa-core mcp: listening on stdio (KOA_HOME={cfg.home})", file=sys.stderr)
    for line in in_stream:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"koa-core mcp: invalid line ({e})", file=sys.stderr)
            continue
        try:
            resp = handle_request(server, req)
        except Exception as e:
            resp = _rpc_error(req.get("id"), -32603, str(e))
        if resp is not None:
            out_stream.write(json.dumps(resp, ensure_ascii=False) + "\n")
            out_stream.flush()
