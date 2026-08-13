from __future__ import annotations

import sqlite3

import pytest

from fiverr_seller_os.evidence import (
    EvidenceApprovalError,
    EvidenceValidationError,
    add_evidence_card,
    list_evidence_cards,
    review_evidence_card,
    usable_evidence,
)
from fiverr_seller_os.store import initialize_store, open_connection


def _db(tmp_path):
    return initialize_store(tmp_path / "state")


def test_evidence_card_is_metadata_only_and_immutable(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        card = add_evidence_card(
            connection,
            source_ref="docs/demo.md",
            title="Local MCP demo",
            observed_summary="A synthetic local integration test exists.",
            epistemic_state="observed",
            usage_gate="needs_review",
            rights_state="owned",
            uncertainty="low",
        )
    assert card.source_ref == "docs/demo.md"
    assert card.usage_gate == "needs_review"
    with pytest.raises((AttributeError, TypeError)):
        card.title = "changed"


def test_evidence_rejects_raw_content_credentials_and_unsafe_paths(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        for kwargs in (
            {"source_ref": "/private/source.md"},
            {"source_ref": "C:\\private\\source.md"},
            {"source_ref": "\\\\server\\share\\source.md"},
            {"source_ref": "docs/../secret.md"},
            {"source_ref": "docs/password/source.md"},
            {"source_ref": "docs/source.md", "observed_summary": "password=secret"},
        ):
            with pytest.raises(EvidenceValidationError):
                add_evidence_card(
                    connection,
                    title="x",
                    observed_summary=kwargs.get("observed_summary", "safe summary"),
                    epistemic_state="observed",
                    usage_gate="needs_review",
                    rights_state="owned",
                    uncertainty="low",
                    source_ref=kwargs["source_ref"],
                )


def test_review_is_atomic_and_usable_evidence_is_conservative(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        blocked = add_evidence_card(connection, "docs/inferred.md", "Inferred", "Maybe", "inferred", "needs_review", "owned", "medium")
        good = add_evidence_card(connection, "docs/observed.md", "Observed", "Verified", "observed", "needs_review", "owned", "low")
        with pytest.raises(EvidenceApprovalError):
            review_evidence_card(connection, blocked.id, reviewer="owner", usage_gate="approved")
        approved = review_evidence_card(connection, good.id, reviewer="owner", usage_gate="approved")
        assert approved.usage_gate == "approved"
        assert [item.id for item in usable_evidence(connection)] == [good.id]
        audit = connection.execute("SELECT event_type FROM audit_events WHERE entity_type = 'evidence_card'").fetchall()
        assert [row[0] for row in audit] == ["evidence_reviewed"]


def test_evidence_listing_is_stable_and_review_rejects_unknown_gate(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        add_evidence_card(connection, "b.md", "B", "B", "observed", "needs_review", "owned", "low")
        add_evidence_card(connection, "a.md", "A", "A", "observed", "needs_review", "owned", "low")
        assert [item.source_ref for item in list_evidence_cards(connection)] == ["b.md", "a.md"]
        with pytest.raises(EvidenceValidationError):
            review_evidence_card(connection, 1, reviewer="owner", usage_gate="unknown")


def test_review_rejects_stale_card_without_audit(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        card = add_evidence_card(connection, "stale.md", "Stale", "Summary", "observed", "needs_review", "owned", "low")
        connection.execute("UPDATE evidence_cards SET usage_gate = 'blocked' WHERE id = ?", (card.id,))
        with pytest.raises(EvidenceValidationError, match="awaiting review"):
            review_evidence_card(connection, card.id, reviewer="owner", usage_gate="approved")
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 0


def test_review_rolls_back_when_audit_insert_fails(tmp_path):
    database = _db(tmp_path)
    with open_connection(database) as connection:
        card = add_evidence_card(connection, "rollback.md", "Rollback", "Summary", "observed", "needs_review", "owned", "low")
        connection.execute("CREATE TRIGGER fail_evidence_audit BEFORE INSERT ON audit_events BEGIN SELECT RAISE(ABORT, 'forced audit failure'); END")
        with pytest.raises(sqlite3.IntegrityError, match="forced audit failure"):
            review_evidence_card(connection, card.id, reviewer="owner", usage_gate="approved")
        assert list_evidence_cards(connection)[0].usage_gate == "needs_review"
