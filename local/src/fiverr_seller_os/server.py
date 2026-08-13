"""Private stdio MCP facade for local Seller OS state.

The module is intentionally inert at import time.  Each tool resolves and
initializes the application-owned SQLite database only when that tool runs.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from mcp.server import MCPServer

from . import state_path
from .changesets import approve_changeset, get_changeset, list_changesets, propose_changeset
from .intake import analyze_buyer_intake
from .models import get_gig, get_profile, list_gigs
from .projects import create_project, get_project, list_projects, transition_project
from .store import initialize_store, open_connection


LOCAL_NOTICE = "This affects only local Seller OS state; no Fiverr action is performed."
TOOL_SAFETY_SUFFIX = " Local Seller OS state only; no Fiverr or external action is performed."


def create_server() -> MCPServer:
    """Build the MCP server without touching the filesystem."""
    server = MCPServer(
        name="Fiverr Seller OS",
        description="Private local seller records with reviewable changes.",
    )

    @server.tool(description=_tool_description("Summarize current local seller records."))
    def seller_get_brief() -> str:
        database = _database_path()
        with open_connection(database) as connection:
            counts = {
                "profiles": _count(connection, "profiles"),
                "gigs": _count(connection, "gigs"),
                "changesets": _count(connection, "changesets"),
                "projects": _count(connection, "projects"),
                "local_only": True,
            }
        return _json(counts)

    @server.tool(description=_tool_description("Read one local profile snapshot by identifier."))
    def profile_get(profile_id: int) -> str:
        return _json(get_profile(_database_path(), profile_id))

    @server.tool(description=_tool_description("List local Gig snapshots in stable order."))
    def gigs_list() -> str:
        return _json(list_gigs(_database_path()))

    @server.tool(description=_tool_description("Read one local Gig snapshot by identifier."))
    def gig_get(gig_id: int) -> str:
        return _json(get_gig(_database_path(), gig_id))

    @server.tool(description=_tool_description("Propose a version-checked local profile or Gig change for later review."))
    def changeset_propose(
        target_type: str,
        target_id: int,
        patch: dict[str, object],
        base_revision: int,
        actor: str,
    ) -> str:
        proposal = propose_changeset(
            _database_path(),
            target_type=target_type,
            target_id=target_id,
            patch=patch,
            base_revision=base_revision,
            actor=actor,
        )
        return _mutation_json(proposal)

    @server.tool(description=_tool_description("Read one local proposed change by identifier."))
    def changeset_get(changeset_id: int) -> str:
        return _json(get_changeset(_database_path(), changeset_id))

    @server.tool(description=_tool_description("List local proposed changes, optionally for one target."))
    def changesets_list(target_type: str | None = None, target_id: int | None = None) -> str:
        return _json(list_changesets(_database_path(), target_type=target_type, target_id=target_id))

    @server.tool(description=_tool_description("Approve one version-checked local proposed change after explicit confirmation."))
    def changeset_approve(
        changeset_id: int,
        expected_revision: int,
        actor: str,
        approval_confirmed: bool,
    ) -> str:
        _require_approval(approval_confirmed)
        proposal = approve_changeset(
            _database_path(), changeset_id, expected_revision=expected_revision, actor=actor
        )
        return _mutation_json(proposal)

    @server.tool(description=_tool_description("Analyze buyer scope without retaining the submitted request."))
    def buyer_intake_analyze(request: str) -> str:
        return _json(analyze_buyer_intake(request))

    @server.tool(description=_tool_description("Create a local project lead after explicit confirmation."))
    def projects_create(
        title: str,
        summary: str,
        approval_confirmed: bool,
        gig_id: int | None = None,
    ) -> str:
        _require_approval(approval_confirmed)
        project = create_project(_database_path(), title=title, summary=summary, gig_id=gig_id)
        return _mutation_json(project)

    @server.tool(description=_tool_description("List local project snapshots in stable order."))
    def projects_list() -> str:
        return _json(list_projects(_database_path()))

    @server.tool(description=_tool_description("Read one local project snapshot by identifier."))
    def project_get(project_id: int) -> str:
        return _json(get_project(_database_path(), project_id))

    @server.tool(description=_tool_description("Advance one local project by one version-checked lifecycle step."))
    def project_transition(
        project_id: int,
        expected_revision: int,
        next_status: str,
        actor: str,
        approval_confirmed: bool,
    ) -> str:
        _require_approval(approval_confirmed)
        project = transition_project(
            _database_path(), project_id, expected_revision, next_status, actor
        )
        return _mutation_json(project)

    return server


def _tool_description(description: str) -> str:
    return description + TOOL_SAFETY_SUFFIX


def _database_path() -> Path:
    """Initialize the app-owned database at the point a tool is invoked."""
    return initialize_store(state_path())


def _count(connection: object, table: str) -> int:
    # The table names are fixed literals above, never caller input.
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # type: ignore[union-attr]


def _require_approval(approval_confirmed: bool) -> None:
    if approval_confirmed is not True:
        raise ValueError("approval_confirmed must be true for a local state mutation")


def _mutation_json(value: object) -> str:
    return _json({"local_only": True, "notice": LOCAL_NOTICE, "result": value})


def _json(value: object) -> str:
    return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"))


def _json_ready(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        # ``asdict`` deep-copies values and cannot copy MappingProxyType, which
        # the canonical read models use to enforce immutability.
        return {
            field.name: _json_ready(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    if isinstance(value, MappingProxyType):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value
