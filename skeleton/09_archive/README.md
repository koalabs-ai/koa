# 09_archive — What's been retired

An orderly graveyard: everything no longer in use, in one place.

## What it is for

Avoiding `_old`, `_backup`, `_deprecated` folders scattered across the workspace.

## What goes here

- Finished or paused projects.
- Services you uninstalled but want to keep.
- Old versions of tools.
- Decisions you changed, but documented why.
- Anything dead that could come back.

## What does NOT go here

- Anything you can delete without a second thought.
- Sensitive data (delete it, don't archive it; if it's a secret, 10_personal).

## Naming

- One folder per archived thing: `old-project/`, `discontinued-service/`.
- Include the closing date: `2026-01-31-old-project/`.
- Each archive carries a README explaining why it was closed.

Example:
```
09_archive/
  2026-01-31-test-bot/
    README.md (close date, why, how to revive it)
    <bot code>
```

## For AI agents

- No new work happens here; it's historical reading.
- If you need to revive something, ask permission.
- Respect the closing note: it has the context.
