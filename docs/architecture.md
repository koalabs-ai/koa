# koa-core architecture

## One piece, three doors

```
            CLI (koa-core …)     HTTP (127.0.0.1:8700)     MCP (stdio)
                   \                   |                    /
                    +------- domain: items · plans · memory ·
                    |        claims · activity · agents · naming
                    |
          06_data/koa-core.sqlite      (index and state)
          06_data/memory/*.md          (source of truth for memory)
          99_docs/plans/*.md           (source of truth for plans)
          04_llm/activity.jsonl        (activity log any agent can read)
```

All three doors call the same domain logic. There's no "main door": an
agent without MCP uses the CLI, a remote one uses HTTP, one with MCP
doesn't need the HTTP server to be running.

## Decisions

| Decision | Why |
|---|---|
| Standard library only | Installing = copying files. Nothing compiles or downloads from a package index. |
| Python >= 3.10 | What Ubuntu 22.04 (3.10), Debian 12 (3.11), Ubuntu 24.04 (3.12), and Arch ship with. |
| SQLite with WAL | One person, several agents, zero administration. Postgres is an optional module. |
| Memory and plans as files | Readable with any editor, versioned with git, and outlive koa-core. The database only indexes them. |
| Loopback by default | Nothing gets exposed by accident. Outside loopback, a token is required. |
| Locks with a TTL | An agent that dies doesn't leave something claimed forever. |
| Naming guard with a ratchet | Can be turned on in an old tree without forcing a full migration at once. |

## The built-in agent (opt-in)

```
      koa-core chat (CLI)     Chat tab (web)      POST /v1/chat
                   \                |                    /
                    +---- koa_core.agent: system prompt +
                    |     tool loop (<=12 iterations)
                    |            |
                    |     koa_core.toolbox (same tools as MCP)
                    |
          koa_core.llm.Provider: anthropic (real SDK) |
                                  openai-compatible (urllib: OpenAI, Ollama, …)
          06_data/koa-core.sqlite: conversations, messages (provider-native
                                    history, so a chat can continue)
```

- **No model, no problem.** `koa_core.llm` never imports a provider SDK at
  module scope; only building a configured provider does. With nothing
  configured, `koa-core chat` and `/v1/chat` fail with a localized "not
  configured" message instead of crashing — the rest of KOA is unaffected.
- **One tool table.** `koa_core.toolbox.TOOL_SPECS` is the single source of
  truth for what a tool does and its schema; both the MCP server and the
  agent build their tool list from it, so they can't drift apart. The agent
  gets a fixed subset (no `heartbeat`): no shell, no file writes outside
  those tools, no network beyond the chosen provider.
- **Anthropic**: always the real `anthropic` SDK (`client.beta.messages.create`),
  never raw HTTP, never routed through the OpenAI-compatible path. Errors map
  to localized messages through the SDK's own exception hierarchy
  (`AuthenticationError` → `PermissionDeniedError` → `NotFoundError` →
  `RateLimitError` → `APIStatusError` → `APIConnectionError`).
- **OpenAI-compatible**: stdlib `urllib` only (no SDK) — OpenAI itself,
  Ollama, LM Studio, OpenRouter, anything speaking `/v1/chat/completions`
  with function calling.
- **Keys** live in `10_personal/secrets/<provider>.env` (0600, dir 0700,
  same discipline as the pairing token), never in `koa.toml`, never logged.
  An environment variable (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) always
  overrides the file.
- **Prompt caching**: the system prompt (`AGENTS.md` + `04_llm/constitution.md`
  + the koa-work skill + a live snapshot) is byte-stable for the whole
  conversation except the date line at the very end — the open-items count is
  a snapshot taken once, at conversation creation.
- Every tool call is logged to the activity log (`kind: agent_tool`) with the
  tool name and a short, secret-free argument summary.

## Contracts

The same concepts as a larger KOA (items with evidence when closed, typed
memory `user|feedback|project|reference`, claims with exit code 9,
append-only activity log). So a small KOA can grow without a manual migration.
