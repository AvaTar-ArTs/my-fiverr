import stat
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


def test_importing_and_reloading_store_does_not_create_configured_state_path(tmp_path: Path) -> None:
    """Import safety must hold in a fresh interpreter, not just this test process."""
    state_dir = tmp_path / "configured-but-not-initialized"
    source_dir = Path(__file__).parents[1] / "src"
    environment = os.environ.copy()
    environment["FIVERR_SELLER_OS_STATE_DIR"] = str(state_dir)
    environment["PYTHONPATH"] = str(source_dir)

    subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib; import fiverr_seller_os.store as store; importlib.reload(store)",
        ],
        check=True,
        env=environment,
    )

    assert not state_dir.exists()


def test_initialize_store_creates_private_state_directory_and_database(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store

    state_dir = tmp_path / "seller-os-state"

    database_path = initialize_store(state_dir)

    assert database_path == state_dir / "seller_os.sqlite3"
    assert database_path.is_file()
    assert stat.S_IMODE(state_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(database_path.stat().st_mode) == 0o600


def test_store_has_only_canonical_workflow_tables_and_validates_json_content(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "seller-os-state")
    with open_connection(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert tables == {"profiles", "gigs", "changesets", "projects", "audit_events"}

        profile_columns = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(profiles)")}
        assert profile_columns["public_content_json"] == "TEXT"

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO profiles (public_content_json) VALUES ('not-json')")

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO profiles (public_content_json) VALUES ('[]')")

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO profiles (public_content_json) VALUES ('true')")

        connection.execute("INSERT INTO profiles (public_content_json) VALUES ('{}')")


def test_open_connection_enforces_foreign_keys_for_gigs_and_projects(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "seller-os-state")
    with open_connection(database_path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO gigs (profile_id, title, public_content_json) VALUES (99, 'Test', '{}')"
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO projects (gig_id, buyer_brief_json) VALUES (99, '{}')")


def test_audit_events_cannot_be_updated(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "seller-os-state")
    with open_connection(database_path) as connection:
        connection.execute(
            "INSERT INTO audit_events (event_type, entity_type, event_data_json) VALUES ('created', 'gig', '{}')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE audit_events SET event_type = 'changed' WHERE id = 1")


def test_audit_events_cannot_be_deleted(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "seller-os-state")
    with open_connection(database_path) as connection:
        connection.execute(
            "INSERT INTO audit_events (event_type, entity_type, event_data_json) VALUES ('created', 'gig', '{}')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM audit_events WHERE id = 1")


def test_initialize_store_migrates_pre_revision_profile_and_gig_tables(tmp_path: Path) -> None:
    from fiverr_seller_os.models import get_gig, get_profile
    from fiverr_seller_os.store import DATABASE_NAME, initialize_store, open_connection

    state_dir = tmp_path / "legacy-state"
    state_dir.mkdir()
    database_path = state_dir / DATABASE_NAME
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE profiles (id INTEGER PRIMARY KEY, public_content_json TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE gigs (id INTEGER PRIMARY KEY, profile_id INTEGER, title TEXT NOT NULL, public_content_json TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO profiles (public_content_json) VALUES ('{}')")
        connection.execute(
            "INSERT INTO gigs (profile_id, title, public_content_json) VALUES (1, 'Legacy', '{}')"
        )

    migrated_path = initialize_store(state_dir)
    initialize_store(state_dir)

    assert get_profile(migrated_path, 1).revision == 1
    assert get_gig(migrated_path, 1).revision == 1


def test_initialize_store_refuses_incompatible_legacy_changesets_without_modifying_it(tmp_path: Path) -> None:
    from fiverr_seller_os.store import DATABASE_NAME, initialize_store

    state_dir = tmp_path / "legacy-state"
    state_dir.mkdir()
    database_path = state_dir / DATABASE_NAME
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE changesets (id INTEGER PRIMARY KEY, target_type TEXT NOT NULL)")
        connection.execute("INSERT INTO changesets (target_type) VALUES ('profile')")
    os.chmod(database_path, 0o640)
    original_mode = stat.S_IMODE(database_path.stat().st_mode)

    with pytest.raises(RuntimeError, match="changesets table is incompatible"):
        initialize_store(state_dir)
    assert stat.S_IMODE(database_path.stat().st_mode) == original_mode
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA table_info(changesets)").fetchall() == [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "target_type", "TEXT", 1, None, 0),
        ]
        assert connection.execute("SELECT id, target_type FROM changesets").fetchall() == [(1, "profile")]


def test_initialize_store_rejects_incompatible_legacy_database_before_changing_existing_permissions(
    tmp_path: Path,
) -> None:
    """Legacy rejection must leave both pre-existing filesystem objects untouched."""
    from fiverr_seller_os.store import DATABASE_NAME, initialize_store

    state_dir = tmp_path / "legacy-state"
    state_dir.mkdir(mode=0o755)
    os.chmod(state_dir, 0o755)
    database_path = state_dir / DATABASE_NAME
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE changesets (id INTEGER PRIMARY KEY, target_type TEXT NOT NULL)")
        connection.execute("INSERT INTO changesets (target_type) VALUES ('profile')")
    os.chmod(database_path, 0o640)

    original_directory_mode = stat.S_IMODE(state_dir.stat().st_mode)
    original_database_mode = stat.S_IMODE(database_path.stat().st_mode)
    original_database_bytes = database_path.read_bytes()

    with pytest.raises(RuntimeError, match="changesets table is incompatible"):
        initialize_store(state_dir)

    assert stat.S_IMODE(state_dir.stat().st_mode) == original_directory_mode
    assert stat.S_IMODE(database_path.stat().st_mode) == original_database_mode
    assert database_path.read_bytes() == original_database_bytes
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA table_info(changesets)").fetchall() == [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "target_type", "TEXT", 1, None, 0),
        ]
        assert connection.execute("SELECT id, target_type FROM changesets").fetchall() == [(1, "profile")]
