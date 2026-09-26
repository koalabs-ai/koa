# 04_llm — Constitution, skills, prompts, activity log

What shapes AI agents: values, rules, profiles, activity log. Model-agnostic (Claude, GPT, Gemini, local).

## What it is for

Keeping a single source of truth for what your agents should do and how they should behave.

## What goes here

- constitution.md: values, behavior rules.
- skills/<skill-name>/SKILL.md: one folder per skill.
- prompts/ for reusable prompts.
- Agent profiles, system variables.
- activity.jsonl: the log agents write to.
- openclaw/ or internal model configuration.

## What does NOT go here

- User data (06_data).
- Secrets (10_personal).
- Application code (05_services, 07_tools).

## Naming

- constitution.md is the rules file.
- `skills/` in kebab-case: `skills/plan-maker/`, `skills/code-review/`.
- Each skill: SKILL.md describes what it does.
- Log: `activity.jsonl` (append-only).

## For AI agents

- Read constitution.md first: those are your orders.
- Skills are reusable; if one exists, use it.
- Write to activity.jsonl on every important step.
- Never ignore the constitution's rules.
