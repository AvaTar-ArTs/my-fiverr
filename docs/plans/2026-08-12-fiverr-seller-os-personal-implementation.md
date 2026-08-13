# Fiverr Seller OS Personal Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a private Mac-local Python stdio MCP server that manages versioned Seller OS state without connecting to Fiverr.

**Architecture:** A small domain layer validates profile/Gig changesets and project transitions; a SQLite repository persists canonical records and append-only audit events. A stdio MCP adapter exposes a compact, local-only tool surface. Runtime state is kept out of version control.

**Tech Stack:** Python 3.11+, official `mcp` Python SDK, SQLite from the standard library, `pytest`.

---

## Task 1: Establish the local package and safe runtime boundaries

**Objective:** Create the installable package, test layout, and Git exclusions without generating live seller data.

**Files:**
- Create: `local/pyproject.toml`
- Create: `local/src/fiverr_seller_os/__init__.py`
- Create: `local/tests/test_layout.py`
- Create: `.gitignore`
- Create: `private/SECURITY.md`

**Step 1: Write failing test**

Assert the package version is available and that the runtime state path resolves without creating it. Test runs use the `FIVERR_SELLER_OS_STATE_DIR` override; installed macOS defaults use a user-writable Application Support location.

**Step 2: Run test to verify failure**

Run: `cd local && pytest tests/test_layout.py -v`

Expected: FAIL because package/settings are absent.

**Step 3: Implement minimal package/settings module**

Define a side-effect-free state-path helper. Respect `FIVERR_SELLER_OS_STATE_DIR` when present; on macOS default to a user-writable Application Support location. Do not create state at import time.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_layout.py -v`

Expected: PASS.

## Task 2: Create the SQLite schema and permission-safe initialization

**Objective:** Persist canonical entities and immutable audit events locally.

**Files:**
- Create: `local/src/fiverr_seller_os/store.py`
- Create: `local/tests/test_store.py`

**Step 1: Write failing tests**

Cover state-directory creation with mode `0700`, database creation with mode `0600`, and tables for profiles, gigs, changesets, projects, and audit events.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_store.py -v`

**Step 3: Implement minimum schema**

Use SQLite transactions and JSON text columns for structured public seller content. Do not create columns for credentials, cookies, passwords, or arbitrary file paths.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_store.py -v`

## Task 3: Add canonical profile and Gig read models

**Objective:** Read immutable snapshots of local profile/Gig records with revision numbers.

**Files:**
- Create: `local/src/fiverr_seller_os/models.py`
- Modify: `local/src/fiverr_seller_os/store.py`
- Create: `local/tests/test_records.py`

**Step 1: Write failing tests**

Test profile retrieval, Gig listing, and a missing-Gig error using seed fixtures with clearly fictional values.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_records.py -v`

**Step 3: Implement minimum read operations**

Return typed records with `id`, allowed content fields, and integer `revision`.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_records.py -v`

## Task 4: Implement versioned changeset proposals

**Objective:** Create reviewable proposals that never mutate canonical content.

**Files:**
- Create: `local/src/fiverr_seller_os/changesets.py`
- Modify: `local/src/fiverr_seller_os/store.py`
- Create: `local/tests/test_changesets.py`

**Step 1: Write failing tests**

Test allowed-field validation, stored base revision, status `proposed`, and no change to the target record.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_changesets.py -v`

**Step 3: Implement minimum proposal service**

Accept only profile/Gig targets and an allowlisted patch. Record actor label, timestamp, target ID, normalized patch, and base revision.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_changesets.py -v`

## Task 5: Implement atomic changeset approval and audits

**Objective:** Apply only explicit, fresh approvals and append an audit event.

**Files:**
- Modify: `local/src/fiverr_seller_os/changesets.py`
- Modify: `local/src/fiverr_seller_os/store.py`
- Modify: `local/tests/test_changesets.py`

**Step 1: Write failing tests**

Test approval updates the target exactly once, increments revision, appends an audit event, and rejects stale `expected_revision`.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_changesets.py -v`

**Step 3: Implement transaction-bound approval**

Use a single SQLite transaction to compare revision, update canonical content, mark approved, and insert audit metadata.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_changesets.py -v`

## Task 6: Add buyer-intake analysis without secret retention

**Objective:** Produce structured scope guidance from buyer input without storing raw content by default.

**Files:**
- Create: `local/src/fiverr_seller_os/intake.py`
- Create: `local/tests/test_intake.py`

**Step 1: Write failing tests**

Cover missing requirements, technical-comfort classification, credential-risk warning, and quote-readiness false when essential facts are absent.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_intake.py -v`

**Step 3: Implement deterministic first-pass analysis**

Return questions, risks, scope assumptions, and a delivery-profile recommendation. Reject content containing obvious secret-field submissions rather than echoing it.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_intake.py -v`

## Task 7: Add project lifecycle validation

**Objective:** Track projects with an explicit, safe lifecycle.

**Files:**
- Create: `local/src/fiverr_seller_os/projects.py`
- Modify: `local/src/fiverr_seller_os/store.py`
- Create: `local/tests/test_projects.py`

**Step 1: Write failing tests**

Test valid adjacent transition and rejection of a skipped transition, such as `lead` directly to `building`.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_projects.py -v`

**Step 3: Implement allowlisted transitions**

Use the approved lifecycle from the design document; append an audit event for each accepted transition.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_projects.py -v`

## Task 8: Expose the local-only stdio MCP tools

**Objective:** Adapt domain services to the approved tool list without leaking persistence details.

**Files:**
- Create: `local/src/fiverr_seller_os/server.py`
- Create: `local/src/fiverr_seller_os/cli.py`
- Create: `local/tests/test_server_tools.py`

**Step 1: Write failing tool-discovery test**

Start the server through the official SDK's stdio client harness and assert the approved tool names are present.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_server_tools.py -v`

**Step 3: Implement one tool per action**

Expose only the 13 tools listed in the design. Every mutation tool requires explicit expected revision/approval input and states it changes local Seller OS data only.

**Step 4: Verify green**

Run: `cd local && pytest tests/test_server_tools.py -v`

## Task 9: Add local setup and MCP integration verification

**Objective:** Give the user a repeatable Mac-local installation and end-to-end test.

**Files:**
- Create: `local/scripts/setup.sh`
- Create: `local/scripts/test_mcp.py`
- Create: `local/README.md`

**Step 1: Write the integration test first**

The client must initialize stdio transport, list tools, and call `seller_get_brief` against an isolated test database.

**Step 2: Verify red**

Run the client before its target entry point exists; expect a connection/startup failure.

**Step 3: Implement the smallest scripts/docs**

`setup.sh` creates a local virtual environment and installs declared dependencies. It must not install Playwright, cloudflared, launch agents, or manipulate DNS.

**Step 4: Verify green**

Run: `cd local && ./scripts/setup.sh && .venv/bin/python scripts/test_mcp.py`

Expected: MCP initialization, tool discovery, and `seller_get_brief` success.

## Task 10: Document deferred remote and Fiverr-control work

**Objective:** Prevent a future phase from accidentally broadening local v1's authority.

**Files:**
- Create: `private/runbooks/future-chatgpt-access.md`
- Create: `private/runbooks/future-fiverr-browser-worker.md`
- Modify: `private/SECURITY.md`

**Step 1: Write documentation checks**

Add a lightweight test that asserts none of the v1 tool descriptions contain `publish`, `save on Fiverr`, `browser`, `cookie`, or `password`.

**Step 2: Verify red**

Run: `cd local && pytest tests/test_server_tools.py -v`

**Completion note:** Tasks 1–10 are implemented in `main`. The current release
is local stdio-only; remote ChatGPT access, HTTP transport, tunnels, Fiverr API
calls, and browser control remain deferred behind the runbooks in `private/`.

**Step 3: Write the runbooks**

State that any personal ChatGPT integration is read/fetch-only until verified; remote access, OAuth, browser filling, and tunneling need separately approved designs.

**Step 4: Verify green**

Run: `cd local && pytest -q`

## Final verification

Run:

```bash
cd /Users/steven/fiverr/local
pytest -q
.venv/bin/python scripts/test_mcp.py
```

Confirm the repository contains no credentials, `state/` files, browser profiles, tunnels, or Fiverr automation code before considering the local v1 complete.
