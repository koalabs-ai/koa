# Security

KOA runs on your own machine and keeps your data there. It listens only on
`127.0.0.1` unless you configure a token, stores secrets under
`10_personal/secrets/` with `0600` permissions, keeps device and pairing tokens
only as SHA-256 hashes, and never sends anything to a third party unless you
connect a model provider yourself.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private vulnerability
reporting on this repository ("Security" → "Report a vulnerability"). Include
the version (`koa-core version`), what you did, and what happened. We aim to
answer within 7 days.

## Scope

In scope: `koa-core` (CLI, HTTP API, web app, MCP server), the installer and
the pairing flow. Out of scope: the security of model providers you choose to
connect, and machines where the owner exposes KOA without a token.
