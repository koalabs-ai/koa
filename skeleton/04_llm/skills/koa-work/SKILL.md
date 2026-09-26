---
name: koa-work
description: How an AI agent works inside a KOA — what to read on start, how to claim what you touch, where to log to-dos, memories, and activity, and how to close out. Use this when opening any session in ~/koa.
---

# Working inside a KOA

## On start
1. Read `AGENTS.md` at the root and the `README.md` of the folder you're going to work in.
2. Look for what's already known: `koa-core mem recall "<topic>"`.
3. Check what's pending: `koa-core todo list`.
4. Signal you're here: `koa-core heartbeat`.

## While working
- **Claim what you touch** if another agent might touch it too:
  `koa-core claim acquire <path> --intent "what you're doing"`. If it exits
  with code 9, another agent has it: pick something else, don't retry.
- **Anything workable is a to-do**, not a line in the chat:
  `koa-core todo add "imperative title" --tag bug`.
- **Anything you learn that will be useful later is a memory**:
  `koa-core mem add --type feedback --name <slug> --description "…" --body "…"`.
- **Leave a trace** of anything important: `koa-core log "what happened" --kind deploy`.
- **Naming**: respect the naming guard. If a commit is blocked on a name,
  rename it; don't bypass it.

## On close
1. Close finished work with evidence: `koa-core todo done <id> --evidence "<how to verify it>"`.
2. Release your claims: `koa-core claim release <id>`.
3. Summarize in plain words what got done and what's next.

## Never
- Read, copy, or index `10_personal/`.
- Paste secrets into the chat, into logs, or into git.
- Say "done" without having run the command that proves it.
