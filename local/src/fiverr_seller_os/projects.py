"""Local-only, revisioned Seller OS project lifecycle records."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

from .store import open_connection


class InvalidProjectError(ValueError):
    """Raised for invalid local project lifecycle requests."""


class ProjectNotFoundError(LookupError):
    """Raised when a local project does not exist."""


PROJECT_STATUSES = (
    "lead", "intake", "scoped", "quoted", "ordered", "building", "testing",
    "delivery-ready", "delivered", "closed",
)
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[ _-]?key|apikey|client[ _-]?secret|clientsecret|access[ _-]?token|accesstoken|password|token|secret|cookie|credentials?)\s*[:=]\s*\S+"
)
_BEARER_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S+")


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    id: int
    gig_id: int | None
    title: str
    summary: str
    status: str
    revision: int


def create_project(database_path: Path, *, title: str, summary: str, gig_id: int | None = None) -> ProjectSnapshot:
    """Create a local lead after narrow non-secret content validation."""
    clean_title = _validate_content(title, "title")
    clean_summary = _validate_content(summary, "summary")
    if gig_id is not None:
        _validate_id(gig_id, "gig_id")
    with open_connection(database_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            if gig_id is not None and connection.execute("SELECT 1 FROM gigs WHERE id = ?", (gig_id,)).fetchone() is None:
                raise InvalidProjectError("gig_id was not found")
            cursor = connection.execute(
                "INSERT INTO projects (gig_id, title, summary) VALUES (?, ?, ?)",
                (gig_id, clean_title, clean_summary),
            )
            row = connection.execute(_PROJECT_SELECT + " WHERE id = ?", (cursor.lastrowid,)).fetchone()
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    assert row is not None
    return _snapshot(row)


def get_project(database_path: Path, project_id: int) -> ProjectSnapshot:
    _validate_id(project_id, "project_id")
    with open_connection(database_path) as connection:
        row = connection.execute(_PROJECT_SELECT + " WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ProjectNotFoundError(f"Project {project_id} was not found")
    return _snapshot(row)


def list_projects(database_path: Path) -> tuple[ProjectSnapshot, ...]:
    with open_connection(database_path) as connection:
        rows = connection.execute(_PROJECT_SELECT + " ORDER BY id").fetchall()
    return tuple(_snapshot(row) for row in rows)


def transition_project(database_path: Path, project_id: int, expected_revision: int, next_status: str, actor: str) -> ProjectSnapshot:
    """Atomically make precisely one forward lifecycle transition and audit it."""
    _validate_id(project_id, "project_id")
    _validate_id(expected_revision, "expected_revision")
    _validate_actor(actor)
    if not isinstance(next_status, str) or next_status not in PROJECT_STATUSES:
        raise InvalidProjectError("next_status is not a valid project lifecycle status")
    with open_connection(database_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(_PROJECT_SELECT + " WHERE id = ?", (project_id,)).fetchone()
            if row is None:
                raise ProjectNotFoundError(f"Project {project_id} was not found")
            current = _snapshot(row)
            if current.revision != expected_revision:
                raise InvalidProjectError("expected_revision does not match the project")
            current_index = PROJECT_STATUSES.index(current.status)
            if current_index + 1 >= len(PROJECT_STATUSES) or next_status != PROJECT_STATUSES[current_index + 1]:
                raise InvalidProjectError("next_status must be the adjacent forward lifecycle status")
            new_revision = current.revision + 1
            update = connection.execute(
                "UPDATE projects SET status = ?, revision = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND revision = ?",
                (next_status, new_revision, project_id, current.revision),
            )
            if update.rowcount != 1:
                raise RuntimeError("project changed during transition")
            audit_data = json.dumps({"actor": actor.strip(), "from_status": current.status, "new_revision": new_revision, "previous_revision": current.revision, "to_status": next_status}, sort_keys=True, separators=(",", ":"))
            connection.execute("INSERT INTO audit_events (event_type, entity_type, entity_id, event_data_json) VALUES ('project_transitioned', 'project', ?, ?)", (project_id, audit_data))
            moved_row = connection.execute(_PROJECT_SELECT + " WHERE id = ?", (project_id,)).fetchone()
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    assert moved_row is not None
    return _snapshot(moved_row)


_PROJECT_SELECT = "SELECT id, gig_id, title, summary, status, revision FROM projects"


def _snapshot(row: tuple[object, ...]) -> ProjectSnapshot:
    return ProjectSnapshot(id=int(row[0]), gig_id=None if row[1] is None else int(row[1]), title=str(row[2]), summary=str(row[3]), status=str(row[4]), revision=int(row[5]))


def _validate_id(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InvalidProjectError(f"{label} must be a positive integer")


def _validate_actor(actor: object) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise InvalidProjectError("actor must be a non-empty label")


def _validate_content(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidProjectError(f"{label} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > 4000:
        raise InvalidProjectError(f"{label} is too long")
    if _CREDENTIAL_ASSIGNMENT.search(cleaned) or _BEARER_AUTHORIZATION.search(cleaned):
        raise InvalidProjectError(f"{label} must not contain credential-like assignment text")
    return cleaned
