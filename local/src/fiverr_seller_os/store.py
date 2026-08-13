"""Private SQLite storage for the local Seller OS.

This module owns only local canonical state. It intentionally contains no
network, browser, credential, or arbitrary-file handling.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import re

DATABASE_NAME = "seller_os.sqlite3"


def open_connection(database_path: Path) -> sqlite3.Connection:
    """Open a Seller OS database connection with referential integrity enabled."""
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_store(state_dir: Path) -> Path:
    """Create the private state directory, database, and core schema.

    The caller chooses the state directory explicitly; importing this module
    never creates the runtime default location.
    """
    resolved_state_dir = Path(state_dir).expanduser()
    state_directory_exists = resolved_state_dir.exists()
    database_path = resolved_state_dir / DATABASE_NAME

    # An existing database may contain a legacy changesets table that needs an
    # explicit migration. Inspect it before changing permissions on either
    # pre-existing filesystem object or making any schema changes.
    if state_directory_exists and database_path.exists():
        existing_connection = open_connection(database_path)
        try:
            _reject_incompatible_changesets_schema(existing_connection)
        finally:
            existing_connection.close()

    resolved_state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(resolved_state_dir, 0o700)

    connection = open_connection(database_path)
    try:
        with connection:
            # Validate an existing legacy table before changing the database's
            # permissions or schema. A rejected legacy database must remain
            # byte-for-byte and mode-for-mode available for explicit migration.
            _reject_incompatible_changesets_schema(connection)
            for statement in _SCHEMA:
                connection.execute(statement)
            _migrate_legacy_revisions(connection)
            _migrate_legacy_project_fields(connection)
        # New databases and accepted schemas are private. Do this only after
        # compatibility validation so a rejected existing database is untouched.
        os.chmod(database_path, 0o600)
    finally:
        connection.close()
    return database_path


def _migrate_legacy_revisions(connection: sqlite3.Connection) -> None:
    """Upgrade pre-revision profile and Gig tables without replacing user data."""
    for table in ("profiles", "gigs"):
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if "revision" not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1)"
            )


def _migrate_legacy_project_fields(connection: sqlite3.Connection) -> None:
    """Add lifecycle read fields without discarding an earlier local project table."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(projects)")}
    additions = (
        ("buyer_brief_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("summary", "TEXT NOT NULL DEFAULT ''"),
        ("revision", "INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1)"),
    )
    for name, definition in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE projects ADD COLUMN {name} {definition}")


def _reject_incompatible_changesets_schema(connection: sqlite3.Connection) -> None:
    """Refuse to overwrite an older changeset table with unreviewed data."""
    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'changesets'"
    ).fetchone()
    if table_exists is None:
        return
    columns = connection.execute("PRAGMA table_info(changesets)").fetchall()
    expected = {
        "id": ("INTEGER", 0, None, 1),
        "target_type": ("TEXT", 1, None, 0),
        "target_id": ("INTEGER", 1, None, 0),
        "patch_json": ("TEXT", 1, None, 0),
        "base_revision": ("INTEGER", 1, None, 0),
        "actor": ("TEXT", 1, None, 0),
        "status": ("TEXT", 1, "'proposed'", 0),
        "created_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
        "approved_at": ("TEXT", 0, None, 0),
        "approved_by": ("TEXT", 0, None, 0),
    }
    actual = {str(row[1]): (str(row[2]).upper(), int(row[3]), row[4], int(row[5])) for row in columns}
    sql_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'changesets'"
    ).fetchone()
    normalized_sql = re.sub(r"\s+", "", str(sql_row[0]).upper()) if sql_row else ""
    required_constraints = (
        "CHECK(TARGET_TYPEIN('PROFILE','GIG'))",
        "CHECK(JSON_VALID(PATCH_JSON)ANDJSON_TYPE(PATCH_JSON)='OBJECT')",
        "CHECK(BASE_REVISION>=1)",
        "STATUS='PROPOSED'",
        "STATUS='APPROVED'",
        "APPROVED_ATISNOTNULL",
        "APPROVED_BYISNOTNULL",
    )
    if actual != expected or not all(constraint in normalized_sql for constraint in required_constraints):
        raise RuntimeError(
            "The existing changesets table is incompatible and requires an explicit migration; local data was not changed"
        )


_SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY,
    public_content_json TEXT NOT NULL CHECK(json_valid(public_content_json) AND json_type(public_content_json) = 'object'),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",

    """
CREATE TABLE IF NOT EXISTS gigs (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    title TEXT NOT NULL,
    public_content_json TEXT NOT NULL CHECK(json_valid(public_content_json) AND json_type(public_content_json) = 'object'),
    status TEXT NOT NULL DEFAULT 'draft',
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",

    """
CREATE TABLE IF NOT EXISTS changesets (
    id INTEGER PRIMARY KEY,
    target_type TEXT NOT NULL CHECK(target_type IN ('profile', 'gig')),
    target_id INTEGER NOT NULL,
    patch_json TEXT NOT NULL CHECK(json_valid(patch_json) AND json_type(patch_json) = 'object'),
    base_revision INTEGER NOT NULL CHECK(base_revision >= 1),
    actor TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TEXT,
    approved_by TEXT,
    CHECK(
        (status = 'proposed' AND approved_at IS NULL AND approved_by IS NULL)
        OR (status = 'approved' AND approved_at IS NOT NULL AND approved_by IS NOT NULL)
    )
)
""",

    """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    gig_id INTEGER REFERENCES gigs(id),
    buyer_brief_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(buyer_brief_json) AND json_type(buyer_brief_json) = 'object'),
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
    status TEXT NOT NULL DEFAULT 'lead' CHECK(status IN (
        'lead', 'intake', 'scoped', 'quoted', 'ordered', 'building',
        'testing', 'delivery-ready', 'delivered', 'closed'
    )),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",

    """
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    event_data_json TEXT NOT NULL CHECK(json_valid(event_data_json) AND json_type(event_data_json) = 'object'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",
    """
CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END
""",
    """
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END
""",
)
