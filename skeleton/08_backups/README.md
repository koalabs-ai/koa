# 08_backups — Backups

Backups and how to restore them. Heavy content doesn't go into git.

## What it is for

Keeping a copy for when something breaks; documenting how to restore it.

## What goes here

- Database snapshots (tarball, SQL dump).
- Backup of critical configuration.
- Restore documentation (runbook).
- Compressed archives of important data.

## What does NOT go here

- Anything easy to regenerate.
- Files without their restore runbook.

## Naming

- One folder per service: `database/`, `critical-config/`.
- Compressed file: `2026-01-31-snapshot-name.tar.gz`.
- Runbook: `RESTORE-name.md` next to the backup.

Good example:
```
08_backups/database/
  2026-01-31-koa-core.sqlite.tar.gz
  RESTORE-koa-core.md
```

## For AI agents

- Backups are critical; respect them.
- Restoring must be explicit: never automate it without permission.
- If you change how something gets backed up, update the RESTORE file.
