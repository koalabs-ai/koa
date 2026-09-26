# 10_personal — PRIVATE: secrets and personal documents

Private folder: never versioned in git, never read by AI agents without explicit permission.

## What it is for

Storing secrets, credentials, sensitive documents, personal information.

## What goes here

- Secrets: `.env` files with credentials, API keys, tokens.
- Personal documents: passport, contract, financial records.
- Medical, legal, or identity information.
- SSH keys, GPG keys, certs.
- Configuration for private services.

Structure:
```
10_personal/
  secrets/
    github.env
    aws.env
    openai.env
  docs/
    contract.pdf
    id-card.pdf
  ssh/
    id_rsa
    id_rsa.pub
  gpg/
```

## What does NOT go here

- Anything public.
- Project code (11_work).
- Tools (07_tools).

## Secrets: the golden rule

- One file per service: `10_personal/secrets/<service>.env`.
- Permissions 600: `chmod 600 10_personal/secrets/*.env`.
- Never in git: .gitignore ignores all of `10_personal/*`.
- Never in chat: a program reads it from the file; you never copy or paste it.

Example `.env`:
```
export SERVICE_API_KEY=sk-...
export OAUTH_SECRET=secret-...
```

Loading it: `source 10_personal/secrets/service.env`.

## For AI agents

- FORBIDDEN: reading, editing, or indexing 10_personal.
- If a program needs a secret, it loads it from the file (`EnvironmentFile=` or `source`); the agent never sees the value.
- If a new secret is needed, the agent says which file to create and the person writes it with `read -rsp` (so it never ends up in the shell history).
- Found a secret (in a log, a backup, etc.): report it without printing it.
- If you see a secrets file without `chmod 600`, flag it.
