"""Contract tests for the reproducible local setup and MCP check scripts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


LOCAL_ROOT = Path(__file__).parents[1]


def test_setup_script_is_local_and_idempotent() -> None:
    script = LOCAL_ROOT / "scripts" / "setup.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)
    source = script.read_text()
    assert "uv sync" in source
    assert "test_mcp.py" in source
    assert "uv run python scripts/test_mcp.py" in source
    for forbidden in ("cloudflared", "tunnel", "ftp", "playwright", "launchctl"):
        assert forbidden not in source.casefold()


def test_mcp_script_performs_real_stdio_smoke_check() -> None:
    script = LOCAL_ROOT / "scripts" / "test_mcp.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=LOCAL_ROOT,
        env={**os.environ, "PYTHONPATH": str(LOCAL_ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "MCP stdio check passed" in result.stdout
    assert "13 tools" in result.stdout
    assert "seller_get_brief" in result.stdout
