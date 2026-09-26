# skills — Collection of automated tasks

One folder per skill: tasks an agent can do on its own or invoke.

## What it is for

Documenting reusable prompts, processes, and tools.

## What goes here

- One folder per skill: `plan-maker/`, `code-review/`, `deploy-check/`.
- Each skill: SKILL.md describes what it does and when to use it.
- Prompt if it's AI-driven: `PROMPT.md`.
- Script if it's code: `.sh`, `.py`.
- Test file if applicable.

## What does NOT go here

- Application code (05_services, 07_tools).
- Project data (06_data).
- Personal configuration (01_dotfiles).

## Naming

- kebab-case folder: `my-skill/`, `my-automation/`.
- File: `SKILL.md` is required.
- Prompt: `PROMPT.md` if it invokes AI.
- Script: a short script name.

## For AI agents

- Read SKILL.md before invoking the skill.
- Skills are public; don't hardcode personal data into them.
- If a skill fails, report it: it might need an update.
