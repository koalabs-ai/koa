# 07_tools — CLI tools and libraries

Reusable code: command-line tools, libraries, utilities with no running service.

## What it is for

Keeping code that any project can use.

## What goes here

- CLI tools: `koa-core`, `my-script.sh`, `my-tool.py`.
- Shared libraries: `lib_common.py`, `utils.sh`.
- Installers: `setup.sh`, `Makefile`.
- Tests for the tools.
- README.md explains what it does and how to install it.

## What does NOT go here

- Code for a specific project (11_work).
- Running services (05_services).
- Personal configuration (01_dotfiles).
- System scripts (03_system).

## Naming

- One folder per tool: `koa-core/`, `my-generator/`.
- Inside: `README.md`, `setup.sh`, `bin/`, `lib/`.
- Script: kebab-case, no `.sh`: `koa-core`, `my-tool`.

## For AI agents

- README.md describes usage and architecture.
- A tool is broken: check setup.sh and INSTALL.md.
- Changes to shared tools affect everything; check first.
