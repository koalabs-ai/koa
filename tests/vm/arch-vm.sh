#!/usr/bin/env bash
# Tests the seed on a real Arch Linux virtual machine (with systemd),
# not a container. One command; the VM is disposable: every run boots
# clean from the official image and nothing gets written to it.
#
# Usage:
#   bash tests/vm/arch-vm.sh           # installs, leaves the VM running, tells you how to log in
#   bash tests/vm/arch-vm.sh --check   # installs, tests, and shuts down; exit 0 = all good
#   bash tests/vm/arch-vm.sh --stop    # shuts down a VM you left running
#
# Requires: qemu-system-x86_64 with KVM, python3, ssh, curl. Nothing else: the
# initial configuration (cloud-init) is served from this same machine over HTTP.
set -euo pipefail

SEED_DIR=$(cd "$(dirname "$0")/../.." && pwd)
CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/koa-semilla/vm
IMG_URL=${KOA_VM_IMAGE_URL:-https://geo.mirror.pkgbuild.com/images/latest/Arch-Linux-x86_64-cloudimg.qcow2}
IMG=$CACHE/arch-cloudimg.qcow2
SSH_PORT=${KOA_VM_SSH_PORT:-2222}
MEM=${KOA_VM_MEM:-2048}
TIMEOUT=${KOA_VM_TIMEOUT:-900}
PIDFILE=$CACHE/qemu.pid
MODE=interactive

case "${1:-}" in
  --check) MODE=check ;;
  --stop)
    if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then echo "VM stopped."; else echo "No VM was running."; fi
    rm -f "$PIDFILE"; exit 0 ;;
  ""|--interactive) ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac

say() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v qemu-system-x86_64 >/dev/null || die "qemu is missing (Arch: sudo pacman -S qemu-base · Debian/Ubuntu: sudo apt install qemu-system-x86)"
[ -w /dev/kvm ] || die "no access to /dev/kvm: add your user to the kvm group and log back in"
[ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && die "a VM is already running (bash $0 --stop)"
mkdir -p "$CACHE"

# 1. Official image, verified against its SHA256.
if [ ! -f "$IMG" ] || [ "${KOA_VM_REFRESH:-0}" = 1 ]; then
  say "downloading the official Arch image (~560 MB, one time only)"
  curl -fL --progress-bar -o "$IMG.part" "$IMG_URL"
  want=$(curl -fsSL "$IMG_URL.SHA256" | awk '{print $1}')
  got=$(sha256sum "$IMG.part" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$got" ] || { rm -f "$IMG.part"; die "SHA256 checksum doesn't match"; }
  mv "$IMG.part" "$IMG"
fi

# 2. Disposable SSH key, just for this VM (doesn't touch your own keys).
[ -f "$CACHE/id_ed25519" ] || ssh-keygen -q -t ed25519 -N '' -C koa-vm -f "$CACHE/id_ed25519"
SSH=(ssh -i "$CACHE/id_ed25519" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=5 koa@127.0.0.1)

# 3. The packaged seed + cloud-init, served to the VM over HTTP.
WORK=$(mktemp -d)
cleanup() { [ -n "${HTTP_PID:-}" ] && kill "$HTTP_PID" 2>/dev/null || true; }
trap cleanup EXIT
tar czf "$WORK/semilla.tgz" -C "$SEED_DIR" --exclude=.pytest_cache --exclude=__pycache__ --exclude=.git .
HTTP_PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
cat > "$WORK/meta-data" <<EOF
instance-id: koa-vm-$(date +%s)
local-hostname: koa-prueba
EOF
cat > "$WORK/user-data" <<EOF
#cloud-config
users:
  - name: koa
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - $(cat "$CACHE/id_ed25519.pub")
runcmd:
  - [bash, -c, "loginctl enable-linger koa; sleep 3"]
  - - bash
    - -c
    - |
      u=\$(id -u koa)
      sudo -u koa env HOME=\$(getent passwd koa | cut -d: -f6) XDG_RUNTIME_DIR=/run/user/\$u DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$u/bus bash -lc '
        mkdir -p ~/semilla && curl -fsS http://10.0.2.2:$HTTP_PORT/semilla.tgz | tar xz -C ~/semilla &&
        bash ~/semilla/install.sh --yes --home ~/koa --smoke' > /var/log/koa-install.log 2>&1
      echo "KOA-VM-RESULT=\$?" > /dev/ttyS0
EOF
python3 -m http.server --bind 127.0.0.1 "$HTTP_PORT" --directory "$WORK" >/dev/null 2>&1 &
HTTP_PID=$!

# 4. Boot the VM. snapshot=on: anything it writes is discarded on shutdown.
say "booting Arch in QEMU/KVM (${MEM} MB, SSH on 127.0.0.1:$SSH_PORT)"
: > "$WORK/serial.log"
qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m "$MEM" \
  -drive "file=$IMG,if=virtio,format=qcow2,snapshot=on" \
  -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22" \
  -smbios "type=1,serial=ds=nocloud;s=http://10.0.2.2:$HTTP_PORT/" \
  -display none -serial "file:$WORK/serial.log" \
  -daemonize -pidfile "$PIDFILE"

# 5. Wait for the installer to finish inside.
say "waiting for cloud-init to install the seed (max ${TIMEOUT}s)"
result=""
for _ in $(seq "$TIMEOUT"); do
  result=$(grep -ao 'KOA-VM-RESULT=[0-9]*' "$WORK/serial.log" | tail -1 | cut -d= -f2 || true)
  [ -n "$result" ] && break
  sleep 1
done
[ -n "$result" ] || { kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"; die "timed out; console log at $WORK/serial.log"; }

# 6. What containers don't test: the user systemd service.
say "installer result: exit $result"
"${SSH[@]}" 'tail -n 12 /var/log/koa-install.log' || true
svc=$("${SSH[@]}" 'systemctl --user is-active koa-core' 2>/dev/null || true)
health=$("${SSH[@]}" 'curl -fsS http://127.0.0.1:8700/v1/health' 2>/dev/null || true)
echo "koa-core service:  ${svc:-no response}"
echo "health:            ${health:-no response}"
# A fresh install should stay OPEN (no devices): if the smoke test leaves one
# active, auth turns itself on and the browser asks for a code (bug 2026-09-25).
open_code=$("${SSH[@]}" 'curl -s -o /dev/null -w %{http_code} http://127.0.0.1:8700/v1/items' 2>/dev/null || true)
echo "API without token: ${open_code:-no response} (expected 200)"
ok=0; [ "$result" = 0 ] && [ "$svc" = active ] && [ -n "$health" ] && [ "$open_code" = 200 ] && ok=1

# 7. And that it comes back on its own after a reboot (what someone installing on their laptop expects).
if [ "$ok" = 1 ] && [ "$MODE" = check ]; then
  say "rebooting the VM to check that the service comes back on its own"
  "${SSH[@]}" 'sudo systemctl reboot' >/dev/null 2>&1 || true
  sleep 10; svc=""
  # `active` shows up as soon as the process starts, before it opens the port:
  # also wait for it to answer /v1/health.
  health=""
  for _ in $(seq 120); do
    svc=$("${SSH[@]}" 'systemctl --user is-active koa-core' 2>/dev/null || true)
    if [ "$svc" = active ]; then
      health=$("${SSH[@]}" 'curl -fsS http://127.0.0.1:8700/v1/health' 2>/dev/null || true)
      [ -n "$health" ] && break
    fi
    sleep 2
  done
  echo "after reboot:      service=${svc:-no response} health=${health:+ok}"
  [ "$svc" = active ] && [ -n "$health" ] || ok=0
fi

if [ "$MODE" = check ]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true; rm -f "$PIDFILE"
  [ "$ok" = 1 ] && { echo "PASS  arch-vm (systemd)"; exit 0; }
  echo "FAIL  arch-vm"; exit 1
fi

cat <<EOF

The VM is still running. To log in:
  ssh -i $CACHE/id_ed25519 -p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null koa@127.0.0.1

To see the web app in your browser (leave this open and go to http://127.0.0.1:8700):
  ssh -i $CACHE/id_ed25519 -p $SSH_PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -N -L 8700:127.0.0.1:8700 koa@127.0.0.1

Inside, try: koa-core doctor · koa-core pair · reboot the VM with 'sudo reboot' and check the service comes back on its own.
To shut it down: bash $0 --stop   (everything gets wiped on shutdown)
EOF
[ "$ok" = 1 ]
