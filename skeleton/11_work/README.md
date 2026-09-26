# 11_work — Projects, clients, business

Live projects: clients, business, work. One folder per project, in kebab-case.

## What it is for

Organizing work by client or project; keeping code, docs, and decisions in their own context.

## What goes here

- One folder per project: `client-a/`, `my-startup/`, `short-freelance/`.
- The project's README.md (what it is, stakeholders, status).
- AGENTS.md with the project's rules (if it has agents).
- The project's code, documents, plans.
- Subfolders: frontend/, backend/, docs/, data/ as needed.

## What does NOT go here

- Shared tools (07_tools).
- Personal configuration (01_dotfiles).
- Secrets in the repo (go to 10_personal/secrets/<project>.env).

## Naming

- kebab-case folder: `client-abc/`, `project-x/`, `freelance-2026/`.
- The brand name goes in README.md, not in the folder name.
- Inside: README.md, AGENTS.md (if applicable), code, docs.

Example:
```
11_work/
  my-startup/
    README.md (what it is, status, stakeholders)
    AGENTS.md (rules, if there are agents)
    frontend/, backend/, docs/
```

## For AI agents

- Read the project's README.md first.
- Read AGENTS.md if there is one (client rules may differ).
- Secrets: the user hands you 10_personal/secrets/<project>.env, outside git.
- Big changes: check in before deciding.
