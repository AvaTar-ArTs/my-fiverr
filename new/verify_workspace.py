from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    html_path = Path(manifest["html_source"]["path"])
    digest = hashlib.sha256(html_path.read_bytes()).hexdigest()
    assert digest == manifest["html_source"]["sha256"]
    assert manifest["security"]["secrets_read"] is False
    assert manifest["security"]["fiverr_actions"] is False
    with (ROOT / "capability-ledger.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and {"source_id", "source_path", "evidence_state", "decision"} <= set(rows[0])
    with (ROOT / "exclusions.csv").open(newline="") as handle:
        excluded = list(csv.DictReader(handle))
    assert excluded and all(row["action"] for row in excluded)
    for name in ("README.md", "html-profile-audit.md", "hermes-capability-audit.md", "CHANGELOG.md"):
        assert (ROOT / name).is_file(), name
    print(f"workspace verification: PASS; ledger_rows={len(rows)}; exclusions={len(excluded)}")


if __name__ == "__main__":
    main()
