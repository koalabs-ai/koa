# 02_editor — Editor configuration

Editor setup (Emacs, Neovim, VS Code, etc.). Optional if it's already in 01_dotfiles.

## What it is for

Storing complex or editor-specific configs that don't fit well in dotfiles.

## What goes here

- init.lua for Neovim (if it's large).
- Extended init.el for Emacs.
- settings.json for VS Code.
- Themes, snippets, extensions.
- Custom keybindings.

## What does NOT go here

- Basic configuration (dotfiles in 01_dotfiles is cleaner).
- Project files (go to 11_work).
- Command-line tools (go to 07_tools).

## Naming

- One folder per editor: `nvim/`, `emacs/`, `vscode/`.
- Inside, keep the editor's own structure: `nvim/init.lua`, `vscode/settings.json`.
- Readme: `nvim/INSTALL.md` explains installation.

## For AI agents

- Editor changes are local; they don't affect the rest of the workspace.
- If a config depends on an external plugin, document it in INSTALL.md.
- Respect the user's language preferences and keybindings.
