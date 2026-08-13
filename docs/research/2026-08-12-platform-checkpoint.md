# Platform research checkpoint — 2026-08-12

## Decision

Keep Seller OS v1 local-only: Python stdio MCP, local SQLite state, explicit
human approval for canonical writes, and append-only audit history.

## ChatGPT / MCP access

Personal Pro/Plus capability and connector availability must be verified in the
actual account at implementation time. The project therefore does not assume
that a personal account can publish or approve changes.

If private access is revisited, evaluate OpenAI Secure MCP Tunnel first and
start with read-only tools against synthetic state. A public HTTPS MCP endpoint
is a separate security project requiring OAuth 2.1, scope/audience validation,
rate limiting, auditability, and revocation; a shared bearer token or quick
Cloudflare URL is not an equivalent control.

Sources:

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [ChatGPT developer mode and full MCP connectors](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt-beta)
- [OpenAI MCP authentication](https://developers.openai.com/plugins/build/auth)

## Fiverr access

No private or assumed Fiverr seller CRUD API is part of v1. Any future browser
worker must remain local, foreground, allowlisted, fill-only, revision-bound,
and manually supervised; it must stop before save or publish.
