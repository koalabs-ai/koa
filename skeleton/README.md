# KOA — Personal workspace for AI agents

KOA is an organized directory for your Linux machine: purposeful folders, persistent memory, to-dos, an activity log, and rules. Runs without depending on external services. An AI agent reads AGENTS.md first, then the README of the folder it's going to work in.

## Folder map

| Folder | For what |
|---------|----------|
| 00_inbox | Quick capture; sort later |
| 01_dotfiles | Shell and terminal configuration |
| 02_editor | Editor config (Emacs, Neovim, VS Code) |
| 03_system | Systemd units, packages, recovery |
| 04_llm | Constitution, skills, prompts, activity log |
| 05_services | Processes (servers, daemons, bots) |
| 06_data | Memory, sqlite, notes, datasets |
| 07_tools | CLI, in-house libraries |
| 08_backups | Backups |
| 09_archive | What's been retired (a single place) |
| 10_personal | PRIVATE: secrets, personal docs |
| 11_work | Projects, clients, business |
| 99_docs | Plans, concepts, runbooks, decisions |

## Naming rules

At the root: only `NN_name` folders and entry files (AGENTS.md, README.md, koa.toml, .gitignore).

- Lowercase, numbers, hyphens: `my-project`, not `My Project` or `my_project`.
- No spaces, accents, "(1)", `.bak`, `.orig`, `~`, `sync-conflict`.
- ISO dates at the start: `2026-01-31-topic.md`.
- Uppercase only when the tool requires it: README.md, AGENTS.md, LICENSE, Makefile, Dockerfile.
- Exception: `_template` for templates.

## Three commands for the day

```bash
koa-core todo add "Finish the plan"       # New to-do
koa-core mem recall "project X"           # Search memory
koa-core serve                            # Web app at http://127.0.0.1:8700
```

## How an AI agent reads it

1. Read AGENTS.md to understand your rules and priorities.
2. Read the README of the folder it's going to work in.
3. Respect 10_personal: never touch it or index it.
4. Leave a trace: activity log with `koa-core log` and memory with `koa-core mem add`.
