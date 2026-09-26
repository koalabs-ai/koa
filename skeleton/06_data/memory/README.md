# memory — Agents' persistent memory

One file per memory: what agents and you need to remember across sessions.

## What it is for

Giving agents durable context without rereading the whole repo every time.

## What goes here

- Preferences, habits, past decisions.
- Lessons learned (what went wrong and why).
- Context on projects, clients, rules.
- Feedback on how to work with you.

## What does NOT go here

- Temporary notes (00_inbox).
- Raw data (06_data root).
- Code, configuration.

## Naming

Format: `<type>-<slug>.md` (max 50 characters after the type).

Types: `user-`, `feedback-`, `project-`, `reference-`.

Good examples:
- `user-preferences.md`
- `feedback-critical-bug-found.md`
- `project-online-store.md`
- `reference-credentials.md`

## How to add and search

```bash
koa-core mem add "title" "description"      # New
koa-core mem recall "keyword"                # Search
```

Reading: `MEMORY.md` is the index. The full history moves to an archive file as it grows.

## For AI agents

- This is where you save what you learned today.
- Search: `mem recall` is agnostic; you write the slug.
- Each entry: 1 line <= 200 characters (or move older ones to the archive file).
