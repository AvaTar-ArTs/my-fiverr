# Changelog

## 2026-08-13 — Initial bounded Hermes + Fiverr profile audit

### Added

- Historical HTML profile-optimization audit with SHA-256 and evidence limits.
- Safe Hermes capability/lineage audit beyond the `.agent-skills` comparison baseline.
- Machine-readable capability ledger and exclusions register.
- Source manifest and deterministic verification script.

### Boundaries

- No secrets, auth, runtime databases, sessions, logs, caches, or private memory were read or copied.
- No Hermes configuration, plugin, hook, skill, agent, or profile was modified.
- No Fiverr login, scraping, editing, publishing, uploading, contacting, or authenticated browser action occurred.
- Historical export claims remain inherited/unverified unless independently reproduced.
