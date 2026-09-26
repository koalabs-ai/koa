# Optional modules

Rule: a module **never** becomes a requirement of the core. If it's missing,
koa-core still works. Status: design (none implemented yet).

| Module | What it adds | How it connects |
|---|---|---|
| AI provider | KOA itself calling a model (summaries, classifying to-dos) | `[llm]` in `koa.toml`: an OpenAI-compatible endpoint (your own API, local Ollama, a proxy); the key is read from `10_personal/secrets/<provider>.env` |
| Postgres | multiple people, more volume | `[db] url` in `koa.toml`; same tables |
| Telegram chat | talking to your KOA from your phone | your own bot; token in `10_personal/secrets/telegram.env`; webhook or local polling |
| Automation (n8n or other) | flows triggered by events | outgoing webhooks from the activity log |
| Remote access (Caddy + VPN) | using your KOA away from home | reverse proxy with TLS + koa-core token; the VPN is your own |
| Backup | automatic copies | `restic` or `git push` to your own remote |

Each module lives in its own folder, with its own README, its own test, and
its own way to be turned off without leaving a trace.
