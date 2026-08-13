# Seller OS v3 domain context

## Canonical terms

- **Evidence card**: a source-linked, metadata-only statement that may support
  a draft after explicit review. It is not the source content itself.
- **Gig draft**: proposed Fiverr-facing copy and package structure, never live
  marketplace content.
- **Brief response packet**: a local analysis of an imported buyer brief with
  fit, questions, risks, and a draft response. Raw brief text is not retained
  by default.
- **Preflight**: deterministic checks for field limits, unsupported claims,
  prohibited language, evidence coverage, and missing requirements.
- **Approved for copying**: the final local review state. It does not mean
  saved, submitted, or published on Fiverr.

## Authority boundaries

The existing `local/` SQLite store is the only canonical state owner. V3
modules must use its connection and migration seams; they must not create a
parallel database or remote transport. Human approval is required before any
canonical mutation, and Fiverr editor actions remain outside v3.
