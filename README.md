# KOA

Your personal workspace for working with AI agents, on your own machine,
without depending on anyone else.

KOA gives you purposeful folders (each one explains what goes inside), a
to-do list, plans, persistent memory for your agents, locks so two agents
don't step on the same thing, an activity log, and a naming guard that keeps
things tidy. It works with Claude, GPT, Gemini, opencode, or a local model:
any agent that can read an `AGENTS.md`, use a CLI, or speak MCP.

Documentation is in English. The CLI, the HTTP API, and the web UI are
available in English and Spanish — see [Language](#language) below.

## Install

Arch, Debian 12+, or Ubuntu 22.04+:

```bash
bash install.sh --home ~/koa --smoke
```

- Installs `python3` and `git` if missing (asks for `sudo` only in that case).
- Creates `~/koa` with the `00_inbox` … `99_docs` folders, each with its own README.
- Leaves `koa-core` running at `http://127.0.0.1:8700` if your machine runs a systemd user session.
- `--smoke` tests everything at the end and fails loudly if something didn't stick.

Other options: `--yes` (no prompts), `--no-systemd` (containers, WSL),
`--no-deps` (you install the packages yourself), `--prefix DIR` (default `~/.local`).

Want your agent to do it instead? Ask it: "install KOA for me following
`skills/koa-install/SKILL.md`".

## Use

```bash
koa-core doctor                       # is everything OK?
koa-core todo add "My first to-do"
koa-core mem add --type user --name my-profile --description "Who I am" --body "…"
koa-core mem recall "profile"
koa-core plans sync                   # checkboxes in 99_docs/plans/*.md → to-dos
koa-core names --scan                 # checks naming
koa-core serve                        # API + web app at http://127.0.0.1:8700
```

Connect an agent over MCP (example with Claude Code):

```bash
claude mcp add --scope user koa -- koa-core mcp
```

## Try it without touching your machine

In a disposable Arch VM (QEMU/KVM, official image, with real systemd):

```bash
bash tests/vm/arch-vm.sh           # installs and drops you in (SSH + the app in your browser)
bash tests/vm/arch-vm.sh --check   # installs, tests, reboots, tests again, and shuts down
bash tests/vm/arch-vm.sh --stop    # shuts down; everything gets wiped
```

In Arch, Debian, and Ubuntu containers (faster, no systemd): `bash tests/distros/run.sh`.

## Language

English by default. If your locale is Spanish, `koa-core` speaks Spanish
back — no configuration needed. Resolution order:

1. `KOA_LANG=es` (or `en`) — set it once in your shell to force it.
2. `[ui] lang = "es"` in `koa.toml` (default `"auto"`) — pins it for this KOA
   regardless of who's connecting.
3. Your system locale: `LC_ALL` > `LC_MESSAGES` > `LANG`. `es_MX.UTF-8`,
   `es_ES`, or any value starting with `es` selects Spanish; anything else,
   English.

This covers the CLI, `koa-core doctor`, the HTTP API's error messages, and
`install.sh`. The web UI follows the browser's language (`navigator.language`)
the first time, remembers your choice in this browser after that, and has an
EN/ES toggle in the header if you want to switch it by hand.

## What it needs

Python 3.10 or newer, and git. Nothing else: `koa-core` uses only the standard
library. No API keys, cloud, VPN, or external database needed.

## Security

- Listens only on `127.0.0.1`. To open it to your network, `koa-core` requires
  a token: run `koa-core token rotate` (stored in
  `10_personal/secrets/koa-core.token`, permissions 600 — never in git).
- When there's a master token or a paired device, every request to `/v1/*`
  (except `/v1/health`) requires `Authorization: Bearer <token>`.
- `10_personal/` is private: git ignores it and agents don't read it.
- See [`docs/architecture.md`](docs/architecture.md).

## Talk to your KOA

No model is required to install or use KOA — everything above works without
one. If you want a chat (web tab and CLI) that can see your pending items,
plans, and memory, and act on them, connect a model:

```bash
koa-core llm setup      # asks which model, writes koa.toml, tests it
koa-core llm status     # what's connected (never prints the key)
koa-core chat -m "what's still open on my current plan?"
koa-core chat           # interactive: /new starts over, /exit leaves
```

Options and what they cost:

- **Ollama** — free, runs on your machine, nothing leaves it. `koa-core llm
  setup` defaults to `http://127.0.0.1:11434/v1`; pick a model that supports
  tool calling (`ollama pull qwen2.5:3b` if you don't have one yet).
- **Claude (Anthropic)** or **OpenAI** — paid per use, needs your own API
  key. `koa-core llm setup` installs the Anthropic SDK into its own venv the
  first time (never touching your system Python), asks for the key with a
  hidden prompt, and writes it to `10_personal/secrets/<provider>.env`
  (permissions 600) — never into `koa.toml`, never into a log.
- **Any other OpenAI-compatible server** (LM Studio, OpenRouter, …) — give
  it a `--base-url` and a model name.

What leaves the machine: with Ollama, nothing. With Claude or OpenAI, each
chat turn sends the conversation and the tool results (item titles, memory
snippets, activity lines) to that provider's API — the same things already
visible to anyone with local access to your KOA. Secrets never do: keys stay
in `10_personal/secrets/`, are never logged, and never appear in an API
response.

The agent only has the same domain tools any MCP client gets (items, memory,
plans, claims, activity) — no shell, no arbitrary file access, no network of
its own beyond the provider you chose.

## Connect your phone

Your phone, laptop, or any other device pairs with your KOA — no cookies, no
dedicated VPN, no code over WhatsApp:

```bash
koa-core token rotate     # once, if you're going to open it outside 127.0.0.1
koa-core pair             # shows a code XXXX-XXXX (and a QR if you have qrencode)
```

Open the URL it prints (or scan the QR) from the new device: it asks for a
name, exchanges the code for its own token, and it's connected. Each device
has its own token — revoke it whenever you want from the "Devices" tab in the
app, or with `koa-core devices revoke <id>`, without touching the others. The
code lasts 10 minutes and is single-use.

## More

- [`docs/architecture.md`](docs/architecture.md) — how it's built.
- [`docs/optional-modules.md`](docs/optional-modules.md) — how it grows without becoming mandatory.
- [`docs/mobile-and-desktop.md`](docs/mobile-and-desktop.md) — path to Android, iOS, and desktop.
- [`AGENTS.md`](AGENTS.md) — rules for changing the seed.

MIT license.
