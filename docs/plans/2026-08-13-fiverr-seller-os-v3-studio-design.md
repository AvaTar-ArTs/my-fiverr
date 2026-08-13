# Fiverr Seller OS v3 Studio — Consolidation Design

**Status:** proposed design; no v3 code or state migration is enabled by this document.

## Decision

Build v3 as an evidence-led Studio layer inside the existing v1 `local/` package and its application-owned SQLite database. Do not promote `v2/` to canonical status and do not create a second database, state directory, domain model, or MCP runtime.

The v1 runtime remains the source of truth for profiles, Gigs, changesets, projects, and audit events. v3 adds bounded, additive capabilities for evidence, buyer triage, deterministic drafts, and review exports. Every path from a proposed draft to a canonical profile or Gig must use the existing revision-checked changeset workflow.

```
existing local SQLite + domain APIs
                 |
        additive v3 tables/modules
                 |
   evidence -> triage -> draft -> human review
                 |                    |
                 +---- export --------+
                 |
       local CLI / read-heavy stdio MCP
```

Fiverr access, browser automation, remote listeners, tunnels, credentials, and automatic publication remain out of scope.

## Review of the current plan and implementation

### v1 is the canonical foundation

The existing `local/` package already provides the stronger production boundary:

- owner-private SQLite initialization and additive migrations;
- immutable profile/Gig read models;
- public-content validation and credential-like field rejection;
- revisioned changesets with atomic approval and append-only audit events;
- deterministic buyer-intake analysis without raw request persistence;
- project lifecycle validation; and
- a real 13-tool local stdio MCP server.

v3 must call these APIs rather than copying their behavior. In particular, v3 must never update `profiles`, `gigs`, or `projects` directly from a draft, CLI command, or MCP tool.

### v2 is valuable research, not a second runtime

The v2 design contributes useful concepts: source-pinned evidence, explicit rights, epistemic states, deterministic composition, and manual Markdown/CSV handoffs. Its implementation should remain quarantined until retired or archived because it has a separate package, state directory, schema, and changeset model.

The v2 implementation also diverges from its own plan in material ways:

- the planned `approved` / `needs_review` / `blocked` evidence vocabulary is mixed with `pending` / `approved` / `rejected` and a separate usage vocabulary;
- evidence records do not establish that a source exists or pin a source version;
- triage, Studio composition, exports, CLI, and MCP modules described in the plan are not present in the inspected source tree; and
- the v2 store does not provide the v1 runtime's canonical identity and migration boundary.

These are reasons to port the contracts, not to merge databases. A v3 migration must make the vocabulary explicit and preserve uncertainty rather than silently translating ambiguous v2 rows.

## Domain vocabulary

- **Evidence card:** metadata about a source-backed claim; it never contains the source's raw contents.
- **Source reference:** a caller-supplied relative path or stable external reference; it is a pointer for human review, not permission to read arbitrary files.
- **Epistemic state:** `observed`, `inherited`, `inferred`, `declared`, `draft`, or `blocked`.
- **Usage gate:** `approved`, `needs_review`, or `blocked`.
- **Rights state:** `owned`, `permission_needed`, `private`, or `unknown`.
- **Usable evidence:** approved, owned evidence whose epistemic state is observed or inherited and whose uncertainty is recorded.
- **Triage run:** derived, non-persistent analysis of one supplied buyer brief. Only the decision and derived guidance may be retained; the brief is not retained.
- **Studio draft:** reviewable proposed copy with evidence references and a source revision; it is not canonical marketplace content.
- **Handoff export:** a local Markdown/CSV review artifact for manual use; it is not a Fiverr submission.

“Approved” has two separate meanings: evidence approval authorizes a claim for local drafting; changeset approval authorizes a canonical Seller OS mutation. Neither authorizes a Fiverr action.

## Additive storage design

The v3 migration belongs in the v1 `initialize_store()` path and runs on the same `seller_os.sqlite3`. It must be additive, transactional, idempotent, and refuse malformed legacy rows before changing existing data.

### `evidence_cards`

`id`, `source_ref`, optional `source_digest`, `title`, `observed_summary`, `epistemic_state`, `usage_gate`, `rights_state`, `uncertainty`, `reviewer`, `reviewed_at`, `created_at`.

No raw source content, buyer text, credentials, cookies, or arbitrary JSON blob is stored. A digest is provenance metadata only, not proof of authorship. Reviews are compare-and-swap guarded and audited.

### `studio_drafts`

`id`, `draft_kind`, `target_type`, `target_id`, `source_revision`, `content_json`, `evidence_ids_json`, `status`, `created_at`.

Drafts are immutable snapshots constrained to the existing public-content shape plus draft-only metadata. Canonical updates use `propose_changeset()`; they never update target rows directly.

### `triage_runs`

`id`, `decision`, `reasons_json`, `questions_json`, `assumptions_json`, `risks_json`, `delivery_profile_json`, `evidence_ids_json`, `created_at`.

No request, buyer brief, extracted secret, or reversible encoding of raw input is stored. Correlation, if needed, uses only a caller-supplied non-sensitive label.

### `handoff_exports`

`id`, `kind`, `relative_path`, `content_digest`, `record_ids_json`, `created_at`.

Only metadata is stored in SQLite. Files live beneath an owner-private output root, use constrained relative filenames, and contain source references, uncertainty, decisions, and next actions without raw buyer input or secret-like data.

## Bounded vertical slices

### Slice 1 — Evidence ledger

Implement `local/src/fiverr_seller_os/evidence.py` and an additive schema migration with `add_evidence_card`, `list_evidence_cards`, `review_evidence_card`, and `usable_evidence`.

Acceptance: reject raw-content and credential-shaped fields recursively; reject traversal, absolute paths, and credential-like path components; return deeply immutable snapshots; exclude unknown/private/inferred/blocked/unreviewed cards; make review and audit atomic; and keep imports side-effect-free.

### Slice 2 — Buyer triage

Implement `v3_intake.py` as a thin policy layer over the existing pure analyzer, returning exactly `submit`, `fill`, `clarify`, or `hold`.

- `hold`: credential-like input, prohibited platform action, or unsafe request.
- `clarify`: essential facts are missing.
- `fill`: understandable request but no approved usable evidence supports the fulfillment claim.
- `submit`: complete request and evidence gate passes; this means ready for human review, never platform submission.

Synthetic tests must assert no raw request substring, extracted value, secret, or source content appears. Sensitive input must become a safe hold at the adapter boundary.

### Slice 3 — Deterministic draft composition

Implement `studio.py` from existing profile/Gig snapshots, selected usable evidence IDs, and typed triage. Produce a Gig draft and proposal pack containing evidence labels, uncertainty, assumptions, risks, and manual-review boundaries. No market pricing, ranking, review, demand, client outcomes, or platform expertise may be generated from category pages, old plans, or generic skills.

Tests must verify deterministic output, blocked-card exclusion, source-revision capture, and rejection of any patch that fails the existing public-content validator.

### Slice 4 — Review exports

Implement `exports.py` for Markdown and CSV beneath a caller-selected owner-private output root. Constrain filenames and reject paths escaping that root. Markdown includes kind, decision, sources, evidence status, uncertainty, risks, and next action. CSV contains structured metadata and source refs only. Test bytes for secret-like patterns and raw synthetic buyer markers, permissions, and rollback of export history on failure.

### Slice 5 — CLI and MCP surface

Extend the existing v1 CLI/server only after slices 1–4 pass. Do not create a second server package.

Initial CLI commands:

```
evidence-add  evidence-list  evidence-review
buyer-triage  gig-draft       proposal-pack
handoff-export
```

Initial read-heavy MCP additions:

```
evidence_list
buyer_intake_triage
gig_draft_create
proposal_pack_create
handoff_export
```

Descriptions must state local-only behavior. `changeset_approve`, project transitions, and browser handoff remain local-human-controlled and are not in the v3 MCP allowlist. Arguments must be typed, bounded, and must not accept arbitrary filesystem roots or credential material.

### Slice 6 — Safety and migration gates

Before completion: migrate a real v1 fixture and an incompatible-schema fixture; run all v1 and v3 tests; scan imports/subprocesses for HTTP, browser, tunnel, FTP, and credential access; run raw-input/secret regressions on every output; perform independent spec and quality reviews; and verify clean compilation, `git diff --check`, and a real stdio handshake.

Ambiguous v2 rows are reported for human review and excluded from the v1 database. There is no automatic v2-to-v3 migration in the first release.

## Migration and release sequence

1. Freeze `v2/` as a reference implementation and label it non-canonical.
2. Add schema migration scaffolding and tests to v1; prove existing state is unchanged apart from additive schema metadata.
3. Ship Slice 1, then review evidence vocabulary.
4. Ship Slice 2 with no brief persistence.
5. Ship Slice 3 with source revision and evidence IDs on every draft.
6. Ship Slice 4 with output containment and content scanning.
7. Ship Slice 5 with read-heavy MCP exposure and local-only descriptions.
8. Run Slice 6 gates, update changelog/runbooks, and push one reviewed release commit.

## Explicit non-goals

- importing the v2 database or silently translating ambiguous evidence states;
- reading Creation-Guides archives automatically;
- Fiverr login, scraping, private endpoints, browser automation, or publishing;
- public HTTP, Cloudflare, DNS, launch agents, or background workers;
- generated market claims or copied competitor offers; and
- storing raw buyer briefs, source documents, credentials, cookies, or session data.

## Definition of done

V3 is complete only when one local checkout can initialize or migrate the existing v1 database without duplicating it; add and review a metadata-only synthetic evidence card; triage a synthetic brief without retaining it; compose a deterministic evidence-linked draft; export a source-linked Markdown/CSV handoff without secrets or raw input; run the workflow through bounded CLI and read-heavy stdio MCP tools; and pass regression, migration, security, documentation, and independent review gates.

Until then, v3 is a staged implementation effort, not a claim of Fiverr readiness or marketplace performance.

