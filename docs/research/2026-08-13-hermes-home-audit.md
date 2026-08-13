# Hermes Home Audit — 2026-08-13

## Scope

This was a read-only audit of `/Users/steven/.hermes/` for skills, agent
guidance, MCP implementation patterns, security material, and delegation
metadata not already represented in `/Users/steven/.agent-skills/`.

The audit intentionally did **not** read or copy secret-bearing or private
runtime data: `auth/`, `config.yaml`, `.env*`, `sessions/`, `pastes/`,
`memories/`, `logs/`, `kanban.db`, or delegation-log contents. Their presence,
file counts, modes, and (for individual files) short hashes were used only to
confirm that they are private runtime state and not project inputs.

## Inventory

- Hermes repository: `/Users/steven/.hermes/hermes-agent/`
- Hermes bundled skills: 71 `SKILL.md` files; 15 relative paths are not present
  under `/Users/steven/.agent-skills/`.
- Delegation cache: 53 live `.log` files across 99 files in the delegation
  cache. These are process history, not source-of-truth requirements.
- Important non-secret guidance: `AGENTS.md`, `SECURITY.md`,
  `docs/security/network-egress-isolation.md`, the Hermes MCP transport, and
  the MCP/security optional skills.

The Hermes-only skills are mostly product-specific or unrelated to Seller OS
(document conversion, research-paper workflows, desktop inspection, vLLM,
etc.). The relevant additions are the FastMCP, remote MCP OAuth, security
guidance, network egress isolation, and Hermes agent-development material.

## Findings that affect Seller OS

### 1. Keep the core narrow and put capability at the edge

Hermes' contribution guide explicitly favors extending existing code, then a
CLI/skill, plugin, or MCP server before adding core model tools. This confirms
the V3 decision to keep one SQLite/domain/MCP core and add future exports,
ChatGPT connectivity, and browser handoff as thin adapters rather than a
second database or a larger server surface.

### 2. Stdio wire hygiene is a hard requirement

Hermes' own MCP transport documents that protocol traffic belongs on stdout
and diagnostics on stderr, with an explicit allowlist of exposed tools. The
Seller OS stdio server already passes a real initialization/list/call harness;
the next release gate should keep stdout clean and expose only the documented
read/propose/approval surface.

### 3. In-process checks are not the security boundary

Hermes' security policy treats approval gates, redaction, scanners, and tool
allowlists as heuristics—not containment. The actual boundary for hostile
model-emitted commands is OS-level isolation. Therefore Seller OS approval
checks remain useful product policy, but must not be described as sandboxing.
Any future tunnel/HTTP/browser worker must run with an explicitly documented
local-user boundary and least-privilege filesystem/network access.

### 4. Remote deployment needs network segmentation and real OAuth

The egress-isolation guide recommends an internal network plus an allowlisted
egress proxy for remote agent deployments. The remote-MCP skill separately
requires OAuth 2.1/PKCE/resource binding for a public gateway and warns that a
remote gateway's localhost OAuth callback is not the user's browser. This
supports the existing decision: local stdio first; Secure MCP Tunnel or a
properly authenticated public endpoint only after the local contract is
stable. Do not revive the old bearer-token/Cloudflare/JSON overlay.

### 5. Secrets and configuration must stay separate

Hermes guidance says `.env` is for secrets only and behavioral settings belong
in config. Its file-safety and export-redaction code fail closed when a
redactor is unavailable. Seller OS should preserve its current no-credentials
policy, never import Hermes auth/config, and apply redaction before any future
export, audit report, or buyer-intake diagnostic leaves the local process.

### 6. E2E behavior contracts are more valuable than snapshot tests

Hermes' agent guidance emphasizes real end-to-end validation for resolution,
security, remote backends, and I/O, plus invariant-based tests. The current
130-test local suite and real stdio harness follow that model. V3 should keep
adding contract tests around migrations, approval races, exports, and any
adapter boundary rather than freezing incidental tool counts or model output.

## What was not missing

The Hermes agent roster, desktop agent index, delegation cache, and bundled
skills do not reveal a missing Seller OS domain feature. They provide execution
and review patterns, not Fiverr-specific account/gig/project data. The current
V3 gaps remain the planned ones: brief packets, safe exports, read-heavy V3
MCP/CLI ergonomics, and final release review.

## Decisions

1. Do not import Hermes runtime files, auth, config, sessions, memories,
   delegation logs, or installed virtual-environment packages into this repo.
2. Do not add a Hermes dependency merely because Hermes can host MCP servers.
   The official SDK-backed local stdio server is already the smaller boundary.
3. Add future remote work only as a thin adapter with explicit OAuth/tunnel,
   tool allowlisting, stderr-only diagnostics, redacted exports, and an OS-level
   threat model.
4. Treat delegation logs as historical review evidence only; they are not
   canonical requirements and may contain private conversation material.

## Audit conclusion

Hermes confirms the current direction rather than changing it: one local
SQLite Seller OS, deterministic domain logic, explicit review/approval, and a
real stdio MCP contract. No overlooked Hermes agent or skill justifies a second
runtime, public tunnel, browser automation, or Fiverr credential integration.
