from __future__ import annotations

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
        "packages": {
            "basic": {
                "name": "Basic test fixture",
                "description": "A fictional test-only package.",
                "price_usd": 100,
                "delivery_days": 3,
                "revisions": 1,
                "features": ["one safe tool"],
            }
        },
    }


def test_profile_retrieval_returns_an_immutable_revisioned_snapshot(tmp_path: Path) -> None:
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    created = seed_profile_fixture(database_path, _profile_content())

    profile = get_profile(database_path, created.id)

    assert profile.id == created.id
    assert profile.revision == 1
    assert profile.public_content["display_name"] == "Example Automation Studio"
    with pytest.raises(TypeError):
        profile.public_content["tagline"] = "mutated"  # type: ignore[index]


def test_profile_snapshot_is_deeply_immutable(tmp_path: Path) -> None:
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    created = seed_profile_fixture(database_path, _profile_content())

    profile = get_profile(database_path, created.id)

    with pytest.raises(AttributeError):
        profile.public_content["skills"].append("mutated")  # type: ignore[union-attr]


def test_gig_list_and_get_return_revisioned_snapshots(tmp_path: Path) -> None:
    from fiverr_seller_os.models import get_gig, list_gigs
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    created = seed_gig_fixture(database_path, profile.id, _gig_content())

    gigs = list_gigs(database_path)
    gig = get_gig(database_path, created.id)

    assert gigs == (gig,)
    assert gig.id == created.id
    assert gig.revision == 1
    assert gig.public_content["title"] == "Build a fictional MCP server fixture"


def test_get_gig_raises_a_specific_error_when_missing(tmp_path: Path) -> None:
    from fiverr_seller_os.models import RecordNotFoundError, get_gig
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(RecordNotFoundError, match="Gig 404 was not found"):
        get_gig(database_path, 404)


def test_get_profile_raises_a_specific_error_when_missing(tmp_path: Path) -> None:
    from fiverr_seller_os.models import RecordNotFoundError, get_profile
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(RecordNotFoundError, match="Profile 404 was not found"):
        get_profile(database_path, 404)


def test_gig_snapshot_is_deeply_immutable(tmp_path: Path) -> None:
    from fiverr_seller_os.models import get_gig
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    created = seed_gig_fixture(database_path, profile.id, _gig_content())

    gig = get_gig(database_path, created.id)
    package = gig.public_content["packages"]["basic"]  # type: ignore[index]
    features = package["features"]  # type: ignore[index]

    with pytest.raises(TypeError):
        package["name"] = "mutated"  # type: ignore[index]
    with pytest.raises(AttributeError):
        features.append("mutated")  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("factory", "content"),
    [
        ("profile", {"display_name": "Fixture", "secret": "must not persist"}),
        (
            "gig",
            {
                "title": "Fixture",
                "description": "Fixture",
                "category": "Programming & Tech",
                "tags": [],
                "packages": {},
                "credentials": "must not persist",
            },
        ),
    ],
)
def test_fixture_helpers_reject_non_allowlisted_public_content(
    tmp_path: Path, factory: str, content: dict[str, object]
) -> None:
    from fiverr_seller_os.models import InvalidPublicContentError
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(InvalidPublicContentError, match="not allowed"):
        if factory == "profile":
            seed_profile_fixture(database_path, content)
        else:
            profile = seed_profile_fixture(database_path, _profile_content())
            seed_gig_fixture(database_path, profile.id, content)


@pytest.mark.parametrize(
    ("factory", "content"),
    [
        ("profile", {**_profile_content(), "skills": [{"token": "forbidden"}]}),
        ("profile", {**_profile_content(), "skills": [{"client_secret": "forbidden"}]}),
        ("gig", {**_gig_content(), "packages": {"basic": {"secret": "forbidden"}}}),
    ],
)
def test_fixture_helpers_reject_nested_sensitive_keys(
    tmp_path: Path, factory: str, content: dict[str, object]
) -> None:
    from fiverr_seller_os.models import InvalidPublicContentError
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(InvalidPublicContentError, match="sensitive"):
        if factory == "profile":
            seed_profile_fixture(database_path, content)
        else:
            seed_gig_fixture(database_path, None, content)


@pytest.mark.parametrize(
    "content",
    [
        {**_profile_content(), "skills": [{"apiKey": "forbidden"}]},
        {**_profile_content(), "skills": [{"API-KEY": "forbidden"}]},
        {**_profile_content(), "skills": [{"clientSecret": "forbidden"}]},
        {**_profile_content(), "bio": "Use api_key=abc123 to connect."},
        {**_profile_content(), "bio": "Authorization: Bearer abc123"},
        {**_profile_content(), "bio": "Configure client_secret=abc123 before starting."},
        {**_profile_content(), "bio": "Configure clientSecret=abc123 before starting."},
        {**_profile_content(), "bio": "Configure clientsecret=abc123 before starting."},
        {**_profile_content(), "bio": "Configure access_token=abc123 before starting."},
        {**_profile_content(), "bio": "Configure accessToken=abc123 before starting."},
        {**_profile_content(), "bio": "Configure accesstoken=abc123 before starting."},
    ],
)
def test_fixture_helpers_reject_credential_key_variants_and_assignment_text(
    tmp_path: Path, content: dict[str, object]
) -> None:
    from fiverr_seller_os.models import InvalidPublicContentError
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    with pytest.raises(InvalidPublicContentError, match="credential"):
        seed_profile_fixture(database_path, content)


@pytest.mark.parametrize("key", ["client_secret", "clientSecret", "clientsecret", "access_token", "accessToken", "accesstoken"])
def test_fixture_helpers_reject_compact_and_camel_credential_keys(tmp_path: Path, key: str) -> None:
    from fiverr_seller_os.models import InvalidPublicContentError
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    with pytest.raises(InvalidPublicContentError, match="sensitive"):
        seed_profile_fixture(database_path, {**_profile_content(), "skills": [{key: "forbidden"}]})


def test_public_prose_can_discuss_an_api_key_without_storing_one(tmp_path: Path) -> None:
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(
        database_path,
        {
            **_profile_content(),
            "bio": "I can explain client secrets and access tokens without collecting credentials.",
        },
    )
    assert profile.id == 1


@pytest.mark.parametrize(
    "packages",
    [
        {"basic": "not a package object"},
        {"basic": {**_gig_content()["packages"]["basic"], "unknown": "not allowed"}},  # type: ignore[index]
        {"enterprise": _gig_content()["packages"]["basic"]},  # type: ignore[index]
    ],
)
def test_fixture_helpers_reject_invalid_nested_package_shapes(
    tmp_path: Path, packages: object
) -> None:
    from fiverr_seller_os.models import InvalidPublicContentError
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    content = {**_gig_content(), "packages": packages}

    with pytest.raises(InvalidPublicContentError):
        seed_gig_fixture(database_path, None, content)
