# 01_dotfiles — Shell and terminal configuration

Dotfiles: shell, terminal, desktop. Symlinked to ~. Never any secrets here.

## What it is for

Carrying your dev environment from machine to machine without losing your personal setup.

## What goes here

- .bashrc, .zshrc, .profile for the shell.
- .gitconfig, .gitignore_global for Git.
- .config/nvim/, .emacs.d/ for the editor.
- .config/alacritty/, .config/wezterm/ for the terminal.
- General-purpose aliases and functions.
- .config/koa/ for the command-line client.

## What does NOT go here

- Secrets (.env, tokens, private keys): go to 10_personal/secrets.
- Project-specific stuff (a project's README belongs in 11_work).
- System configuration (packages, units: go to 03_system).

## Naming

- Same name as in ~: `.bashrc`, `.gitconfig`, `.config/nvim/init.lua`.
- `.config/<app>/` subfolder for a modern app.
- Description file: `INSTALL.md` explains how to link them.

## For AI agents

- Read INSTALL.md before making changes.
- gitconfig changes that involve secrets go to 10_personal, not here.
- Respect the user's aliases and functions; ask before adding new ones.
