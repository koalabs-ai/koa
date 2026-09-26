---
name: koa-install
description: Install a standalone, independent KOA on a Linux machine (Arch, Debian, or Ubuntu) — detect the distro, ask the bare minimum, install koa-core, create the skeleton at ~/koa, leave it running, and test it. Use this when someone asks "install KOA for me", "I want my own KOA", or clones this repo without knowing where to start.
---

# Install a standalone KOA

KOA is a personal workspace for working with AI agents: purposeful folders,
to-dos, memory, an activity log, locks between agents, and a naming guard.
This install **doesn't depend on anyone else**: no third-party servers, no
VPN, no API keys. Everything lives on the person's own machine.

You are the agent installing it. Your job ends when `koa-core doctor` comes
back green and you've shown the person the output.

## 0. Before touching anything

1. Confirm where you are: `cat /etc/os-release`, `python3 --version`, `git --version`.
   - Supported: Arch (and derivatives), Debian 12+, Ubuntu 22.04+. Python 3.10 or newer.
   - Other distro: don't improvise packages. Explain what's missing (python3 >= 3.10, git)
     and let the person install it; then continue from step 2 with `--no-deps`.
2. Ask **only** this, in one pass, with defaults:
   - Where should your KOA live? (default `~/koa`)
   - Should it start on boot? (default yes, if a user systemd is available)
   - Do you already have a `~/koa` folder? If it exists and has stuff in it,
     **don't overwrite it**: propose another path or ask for explicit permission.
3. Don't ask for API keys. KOA works without any. If the person wants a
   model, that's a separate step (section 5), and the key goes in
   `10_personal/`, never in the chat.

## 1. Get the seed

If you're already inside the seed repo (you see `install.sh`, `core/`, `skeleton/`),
use that directory. Otherwise, clone it wherever the person says (the public URL
comes from the project README; don't make one up).

## 2. Install

```bash
bash install.sh --home ~/koa --smoke          # interactive: asks for sudo only if a package is missing
bash install.sh --home ~/koa --yes --smoke    # no prompts
bash install.sh --home ~/koa --no-systemd     # no service (containers, WSL)
```

What it does, so you can explain it in plain words:
- installs `python3` and `git` if missing (pacman or apt);
- copies `koa-core` to `~/.local/share/koa-core/` and leaves the `~/.local/bin/koa-core` command;
- creates the skeleton at `~/koa`: `00_inbox` … `99_docs` folders, each with a
  README explaining what goes there, plus `AGENTS.md`, `koa.toml`, and `.gitignore`;
- runs `git init` and installs the naming guard as a pre-commit hook;
- if a user systemd is available, leaves `koa-core serve` running as a service on `127.0.0.1:8700`;
- with `--smoke`, tests the API, CLI, and MCP and exits with an error if anything fails.

If `~/.local/bin` isn't in `PATH`, say so and give the exact line to add it
(`echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc`).

## 3. Verify (don't skip this)

```bash
koa-core doctor
curl -s http://127.0.0.1:8700/v1/health
```

Show the output. Only say it's done if `doctor` has no FAIL.
A WARN gets explained, not hidden.

## 4. First use, with the person

```bash
koa-core todo add "Read the README in each folder"
koa-core mem add --type user --name my-profile --description "Who I am and how I work" --body "…"
koa-core plans sync          # turns checkboxes in 99_docs/plans/*.md into to-dos
koa-core names --scan        # checks the naming of what already exists
```

Have them open `http://127.0.0.1:8700` in the browser (it can also be
installed as an app from the phone's browser if it's on the same network and
a token is set up).

## 5. Connect agents (optional)

- **MCP** (Claude Code, Cursor, opencode, any MCP client): the server is
  `koa-core mcp` over stdio. Claude Code example:
  `claude mcp add --scope user koa -- koa-core mcp`.
- **Any agent without MCP**: have it read `~/koa/AGENTS.md` on start and use the CLI.
- **Models**: KOA doesn't bundle or require a provider. The person's key goes
  in `~/koa/10_personal/secrets/<provider>.env` with `chmod 600`. Never in
  the chat, never in git, never in `koa.toml`.

## 5b. Talk to your KOA (a built-in chat, optional)

Separate from MCP: this gives the *person* a chat (web tab and CLI) backed
by a model of their choice, that can see and act on their own KOA (items,
plans, memory, activity).

```bash
koa-core llm setup      # interactive: asks which model, tests it
koa-core chat -m "what's still open?"
```

Ask which one, in plain words about cost:
- **Ollama** — free, runs on their machine, nothing leaves it. Needs a model
  that supports tool calling installed (`ollama pull qwen2.5:3b` if unsure).
- **Claude or OpenAI** — paid per use, needs their own API key (never ask for
  it in chat; `koa-core llm setup` prompts for it with a hidden input and
  writes it straight to `10_personal/secrets/<provider>.env`, 600).

Non-interactively (only when the key is already in the environment):
`bash install.sh --llm anthropic` (needs `ANTHROPIC_API_KEY` set) or
`bash install.sh --llm ollama` (no key needed).

Verify with `koa-core llm status` (never prints the key) before saying it's connected.

## 6. Open it to other devices (optional, be careful)

By default it only listens on `127.0.0.1`. To see it from a phone or another
machine, the path is pairing the device, not sharing a single key:

1. `koa-core token rotate` — generates the master token and stores it in
   `10_personal/secrets/koa-core.token` (permissions 600, never in git or
   `koa.toml`; if `[api].token` from an old install has something in it,
   `rotate` clears it).
2. If it's going to listen outside loopback: `host = "0.0.0.0"` (or the VPN
   IP) in `[api]` in `koa.toml` — koa-core refuses to start that way without
   the token from the previous step.
3. `koa-core pair` on the home machine: prints a code `XXXX-XXXX` (and a QR
   if `qrencode` is installed), valid for 10 minutes, single-use.
4. On the new device, open the printed URL (`http://…/pair#code=…`) or scan
   the QR: it asks for a name and exchanges the code for that device's own
   token — it never sees or shares the master token.
5. Explain that each device is revoked separately
   (`koa-core devices list` / `koa-core devices revoke <id>`, or the
   "Devices" tab in the app if the device is admin) and that the code
   expires on its own if nobody uses it within 10 minutes.

## Rules for you, the agent

- Don't delete or overwrite anything of the person's without explicit permission.
- Don't publish anything (repos, screenshots with data) without permission.
- Don't put your own data, your operator's data, or another install's data into this one.
- If something fails, show the real error and the command that produced it;
  don't blindly retry or silently change strategy.
- When done, summarize in plain words: what got installed, where, how to open
  it, and what's next.
