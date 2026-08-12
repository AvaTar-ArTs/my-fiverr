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


def test_proposed_profile_changeset_is_stored_without_mutating_canonical_content(
    tmp_path: Path,
) -> None:
    from fiverr_seller_os.changesets import propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())

    proposal = propose_changeset(
        database_path,
        target_type="profile",
        target_id=profile.id,
        patch={"tagline": "A revised fictional tagline"},
        base_revision=profile.revision,
        actor="seller",
    )

    assert proposal.id == 1
    assert proposal.target_type == "profile"
    assert proposal.target_id == profile.id
    assert proposal.patch == {"tagline": "A revised fictional tagline"}
    assert proposal.base_revision == profile.revision
    assert proposal.actor == "seller"
    assert proposal.status == "proposed"
    assert proposal.created_at
    assert get_profile(database_path, profile.id).public_content == profile.public_content


def test_proposed_gig_changeset_accepts_an_allowlisted_patch(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import propose_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    gig = seed_gig_fixture(database_path, profile.id, _gig_content())

    proposal = propose_changeset(
        database_path,
        target_type="gig",
        target_id=gig.id,
        patch={"tags": ["mcp", "python", "automation"]},
        base_revision=gig.revision,
        actor="seller-review",
    )

    assert proposal.target_type == "gig"
    assert proposal.patch == {"tags": ("mcp", "python", "automation")}
    with pytest.raises(AttributeError):
        proposal.patch["tags"].append("mutated")  # type: ignore[union-attr]


def test_changesets_are_retrievable_immutable_and_listed_in_id_order(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import get_changeset, list_changesets, propose_changeset
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    first = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"tagline": "First"}, base_revision=profile.revision, actor="seller"
    )
    second = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"bio": "Second"}, base_revision=profile.revision, actor="seller"
    )

    assert get_changeset(database_path, first.id) == first
    assert list_changesets(database_path) == (first, second)
    assert list_changesets(database_path, target_type="profile", target_id=profile.id) == (first, second)
    with open_connection(database_path) as connection:
        direct = connection.execute("SELECT status, created_at FROM changesets WHERE id = ?", (first.id,)).fetchone()
    assert direct == (first.status, first.created_at)
    with pytest.raises(TypeError):
        first.patch["tagline"] = "mutated"  # type: ignore[index]


def test_get_changeset_missing_and_invalid_ids_raise_specific_errors(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import ChangesetNotFoundError, InvalidChangesetError, get_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    with pytest.raises(ChangesetNotFoundError, match="Changeset 404 was not found"):
        get_changeset(database_path, 404)
    with pytest.raises(InvalidChangesetError, match="changeset_id"):
        get_changeset(database_path, True)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "patch",
    [
        {"unreviewed_field": "not allowed"},
        {"tagline": {"api_key": "not allowed"}},
    ],
)
def test_proposal_rejects_disallowed_or_sensitive_patch_fields(
    tmp_path: Path, patch: dict[str, object]
) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, propose_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())

    with pytest.raises(InvalidChangesetError):
        propose_changeset(
            database_path,
            target_type="profile",
            target_id=profile.id,
            patch=patch,
            base_revision=profile.revision,
            actor="seller",
        )


def test_proposal_rejects_unknown_target_type(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, propose_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(InvalidChangesetError, match="target_type"):
        propose_changeset(
            database_path,
            target_type="project",
            target_id=1,
            patch={"status": "done"},
            base_revision=1,
            actor="seller",
        )


@pytest.mark.parametrize(
    ("base_revision", "actor", "patch"),
    [
        (0, "seller", {"tagline": "revised"}),
        (True, "seller", {"tagline": "revised"}),
        (2, "seller", {"tagline": "revised"}),
        (1, "", {"tagline": "revised"}),
        (1, "   ", {"tagline": "revised"}),
        (1, "seller", {}),
        (1, "seller", []),
    ],
)
def test_proposal_rejects_invalid_request_fields(
    tmp_path: Path, base_revision: object, actor: object, patch: object
) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, propose_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    with pytest.raises(InvalidChangesetError):
        propose_changeset(
            database_path, target_type="profile", target_id=profile.id,
            patch=patch,  # type: ignore[arg-type]
            base_revision=base_revision,  # type: ignore[arg-type]
            actor=actor,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("target_id", [0, -1, True, "1"])
def test_proposal_rejects_non_positive_integer_target_ids(tmp_path: Path, target_id: object) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, propose_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")

    with pytest.raises(InvalidChangesetError, match="target_id"):
        propose_changeset(
            database_path,
            target_type="profile",
            target_id=target_id,  # type: ignore[arg-type]
            patch={"tagline": "revised"},
            base_revision=1,
            actor="seller",
        )
