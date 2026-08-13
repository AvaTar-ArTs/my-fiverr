# Changelog

## 0.1.0 — 2026-08-12

- Added a thin `chatgpt/` policy and verification layer over the existing
  local stdio server; it has no database, network listener, tunnel, or
  credentials and begins with a read-only tool allowlist.
- Added the first V3 Studio slices: metadata-only evidence cards with
  review/audit gates and a deterministic Gig preflight for bounded drafts.
- Established the private, Mac-local Seller OS foundation and owner-only SQLite state.
- Added immutable profile/Gig snapshots, versioned changesets, explicit approval, audit events, buyer-intake analysis, and project lifecycle validation.
- Added the official MCP Python SDK 2.x stdio adapter with 13 local-only tools.
- Added repeatable local setup and an isolated end-to-end MCP handshake check.
- Documented deferred ChatGPT access and Fiverr browser-worker boundaries.

The 0.1.0 runtime does not call Fiverr, expose HTTP, start tunnels, automate a
browser, or store credentials/cookies/session material.
