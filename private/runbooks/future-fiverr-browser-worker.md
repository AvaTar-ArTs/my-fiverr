# Future Fiverr browser-worker runbook

This is a deferred design boundary for a possible local browser assistant. It
is not implemented in Seller OS v1, and nothing here authorizes browser
automation, Fiverr login, or a remote worker.

## Purpose and boundary

If this phase is approved later, the worker may help place already-approved
Seller OS drafts into visible Fiverr form fields on Steven's Mac. It must be a
local, foreground, manually supervised worker with an explicit allowlist of
pages, fields, and actions. It must never become a general browser agent.

Allowed in the first browser-worker experiment:

- open a known Fiverr seller page only after the user starts the run;
- read the visible field labels needed to map an approved draft;
- fill text fields from a selected, immutable Seller OS draft;
- pause for the user to inspect every field before any navigation away.

Disallowed:

- login, password entry, cookie extraction, profile/profile-directory access,
  MFA/2FA or recovery-code handling, payment changes, or account settings;
- scraping search results, buyer profiles, messages, analytics, or private
  endpoints;
- sending messages, submitting forms, saving edits, publishing a Gig, placing
  an order, accepting work, or changing availability;
- autonomous retries, background operation, remote control, or arbitrary URLs;
- copying buyer secrets or raw private buyer material into prompts, logs, or
  screenshots.

The browser worker is a presentation aid, not the source of truth. Canonical
content is prepared and approved in local Seller OS first. A field-fill run
must identify the draft revision it used, and a mismatch must abort before any
field is filled.

## Required controls before implementation

1. Define an allowlist for exact hostnames, paths, DOM labels, and fillable
   fields. Fail closed on redirects, unknown labels, iframes, unexpected
   dialogs, or a changed page structure.
2. Require a foreground confirmation immediately before starting and a second
   confirmation after the final field is filled. The worker must stop there;
   saving and publishing stay manual.
3. Use a fresh, user-created browser profile only if the user explicitly
   chooses one. Never copy or commit a profile, cookies, local storage,
   password, or authentication header into this repository or Seller OS.
4. Keep the worker local-only. No tunnel, webhook, public HTTP endpoint,
   launch agent, or remote browser-control channel is part of this phase.
5. Log only non-sensitive metadata: draft ID/revision, allowlisted route,
   field names, result, and timestamp. Redact field values, screenshots, page
   source, tokens, cookies, and buyer content.
6. Test first with a blank/sandbox-like account or static fixture. Verify that
   a network disconnect, stale revision, unexpected page, or user cancel
   leaves no partial canonical mutation and no submission.

## Review gate

Implementation requires a new design review, threat model, tests, and explicit
human sign-off. At minimum, reviewers must confirm that the worker cannot
save/publish, cannot bypass Seller OS approval or revision checks, cannot
receive credentials through prompts or environment variables, and cannot be
reached from the network. If Fiverr changes its UI or terms, pause the worker
until the allowlist and tests are revalidated.
