"""Message catalogs for :mod:`koa_core.i18n`. Two flat dicts, same keys,
``str.format`` placeholders. ``core/tests/test_i18n.py`` checks both have
the same keys and the same placeholder names per key.
"""
from __future__ import annotations

EN: dict[str, str] = {
    # ── cli: argparse ──────────────────────────────────────────────
    "cli.description": "Minimal core of a KOA workspace",
    "cli.home_help": "KOA_HOME (default: $KOA_HOME or ~/koa)",
    "cli.pair.admin_help": "the device will be able to administer others",
    "cli.pair.url_help": "public URL of this KOA (default: host/port from the config)",
    "cli.token.show_help": "print the new token (default: don't)",

    # ── shared ─────────────────────────────────────────────────────
    "common.error": "error: {err}",
    "common.warning_prefix": "warning: ",
    "common.no_results": "no results",

    # ── init ───────────────────────────────────────────────────────
    "init.no_seed": "can't find the seed at {seed} (check KOA_SEED_DIR)",
    "init.done": "KOA ready at {home}",
    "init.seed_summary": "  seed: {copied} file(s) copied, {skipped} already existed",
    "init.toml_written": "written",
    "init.toml_kept": "already existed, left alone",
    "init.git_missing": "git isn't installed: skipping git init",
    "init.git_already": "already a git repo",
    "init.git_done": "git init done",
    "init.git_failed": "git init failed: {err}",

    # ── hooks ──────────────────────────────────────────────────────
    "hooks.no_git": "no .git: skipping the hook",
    "hooks.updated": "naming hook updated",
    "hooks.chained": "naming hook chained onto the existing pre-commit",
    "hooks.installed": "naming hook installed",
    "hooks.override_hint": (
        "core.hooksPath={value}: git ignores .git/hooks and the naming hook never "
        "runs. Fix: `git -C {home} config core.hooksPath .git/hooks` (this repo "
        "only) or add `koa-core names --staged` to {value}'s pre-commit"
    ),

    # ── doctor ─────────────────────────────────────────────────────
    "doctor.python_fail": "needs >=3.10, found {have}",
    "doctor.toml_missing": "doesn't exist, using defaults",
    "doctor.toml_parse_fail": "doesn't parse: {err}",
    "doctor.db_pass": "{path} (schema v{version})",
    "doctor.port_free": "port {port} free",
    "doctor.port_healthy": "already a healthy koa-core at {url}",
    "doctor.port_unhealthy": "{url} answered but isn't ok",
    "doctor.port_busy": "port {port} busy and it isn't koa-core ({err})",
    "doctor.git_missing": "not installed",
    "doctor.hook_not_installed": "not installed (koa-core hooks install)",
    "doctor.naming_issues": "{n} problem(s)",
    "doctor.devices_active": "{n} active device(s)",
    "doctor.token_bad_perms": (
        "{path} has permissions {mode} (should be 600): chmod 600 {path}"
    ),
    "doctor.token_in_toml": "token in koa.toml: move it with `koa-core token rotate`",
    "doctor.token_env": "KOA_TOKEN (environment variable)",
    "doctor.token_open": "no token (open mode, loopback only)",
    "doctor.token_exposed": "no token and listening outside loopback",
    "doctor.token_perm_unreadable": "couldn't read permissions of {path}: {err}",

    # ── todo ───────────────────────────────────────────────────────
    "todo.empty": "no pending items",
    "todo.created": "item created: {id}  {title}",

    # ── plans ──────────────────────────────────────────────────────
    "plans.none": "no plans in {dir}",
    "plans.sync_line": (
        "{slug}: {tasks} task(s), {created} new, {completed} completed, "
        "{orphans} orphan(s)"
    ),
    "plans.no_status": "no status",
    "plans.list_line": "{slug}: {title} ({status})",

    # ── mem ────────────────────────────────────────────────────────
    "mem.saved": "memory saved: {path}",
    "mem.reindexed": "reindexed {n} memory item(s)",

    # ── claim ──────────────────────────────────────────────────────
    "claim.acquired": "lock acquired: {id} on {target} until {expires_at}",
    "claim.released": "released",
    "claim.not_found": "no such lock",
    "claim.list_line": "{id}  {target}  {agent}  until {expires_at}",

    # ── pair ───────────────────────────────────────────────────────
    "pair.expires": "expires: {expires_at}",
    "pair.open_url": "open this on the new device: {url}",
    "pair.install_qrencode": (
        "install `qrencode` to see the QR right here "
        "(pacman -S qrencode / apt install qrencode)."
    ),

    # ── devices ────────────────────────────────────────────────────
    "devices.empty": "no paired devices",
    "devices.status_revoked": "revoked",
    "devices.status_active": "active",
    "devices.admin_suffix": " (admin)",
    "devices.never_seen": "never",
    "devices.no_platform": "no platform",
    "devices.list_line": "{id}  [{status:8}] {name}{admin} · {platform} · seen: {seen}",
    "devices.revoked": "revoked",
    "devices.revoke_not_found": "no such device (or it was already revoked)",
    "devices.invalid_code": "invalid code",
    "devices.invalid_or_expired_code": "invalid or expired code",
    "devices.too_many_attempts": "too many failed attempts: wait a few minutes",
    "devices.default_name": "device",

    # ── token ──────────────────────────────────────────────────────
    "token.rotated": "new token at {path} (permissions 600)",
    "token.toml_cleared": "cleared [api].token in {path}: it no longer lives there",
    "token.usage_hint": (
        'use it as Authorization: Bearer <token>, or paste it into the '
        '"Connect this device" screen if this is the first pairing without '
        "opening any ports."
    ),
    "token.value": "token: {token}",

    # ── unit ───────────────────────────────────────────────────────
    "unit.description": "koa-core (your KOA's API)",
    "unit.written": "unit written to {path}",
    "unit.enable_hint": "to enable it: systemctl --user enable --now koa-core.service",

    # ── config (koa.toml written by `koa-core init`) ────────────────
    "config.default_toml": """\
# Configuration for this KOA. Relative paths are relative to KOA_HOME.
[api]
host = "127.0.0.1"
port = 8700
# The token lives in 10_personal/secrets/koa-core.token ("koa-core token
# rotate" creates it). This field is only for compatibility with old
# installs: if it has something in it, "koa-core doctor" warns and
# "koa-core token rotate" clears it.
token = ""

[db]
path = "06_data/koa-core.sqlite"

[pairing]
# lifetime in seconds of a "koa-core pair" code before it expires
code_ttl_s = 600

[ui]
# "auto" follows KOA_LANG / LC_ALL / LC_MESSAGES / LANG; or force "en" / "es".
lang = "auto"

[llm]
# No model is required to install or use KOA. Connect one with
# "koa-core llm setup" (it writes this section; the API key never lives
# here, see 10_personal/secrets/<provider>.env).
provider = ""          # "", "anthropic", "openai-compatible"
model = ""             # default per provider: claude-opus-5 / (required for openai-compatible)
base_url = ""          # openai-compatible only (e.g. Ollama: http://127.0.0.1:11434/v1)
""",

    # ── api ────────────────────────────────────────────────────────
    "api.bad_json": "body isn't valid JSON: {err}",
    "api.token_missing": "missing token (Authorization: Bearer <token>)",
    "api.token_invalid": "invalid or revoked token",
    "api.not_found": "not found",
    "api.route_not_found": "route not found",
    "api.method_not_supported": "method not supported",
    "api.pair_needs_token": (
        "set up a token first (koa-core token rotate) or use `koa-core pair` "
        "on the machine itself"
    ),
    "api.requires_admin": "requires a master token or an admin device",
    "api.refuses_non_loopback": (
        "koa-core refuses to listen outside 127.0.0.1 without a token. "
        "Run `koa-core token rotate` (or set KOA_TOKEN)."
    ),
    "api.serving": "koa-core listening at http://{host}:{port}  (KOA_HOME={home})",
    "api.chat_needs_message": "the body needs a non-empty \"message\"",

    # ── activity log text (shown in the UI's Activity tab) ──────────
    "activity.pair_generated": "pairing code generated",
    "activity.device_paired": "device paired: {name}",
    "err.item_title": 'an item needs a title',
    "err.item_status": 'invalid status: {status}',
    "err.item_missing": 'no such item: {id}',
    "err.item_evidence": 'moving to done/dropped requires --evidence',
    "err.mem_type": 'invalid type: {type} (use {types})',
    "err.mem_name": 'memory needs --name',
    "naming.deny.spaces": 'has spaces',
    "naming.deny.ascii": 'has accents or non-ASCII characters',
    "naming.deny.syncthing": 'is a Syncthing conflict',
    "naming.deny.orig": "is a merge's .orig backup",
    "naming.deny.bak": 'is a .bak backup',
    "naming.deny.tilde": 'is an editor backup (~)',
    "naming.deny.autosave": 'is an Emacs autosave (#…#)',
    "naming.deny.lock": 'is an Emacs lock (.#…)',
    "naming.deny.egg": 'is Python build output',
    "naming.deny.copy": 'has a «(1)» copy suffix',
    "naming.deny.dash": 'ends in a dash (a cut-off slug)',
    "naming.length": 'is {n} characters long (max {max})',
    "naming.root": 'the root only admits NN_name folders and the entry files (AGENTS.md, README.md, koa.toml…)',
    "naming.root_hint": 'move it into the NN_ folder it belongs to',
    "naming.level1": 'first-level folders go in kebab-case (lowercase and dashes)',
    "naming.ok": 'names: OK',
    "naming.count": 'names: {n} problem(s)',

    # ── llm: provider errors (koa_core.llm, shown by chat/API/CLI) ───
    "llm.error.not_configured": "no model connected yet: run `koa-core llm setup`",
    "llm.error.sdk_missing": "the Anthropic SDK isn't installed: run `koa-core llm setup` to install it",
    "llm.error.key_missing": "no API key for {provider} (set {env} or run `koa-core llm setup`)",
    "llm.error.model_missing": "no model configured: run `koa-core llm setup`",
    "llm.error.unknown_provider": "unknown provider: {provider}",
    "llm.error.auth": "the API rejected the key (authentication failed): check it with `koa-core llm setup`",
    "llm.error.permission": "the API refused permission for this key",
    "llm.error.not_found": "the API says that model or resource doesn't exist",
    "llm.error.rate_limit": "rate limit reached: try again in a moment",
    "llm.error.server": "the provider's servers are having trouble: try again shortly",
    "llm.error.connection": "couldn't reach the provider: check your connection",
    "llm.error.timeout": "the provider took too long to answer",
    "llm.error.refusal": "the model declined to answer",
    "llm.error.http": "the server answered with an error ({status}): {detail}",
    "llm.error.unexpected": "unexpected error from the provider: {detail}",
    "llm.error.max_tokens_cut": "(cut off: the answer hit the model's token limit)",
    "llm.error.iteration_cap": "stopped after {n} tool calls in a row; ask again if you need more",
    "llm.error.conversation_missing": "no such conversation: {id}",

    # ── llm: `koa-core llm setup/status/test` ────────────────────────
    "llm.setup.ask_provider_prompt": (
        "Connect a model:\n"
        "  1) Claude (Anthropic API key)\n"
        "  2) OpenAI\n"
        "  3) Ollama (local, free)\n"
        "  4) Other OpenAI-compatible\n"
        "Choice [1-4]: "
    ),
    "llm.setup.invalid_choice": "invalid choice",
    "llm.setup.needs_provider": "pass --provider anthropic|openai|ollama|other, or run without --yes to answer interactively",
    "llm.setup.needs_model": "this provider needs --model",
    "llm.setup.needs_base_url": "an OpenAI-compatible provider needs --base-url",
    "llm.setup.key_prompt": "{provider} API key: ",
    "llm.setup.key_missing": "no key given (set {env} or answer the prompt)",
    "llm.setup.installing_sdk": "installing the Anthropic SDK into {path}",
    "llm.setup.python_missing": "python3 isn't available to create the venv",
    "llm.setup.venv_missing_apt": "python3-venv isn't installed. Run: sudo apt install python3-venv",
    "llm.setup.venv_failed": "couldn't create the venv: {err}",
    "llm.setup.pip_failed": "couldn't install anthropic: {err}",
    "llm.setup.sdk_installed": "Anthropic SDK installed at {path}",
    "llm.setup.restart_hint": "run `koa-core llm setup` again to finish (it now uses its own venv)",
    "llm.setup.test_prompt": "Say hello in a single short sentence.",
    "llm.setup.test_system": "You're a quick connectivity check. Answer in one short sentence.",
    "llm.setup.test_ok": "connected: {model} (in: {input_tokens} tokens, out: {output_tokens} tokens)",
    "llm.status.none": "no model connected (koa-core llm setup)",
    "llm.status.line": "{provider} · model {model} · key: {key_state}",
    "llm.status.key_yes": "yes",
    "llm.status.key_no": "no",

    # ── chat: `koa-core chat`, `/v1/chat` ─────────────────────────────
    "chat.list_empty": "no conversations yet",
    "chat.untitled": "(untitled)",
    "chat.list_line": "{id}  {title}  ({updated_at})",
    "chat.usage_line": "tokens: {input_tokens} in / {output_tokens} out",
    "chat.repl_hint": "chat with your KOA. /new starts over, /exit leaves.",
    "chat.new_conversation": "new conversation",

    # ── agent: system prompt live context ─────────────────────────────
    "agent.system.live_context": "Today is {today}. Open items right now: {open_items}.",
}

ES: dict[str, str] = {
    # ── cli: argparse ──────────────────────────────────────────────
    "cli.description": "Núcleo mínimo de un workspace KOA",
    "cli.home_help": "KOA_HOME (default: $KOA_HOME o ~/koa)",
    "cli.pair.admin_help": "el dispositivo podrá administrar otros",
    "cli.pair.url_help": "URL pública de este KOA (default: host/puerto de la config)",
    "cli.token.show_help": "imprime el token nuevo (por defecto no)",

    # ── shared ─────────────────────────────────────────────────────
    "common.error": "error: {err}",
    "common.warning_prefix": "aviso: ",
    "common.no_results": "sin resultados",

    # ── init ───────────────────────────────────────────────────────
    "init.no_seed": "no encuentro la semilla en {seed} (revisa KOA_SEED_DIR)",
    "init.done": "KOA listo en {home}",
    "init.seed_summary": "  semilla: {copied} archivo(s) copiados, {skipped} ya existían",
    "init.toml_written": "escrito",
    "init.toml_kept": "ya existía, sin tocar",
    "init.git_missing": "git no está instalado: se omite git init",
    "init.git_already": "ya era un repo git",
    "init.git_done": "git init hecho",
    "init.git_failed": "git init falló: {err}",

    # ── hooks ──────────────────────────────────────────────────────
    "hooks.no_git": "sin .git: se omite el hook",
    "hooks.updated": "hook de nombres actualizado",
    "hooks.chained": "hook de nombres encadenado al pre-commit existente",
    "hooks.installed": "hook de nombres instalado",
    "hooks.override_hint": (
        "core.hooksPath={value}: git ignora .git/hooks y el candado de nombres no "
        "corre. Arreglo: `git -C {home} config core.hooksPath .git/hooks` (sólo "
        "este repo) o agrega `koa-core names --staged` al pre-commit de {value}"
    ),

    # ── doctor ─────────────────────────────────────────────────────
    "doctor.python_fail": "se necesita >=3.10, hay {have}",
    "doctor.toml_missing": "no existe, se usan defaults",
    "doctor.toml_parse_fail": "no parsea: {err}",
    "doctor.db_pass": "{path} (esquema v{version})",
    "doctor.port_free": "puerto {port} libre",
    "doctor.port_healthy": "ya hay un koa-core sano en {url}",
    "doctor.port_unhealthy": "{url} respondió pero no está ok",
    "doctor.port_busy": "puerto {port} ocupado y no es koa-core ({err})",
    "doctor.git_missing": "no instalado",
    "doctor.hook_not_installed": "no instalado (koa-core hooks install)",
    "doctor.naming_issues": "{n} problema(s)",
    "doctor.devices_active": "{n} dispositivo(s) activo(s)",
    "doctor.token_bad_perms": (
        "{path} tiene permisos {mode} (debería ser 600): chmod 600 {path}"
    ),
    "doctor.token_in_toml": "token en koa.toml: muévelo con `koa-core token rotate`",
    "doctor.token_env": "KOA_TOKEN (variable de entorno)",
    "doctor.token_open": "sin token (modo abierto, sólo loopback)",
    "doctor.token_exposed": "sin token y escuchando fuera de loopback",
    "doctor.token_perm_unreadable": "no pude leer permisos de {path}: {err}",

    # ── todo ───────────────────────────────────────────────────────
    "todo.empty": "sin pendientes",
    "todo.created": "pendiente creado: {id}  {title}",

    # ── plans ──────────────────────────────────────────────────────
    "plans.none": "sin planes en {dir}",
    "plans.sync_line": (
        "{slug}: {tasks} tarea(s), {created} nueva(s), {completed} completada(s), "
        "{orphans} huérfana(s)"
    ),
    "plans.no_status": "sin status",
    "plans.list_line": "{slug}: {title} ({status})",

    # ── mem ────────────────────────────────────────────────────────
    "mem.saved": "memoria guardada: {path}",
    "mem.reindexed": "reindexados {n} recuerdo(s)",

    # ── claim ──────────────────────────────────────────────────────
    "claim.acquired": "candado tomado: {id} sobre {target} hasta {expires_at}",
    "claim.released": "liberado",
    "claim.not_found": "no existía ese candado",
    "claim.list_line": "{id}  {target}  {agent}  hasta {expires_at}",

    # ── pair ───────────────────────────────────────────────────────
    "pair.expires": "vence: {expires_at}",
    "pair.open_url": "abre esto en el dispositivo nuevo: {url}",
    "pair.install_qrencode": (
        "instala `qrencode` para ver el QR aquí mismo "
        "(pacman -S qrencode / apt install qrencode)."
    ),

    # ── devices ────────────────────────────────────────────────────
    "devices.empty": "sin dispositivos emparejados",
    "devices.status_revoked": "revocado",
    "devices.status_active": "activo",
    "devices.admin_suffix": " (admin)",
    "devices.never_seen": "nunca",
    "devices.no_platform": "sin plataforma",
    "devices.list_line": "{id}  [{status:8}] {name}{admin} · {platform} · visto: {seen}",
    "devices.revoked": "revocado",
    "devices.revoke_not_found": "no existía ese dispositivo (o ya estaba revocado)",
    "devices.invalid_code": "código inválido",
    "devices.invalid_or_expired_code": "código inválido o expirado",
    "devices.too_many_attempts": "demasiados intentos fallidos: espera unos minutos",
    "devices.default_name": "dispositivo",

    # ── token ──────────────────────────────────────────────────────
    "token.rotated": "token nuevo en {path} (permisos 600)",
    "token.toml_cleared": "se vació [api].token en {path}: ya no vive ahí",
    "token.usage_hint": (
        'úsalo como Authorization: Bearer <token>, o pégalo en la pantalla de '
        '"Conectar este dispositivo" si emparejas por primera vez sin abrir '
        "puertos."
    ),
    "token.value": "token: {token}",

    # ── unit ───────────────────────────────────────────────────────
    "unit.description": "koa-core (API de tu KOA)",
    "unit.written": "unit escrita en {path}",
    "unit.enable_hint": "para activarla: systemctl --user enable --now koa-core.service",

    # ── config (koa.toml escrito por `koa-core init`) ───────────────
    "config.default_toml": """\
# Configuracion de este KOA. Rutas relativas son relativas a KOA_HOME.
[api]
host = "127.0.0.1"
port = 8700
# El token vive en 10_personal/secrets/koa-core.token (koa-core token rotate
# lo crea). Este campo es solo compatibilidad con instalaciones viejas: si
# tiene algo, "koa-core doctor" avisa y "koa-core token rotate" lo vacia.
token = ""

[db]
path = "06_data/koa-core.sqlite"

[pairing]
# minutos de vida de un codigo de "koa-core pair" antes de que expire
code_ttl_s = 600

[ui]
# "auto" sigue KOA_LANG / LC_ALL / LC_MESSAGES / LANG; o fuerza "en" / "es".
lang = "auto"

[llm]
# No hace falta ningun modelo para instalar o usar KOA. Conecta uno con
# "koa-core llm setup" (esa seccion la escribe el; la llave nunca vive
# aqui, ve 10_personal/secrets/<provider>.env).
provider = ""          # "", "anthropic", "openai-compatible"
model = ""             # default por proveedor: claude-opus-5 / (obligatorio en openai-compatible)
base_url = ""          # solo openai-compatible (p. ej. Ollama: http://127.0.0.1:11434/v1)
""",

    # ── api ────────────────────────────────────────────────────────
    "api.bad_json": "cuerpo no es JSON válido: {err}",
    "api.token_missing": "falta el token (Authorization: Bearer <token>)",
    "api.token_invalid": "token inválido o revocado",
    "api.not_found": "no encontrado",
    "api.route_not_found": "ruta no encontrada",
    "api.method_not_supported": "método no soportado",
    "api.pair_needs_token": (
        "configura un token primero (koa-core token rotate) o usa "
        "`koa-core pair` en la máquina"
    ),
    "api.requires_admin": "requiere token maestro o dispositivo admin",
    "api.refuses_non_loopback": (
        "koa-core se niega a escuchar fuera de 127.0.0.1 sin un token. "
        "Corre `koa-core token rotate` (o define KOA_TOKEN)."
    ),
    "api.serving": "koa-core escuchando en http://{host}:{port}  (KOA_HOME={home})",
    "api.chat_needs_message": "el cuerpo necesita un \"message\" no vacío",

    # ── texto de bitácora (se ve en la pestaña Actividad de la UI) ──
    "activity.pair_generated": "código de emparejamiento generado",
    "activity.device_paired": "dispositivo emparejado: {name}",
    "err.item_title": 'un pendiente necesita título',
    "err.item_status": 'estado inválido: {status}',
    "err.item_missing": 'no existe el pendiente: {id}',
    "err.item_evidence": 'cerrar como done/dropped requiere --evidence',
    "err.mem_type": 'tipo inválido: {type} (usa {types})',
    "err.mem_name": 'el recuerdo necesita --name',
    "naming.deny.spaces": 'tiene espacios',
    "naming.deny.ascii": 'tiene acentos o caracteres no ASCII',
    "naming.deny.syncthing": 'es un conflicto de Syncthing',
    "naming.deny.orig": 'es un respaldo .orig de un merge',
    "naming.deny.bak": 'es un respaldo .bak',
    "naming.deny.tilde": 'es un respaldo de editor (~)',
    "naming.deny.autosave": 'es un autoguardado de Emacs (#…#)',
    "naming.deny.lock": 'es un lock de Emacs (.#…)',
    "naming.deny.egg": 'es salida de build de Python',
    "naming.deny.copy": 'tiene sufijo de copia «(1)»',
    "naming.deny.dash": 'termina en guion (slug cortado)',
    "naming.length": 'mide {n} caracteres (máx {max})',
    "naming.root": 'la raíz sólo admite carpetas NN_nombre y los archivos de entrada (AGENTS.md, README.md, koa.toml…)',
    "naming.root_hint": 'muévelo a la carpeta NN_ que le corresponde',
    "naming.level1": 'las carpetas de primer nivel van en kebab-case (minúsculas y guiones)',
    "naming.ok": 'nombres: OK',
    "naming.count": 'nombres: {n} problema(s)',

    # ── llm: errores de proveedor (koa_core.llm, chat/API/CLI) ────────
    "llm.error.not_configured": "sin modelo conectado todavía: corre `koa-core llm setup`",
    "llm.error.sdk_missing": "el SDK de Anthropic no está instalado: corre `koa-core llm setup` para instalarlo",
    "llm.error.key_missing": "sin llave de API para {provider} (define {env} o corre `koa-core llm setup`)",
    "llm.error.model_missing": "sin modelo configurado: corre `koa-core llm setup`",
    "llm.error.unknown_provider": "proveedor desconocido: {provider}",
    "llm.error.auth": "la API rechazó la llave (falló la autenticación): revísala con `koa-core llm setup`",
    "llm.error.permission": "la API negó permiso para esta llave",
    "llm.error.not_found": "la API dice que ese modelo o recurso no existe",
    "llm.error.rate_limit": "se alcanzó el límite de uso: intenta de nuevo en un momento",
    "llm.error.server": "los servidores del proveedor están fallando: intenta de nuevo en un rato",
    "llm.error.connection": "no se pudo alcanzar al proveedor: revisa tu conexión",
    "llm.error.timeout": "el proveedor tardó demasiado en responder",
    "llm.error.refusal": "el modelo se negó a responder",
    "llm.error.http": "el servidor respondió con un error ({status}): {detail}",
    "llm.error.unexpected": "error inesperado del proveedor: {detail}",
    "llm.error.max_tokens_cut": "(cortado: la respuesta llegó al límite de tokens del modelo)",
    "llm.error.iteration_cap": "se detuvo tras {n} llamadas a herramientas seguidas; pregunta de nuevo si hace falta más",
    "llm.error.conversation_missing": "no existe esa conversación: {id}",

    # ── llm: `koa-core llm setup/status/test` ─────────────────────────
    "llm.setup.ask_provider_prompt": (
        "Conecta un modelo:\n"
        "  1) Claude (llave de la API de Anthropic)\n"
        "  2) OpenAI\n"
        "  3) Ollama (local, gratis)\n"
        "  4) Otro compatible con OpenAI\n"
        "Opción [1-4]: "
    ),
    "llm.setup.invalid_choice": "opción inválida",
    "llm.setup.needs_provider": "pasa --provider anthropic|openai|ollama|other, o corre sin --yes para responder de forma interactiva",
    "llm.setup.needs_model": "este proveedor necesita --model",
    "llm.setup.needs_base_url": "un proveedor compatible con OpenAI necesita --base-url",
    "llm.setup.key_prompt": "llave de la API de {provider}: ",
    "llm.setup.key_missing": "no se dio ninguna llave (define {env} o respóndele al prompt)",
    "llm.setup.installing_sdk": "instalando el SDK de Anthropic en {path}",
    "llm.setup.python_missing": "python3 no está disponible para crear el venv",
    "llm.setup.venv_missing_apt": "python3-venv no está instalado. Corre: sudo apt install python3-venv",
    "llm.setup.venv_failed": "no se pudo crear el venv: {err}",
    "llm.setup.pip_failed": "no se pudo instalar anthropic: {err}",
    "llm.setup.sdk_installed": "SDK de Anthropic instalado en {path}",
    "llm.setup.restart_hint": "corre `koa-core llm setup` otra vez para terminar (ya usa su propio venv)",
    "llm.setup.test_prompt": "Saluda en una sola frase corta.",
    "llm.setup.test_system": "Eres una prueba rápida de conectividad. Responde en una frase corta.",
    "llm.setup.test_ok": "conectado: {model} (entrada: {input_tokens} tokens, salida: {output_tokens} tokens)",
    "llm.status.none": "sin modelo conectado (koa-core llm setup)",
    "llm.status.line": "{provider} · modelo {model} · llave: {key_state}",
    "llm.status.key_yes": "sí",
    "llm.status.key_no": "no",

    # ── chat: `koa-core chat`, `/v1/chat` ──────────────────────────────
    "chat.list_empty": "sin conversaciones todavía",
    "chat.untitled": "(sin título)",
    "chat.list_line": "{id}  {title}  ({updated_at})",
    "chat.usage_line": "tokens: {input_tokens} entrada / {output_tokens} salida",
    "chat.repl_hint": "platica con tu KOA. /new empieza de nuevo, /exit sale.",
    "chat.new_conversation": "conversación nueva",

    # ── agent: contexto vivo del system prompt ─────────────────────────
    "agent.system.live_context": "Hoy es {today}. Pendientes abiertos ahora mismo: {open_items}.",
}
