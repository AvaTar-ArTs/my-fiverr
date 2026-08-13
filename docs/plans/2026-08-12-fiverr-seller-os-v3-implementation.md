# Fiverr Seller OS v3 Studio Implementation Plan

> **For Hermes:** Use subagent-driven-development and test-driven-development task-by-task.

**Goal:** Extend the existing local SQLite/stdio Seller OS into an evidence-led
Gig and brief-response studio without creating a second store or external
Fiverr capability.

**Architecture:** V3 is an additive domain layer inside `local/src/fiverr_seller_os`.
It reuses the v1 connection, audit, revision, and MCP seams. Evidence cards,
draft packets, preflight findings, and handoff exports are metadata-only and
reviewable. The `v3/` directory contains domain context and research only.

**Tech Stack:** Python 3.11+, SQLite, standard-library JSON/CSV/Markdown,
official MCP SDK already used by `local/`, pytest, deterministic rules.

## Shared constraints

- Never access Fiverr, scrape, log in, automate a browser, publish, or send.
- Never store passwords, cookies, tokens, raw buyer briefs, or arbitrary source contents.
- Reuse the existing local SQLite database; add only explicit additive migrations.
- Every affirmative Gig/proposal claim needs an evidence reference or is marked inferred/draft.
- Approval ends at `approved_for_copying`, not publication.
- Rules must retain source URL and retrieval date; live policies may change.

## Task 1: Add the evidence-card contract to the canonical local store

Create `local/src/fiverr_seller_os/evidence.py` and `local/tests/test_evidence.py`.
Add an additive `evidence` table/migration in `store.py` with metadata-only
cards: id, source path, title, observed summary, epistemic state, usage status,
rights status, uncertainty, review status, and timestamps. Return deeply
immutable snapshots. Reject raw-content fields, credentials, traversal paths,
and invalid states. Provide `usable_evidence()` that returns only reviewed,
owned, public, non-blocked evidence.

Use strict RED → GREEN tests for validation, immutability, deterministic
listing, public-use filtering, and atomic review/audit behavior.

## Task 2: Add deterministic Gig readiness drafting and preflight

Create `local/src/fiverr_seller_os/studio.py` and tests. Model title,
description, tags, up to three packages, requirements, FAQ, evidence refs,
assumptions, and unknowns. Enforce the researched 1,200-character description
limit and three-package limit. Add deterministic findings for unsupported
claims, guarantees, contact/payment leakage, prohibited automation language,
and missing evidence. Do not generate market prices or performance claims.

## Task 3: Add brief-response packets without raw-text retention

Extend intake or create `briefs.py` with typed fit, expiry, questions, risks,
and draft response output. Detect credential/platform-automation requests,
support `submit`, `fill`, `clarify`, and `hold`, and never echo or persist raw
brief text. Use synthetic fixtures only.

## Task 4: Add safe Markdown/CSV handoffs

Create `local/src/fiverr_seller_os/exports.py` and tests. Export source-linked
Gig/brief packets with findings, uncertainty, evidence IDs, and next actions.
Reject output paths that traverse unsafe locations, use owner-only directories,
and ensure raw buyer text and secrets cannot appear in Markdown or CSV.

## Task 5: Add read-heavy local MCP/CLI surfaces

Extend the local server only with read/analysis/draft/export tools after the
domain seams are stable: `evidence_list`, `gig_draft_create`,
`buyer_brief_analyze`, and `handoff_export`. Keep canonical writes and any
approval outside the initial ChatGPT policy. Update the tool policy only after
an independent review.

## Task 6: Documentation and release gates

Update `local/README.md`, `CHANGELOG.md`, and v3 runbooks. Add documentation
safety tests. Run the local suite, real stdio integration, bridge verification,
compileall, and `git diff --check`. Review the v3 diff for duplicate stores,
network/browser code, raw-text retention, unsupported claims, and scope creep.

V3 is not complete until each task has an independent spec review and quality
review, and all release commands pass from the `local/` project boundary.
