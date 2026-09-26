# runbooks — How to operate (step by step)

Procedures: how to do something operational. Step by step, no shortcuts, no decisions.

## What it is for

Letting someone (including an agent, or you at 3am) follow steps without having to think.

## What goes here

- Step 1, Step 2, Step 3... (numbered).
- Exact commands to run.
- What to expect at each step.
- How to tell if it failed.
- What to do if it fails (rollback, contact).

## What does NOT go here

- Explaining why (concepts).
- Decisions (decisions).
- Plans (plans).

## Naming

- `runbook-name.md` or `name-runbook.md`.
- Title: "How to [verb] [object]".

Example:
```
# How to deploy to production

## Step 1: Check tests
$ npm test
Expected: 0 errors.

## Step 2: Build
$ npm run build
Expected: dist/ folder with no errors.

...
```

## For AI agents

- Runbooks: follow them to the letter, don't improvise.
- If a step is missing or something fails, report it.
- Don't run it if the runbook says "check first".
