"""Typed, immutable read views of local Seller OS canonical records.

This module intentionally provides no record-creation API. Production writes
must use an approved changeset workflow; test fixtures live under ``tests/``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

from .store import open_connection


class RecordNotFoundError(LookupError):
    """Raised when a requested local canonical record does not exist."""


class InvalidPublicContentError(ValueError):
    """Raised when fixture content is not a permitted public record shape."""


PublicContent = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    id: int
    public_content: PublicContent
    revision: int


@dataclass(frozen=True, slots=True)
class GigSnapshot:
    id: int
    profile_id: int | None
    public_content: PublicContent
    revision: int


_PROFILE_FIELDS = frozenset({"display_name", "tagline", "bio", "skills"})
_GIG_FIELDS = frozenset({"title", "description", "category", "tags", "packages"})
_PACKAGE_TIERS = frozenset({"basic", "standard", "premium"})
_PACKAGE_FIELDS = frozenset(
    {"name", "description", "price_usd", "delivery_days", "revisions", "features"}
)
# Public records are deliberately a narrow, non-secret subset of seller data.
# These patterns reject assignments, not ordinary prose mentioning an API key.
_SENSITIVE_KEY_PARTS = frozenset({"password", "token", "secret", "cookie", "credential", "credentials"})
_SENSITIVE_COMPACT_NAMES = _SENSITIVE_KEY_PARTS | frozenset({"apikey"})
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(?:"
    r"api[ _-]?key|apikey|"
    r"client[ _-]?secret|clientsecret|"
    r"access[ _-]?token|accesstoken|"
    r"password|token|secret|cookie|credentials?"
    r")\s*[:=]\s*\S+"
)
_BEARER_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S+")


def get_profile(database_path: Path, profile_id: int) -> ProfileSnapshot:
    with open_connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, public_content_json, revision FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"Profile {profile_id} was not found")
    return ProfileSnapshot(id=row[0], public_content=_freeze_json_object(row[1]), revision=row[2])


def list_gigs(database_path: Path) -> tuple[GigSnapshot, ...]:
    with open_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, profile_id, public_content_json, revision FROM gigs ORDER BY id"
        ).fetchall()
    return tuple(_gig_snapshot(row) for row in rows)


def get_gig(database_path: Path, gig_id: int) -> GigSnapshot:
    with open_connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, profile_id, public_content_json, revision FROM gigs WHERE id = ?", (gig_id,)
        ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"Gig {gig_id} was not found")
    return _gig_snapshot(row)


def _gig_snapshot(row: tuple[object, ...]) -> GigSnapshot:
    return GigSnapshot(
        id=int(row[0]),
        profile_id=None if row[1] is None else int(row[1]),
        public_content=_freeze_json_object(str(row[2])),
        revision=int(row[3]),
    )


def _validate_profile_content(content: Mapping[str, object]) -> dict[str, object]:
    _reject_sensitive_keys(content)
    _validate_fields(content, _PROFILE_FIELDS, "profile")
    for field in ("display_name", "tagline", "bio"):
        if not isinstance(content[field], str):
            raise InvalidPublicContentError(f"profile field {field!r} must be a string")
    _validate_string_list(content["skills"], "profile field 'skills'")
    return dict(content)


def _validate_gig_content(content: Mapping[str, object]) -> dict[str, object]:
    _reject_sensitive_keys(content)
    _validate_fields(content, _GIG_FIELDS, "gig")
    for field in ("title", "description", "category"):
        if not isinstance(content[field], str):
            raise InvalidPublicContentError(f"gig field {field!r} must be a string")
    _validate_string_list(content["tags"], "gig field 'tags'")
    _validate_packages(content["packages"])
    return dict(content)


def _validate_fields(content: Mapping[str, object], allowed: frozenset[str], record_name: str) -> None:
    fields = set(content)
    disallowed = fields - allowed
    if disallowed:
        raise InvalidPublicContentError(
            f"{record_name} public content fields are not allowed: {', '.join(sorted(disallowed))}"
        )
    missing = allowed - fields
    if missing:
        raise InvalidPublicContentError(
            f"{record_name} public content is missing: {', '.join(sorted(missing))}"
        )


def _validate_string_list(value: object, label: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InvalidPublicContentError(f"{label} must be a list of strings")


def _validate_packages(value: object) -> None:
    if not isinstance(value, Mapping) or not value:
        raise InvalidPublicContentError("gig field 'packages' must be a non-empty object")
    disallowed_tiers = set(value) - _PACKAGE_TIERS
    if disallowed_tiers:
        raise InvalidPublicContentError(
            f"gig package tiers are not allowed: {', '.join(sorted(disallowed_tiers))}"
        )
    for tier, package in value.items():
        if not isinstance(package, Mapping):
            raise InvalidPublicContentError(f"gig package {tier!r} must be an object")
        _validate_fields(package, _PACKAGE_FIELDS, f"gig package {tier!r}")
        for field in ("name", "description"):
            if not isinstance(package[field], str):
                raise InvalidPublicContentError(
                    f"gig package {tier!r} field {field!r} must be a string"
                )
        if not _is_number(package["price_usd"]):
            raise InvalidPublicContentError(
                f"gig package {tier!r} field 'price_usd' must be a number"
            )
        for field in ("delivery_days", "revisions"):
            if not isinstance(package[field], int) or isinstance(package[field], bool):
                raise InvalidPublicContentError(
                    f"gig package {tier!r} field {field!r} must be an integer"
                )
        _validate_string_list(package["features"], f"gig package {tier!r} field 'features'")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _reject_sensitive_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise InvalidPublicContentError("public content keys must be strings")
            # Split ``clientSecret``, ``client_secret`` and ``client-secret``
            # equivalently, then also inspect their compact spelling.
            segmented = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key)
            parts = tuple(part.casefold() for part in re.split(r"[^A-Za-z0-9]+", segmented) if part)
            compact = "".join(parts)
            if (
                compact in _SENSITIVE_COMPACT_NAMES
                or compact in {"clientsecret", "accesstoken"}
                or any(part in _SENSITIVE_KEY_PARTS or "apikey" in part for part in parts)
            ):
                raise InvalidPublicContentError(
                    f"sensitive credential-like key {key!r} is not allowed in public content"
                )
            _reject_sensitive_keys(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            _reject_sensitive_keys(nested_value)
    elif isinstance(value, str) and (
        _CREDENTIAL_ASSIGNMENT.search(value) or _BEARER_AUTHORIZATION.search(value)
    ):
        raise InvalidPublicContentError(
            "credential-like assignment text is not allowed in public content"
        )


def _freeze_json_object(encoded_content: str) -> PublicContent:
    parsed = json.loads(encoded_content)
    return _freeze_json_value(parsed)


def _freeze_json_value(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value
