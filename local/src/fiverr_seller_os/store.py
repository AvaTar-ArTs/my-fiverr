"""Private SQLite storage for the local Seller OS.

This module owns only local canonical state. It intentionally contains no
network, browser, credential, or arbitrary-file handling.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3

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
    resolved_state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(resolved_state_dir, 0o700)
    database_path = resolved_state_dir / DATABASE_NAME

    connection = open_connection(database_path)
    try:
        os.chmod(database_path, 0o600)
        with connection:
            for statement in _SCHEMA:
                connection.execute(statement)
    finally:
        connection.close()
    return database_path


_SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY,
    public_content_json TEXT NOT NULL CHECK(json_valid(public_content_json) AND json_type(public_content_json) = 'object'),
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",

    """
CREATE TABLE IF NOT EXISTS changesets (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    proposed_content_json TEXT NOT NULL CHECK(json_valid(proposed_content_json) AND json_type(proposed_content_json) = 'object'),
    status TEXT NOT NULL DEFAULT 'proposed',
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""",

    """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    gig_id INTEGER REFERENCES gigs(id),
    buyer_brief_json TEXT NOT NULL CHECK(json_valid(buyer_brief_json) AND json_type(buyer_brief_json) = 'object'),
    status TEXT NOT NULL DEFAULT 'intake',
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
