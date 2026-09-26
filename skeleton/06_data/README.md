# 06_data — Data, memory, notes

Data store: agents' persistent memory, database, notes, exports, datasets.

## What it is for

Keeping durable information that agents and you need to remember.

## What goes here

- memory/: memory files (one per memory entry).
- *.sqlite, *.sqlite-wal, *.sqlite-shm: databases.
- notes/: long notes, research documents.
- exports/: data exports (CSV, JSON).
- datasets/: data for analysis.

## What does NOT go here

- Anything regenerated (build/, dist/, .cache/): git ignores it.
- Configuration (01_dotfiles, 03_system).
- Secrets (10_personal/secrets).
- Code (07_tools, 05_services).

## Naming

- Memory: `<type>-<slug>.md` (user-preferences.md, feedback-critical-bug.md).
- Database: `name.sqlite`.
- Note: `2026-01-31-topic.md` if temporary, `topic.md` if permanent.
- Export: `2026-01-31-export-name.csv`.

## For AI agents

- Memory is where you save what you learned.
- Read memory/MEMORY.md before searching.
- Exports are raw data; don't edit them by hand (edits are lost on the next sync).
