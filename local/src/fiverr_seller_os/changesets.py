"""Reviewable, local-only proposals for canonical profile and Gig changes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from .models import (
    InvalidPublicContentError,
    _validate_gig_content,
    _validate_profile_content,
    _freeze_json_value,
    get_gig,
    get_profile,
)
from .store import open_connection


class InvalidChangesetError(ValueError):
    """Raised when a proposed local changeset is not reviewable or safe."""


class ChangesetNotFoundError(LookupError):
    """Raised when a requested local changeset does not exist."""


@dataclass(frozen=True, slots=True)
class ChangesetProposal:
    id: int
    target_type: str
    target_id: int
    patch: Mapping[str, object]
    base_revision: int
    actor: str
    status: str
    created_at: str


def propose_changeset(
    database_path: Path,
    *,
    target_type: str,
    target_id: int,
    patch: Mapping[str, object],
    base_revision: int,
    actor: str,
) -> ChangesetProposal:
    """Store a validated proposal without changing its canonical target."""
    _validate_target_id(target_id)
    content, current_revision = _target_content(database_path, target_type, target_id)
    _validate_request(patch, base_revision, current_revision, actor)
    normalized_patch = _validate_patch(target_type, content, patch)

    with open_connection(database_path) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO changesets
                    (target_type, target_id, patch_json, base_revision, actor)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    target_type,
                    target_id,
                    json.dumps(normalized_patch, sort_keys=True, separators=(",", ":")),
                    base_revision,
                    actor.strip(),
                ),
            )
            row = connection.execute(
                """
                SELECT id, target_type, target_id, patch_json, base_revision, actor, status, created_at
                FROM changesets WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    assert row is not None
    return _changeset_snapshot(row)


def get_changeset(database_path: Path, changeset_id: int) -> ChangesetProposal:
    """Return one immutable local proposal without changing canonical records."""
    _validate_changeset_id(changeset_id)
    with open_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, target_type, target_id, patch_json, base_revision, actor, status, created_at
            FROM changesets WHERE id = ?
            """,
            (changeset_id,),
        ).fetchone()
    if row is None:
        raise ChangesetNotFoundError(f"Changeset {changeset_id} was not found")
    return _changeset_snapshot(row)


def list_changesets(
    database_path: Path, *, target_type: str | None = None, target_id: int | None = None
) -> tuple[ChangesetProposal, ...]:
    """Return immutable proposals in stable creation (ID) order.

    Optional filters are conjunctive. A target ID without a target type is
    useful when reviewing one canonical record across its supported types.
    """
    if target_type is not None and target_type not in {"profile", "gig"}:
        raise InvalidChangesetError("target_type must be 'profile' or 'gig'")
    if target_id is not None:
        _validate_target_id(target_id)
    predicates: list[str] = []
    values: list[object] = []
    if target_type is not None:
        predicates.append("target_type = ?")
        values.append(target_type)
    if target_id is not None:
        predicates.append("target_id = ?")
        values.append(target_id)
    where_clause = f" WHERE {' AND '.join(predicates)}" if predicates else ""
    with open_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, target_type, target_id, patch_json, base_revision, actor, status, created_at "
            f"FROM changesets{where_clause} ORDER BY id",
            values,
        ).fetchall()
    return tuple(_changeset_snapshot(row) for row in rows)


def _changeset_snapshot(row: tuple[object, ...]) -> ChangesetProposal:
    """Convert a database row into a typed, deeply immutable public snapshot."""
    patch = json.loads(str(row[3]))
    if not isinstance(patch, dict):  # Protected by schema; defensive for legacy corruption.
        raise RuntimeError("changeset patch_json is not an object")
    frozen_patch = _freeze_json_value(patch)
    assert isinstance(frozen_patch, Mapping)
    return ChangesetProposal(
        id=int(row[0]),
        target_type=str(row[1]),
        target_id=int(row[2]),
        patch=frozen_patch,
        base_revision=int(row[4]),
        actor=str(row[5]),
        status=str(row[6]),
        created_at=str(row[7]),
    )


def _target_content(database_path: Path, target_type: str, target_id: int) -> tuple[Mapping[str, object], int]:
    if target_type == "profile":
        target = get_profile(database_path, target_id)
    elif target_type == "gig":
        target = get_gig(database_path, target_id)
    else:
        raise InvalidChangesetError("target_type must be 'profile' or 'gig'")
    return target.public_content, target.revision


def _validate_request(
    patch: Mapping[str, object], base_revision: int, current_revision: int, actor: str
) -> None:
    if not isinstance(patch, Mapping) or not patch:
        raise InvalidChangesetError("patch must be a non-empty object")
    if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 1:
        raise InvalidChangesetError("base_revision must be a positive integer")
    if base_revision != current_revision:
        raise InvalidChangesetError("base_revision does not match the canonical target")
    if not isinstance(actor, str) or not actor.strip():
        raise InvalidChangesetError("actor must be a non-empty label")


def _validate_target_id(target_id: object) -> None:
    if not isinstance(target_id, int) or isinstance(target_id, bool) or target_id < 1:
        raise InvalidChangesetError("target_id must be a positive integer")


def _validate_changeset_id(changeset_id: object) -> None:
    if not isinstance(changeset_id, int) or isinstance(changeset_id, bool) or changeset_id < 1:
        raise InvalidChangesetError("changeset_id must be a positive integer")


def _validate_patch(
    target_type: str, content: Mapping[str, object], patch: Mapping[str, object]
) -> dict[str, object]:
    proposed_content = _mutable_json_value(content)
    proposed_content.update(patch)
    try:
        if target_type == "profile":
            _validate_profile_content(proposed_content)
        else:
            _validate_gig_content(proposed_content)
    except InvalidPublicContentError as error:
        raise InvalidChangesetError(str(error)) from error
    return json.loads(json.dumps(dict(patch), sort_keys=True, separators=(",", ":")))


def _mutable_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _mutable_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_mutable_json_value(item) for item in value]
    return value
