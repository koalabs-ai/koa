# AGENTS.md — this KOA

Read by every AI agent working here (Claude, GPT, Gemini, local models,
whatever). It's short on purpose: the detail lives in each folder's README
and in `04_llm/constitution.md`.

## First
1. Read `04_llm/constitution.md` (how you behave) and the skill
   `04_llm/skills/koa-work/SKILL.md` (how you work here).
2. Before working in a folder, read its `README.md`.

## Map

| Folder | What for |
|---|---|
| `00_inbox` | Quick capture; emptied often. |
| `01_dotfiles` | Personal config (shell, terminal, desktop). |
| `02_editor` | Editor configuration. |
| `03_system` | Operating system: services, packages, recovery. |
| `04_llm` | What shapes the agents: constitution, skills, prompts, activity log. |
| `05_services` | What runs as a process. |
| `06_data` | Data and persistent memory. |
| `07_tools` | Command-line tools and in-house libraries. |
| `08_backups` | Backups and how to restore them. |
| `09_archive` | What's been retired. Moved here, never deleted. |
| `10_personal` | **Private. Don't read it, don't copy it, don't index it.** |
| `11_work` | Work projects, one per folder. |
| `99_docs` | Plans, concepts, runbooks, decisions. |

## Rules
1. `10_personal/` is off-limits. Secrets live there and never get pasted into
   the chat, into logs, or into git.
2. Ask permission before anything irreversible or public: deleting,
   publishing, paying, writing to third parties.
3. Evidence before assertion: show the output of the command that proves what you're saying.
4. Anything workable is a to-do (`koa-core todo add`), not a line in the chat.
5. Code goes in branches; `main` stays stable.
6. Naming: only `NN_name` at the root, kebab-case at the first level, no
   spaces, accents, or stray backups. The pre-commit hook checks this.
7. A model never pretends to be another one.

## Tools
`koa-core` (CLI), `http://127.0.0.1:8700` (API and UI), `koa-core mcp` (MCP over stdio).
`koa-core doctor` tells you if everything's OK.
