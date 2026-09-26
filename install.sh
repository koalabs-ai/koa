#!/usr/bin/env bash
# KOA (koa-core) installer: Arch, Debian, and Ubuntu. No dependencies
# beyond python3 >= 3.10 and git. Doesn't use sudo unless a package is missing.
set -euo pipefail

HOME_DIR="${HOME}/koa"
PREFIX="${HOME}/.local"
YES=0
NO_SYSTEMD=0
NO_DEPS=0
SMOKE=0
LLM_CHOICE="none"

# ── idioma: KOA_LANG > LC_ALL > LC_MESSAGES > LANG > "en" ─────────────
# Mismo criterio que koa_core.i18n: cualquier valor que empiece con "es"
# (sin importar mayúsculas) elige español; lo demás, inglés.
LANG_CODE="en"
for _v in "${KOA_LANG:-}" "${LC_ALL:-}" "${LC_MESSAGES:-}" "${LANG:-}"; do
  case "$_v" in
    "" | [Aa][Uu][Tt][Oo]) continue ;;
    [Ee][Ss]*) LANG_CODE="es"; break ;;
    *) LANG_CODE="en"; break ;;
  esac
done
unset _v

# msg EN ES -> prints the string matching LANG_CODE, no trailing newline logic
msg() { if [ "$LANG_CODE" = "es" ]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }
log() { printf '==> %s\n' "$(msg "$1" "${2:-$1}")"; }
fail() { printf 'ERROR: %s\n' "$(msg "$1" "${2:-$1}")" >&2; exit 1; }

usage() {
  if [ "$LANG_CODE" = "es" ]; then
    cat <<'EOF'
Uso: install.sh [--home DIR] [--prefix DIR] [--yes] [--no-systemd] [--no-deps] [--smoke] [--llm anthropic|ollama|none]

  --home DIR      donde vive tu KOA (default: ~/koa)
  --prefix DIR    donde se instala el binario (default: ~/.local)
  --yes           no preguntar nada
  --no-systemd    no instalar el servicio de systemd de usuario
  --no-deps       no instalar paquetes del sistema (asume que ya estan)
  --smoke         al terminar, probar API + CLI + MCP y fallar si algo no funciona
  --llm CHOICE    conecta un modelo sin preguntar: "anthropic" (necesita
                  ANTHROPIC_API_KEY en el ambiente), "ollama" (local, gratis;
                  KOA_OLLAMA_MODEL opcional, default qwen2.5:3b) o "none" (default)
EOF
  else
    cat <<'EOF'
Usage: install.sh [--home DIR] [--prefix DIR] [--yes] [--no-systemd] [--no-deps] [--smoke] [--llm anthropic|ollama|none]

  --home DIR      where your KOA lives (default: ~/koa)
  --prefix DIR    where the binary is installed (default: ~/.local)
  --yes           don't ask anything
  --no-systemd    don't install the user systemd service
  --no-deps       don't install system packages (assumes they're already there)
  --smoke         after installing, test API + CLI + MCP and fail if anything doesn't work
  --llm CHOICE    connect a model without asking: "anthropic" (needs
                  ANTHROPIC_API_KEY in the environment), "ollama" (local, free;
                  optional KOA_OLLAMA_MODEL, default qwen2.5:3b), or "none" (default)
EOF
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --home) HOME_DIR="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --yes) YES=1; shift ;;
    --no-systemd) NO_SYSTEMD=1; shift ;;
    --no-deps) NO_DEPS=1; shift ;;
    --smoke) SMOKE=1; shift ;;
    --llm) LLM_CHOICE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: %s\n' "$(msg "unknown option: $1" "opcion desconocida: $1")" >&2; usage; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARE_DIR="${PREFIX}/share/koa-core"
BIN_DIR="${PREFIX}/bin"

# ── 1. distro ────────────────────────────────────────────────────────
DISTRO_FAMILY=""
if [ -r /etc/os-release ]; then
  . /etc/os-release
  case "${ID:-}${ID_LIKE:-}" in
    *arch*) DISTRO_FAMILY="arch" ;;
    *) case "${ID:-}" in
         debian|ubuntu) DISTRO_FAMILY="debian" ;;
         *) case "${ID_LIKE:-}" in *debian*) DISTRO_FAMILY="debian" ;; esac ;;
       esac ;;
  esac
fi
if [ -z "$DISTRO_FAMILY" ]; then
  if [ "$LANG_CODE" = "es" ]; then
    cat <<EOF >&2
No reconozco esta distro (ID=${ID:-?} ID_LIKE=${ID_LIKE:-?}).
Instala a mano: python3 >= 3.10, git. Luego corre este script con --no-deps.
EOF
  else
    cat <<EOF >&2
I don't recognize this distro (ID=${ID:-?} ID_LIKE=${ID_LIKE:-?}).
Install by hand: python3 >= 3.10, git. Then run this script with --no-deps.
EOF
  fi
  exit 2
fi
log "distro detected: $DISTRO_FAMILY" "distro detectada: $DISTRO_FAMILY"

# ── 2. dependencias ──────────────────────────────────────────────────
missing=()
command -v python3 >/dev/null 2>&1 || missing+=("python3")
command -v git >/dev/null 2>&1 || missing+=("git")

if [ "$NO_DEPS" -eq 0 ] && [ "${#missing[@]}" -gt 0 ]; then
  log "missing: ${missing[*]} — installing" "faltan: ${missing[*]} — instalando"
  SUDO=""
  if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 \
      || fail "sudo is needed to install packages and it isn't there" \
              "hace falta sudo para instalar paquetes y no esta"
    SUDO="sudo"
  fi
  if [ "$DISTRO_FAMILY" = "arch" ]; then
    $SUDO pacman -Sy --needed --noconfirm python git ca-certificates
  else
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq python3 git ca-certificates
  fi
elif [ "${#missing[@]}" -gt 0 ]; then
  fail "missing packages (${missing[*]}) and --no-deps was passed" \
       "faltan paquetes (${missing[*]}) y se paso --no-deps"
else
  log "python3 and git were already there: not touching the package system" \
      "python3 y git ya estaban: no se toca el sistema de paquetes"
fi

command -v python3 >/dev/null 2>&1 \
  || fail "python3 is still missing after installing" \
          "python3 sigue sin aparecer después de instalar"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "python3 >= 3.10 is needed (found $(python3 --version 2>&1))" \
          "se necesita python3 >= 3.10 (hay $(python3 --version 2>&1))"

# ── 3. copiar koa-core + skeleton ────────────────────────────────────
log "installing koa-core into $SHARE_DIR" "instalando koa-core en $SHARE_DIR"
mkdir -p "$SHARE_DIR" "$BIN_DIR"
rm -rf "$SHARE_DIR/koa_core" "$SHARE_DIR/skeleton"
cp -r "$SCRIPT_DIR/core/koa_core" "$SHARE_DIR/koa_core"
cp -r "$SCRIPT_DIR/skeleton" "$SHARE_DIR/skeleton"

cat > "$BIN_DIR/koa-core" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${SHARE_DIR}\${PYTHONPATH:+:\$PYTHONPATH}"
export KOA_SEED_DIR="${SHARE_DIR}/skeleton"
exec python3 -m koa_core "\$@"
EOF
chmod +x "$BIN_DIR/koa-core"
case ":$PATH:" in
  *":$BIN_DIR:"*) : ;;
  *) log "add $BIN_DIR to your PATH: echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc" \
         "agrega $BIN_DIR a tu PATH: echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc" ;;
esac
export PATH="$BIN_DIR:$PATH"

case "$LLM_CHOICE" in
  none|anthropic|ollama) : ;;
  *) fail "unknown --llm value: $LLM_CHOICE (use anthropic, ollama, or none)" \
          "valor desconocido para --llm: $LLM_CHOICE (usa anthropic, ollama o none)" ;;
esac

# ── 4. crear el workspace ────────────────────────────────────────────
log "creating the skeleton at $HOME_DIR" "creando el skeleton en $HOME_DIR"
KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" init

# ── 4b. conectar un modelo (opcional) ─────────────────────────────────
if [ "$LLM_CHOICE" = "anthropic" ]; then
  [ -n "${ANTHROPIC_API_KEY:-}" ] || fail \
    "--llm anthropic needs ANTHROPIC_API_KEY set in the environment" \
    "--llm anthropic necesita ANTHROPIC_API_KEY en el ambiente"
  log "connecting Claude (Anthropic)" "conectando Claude (Anthropic)"
  KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" llm setup --provider anthropic --yes
elif [ "$LLM_CHOICE" = "ollama" ]; then
  log "connecting Ollama (local)" "conectando Ollama (local)"
  KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" llm setup --provider ollama \
    --model "${KOA_OLLAMA_MODEL:-qwen2.5:3b}" --yes
else
  echo "$(msg "Want to talk to your KOA? Run: koa-core llm setup" \
            "¿Quieres platicar con tu KOA? Corre: koa-core llm setup")"
fi

# ── 5. systemd de usuario (opcional) ─────────────────────────────────
STARTED_BY_SYSTEMD=0
if [ "$NO_SYSTEMD" -eq 0 ] && systemctl --user show-environment >/dev/null 2>&1; then
  log "user systemd available: installing the service" \
      "systemd de usuario disponible: instalando servicio"
  KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" unit install
  systemctl --user daemon-reload
  systemctl --user enable --now koa-core.service
  STARTED_BY_SYSTEMD=1
else
  log "no user systemd (or --no-systemd): start it by hand with:" \
      "sin systemd de usuario (o --no-systemd): arranca a mano con:"
  echo "    KOA_HOME=\"$HOME_DIR\" koa-core serve"
fi

# ── 6. smoke test ─────────────────────────────────────────────────────
if [ "$SMOKE" -eq 1 ]; then
  log "smoke test" "smoke test"
  # El smoke corre sobre un KOA TEMPORAL, no sobre el del usuario: antes dejaba
  # un dispositivo admin activo (la auth quedaba prendida en una instalación
  # nueva y el navegador pedía código) más pendientes y memorias de prueba.
  SMOKE_DIR="$(mktemp -d)"
  SMOKE_HOME="$SMOKE_DIR/koa"
  "$BIN_DIR/koa-core" init --home "$SMOKE_HOME" >/dev/null \
    || fail "couldn't create the smoke test's temporary KOA" \
            "no se pudo crear el KOA temporal del smoke"
  KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" doctor \
    || fail "koa-core doctor came back with a FAIL" "koa-core doctor salio con FAIL"
  SMOKE_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" serve --host 127.0.0.1 --port "$SMOKE_PORT" \
    >$SMOKE_DIR/smoke.log 2>&1 &
  SERVER_PID=$!
  cleanup() { kill "$SERVER_PID" >/dev/null 2>&1 || true; case "$SMOKE_DIR" in /tmp/*|"${TMPDIR:-/tmp}"/*) rm -rf "$SMOKE_DIR" ;; esac; }
  trap cleanup EXIT

  ok=0
  for _ in $(seq 1 50); do
    if python3 -c "
import urllib.request, sys
try:
    with urllib.request.urlopen('http://127.0.0.1:${SMOKE_PORT}/v1/health', timeout=1) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
"; then ok=1; break; fi
    sleep 0.2
  done
  [ "$ok" -eq 1 ] || fail "the server didn't answer /v1/health" "el servidor no contesto /v1/health"
  log "health OK on :$SMOKE_PORT" "health OK en :$SMOKE_PORT"


  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" todo add "smoke test" --json >$SMOKE_DIR/smoke-item.json \
    || fail "todo add failed" "todo add falló"
  grep -q "smoke test" $SMOKE_DIR/smoke-item.json \
    || fail "todo add didn't return the item" "todo add no devolvio el item"
  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" todo list --json | grep -q "smoke test" \
    || fail "todo list doesn't show the item" "todo list no muestra el item"

  mcp_out="$(printf '%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
    | KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" mcp 2>$SMOKE_DIR/smoke-mcp.log)"
  echo "$mcp_out" | grep -q '"serverInfo"' \
    || fail "mcp initialize didn't answer serverInfo" "mcp initialize no respondio serverInfo"
  echo "$mcp_out" | grep -q '"todo_add"' \
    || fail "mcp tools/list doesn't include todo_add" "mcp tools/list no incluye todo_add"
  log "mcp OK" "mcp OK"

  log "pairing (pair -> claim -> authenticated -> revoke -> 401)" \
      "emparejamiento (pair -> claim -> autenticado -> revocar -> 401)"
  # Un dispositivo admin primero (para que la auth siga exigida tras revocar
  # el segundo) y luego el dispositivo "normal" que se prueba de verdad.
  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" pair --admin --json --url "http://127.0.0.1:${SMOKE_PORT}" \
    >$SMOKE_DIR/smoke-pair-admin.json || fail "koa-core pair --admin failed" "koa-core pair --admin falló"
  python3 -c "
import json, urllib.request
pair = json.load(open('$SMOKE_DIR/smoke-pair-admin.json'))
req = urllib.request.Request(
    'http://127.0.0.1:${SMOKE_PORT}/v1/pair/claim', method='POST',
    data=json.dumps({'code': pair['code'], 'name': 'smoke-admin', 'platform': 'linux'}).encode(),
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=5) as r:
    json.dump(json.load(r), open('$SMOKE_DIR/smoke-claim-admin.json', 'w'))
" || fail "pair/claim (admin) failed" "pair/claim (admin) falló"

  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" pair --json --url "http://127.0.0.1:${SMOKE_PORT}" \
    >$SMOKE_DIR/smoke-pair.json || fail "koa-core pair failed" "koa-core pair falló"
  python3 -c "
import json, urllib.request
pair = json.load(open('$SMOKE_DIR/smoke-pair.json'))
req = urllib.request.Request(
    'http://127.0.0.1:${SMOKE_PORT}/v1/pair/claim', method='POST',
    data=json.dumps({'code': pair['code'], 'name': 'smoke', 'platform': 'linux'}).encode(),
    headers={'Content-Type': 'application/json'},
)
with urllib.request.urlopen(req, timeout=5) as r:
    json.dump(json.load(r), open('$SMOKE_DIR/smoke-claim.json', 'w'))
" || fail "pair/claim failed" "pair/claim falló"
  DEVICE_TOKEN="$(python3 -c "import json; print(json.load(open('$SMOKE_DIR/smoke-claim.json'))['token'])")"
  DEVICE_ID="$(python3 -c "import json; print(json.load(open('$SMOKE_DIR/smoke-claim.json'))['device_id'])")"
  [ -n "$DEVICE_TOKEN" ] || fail "pair/claim didn't return a token" "pair/claim no devolvio token"

  python3 -c "
import urllib.error, urllib.request
req = urllib.request.Request('http://127.0.0.1:${SMOKE_PORT}/v1/items')
try:
    urllib.request.urlopen(req, timeout=3)
    raise SystemExit('no token should have given 401')
except urllib.error.HTTPError as e:
    assert e.code == 401, e.code
" || fail "after pairing, /v1/items without a token should have given 401" \
          "tras emparejar, /v1/items sin token debió dar 401"

  python3 -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:${SMOKE_PORT}/v1/items')
req.add_header('Authorization', 'Bearer ${DEVICE_TOKEN}')
with urllib.request.urlopen(req, timeout=3) as r:
    assert r.status == 200, r.status
" || fail "/v1/items with the device's token should have given 200" \
          "/v1/items con el token del dispositivo debió dar 200"

  KOA_HOME="$SMOKE_HOME" "$BIN_DIR/koa-core" devices revoke "$DEVICE_ID" \
    || fail "koa-core devices revoke failed" "koa-core devices revoke falló"

  python3 -c "
import urllib.error, urllib.request
req = urllib.request.Request('http://127.0.0.1:${SMOKE_PORT}/v1/items')
req.add_header('Authorization', 'Bearer ${DEVICE_TOKEN}')
try:
    urllib.request.urlopen(req, timeout=3)
    raise SystemExit('revoked token should have given 401')
except urllib.error.HTTPError as e:
    assert e.code == 401, e.code
" || fail "after revoking, the old token should have given 401" \
          "tras revocar, el token viejo debió dar 401"
  log "pairing OK" "emparejamiento OK"

  cleanup
  trap - EXIT
  # El KOA real tiene que quedar abierto (sin dispositivos) tras el smoke.
  # Se compara el JSON, no el texto traducido de "koa-core devices list".
  if KOA_HOME="$HOME_DIR" "$BIN_DIR/koa-core" devices list --json 2>/dev/null \
      | grep -qF '"revoked_at": null'; then
    fail "the smoke test left active devices in $HOME_DIR" \
         "el smoke dejó dispositivos activos en $HOME_DIR"
  fi
  log "smoke test OK" "smoke test OK"
fi

echo
echo "$(msg "Done. Your KOA lives at $HOME_DIR." "Listo. Tu KOA vive en $HOME_DIR.")"
if [ "$STARTED_BY_SYSTEMD" -eq 1 ]; then
  echo "$(msg "Running as a service: http://127.0.0.1:8700" "Corriendo como servicio: http://127.0.0.1:8700")"
else
  echo "$(msg "Start it with: KOA_HOME=\"$HOME_DIR\" koa-core serve" \
            "Arráncalo con: KOA_HOME=\"$HOME_DIR\" koa-core serve")"
fi
echo "$(msg "First steps: koa-core doctor · koa-core todo add \"...\" · open http://127.0.0.1:8700" \
          "Primeros pasos: koa-core doctor · koa-core todo add \"...\" · abre http://127.0.0.1:8700")"
