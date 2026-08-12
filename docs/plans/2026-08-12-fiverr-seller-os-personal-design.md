# Fiverr Seller OS — Personal Account Design

## Decision

Build a private, Mac-local Seller OS first. It owns the canonical seller record and can be used locally through a Python stdio MCP server. ChatGPT personal-account access is optional and read/fetch-only until current product support is verified in the account.

## Source of truth

This design reconciles `Fiverr_MCP_Creation.tavern.jsonl`. That transcript is a requirements history, not an implementation: its referenced ZIPs, source code, seeded Gigs, and test results are absent from this workspace.

## Goals

- Keep approved seller content, versioned Gig/profile changes, buyer intake, project state, and audit history on Steven's Mac.
- Let an AI client read the current seller brief and prepare reviewable changes.
- Require explicit approval plus optimistic revision checks before canonical content changes.
- Support nontechnical buyers through structured intake and delivery-preflight information.

## Non-goals for v1

- No Fiverr API/private-endpoint integration, scraping, browser automation, form filling, saving, or publishing.
- No session cookies, passwords, MFA codes, API keys, OAuth tokens, or browser profiles in the workspace or Seller OS data.
- No public HTTP endpoint, Cloudflare Tunnel, DNS changes, launch agents, dashboard, or ChatGPT write tools.
- No fabricated live Gigs, buyers, performance data, portfolio facts, prices, or competitor research.

## Architecture

```text
Local AI client / CLI
        |
        v
Python stdio MCP server
        |
        v
Seller OS domain services
        |
        v
SQLite canonical state + append-only audit events
```

The MCP service is local-only. The data directory is outside version control and uses owner-only permissions. Seller OS stores credential plans and project references, never secrets or raw client private material.

## Canonical workflow

```text
canonical profile or Gig
        |
        v
versioned proposed changeset
        |
        v
human review
        |
        v
explicit approval with expected current revision
        |
        v
atomic canonical update + immutable audit event
```

Approval rejects stale revisions. A proposal cannot mark itself approved. No v1 tool deletes or rewrites audit history.

## V1 MCP tools

- `seller_get_brief`
- `profile_get`
- `gigs_list`
- `gig_get`
- `changeset_propose`
- `changeset_get`
- `changesets_list`
- `changeset_approve`
- `buyer_intake_analyze`
- `projects_create`
- `projects_list`
- `project_get`
- `project_transition`

Tool descriptions and input schemas must explicitly state that the service operates on local canonical state only and takes no action on Fiverr.

## Project lifecycle

`lead → intake → scoped → quoted → ordered → building → testing → delivery-ready → delivered → closed`

Only declared adjacent transitions are valid. `buyer_intake_analyze` returns structured guidance without persisting buyer text unless a later explicit project attachment feature is approved.

## Filesystem split

```text
local/
  src/                 Python package and stdio MCP entry point
  tests/               Unit and integration tests
  scripts/             Local setup and test helpers
  state/               Gitignored SQLite state; created at runtime

private/
  SECURITY.md          Threat model and operating rules
  cloudflare/          Future templates only
  launchd/             Future templates only
  runbooks/            Future remote-access and recovery guidance
```

## Future phases

1. Validate local core and stdio MCP client behavior.
2. If ChatGPT developer-mode support is available, add a private read/fetch connection through OpenAI Secure MCP Tunnel.
3. Separately design authenticated remote write access only if plan support and OAuth requirements justify it.
4. Separately design a local, allowlisted Fiverr browser worker that fills approved drafts but never saves or publishes.

## Verification requirements

- Unit tests prove change proposals do not mutate canonical records.
- Unit tests prove stale approvals are rejected and audit events are appended.
- Unit tests prove invalid project lifecycle jumps are rejected.
- Integration test starts the local stdio MCP server, initializes an MCP client, discovers tools, and calls `seller_get_brief`.
- Permission checks prove runtime state is not group/world readable.

## Account constraint

For personal ChatGPT accounts, local Seller OS remains the authority for state-changing operations. The ChatGPT integration is not a prerequisite for v1 and must not be treated as approval to expose a public service or to automate Fiverr.
