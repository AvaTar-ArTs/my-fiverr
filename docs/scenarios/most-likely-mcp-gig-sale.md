# Scenario: First Likely MCP Gig Sale

This is a synthetic, local-only acceptance scenario for the most probable
initial Fiverr workflow: a buyer needs a small private Python MCP server that
turns an existing CSV/API workflow into structured JSON output.

## Buyer message shape

> I want to automate turning CSV product rows into JSON summaries. Currently
> our team manually exports CSV, reviews rows, and sends a report. Inputs are
> CSV files and a documented API. Output should be a JSON report and
> notification. I am a developer and can configure the terminal.

This message intentionally contains no real credentials, customer identity,
Fiverr URL, cookie, token, or private business data.

## Expected Seller OS flow

1. Analyze intake without retaining the raw buyer message. It should be
   quote-ready and classify the buyer as technically comfortable.
2. Create a local project linked to the MCP Gig at `lead`.
3. Advance one adjacent state at a time through:
   `lead → intake → scoped → quoted → ordered → building → testing →
   delivery-ready → delivered → closed`.
4. Add synthetic portfolio evidence as `needs_review`, review it as owned and
   observed, and confirm it becomes usable evidence.
5. Run deterministic Gig preflight. It should be ready for human review and
   contain no contact/payment leakage, guarantee, or unsupported-claim finding.
6. Propose a profile tagline change at the current revision, then explicitly
   approve it. The canonical profile revision must increment exactly once and
   the approval must append an audit event.

## Safety assertions

- No Fiverr request, browser action, tunnel, network call, credential access,
  or automatic publishing occurs.
- The buyer message is not present in the intake result or persisted state.
- Every project transition is adjacent and revision-checked.
- Evidence is not publicly usable until rights and epistemic review pass.
- Profile mutation occurs only through propose → approve.
- All state changes remain local and auditable.

The scenario was executed successfully on 2026-08-13 with 11 resulting audit
events (9 project transitions, 1 evidence review, and 1 profile approval).
