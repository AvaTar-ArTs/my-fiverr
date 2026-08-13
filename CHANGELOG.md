# Changelog

## 0.1.0 — 2026-08-12

- Established the private, Mac-local Seller OS foundation and owner-only SQLite state.
- Added immutable profile/Gig snapshots, versioned changesets, explicit approval, audit events, buyer-intake analysis, and project lifecycle validation.
- Added the official MCP Python SDK 2.x stdio adapter with 13 local-only tools.
- Added repeatable local setup and an isolated end-to-end MCP handshake check.
- Documented deferred ChatGPT access and Fiverr browser-worker boundaries.

The 0.1.0 runtime does not call Fiverr, expose HTTP, start tunnels, automate a
browser, or store credentials/cookies/session material.
