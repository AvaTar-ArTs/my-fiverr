from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import seed_gig_fixture, seed_profile_fixture


def _profile_content() -> dict[str, object]:
    return {
        "display_name": "Example Automation Studio",
        "tagline": "Fictional local test profile",
        "bio": "A fictional fixture used only by tests.",
        "skills": ["python", "mcp"],
    }


def _gig_content() -> dict[str, object]:
    return {
        "title": "Build a fictional MCP server fixture",
        "description": "A fictional test-only service description.",
        "category": "Programming & Tech",
        "tags": ["mcp", "python"],
        "packages": {"basic": {"name": "Basic", "description": "Fixture", "price_usd": 100, "delivery_days": 3, "revisions": 1, "features": ["one safe tool"]}},
    }


def test_create_read_and_list_project_return_immutable_revisioned_snapshots(tmp_path: Path) -> None:
    from fiverr_seller_os.projects import create_project, get_project, list_projects
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    created = create_project(database_path, title="MCP integration discovery", summary="Clarify the buyer's workflow.")

    assert created.id == 1
    assert created.gig_id is None
    assert created.status == "lead"
    assert created.revision == 1
    assert get_project(database_path, created.id) == created
    assert list_projects(database_path) == (created,)
    with pytest.raises(AttributeError):
        setattr(created, "status", "building")


def test_create_project_accepts_only_existing_optional_gig(tmp_path: Path) -> None:
    from fiverr_seller_os.projects import InvalidProjectError, create_project
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    gig = seed_gig_fixture(database_path, profile.id, _gig_content())
    assert create_project(database_path, title="Linked", summary="Safe summary", gig_id=gig.id).gig_id == gig.id
    with pytest.raises(InvalidProjectError, match="gig_id"):
        create_project(database_path, title="Unlinked", summary="Safe summary", gig_id=999)


def test_transition_advances_only_one_lifecycle_state_and_appends_audit(tmp_path: Path) -> None:
    from fiverr_seller_os.projects import create_project, transition_project
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    project = create_project(database_path, title="MCP discovery", summary="Safe scope discussion")
    moved = transition_project(database_path, project.id, project.revision, "intake", "seller")

    assert moved.status == "intake"
    assert moved.revision == 2
    with open_connection(database_path) as connection:
        events = connection.execute("SELECT event_type, entity_type, entity_id, event_data_json FROM audit_events").fetchall()
    assert events == [("project_transitioned", "project", project.id, json.dumps({"actor": "seller", "from_status": "lead", "new_revision": 2, "previous_revision": 1, "to_status": "intake"}, sort_keys=True, separators=(",", ":")))]


def test_transition_rejects_skipped_state_without_mutating_or_auditing(tmp_path: Path) -> None:
    from fiverr_seller_os.projects import InvalidProjectError, create_project, get_project, transition_project
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    project = create_project(database_path, title="MCP discovery", summary="Safe scope discussion")
    with pytest.raises(InvalidProjectError, match="adjacent"):
        transition_project(database_path, project.id, 1, "building", "seller")
    assert get_project(database_path, project.id) == project
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []


@pytest.mark.parametrize(
    ("expected_revision", "next_status", "actor", "message"),
    [(2, "intake", "seller", "expected_revision"), (1, "lead", "seller", "adjacent"), (1, "intake", " ", "actor"), (True, "intake", "seller", "expected_revision")],
)
def test_transition_rejects_stale_repeat_and_invalid_requests_with_rollback(tmp_path: Path, expected_revision: object, next_status: object, actor: object, message: str) -> None:
    from fiverr_seller_os.projects import InvalidProjectError, create_project, get_project, transition_project
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    project = create_project(database_path, title="MCP discovery", summary="Safe scope discussion")
    with pytest.raises(InvalidProjectError, match=message):
        transition_project(database_path, project.id, expected_revision, next_status, actor)  # type: ignore[arg-type]
    assert get_project(database_path, project.id) == project
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []


@pytest.mark.parametrize("title,summary", [("", "Safe"), ("Safe", ""), ("Safe", "api_key=do-not-store")])
def test_create_rejects_empty_or_credential_assignment_text(tmp_path: Path, title: str, summary: str) -> None:
    from fiverr_seller_os.projects import InvalidProjectError, create_project
    from fiverr_seller_os.store import initialize_store

    with pytest.raises(InvalidProjectError):
        create_project(initialize_store(tmp_path / "state"), title=title, summary=summary)
