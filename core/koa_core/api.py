"""Servidor HTTP: API JSON en /v1/* + la UI estática en /.

``ThreadingHTTPServer`` con una conexión sqlite por petición (sqlite3 no
comparte conexiones entre hilos). Loopback (127.0.0.1) por defecto; si se
pide escuchar en otra IP sin token configurado, se niega a arrancar.
"""
from __future__ import annotations

import hmac
import json
import mimetypes
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from koa_core import activity as activitymod
from koa_core import claims as claimsmod
from koa_core import config as configmod
from koa_core import db as dbmod
from koa_core import devices as devicesmod
from koa_core import i18n
from koa_core import items as itemsmod
from koa_core import memory as memorymod
from koa_core import plans as plansmod
from koa_core import __version__

UI_DIR = Path(__file__).parent / "ui"


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


def _read_agents_md(cfg: configmod.Config) -> str:
    try:
        return cfg.agents_md_path.read_text(encoding="utf-8")
    except OSError:
        return ""


class Handler(BaseHTTPRequestHandler):
    server_version = "koa-core/" + __version__
    cfg: configmod.Config  # inyectado por make_server

    # ── infra ──────────────────────────────────────────────
    def log_message(self, fmt, *args):  # silenciar acceso por stdout
        pass

    def _conn(self):
        return dbmod.connect(self.cfg.db_path)

    def _agent(self) -> str:
        return self.headers.get("X-Koa-Agent", self.cfg.agent)

    def _t(self, key: str, **kwargs) -> str:
        return i18n.t(key, lang=self.cfg.lang, **kwargs)

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError as e:
            raise ApiError(400, self._t("api.bad_json", err=e))

    def _check_auth(self, method: str, path: str) -> None:
        """Rellena ``self._auth``. ``None`` = modo abierto (loopback, sin
        token ni dispositivos: el comportamiento de siempre). Si hay token
        maestro configurado o algun dispositivo activo, TODA ruta /v1/*
        salvo /v1/health y POST /v1/pair/claim exige Authorization: Bearer.
        La UI estatica (incluida /pair, que aun no tiene token) nunca pasa
        por aqui: ella misma habla con /v1/* y ahi si se exige el token."""
        self._auth = None
        if not path.startswith("/v1/"):
            return
        if path == "/v1/health":
            return
        if path == "/v1/pair/claim" and method == "POST":
            return
        conn = self._conn()
        try:
            has_devices = devicesmod.has_active_devices(conn)
            if not self.cfg.token and not has_devices:
                return  # nadie configuro nada: sigue abierto en loopback
            header = self.headers.get("Authorization", "")
            token = header[len("Bearer "):].strip() if header.startswith("Bearer ") else ""
            if not token:
                raise ApiError(401, self._t("api.token_missing"))
            if self.cfg.token and hmac.compare_digest(token, self.cfg.token):
                self._auth = {"kind": "master", "admin": True}
                return
            device = devicesmod.authenticate(conn, token)
            if device:
                self._auth = {
                    "kind": "device", "device_id": device["id"],
                    "admin": bool(device["admin"]), "name": device["name"],
                }
                return
            raise ApiError(401, self._t("api.token_invalid"))
        finally:
            conn.close()

    def _can_administer(self) -> bool:
        """Puede crear codigos de emparejamiento y ver/revocar dispositivos:
        modo abierto (nadie configuro auth todavia), token maestro, o un
        dispositivo marcado como admin."""
        auth = self._auth
        if auth is None:
            return True
        if auth["kind"] == "master":
            return True
        return auth["kind"] == "device" and auth.get("admin", False)

    def _pair_url(self, code: str) -> str:
        scheme = self.headers.get("X-Forwarded-Proto", "http")
        host = self.headers.get("Host") or f"{self.cfg.host}:{self.cfg.port}"
        return f"{scheme}://{host}/pair#code={code}"

    # ── dispatch ───────────────────────────────────────────
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        try:
            self._check_auth(method, path)
            if path.startswith("/v1/"):
                self._route_api(method, path, qs)
            elif method == "GET":
                self._route_static(path)
            else:
                raise ApiError(404, self._t("api.not_found"))
        except ApiError as e:
            self._send_json(e.status, {"error": e.message})
        except Exception as e:  # último recurso: nunca tronar sin responder
            self._send_json(500, {"error": str(e)})

    # ── rutas API ──────────────────────────────────────────
    def _route_api(self, method: str, path: str, qs: dict) -> None:
        conn = self._conn()
        try:
            if path == "/v1/health":
                self._send_json(200, {"ok": True, "version": __version__, "home": str(self.cfg.home)})
                return
            if path == "/v1/items":
                if method == "GET":
                    rows = itemsmod.list_items(
                        conn,
                        status=_first(qs, "status"),
                        tag=_first(qs, "tag"),
                        plan=_first(qs, "plan"),
                        q=_first(qs, "q"),
                    )
                    self._send_json(200, rows)
                elif method == "POST":
                    body = self._body_json()
                    try:
                        it = itemsmod.create(
                            conn, title=body.get("title", ""), body=body.get("body", ""),
                            tags=body.get("tags"), plan=body.get("plan"),
                            source_id=body.get("source_id"),
                        )
                    except itemsmod.ItemError as e:
                        raise ApiError(400, str(e))
                    self._log_activity(conn, "item_create", it["title"])
                    self._send_json(201, it)
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            m = re.fullmatch(r"/v1/items/([\w-]+)", path)
            if m:
                item_id = m.group(1)
                if method == "PATCH":
                    body = self._body_json()
                    try:
                        it = itemsmod.update(conn, item_id, **{
                            k: v for k, v in body.items()
                            if k in ("title", "body", "status", "tags", "plan", "evidence")
                        })
                    except itemsmod.ItemError as e:
                        raise ApiError(400, str(e))
                    self._log_activity(conn, "item_update", it["title"], {"status": it["status"]})
                    self._send_json(200, it)
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            if path == "/v1/memory":
                if method == "GET":
                    q = _first(qs, "q") or ""
                    limit = int(_first(qs, "limit") or 10)
                    self._send_json(200, memorymod.recall(conn, q, limit))
                elif method == "POST":
                    body = self._body_json()
                    try:
                        entry = memorymod.add(
                            conn, self.cfg.memory_dir, body.get("type", ""),
                            body.get("name", ""), body.get("description", ""),
                            body.get("body", ""),
                        )
                    except memorymod.MemoryError as e:
                        raise ApiError(400, str(e))
                    self._log_activity(conn, "memory_add", entry["name"])
                    self._send_json(201, entry)
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            if path == "/v1/claims":
                if method == "GET":
                    self._send_json(200, claimsmod.list_claims(conn))
                elif method == "POST":
                    body = self._body_json()
                    try:
                        claim = claimsmod.acquire(
                            conn, body.get("target", ""), body.get("agent") or self._agent(),
                            body.get("intent", ""),
                        )
                    except claimsmod.ClaimHeld as e:
                        self._send_json(409, {"error": str(e), "holder": e.holder})
                        return
                    self._send_json(201, claim)
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            m = re.fullmatch(r"/v1/claims/([\w-]+)", path)
            if m:
                if method == "DELETE":
                    ok = claimsmod.release(conn, m.group(1))
                    self._send_json(200, {"released": ok})
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            if path == "/v1/activity":
                if method == "GET":
                    limit = int(_first(qs, "limit") or 50)
                    self._send_json(200, activitymod.recent(conn, limit))
                elif method == "POST":
                    body = self._body_json()
                    entry = activitymod.log(
                        conn, self.cfg.activity_log_path, body.get("agent") or self._agent(),
                        body.get("text", ""), body.get("kind", "log"), body.get("data"),
                    )
                    self._send_json(201, entry)
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            if path == "/v1/heartbeat" and method == "POST":
                body = self._body_json()
                hb = activitymod.heartbeat(conn, body.get("agent") or self._agent(), body.get("note", ""))
                self._send_json(200, hb)
                return
            if path == "/v1/agents" and method == "GET":
                self._send_json(200, activitymod.list_agents(conn))
                return
            if path == "/v1/llm/status" and method == "GET":
                # No secrets here: just enough for the UI to decide whether
                # to show the chat box or the "connect a model" card.
                self._send_json(200, {
                    "configured": bool(self.cfg.llm_provider),
                    "provider": self.cfg.llm_provider, "model": self.cfg.llm_model,
                })
                return
            if path == "/v1/chat" and method == "GET":
                from koa_core import agent as agentmod

                self._send_json(200, agentmod.list_conversations(conn))
                return
            if path == "/v1/chat" and method == "POST":
                from koa_core import agent as agentmod
                from koa_core import llm as llmmod

                body = self._body_json()
                message = (body.get("message") or "").strip()
                if not message:
                    raise ApiError(400, self._t("api.chat_needs_message"))
                try:
                    result = agentmod.send_message(conn=conn, cfg=self.cfg,
                                                    conversation_id=body.get("conversation_id"), text=message)
                except llmmod.ProviderUnavailable as e:
                    raise ApiError(400, e.render(self.cfg.lang))
                except i18n.LocalizedError as e:
                    raise ApiError(404, e.render(self.cfg.lang))
                self._send_json(200, result)
                return
            m = re.fullmatch(r"/v1/chat/([\w-]+)", path)
            if m:
                if method != "GET":
                    raise ApiError(405, self._t("api.method_not_supported"))
                from koa_core import agent as agentmod

                if agentmod.get_conversation(conn, m.group(1)) is None:
                    raise ApiError(404, self._t("llm.error.conversation_missing", id=m.group(1)))
                self._send_json(200, agentmod.render_messages(conn, m.group(1)))
                return
            if path == "/v1/context" and method == "GET":
                self._send_json(200, {
                    "agents_md": _read_agents_md(self.cfg),
                    "recent_activity": activitymod.recent(conn, 20),
                    "open_items_count": itemsmod.count_open(conn),
                })
                return
            if path == "/v1/pair/start" and method == "POST":
                # En modo abierto (sin token maestro ni dispositivos) todo pasa como
                # admin; si alguien pone un proxy enfrente, cualquiera crearía
                # códigos. Por HTTP se exige credencial; `koa-core pair` (acceso
                # local = dueño) funciona siempre.
                if self._auth is None:
                    raise ApiError(403, self._t("api.pair_needs_token"))
                if not self._can_administer():
                    raise ApiError(403, self._t("api.requires_admin"))
                body = self._body_json()
                code, expires_at = devicesmod.start_pairing(
                    conn, admin=bool(body.get("admin", False)),
                    created_by=self._agent(), ttl_s=self.cfg.code_ttl_s,
                )
                self._log_activity(conn, "pair_start", self._t("activity.pair_generated"))
                self._send_json(201, {
                    "code": code, "expires_at": expires_at, "pair_url": self._pair_url(code),
                })
                return
            if path == "/v1/pair/claim" and method == "POST":
                body = self._body_json()
                try:
                    device_id, token = devicesmod.claim(
                        conn, body.get("code", ""), body.get("name", ""), body.get("platform", ""),
                        lang=self.cfg.lang,
                    )
                except devicesmod.TooManyAttempts as e:
                    self._send_json(429, {"error": str(e)})
                    return
                except devicesmod.PairingError as e:
                    raise ApiError(400, str(e))
                self._log_activity(
                    conn, "pair_claim",
                    self._t("activity.device_paired", name=body.get("name", "")),
                )
                self._send_json(201, {"device_id": device_id, "token": token})
                return
            if path == "/v1/devices" and method == "GET":
                if not self._can_administer():
                    raise ApiError(403, self._t("api.requires_admin"))
                self._send_json(200, devicesmod.list_devices(conn))
                return
            m = re.fullmatch(r"/v1/devices/([\w-]+)", path)
            if m:
                if method == "DELETE":
                    if not self._can_administer():
                        raise ApiError(403, self._t("api.requires_admin"))
                    ok = devicesmod.revoke(conn, m.group(1))
                    self._log_activity(conn, "device_revoke", m.group(1))
                    self._send_json(200, {"revoked": ok})
                else:
                    raise ApiError(405, self._t("api.method_not_supported"))
                return
            if path == "/v1/me" and method == "GET":
                auth = self._auth
                if auth is None:
                    self._send_json(200, {"kind": "open", "admin": True})
                elif auth["kind"] == "master":
                    self._send_json(200, {"kind": "master", "admin": True})
                else:
                    self._send_json(200, {
                        "kind": "device", "device_id": auth["device_id"],
                        "name": auth.get("name"), "admin": auth.get("admin", False),
                    })
                return
            raise ApiError(404, self._t("api.route_not_found"))
        finally:
            conn.close()

    def _log_activity(self, conn, kind: str, text: str, data: dict | None = None) -> None:
        activitymod.log(conn, self.cfg.activity_log_path, self._agent(), text, kind, data)

    # ── UI estática ────────────────────────────────────────
    def _route_static(self, path: str) -> None:
        # "/pair" es una vista de la misma SPA (app.js decide que mostrar
        # segun location.pathname/hash): se sirve el mismo index.html.
        rel = "index.html" if path in ("/", "", "/pair") else path.lstrip("/")
        rel = rel.split("?", 1)[0]
        file_path = (UI_DIR / rel).resolve()
        if UI_DIR.resolve() not in file_path.parents and file_path != UI_DIR.resolve():
            raise ApiError(404, self._t("api.not_found"))
        if not file_path.is_file():
            raise ApiError(404, self._t("api.not_found"))
        ctype, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _first(qs: dict, key: str) -> str | None:
    vals = qs.get(key)
    return vals[0] if vals else None


def make_server(cfg: configmod.Config) -> ThreadingHTTPServer:
    i18n.set_active(cfg.lang)
    if cfg.host not in ("127.0.0.1", "localhost", "::1") and not cfg.token:
        raise RuntimeError(i18n.t("api.refuses_non_loopback", lang=cfg.lang))
    handler = type("BoundHandler", (Handler,), {"cfg": cfg})
    server = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    return server


def serve(cfg: configmod.Config) -> None:
    server = make_server(cfg)
    print(i18n.t("api.serving", lang=cfg.lang, host=cfg.host, port=cfg.port, home=cfg.home))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) != 0
