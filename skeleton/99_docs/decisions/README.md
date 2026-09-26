# decisions — Decisions made and why

A record of important decisions: date, context, decision, alternatives, consequences.

## What it is for

Letting someone understand why you decided something 6 months ago, and giving them the context if it needs to change.

## What goes here

- An important decision (architecture, policy, tool, service).
- Context: why it was a decision at all.
- Alternatives you evaluated.
- The final decision and why it won.
- Consequences or risks.

## What does NOT go here

- Operations (runbooks).
- Theoretical explanations (concepts).
- Plans (plans).

## Naming

- `2026-01-31-title.md` (date required, ISO).

## What a decision needs

```
---
title: We use Postgres instead of SQLite
date: 2026-01-31
context: We needed complex transactions and concurrency
---

## Alternatives

1. SQLite: simple, local, no server
2. Postgres: robust, distributable, more expensive
3. MongoDB: schemaless, slow for our case

## Decision

Postgres. It won on ACID transactions and scalability.

## Consequences

- More complex deployment.
- Server cost.
- Better for larger teams.
```

## For AI agents

- Decisions are constraints: don't ignore them without a new decision.
- If you propose a change, write a decision_revision.
