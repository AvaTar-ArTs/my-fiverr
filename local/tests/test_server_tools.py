"""End-to-end stdio checks for the private local MCP boundary."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from conftest import seed_profile_fixture
from fiverr_seller_os.store import initialize_store


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


def test_stdio_server_lists_only_safe_local_tools_and_serves_a_brief(tmp_path: Path) -> None:
    asyncio.run(_exercise_stdio_server(tmp_path))


def test_stdio_server_serializes_immutable_profile_views(tmp_path: Path) -> None:
    database = initialize_store(tmp_path)
    profile = seed_profile_fixture(
        database,
        {
            "display_name": "Local Seller",
            "tagline": "Helpful systems",
            "bio": "Local canonical profile.",
            "skills": ["Python"],
        },
    )
    asyncio.run(_read_profile_over_stdio(tmp_path, profile.id))


async def _exercise_stdio_server(state_dir: Path) -> None:
    environment = dict(os.environ)
    environment["FIVERR_SELLER_OS_STATE_DIR"] = str(state_dir)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fiverr_seller_os.cli"],
        cwd=Path(__file__).parents[1],
        env=environment,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {tool.name for tool in listed.tools} == EXPECTED_TOOLS
            for tool in listed.tools:
                description = tool.description.casefold()
                assert "local" in description
                assert "no fiverr" in description
                assert "publish" not in description
                assert "save" not in description
                assert "browser" not in description
                assert "cookie" not in description
                assert "password" not in description

            result = await session.call_tool("seller_get_brief")
            assert not result.is_error
            assert result.content[0].type == "text"
            payload = json.loads(result.content[0].text)
            assert payload == {
                "changesets": 0,
                "gigs": 0,
                "local_only": True,
                "profiles": 0,
                "projects": 0,
            }
            assert (state_dir / "seller_os.sqlite3").is_file()


async def _read_profile_over_stdio(state_dir: Path, profile_id: int) -> None:
    environment = dict(os.environ)
    environment["FIVERR_SELLER_OS_STATE_DIR"] = str(state_dir)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fiverr_seller_os.cli"],
        cwd=Path(__file__).parents[1],
        env=environment,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("profile_get", {"profile_id": profile_id})
            assert not result.is_error
            payload = json.loads(result.content[0].text)
            assert payload["public_content"]["display_name"] == "Local Seller"
