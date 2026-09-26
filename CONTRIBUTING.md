# Contributing to KOA

Thanks for helping. KOA is small on purpose, so a few rules keep it that way.

## Before you open a pull request

1. **The core stays dependency-free.** `core/koa_core` uses only the Python
   standard library (3.10+). Anything that needs a package is an optional
   module (see `docs/optional-modules.md`), like the Claude provider, which
   installs the official Anthropic SDK in its own virtual environment.
2. **Local-first, loopback by default.** Nothing listens outside `127.0.0.1`
   without a token.
3. **No personal data.** No real names, businesses, hostnames, private IPs,
   home paths or keys. `core/tests/test_no_personal_traces.py` enforces this.
4. **Every user-facing string goes through i18n** (`koa_core/i18n_catalog.py`
   and `koa_core/ui/i18n.js`) in English and Spanish.
5. **Names follow the naming guard:** `koa-core names --scan` must be clean.

## Tests

```bash
cd core && python3 -m pytest -q          # unit tests
bash tests/distros/run.sh                # installer on Arch, Debian 12, Ubuntu 24.04, Ubuntu 22.04 (Docker)
bash tests/vm/arch-vm.sh --check         # real Arch VM with systemd and a reboot (QEMU/KVM)
```

If your change touches the installer or the service, run the VM check too.

## Style

- Code and docs in English; comments explain *why*, not *what*.
- Small pull requests with a clear description of the problem they solve.
