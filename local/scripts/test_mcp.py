#!/usr/bin/env python3
"""Run a real local stdio MCP handshake against an isolated state directory."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


EXPECTED_TOOLS = {
    "seller_get_brief",
    "profile_get",
    "gigs_list",
    "gig_get",
    "changeset_propose",
    "changeset_get",
    "changesets_list",
    "changeset_approve",
    "buyer_intake_analyze",
    "projects_create",
    "projects_list",
    "project_get",
    "project_transition",
}


async def _check(local_root: Path, state_dir: Path) -> None:
    environment = dict(os.environ)
    environment["FIVERR_SELLER_OS_STATE_DIR"] = str(state_dir)
    source_root = str(local_root / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        [source_root, environment["PYTHONPATH"]]
        if environment.get("PYTHONPATH")
        else [source_root]
    )
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fiverr_seller_os.cli"],
        cwd=local_root,
        env=environment,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            if names != EXPECTED_TOOLS:
                raise RuntimeError(f"unexpected MCP tools: {sorted(names)}")
            result = await session.call_tool("seller_get_brief")
            if result.is_error or not result.content or result.content[0].type != "text":
                raise RuntimeError("seller_get_brief did not return text successfully")
            payload = json.loads(result.content[0].text)
            expected = {
                "changesets": 0,
                "gigs": 0,
                "local_only": True,
                "profiles": 0,
                "projects": 0,
            }
            if payload != expected:
                raise RuntimeError(f"unexpected seller brief: {payload!r}")
    database = state_dir / "seller_os.sqlite3"
    if not database.is_file():
        raise RuntimeError("the isolated Seller OS database was not created")


def main() -> int:
    local_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="fiverr-seller-os-mcp-") as temporary:
        asyncio.run(_check(local_root, Path(temporary)))
    print("MCP stdio check passed: 13 tools; seller_get_brief returned local-only state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
