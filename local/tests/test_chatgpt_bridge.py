from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_ROOT = REPO_ROOT / "chatgpt"

READ_ONLY_TOOLS = {
    "seller_get_brief",
    "profile_get",
    "gigs_list",
    "gig_get",
    "changeset_get",
    "changesets_list",
    "projects_list",
    "project_get",
}


def test_bridge_documents_local_only_read_policy() -> None:
    policy = (BRIDGE_ROOT / "tool-policy.md").read_text()
    for tool in READ_ONLY_TOOLS:
        assert tool in policy
    assert "changeset_approve" in policy
    assert "local approval" in policy.lower()
    assert "no second database" in policy.lower()


def test_connection_verifier_uses_existing_stdio_server() -> None:
    verifier = BRIDGE_ROOT / "verify_chatgpt_connection.py"
    source = verifier.read_text()
    assert "fiverr_seller_os.cli" in source
    assert "StdioServerParameters" in source
    assert "FIVERR_SELLER_OS_STATE_DIR" in source
    assert "http://" not in source
    assert "cloudflared" not in source
    assert "EXPECTED_READ_ONLY_TOOLS" in source


def test_connection_verifier_passes_with_isolated_state() -> None:
    verifier = BRIDGE_ROOT / "verify_chatgpt_connection.py"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPO_ROOT / "local" / "src")
    completed = subprocess.run(
        [sys.executable, str(verifier)],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "read-only tool policy verified" in completed.stdout.lower()


def test_bridge_docs_forbid_remote_and_external_mutation() -> None:
    readme = (BRIDGE_ROOT / "README.md").read_text()
    tunnel = (BRIDGE_ROOT / "secure-tunnel" / "README.md").read_text()
    combined = (readme + tunnel).lower()
    assert "cd /users/steven/fiverr/local" in combined
    assert "uv run python ../chatgpt/verify_chatgpt_connection.py" in combined
    assert "no cloudflare" in combined
    assert "no credentials" in combined
    assert "proposal" in combined and "approval" in combined
