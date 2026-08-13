# Repository Dogfood Report — 2026-08-13

## Scope

Exploratory dogfooding of the user-visible local workflows in `/Users/steven/fiverr`:

- local setup and repeatability;
- canonical Seller OS test suite;
- real stdio MCP initialization/list/call;
- ChatGPT bridge policy verification;
- synthetic buyer scenario;
- Hermes Gig preflight;
- Codex Gig JSON validation;
- Python compilation and working-tree hygiene.

No Fiverr login, browser action, network publication, tunnel, credential, or
remote write was attempted.

## Results

| Flow | Result |
|---|---|
| `local/scripts/setup.sh` | PASS; repeatable `uv sync --dev` |
| Canonical local tests | PASS; 130 passed |
| Real MCP harness | PASS; 13 tools and local-only brief |
| ChatGPT bridge verifier | PASS |
| Python compile check | PASS |
| Synthetic buyer scenario | PASS; clarify → fill → submit → hold |
| Hermes Gig preflight | PASS; local draft only, publication blocked |
| Codex Gig JSON | PASS |

## Findings

### DF-001 — Scenario dogfood runs the quarantined v2 implementation

Severity: Medium — test integrity / maintenance

`test/run_scenario.py` imports `fiverr_seller_os_v2` from `/Users/steven/fiverr/v2`
and `test/README.md` instructs users to run its regression under `v2`. The
canonical implementation is now `local/`, so this scenario can pass while
canonical Seller OS behavior changes or regresses independently.

Recommendation: either port the scenario to the canonical local API or label
it explicitly as a legacy v2 compatibility fixture with a separate purpose.

### DF-002 — First-run root UX is under-documented

Severity: Low — usability/documentation

The root `README.md` only describes the repository in one sentence. A new user
must discover `local/README.md` to find setup, test, and MCP commands.

Recommendation: add a concise root quickstart linking to local setup, the
synthetic scenario, Gig drafts, and the security boundary.

### DF-003 — Active Gig and Hermes review packets have different release tools

Severity: Low — workflow consistency

`gigs/hermes/` has an executable preflight, while the canonical Chotaku and
Codex workspaces have only checklists/expectations. This makes the richest
review packet the easiest one to validate even though it contains stale
`not_located` source status and generated artifacts.

Recommendation: move a corrected, source-current preflight into the canonical
Codex workflow, then retain Hermes as archive/reference material.

### DF-004 — Untracked review and generated material remains broad

Severity: Medium — release hygiene

The repository still has untracked transcript exports, HTML archives, ZIP
installers, `v2/`, `test/`, `terminal-outputs/`, and `gigs/hermes/`. Generated
`.DS_Store` and `__pycache__` files are present in review material.

Recommendation: keep these outside commits or add narrowly scoped ignore rules
after confirming which artifacts the user wants retained.

## Conclusion

The canonical local runtime is dogfoodable and passes all tested paths. The
remaining issues are consolidation and first-run UX problems, not failures in
the tested MCP/domain workflows. V3 should not be called complete until the
scenario authority is resolved, exports are implemented, and the release
surface is narrowed to one current Gig review path.
