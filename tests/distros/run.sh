#!/usr/bin/env bash
# Runs install.sh --smoke inside containers of each supported distro.
# Usage: bash tests/distros/run.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMAGES=(
  "archlinux:latest"
  "debian:12"
  "ubuntu:24.04"
  "ubuntu:22.04"
)

RESULTS=()
FAILED=0

for image in "${IMAGES[@]}"; do
  echo "==================================================================="
  echo "== $image"
  echo "==================================================================="
  if docker run --rm -v "$SEED_DIR:/seed:ro" "$image" bash -lc '
      set -e
      cp -r /seed /tmp/seed
      cd /tmp/seed
      bash install.sh --yes --no-systemd --smoke
    '; then
    RESULTS+=("PASS  $image")
  else
    RESULTS+=("FAIL  $image")
    FAILED=1
  fi
done

echo
echo "=== result by distro ==="
for r in "${RESULTS[@]}"; do
  echo "$r"
done

exit "$FAILED"
