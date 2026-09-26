# 05_services — Processes: servers, daemons, bots

What runs as a service: web servers, daemons, bots, workers.

## What it is for

Keeping each service's code and documentation organized in one place.

## What goes here

- One folder per service: `my-api/`, `my-bot/`, `my-scheduler/`.
- README.md explains what it does.
- AGENTS.md is its AI configuration (if it has one).
- backend/ with the code.
- frontend/ if it has a web UI.
- docs/ for documentation.

## What does NOT go here

- CLI tools (07_tools).
- System configuration (03_system).
- Shared reusable code (that could be 07_tools).
- Secrets in the repo (go to 10_personal/secrets).

## Naming

- kebab-case folder: `my-webhook/`, `my-notifier/`.
- Inside: README.md, AGENTS.md, backend/, frontend/, docs/.
- Dockerfile at the root if applicable.

## For AI agents

- Read the service's AGENTS.md before editing it.
- A service is failing: check README.md to understand its scope.
- Architecture changes go in docs/, not inline in code.
