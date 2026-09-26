# 03_system — Operating system and machine

OS configuration: systemd units, package lists, recovery scripts. What's installed on which machine.

## What it is for

Documenting what each machine needs to work; disaster recovery.

## What goes here

- systemd --user units (.service, .timer).
- Package lists (apt packages, rpm, etc.).
- Initial install scripts.
- Cron jobs that don't have a user home.
- udev rules if you need them.
- Network configuration (netplan, etc.).

## What does NOT go here

- Personal user configuration (01_dotfiles).
- Your own tools (07_tools).
- Data (06_data).
- Work projects (11_work).

## Naming

- By machine or type: `fedora-server/`, `debian-laptop/`.
- Inside: `packages.txt`, `units/`, `install.sh`.
- Date on recipes: `2026-01-31-recovery-after-failure.md`.

## For AI agents

- Read the install script before touching packages.
- A new unit needs a check first: it can lock up the system.
- Changes here sometimes require a reboot; warn the user.
