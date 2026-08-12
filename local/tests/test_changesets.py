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


def test_approval_atomically_updates_the_canonical_target_and_audits_it(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import approve_changeset, get_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    proposal = propose_changeset(
        database_path,
        target_type="profile",
        target_id=profile.id,
        patch={"tagline": "Approved fictional tagline"},
        base_revision=profile.revision,
        actor="draft-author",
    )

    approved = approve_changeset(
        database_path, proposal.id, expected_revision=profile.revision, actor="seller"
    )

    canonical = get_profile(database_path, profile.id)
    assert canonical.public_content["tagline"] == "Approved fictional tagline"
    assert canonical.public_content["skills"] == ("python", "mcp")
    assert canonical.revision == 2
    assert approved.status == "approved"
    assert approved.approved_at
    assert approved.approved_by == "seller"
    assert get_changeset(database_path, proposal.id) == approved
    with open_connection(database_path) as connection:
        events = connection.execute(
            "SELECT event_type, entity_type, entity_id, event_data_json FROM audit_events"
        ).fetchall()
    assert events == [
        (
            "changeset_approved",
            "profile",
            profile.id,
            '{"actor":"seller","changeset_id":1,"new_revision":2,"previous_revision":1}',
        )
    ]


def test_approval_updates_a_gig_and_keeps_its_title_column_in_sync(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_gig
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    gig = seed_gig_fixture(database_path, profile.id, _gig_content())
    proposal = propose_changeset(
        database_path, target_type="gig", target_id=gig.id,
        patch={"title": "Approved fictional MCP integration"}, base_revision=1, actor="draft-author"
    )

    approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    assert get_gig(database_path, gig.id).public_content["title"] == "Approved fictional MCP integration"
    assert get_gig(database_path, gig.id).revision == 2
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT title FROM gigs WHERE id = ?", (gig.id,)).fetchone() == (
            "Approved fictional MCP integration",
        )


def test_approval_replaces_a_nested_packages_value_when_given_the_complete_packages_object(
    tmp_path: Path,
) -> None:
    from fiverr_seller_os.changesets import approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_gig
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    gig_content = _gig_content()
    gig_content["packages"] = {
        **gig_content["packages"],
        "standard": {
            "name": "Existing standard test fixture",
            "description": "An existing package that the replacement removes.",
            "price_usd": 250,
            "delivery_days": 6,
            "revisions": 2,
            "features": ["two safe tools"],
        },
    }
    gig = seed_gig_fixture(database_path, profile.id, gig_content)
    replacement_packages = {
        "basic": {
            "name": "Revised basic test fixture",
            "description": "A complete replacement package object.",
            "price_usd": 175,
            "delivery_days": 5,
            "revisions": 2,
            "features": ["one safe tool", "plain-English handoff"],
        }
    }
    proposal = propose_changeset(
        database_path,
        target_type="gig",
        target_id=gig.id,
        patch={"packages": replacement_packages},
        base_revision=1,
        actor="draft-author",
    )

    approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    packages = get_gig(database_path, gig.id).public_content["packages"]
    assert packages["basic"]["name"] == "Revised basic test fixture"  # type: ignore[index]
    assert packages["basic"]["price_usd"] == 175  # type: ignore[index]
    assert packages["basic"]["features"] == ("one safe tool", "plain-English handoff")  # type: ignore[index]
    assert "standard" not in packages  # type: ignore[operator]


def test_approval_rejects_a_stale_expected_revision_without_modifying_anything(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    proposal = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"tagline": "Never applied"}, base_revision=1, actor="draft-author"
    )

    with pytest.raises(InvalidChangesetError, match="expected_revision"):
        approve_changeset(database_path, proposal.id, expected_revision=2, actor="seller")

    assert get_profile(database_path, profile.id) == profile
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT status, approved_at, approved_by FROM changesets").fetchall() == [
            ("proposed", None, None)
        ]
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []


def test_approval_rejects_a_stale_proposal_base_revision_without_modifying_anything(
    tmp_path: Path,
) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    proposal = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"tagline": "Never applied"}, base_revision=1, actor="draft-author"
    )
    # Simulate a prior approved writer: proposal creation predates canonical revision 2.
    with open_connection(database_path) as connection:
        connection.execute("UPDATE profiles SET revision = 2 WHERE id = ?", (profile.id,))

    with pytest.raises(InvalidChangesetError, match="base_revision"):
        approve_changeset(database_path, proposal.id, expected_revision=2, actor="seller")

    assert get_profile(database_path, profile.id).revision == 2
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT status, approved_at, approved_by FROM changesets").fetchall() == [
            ("proposed", None, None)
        ]
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []


def test_approval_cannot_be_repeated(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    proposal = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"tagline": "Applied once"}, base_revision=1, actor="draft-author"
    )
    approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    with pytest.raises(InvalidChangesetError, match="not proposed"):
        approve_changeset(database_path, proposal.id, expected_revision=2, actor="seller")

    assert get_profile(database_path, profile.id).revision == 2
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (1,)


@pytest.mark.parametrize(
    ("changeset_id", "expected_revision", "actor", "message"),
    [
        (0, 1, "seller", "changeset_id"),
        (True, 1, "seller", "changeset_id"),
        ("1", 1, "seller", "changeset_id"),
        (1, 0, "seller", "expected_revision"),
        (1, True, "seller", "expected_revision"),
        (1, "1", "seller", "expected_revision"),
        (1, 1, "", "actor"),
        (1, 1, "   ", "actor"),
        (1, 1, 1, "actor"),
    ],
)
def test_approval_rejects_invalid_request_fields(
    tmp_path: Path, changeset_id: object, expected_revision: object, actor: object, message: str
) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    with pytest.raises(InvalidChangesetError, match=message):
        approve_changeset(  # type: ignore[arg-type]
            database_path, changeset_id, expected_revision=expected_revision, actor=actor
        )


def test_approval_rejects_a_missing_changeset(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import ChangesetNotFoundError, approve_changeset
    from fiverr_seller_os.store import initialize_store

    database_path = initialize_store(tmp_path / "state")
    with pytest.raises(ChangesetNotFoundError, match="Changeset 404 was not found"):
        approve_changeset(database_path, 404, expected_revision=1, actor="seller")


def test_approval_rolls_back_every_change_when_the_audit_insert_fails(tmp_path: Path) -> None:
    import sqlite3

    from fiverr_seller_os.changesets import approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    profile = seed_profile_fixture(database_path, _profile_content())
    proposal = propose_changeset(
        database_path, target_type="profile", target_id=profile.id,
        patch={"tagline": "Must roll back"}, base_revision=1, actor="draft-author"
    )
    with open_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER abort_approval_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.event_type = 'changeset_approved'
            BEGIN
                SELECT RAISE(ABORT, 'forced audit failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced audit failure"):
        approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    assert get_profile(database_path, profile.id) == profile
    with open_connection(database_path) as connection:
        assert connection.execute("SELECT status, approved_at, approved_by FROM changesets").fetchall() == [
            ("proposed", None, None)
        ]
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []


def test_approval_rolls_back_when_its_canonical_target_is_missing(tmp_path: Path) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    target = seed_profile_fixture(database_path, _profile_content())
    unaffected = seed_profile_fixture(
        database_path, {**_profile_content(), "tagline": "Unaffected canonical profile"}
    )
    proposal = propose_changeset(
        database_path,
        target_type="profile",
        target_id=target.id,
        patch={"tagline": "Never applied"},
        base_revision=target.revision,
        actor="draft-author",
    )
    with open_connection(database_path) as connection:
        connection.execute("DELETE FROM profiles WHERE id = ?", (target.id,))

    with pytest.raises(InvalidChangesetError, match="target was not found"):
        approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    assert get_profile(database_path, unaffected.id) == unaffected
    with open_connection(database_path) as connection:
        assert connection.execute(
            "SELECT status, approved_at, approved_by FROM changesets WHERE id = ?", (proposal.id,)
        ).fetchone() == ("proposed", None, None)
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (0,)


def test_approval_rolls_back_when_corrupted_canonical_content_fails_validation(
    tmp_path: Path,
) -> None:
    from fiverr_seller_os.changesets import InvalidChangesetError, approve_changeset, propose_changeset
    from fiverr_seller_os.models import get_profile
    from fiverr_seller_os.store import initialize_store, open_connection

    database_path = initialize_store(tmp_path / "state")
    target = seed_profile_fixture(database_path, _profile_content())
    unaffected = seed_profile_fixture(
        database_path, {**_profile_content(), "tagline": "Unaffected canonical profile"}
    )
    proposal = propose_changeset(
        database_path,
        target_type="profile",
        target_id=target.id,
        patch={"tagline": "Never applied"},
        base_revision=target.revision,
        actor="draft-author",
    )
    with open_connection(database_path) as connection:
        connection.execute("UPDATE profiles SET public_content_json = '{}' WHERE id = ?", (target.id,))
        corrupted_before_approval = connection.execute(
            "SELECT public_content_json, revision FROM profiles WHERE id = ?", (target.id,)
        ).fetchone()

    with pytest.raises(InvalidChangesetError, match="profile public content is missing"):
        approve_changeset(database_path, proposal.id, expected_revision=1, actor="seller")

    assert get_profile(database_path, unaffected.id) == unaffected
    with open_connection(database_path) as connection:
        assert connection.execute(
            "SELECT public_content_json, revision FROM profiles WHERE id = ?", (target.id,)
        ).fetchone() == corrupted_before_approval
        assert connection.execute(
            "SELECT status, approved_at, approved_by FROM changesets WHERE id = ?", (proposal.id,)
        ).fetchone() == ("proposed", None, None)
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (0,)


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
