#!/usr/bin/env python3
"""Verify the future ChatGPT bridge contract against the local stdio server.

This is a local smoke test only. It starts the existing Seller OS MCP process,
uses a temporary state directory, and never opens a network listener.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


EXPECTED_READ_ONLY_TOOLS = {
    "seller_get_brief",
    "profile_get",
    "gigs_list",
    "gig_get",
    "changeset_get",
    "changesets_list",
    "projects_list",
    "project_get",
}
EXPECTED_SERVER_TOOLS = EXPECTED_READ_ONLY_TOOLS | {
    "changeset_propose",
    "changeset_approve",
    "buyer_intake_analyze",
    "projects_create",
    "project_transition",
}


async def verify(local_root: Path, state_dir: Path) -> None:
    environment = dict(os.environ)
    environment["FIVERR_SELLER_OS_STATE_DIR"] = str(state_dir)
    source_root = str(local_root / "local" / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        [source_root, environment["PYTHONPATH"]]
        if environment.get("PYTHONPATH")
        else [source_root]
    )
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fiverr_seller_os.cli"],
        cwd=local_root / "local",
        env=environment,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            if names != EXPECTED_SERVER_TOOLS:
                raise RuntimeError(f"unexpected MCP tools: {sorted(names)}")
            read_only = names & EXPECTED_READ_ONLY_TOOLS
            if read_only != EXPECTED_READ_ONLY_TOOLS:
                raise RuntimeError(f"read-only policy tools missing: {sorted(EXPECTED_READ_ONLY_TOOLS - read_only)}")
            result = await session.call_tool("seller_get_brief")
            if result.is_error or not result.content or result.content[0].type != "text":
                raise RuntimeError("seller_get_brief did not return text successfully")
            payload = json.loads(result.content[0].text)
            if payload.get("local_only") is not True:
                raise RuntimeError(f"seller_get_brief was not local-only: {payload!r}")
    if not (state_dir / "seller_os.sqlite3").is_file():
        raise RuntimeError("the isolated Seller OS database was not created")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="fiverr-chatgpt-bridge-") as temporary:
        asyncio.run(verify(repository_root, Path(temporary)))
    print("ChatGPT bridge read-only tool policy verified against local stdio MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
