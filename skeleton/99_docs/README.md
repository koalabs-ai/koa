# 99_docs — Documentation: plans, concepts, runbooks, decisions

Reference documentation, plans with tasks, and how to operate things. High number (99_) because it's read often.

## What it is for

One place to look up: what you want to do (plans), what each thing is (concepts), how to operate it (runbooks), and past decisions (decisions).

## What goes here

- plans/: plans with `- [ ]` checkbox tasks, which generate to-dos in koa-core.
- concepts/: explanation of what each thing is.
- runbooks/: how to operate something (step by step).
- decisions/: decisions with date, context, and reasoning.
- templates/: format for plans, notes, decisions.

## What does NOT go here

- Code (05_services, 07_tools, 11_work).
- Configuration (01_dotfiles, 03_system).
- Secrets (10_personal).
- Temporary notes (00_inbox).

## Naming

- Plan: `2026-01-31-topic-plan.md` (ISO + topic).
- Concept: `name.md` (no date, permanent).
- Runbook: `runbook-name.md`.
- Decision: `2026-01-31-title-decision.md` (date required).

## For AI agents

- Plans are the source of truth for tasks: read before executing.
- Runbooks: follow step by step, no shortcuts.
- Concepts: for understanding the domain.
- Decisions: respect them; if you need to change one, propose a new decision.
