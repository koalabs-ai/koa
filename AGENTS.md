# AGENTS.md — KOA seed

This repo is the KOA **seed**: what someone downloads to get their own KOA on
their machine, without depending on anyone else.

- Were you asked to install KOA? Follow [`skills/koa-install/SKILL.md`](skills/koa-install/SKILL.md).
- Going to change the seed? Read this whole file.

## What's here

| Path | What it is |
|---|---|
| `install.sh` | Installer for Arch, Debian, and Ubuntu (detects the distro). |
| `core/` | `koa-core`: to-dos, plans, memory, locks, activity log, HTTP API, installable UI (PWA), and MCP server. Python standard library only, >= 3.10. `core/koa_core/llm/` + `agent.py` are the opt-in built-in agent (`koa-core chat`); they stay out of the core's dependency-free guarantee (rule 2) by only importing a provider SDK when one is actually configured. |
| `skeleton/` | The tree copied to `~/koa`: `NN_name` folders, each with a README explaining it. |
| `skills/` | Skills for agents (install, work). SKILL.md format, model-agnostic. |
| `tests/distros/` | Tests the installer in containers of the supported distros. |
| `tests/vm/` | Tests in a disposable Arch VM with real systemd (QEMU/KVM). |
| `docs/` | Architecture, optional modules, and the path to mobile/desktop. |

## Rules for changing the seed

1. **Nothing from the author inside.** No personal names, businesses, domains,
   IPs, `/home/<someone>` paths, or hosts. `tests/test_no_personal_traces.py` checks this.
2. **No runtime dependencies.** Standard library only. If something needs a
   library, it's an optional module, not the core.
3. **Loopback by default.** Nothing listens outside `127.0.0.1` without a token.
4. **Every change is tested on all four distros**: `bash tests/distros/run.sh`;
   if it touches the installer or the service, also on the VM:
   `bash tests/vm/arch-vm.sh --check` (real systemd and a reboot).
5. English for docs and code. User-facing strings go through i18n (`koa_core/i18n.py`, UI catalog) in English and Spanish.
6. Names follow the naming guard (`koa-core names --scan` must be green).
