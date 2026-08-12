"""Test-only canonical-record fixture helpers.

These helpers deliberately are not part of the Seller OS package API.  They
validate the same public-content boundary before inserting controlled fixture
records directly into a local test database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from fiverr_seller_os.models import (
    GigSnapshot,
    ProfileSnapshot,
    _validate_gig_content,
    _validate_profile_content,
    get_gig,
    get_profile,
)
from fiverr_seller_os.store import open_connection


def seed_profile_fixture(
    database_path: Path, public_content: Mapping[str, object]
) -> ProfileSnapshot:
    content = _validate_profile_content(public_content)
    with open_connection(database_path) as connection:
        with connection:
            cursor = connection.execute(
                "INSERT INTO profiles (public_content_json) VALUES (?)",
                (json.dumps(content, sort_keys=True, separators=(",", ":")),),
            )
    return get_profile(database_path, int(cursor.lastrowid))


def seed_gig_fixture(
    database_path: Path, profile_id: int | None, public_content: Mapping[str, object]
) -> GigSnapshot:
    content = _validate_gig_content(public_content)
    with open_connection(database_path) as connection:
        with connection:
            cursor = connection.execute(
                "INSERT INTO gigs (profile_id, title, public_content_json) VALUES (?, ?, ?)",
                (profile_id, content["title"], json.dumps(content, sort_keys=True, separators=(",", ":"))),
            )
    return get_gig(database_path, int(cursor.lastrowid))
