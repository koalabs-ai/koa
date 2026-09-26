# plans — Work plans with tasks

Plans that automatically generate to-dos with `koa-core plans sync`.

## What it is for

Documenting what you're going to do, broken down into checkbox tasks. Checkboxes sync to koa-core todo.

## What goes here

- Plan: one `.md` file per plan.
- YAML frontmatter: title, status, description.
- Body: context paragraphs.
- Tasks: `- [ ] description` (unchecked) or `- [x] description` (done) lines.

## What does NOT go here

- Loose notes with no tasks (99_docs/concepts).
- Decisions (99_docs/decisions).
- Tasks with no context (add a description).

## Naming

- `2026-01-31-topic-plan.md` (ISO + topic + `-plan`).

Example:
```
---
title: Set up my KOA
status: wip
description: Get the instance ready and learn the workflow
---

First example plan.

- [ ] Read AGENTS.md
- [ ] Run koa-core doctor
- [ ] Save a first memory
- [ ] Create a to-do
- [ ] Check naming
```

## For AI agents

- Plans are tasks to execute, not suggestions.
- If a plan is `wip`, it's urgent.
- Status: `wip` (working), `blocked` (stuck), `done` (finished).
- Updating checkboxes: `koa-core plans sync` reads the file.
