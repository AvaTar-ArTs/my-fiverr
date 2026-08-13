"""Metadata-only evidence cards for the v3 local Studio layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
import re
import sqlite3


class EvidenceValidationError(ValueError):
    """Evidence metadata is malformed or unsafe."""


class EvidenceApprovalError(ValueError):
    """Evidence cannot be approved for public drafting."""


@dataclass(frozen=True, slots=True)
class EvidenceCard:
    id: int
    source_ref: str
    source_digest: str | None
    title: str
    observed_summary: str
    epistemic_state: str
    usage_gate: str
    rights_state: str
    uncertainty: str
    reviewer: str | None
    reviewed_at: str | None
    created_at: str


_EPISTEMIC_STATES = frozenset({"observed", "inherited", "inferred", "declared", "draft", "blocked"})
_USAGE_GATES = frozenset({"approved", "needs_review", "blocked"})
_RIGHTS_STATES = frozenset({"owned", "permission_needed", "private", "unknown"})
_SENSITIVE_PATH = re.compile(r"(?i)(?:password|token|secret|cookie|credential|api[ _-]?key|access[ _-]?token|client[ _-]?secret)")
_SENSITIVE_ASSIGNMENT = re.compile(r"(?i)\b(?:password|token|secret|cookie|credential|api[ _-]?key|access[ _-]?token|client[ _-]?secret)\s*[:=]")


def _text(value: object, name: str, *, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise EvidenceValidationError(f"{name} must be a non-empty string of at most {limit} characters")
    if _SENSITIVE_ASSIGNMENT.search(value):
        raise EvidenceValidationError(f"{name} must not contain credential-like assignments")
    return value.strip()


def _source_ref(value: object) -> str:
    source = _text(value, "source_ref", limit=1000)
    path = PurePath(source)
    if path.is_absolute() or re.match(r"(?i)^[a-z]:[\\/]|^\\\\", source) or ".." in path.parts or any(_SENSITIVE_PATH.search(part) for part in path.parts):
        raise EvidenceValidationError("source_ref must be relative and non-sensitive")
    return source


def _snapshot(row: tuple[object, ...]) -> EvidenceCard:
    return EvidenceCard(
        id=int(row[0]), source_ref=str(row[1]), source_digest=None if row[2] is None else str(row[2]),
        title=str(row[3]), observed_summary=str(row[4]), epistemic_state=str(row[5]),
        usage_gate=str(row[6]), rights_state=str(row[7]), uncertainty=str(row[8]),
        reviewer=None if row[9] is None else str(row[9]), reviewed_at=None if row[10] is None else str(row[10]),
        created_at=str(row[11]),
    )


_SELECT = "SELECT id, source_ref, source_digest, title, observed_summary, epistemic_state, usage_gate, rights_state, uncertainty, reviewer, reviewed_at, created_at FROM evidence_cards"


def add_evidence_card(
    connection: sqlite3.Connection,
    source_ref: str,
    title: str,
    observed_summary: str,
    epistemic_state: str,
    usage_gate: str,
    rights_state: str,
    uncertainty: str,
    source_digest: str | None = None,
) -> EvidenceCard:
    source = _source_ref(source_ref)
    clean_title = _text(title, "title", limit=200)
    clean_summary = _text(observed_summary, "observed_summary", limit=2000)
    if epistemic_state not in _EPISTEMIC_STATES or usage_gate not in _USAGE_GATES or rights_state not in _RIGHTS_STATES:
        raise EvidenceValidationError("invalid epistemic, usage, or rights state")
    clean_uncertainty = _text(uncertainty, "uncertainty", limit=200)
    if source_digest is not None:
        source_digest = _text(source_digest, "source_digest", limit=200)
    if usage_gate == "approved":
        raise EvidenceValidationError("new evidence must begin needs_review or blocked")
    cursor = connection.execute(
        "INSERT INTO evidence_cards (source_ref, source_digest, title, observed_summary, epistemic_state, usage_gate, rights_state, uncertainty) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (source, source_digest, clean_title, clean_summary, epistemic_state, usage_gate, rights_state, clean_uncertainty),
    )
    row = connection.execute(_SELECT + " WHERE id = ?", (cursor.lastrowid,)).fetchone()
    assert row is not None
    return _snapshot(row)


def list_evidence_cards(connection: sqlite3.Connection) -> tuple[EvidenceCard, ...]:
    rows = connection.execute(_SELECT + " ORDER BY id").fetchall()
    return tuple(_snapshot(row) for row in rows)


def usable_evidence(connection: sqlite3.Connection) -> tuple[EvidenceCard, ...]:
    return tuple(
        card for card in list_evidence_cards(connection)
        if card.usage_gate == "approved" and card.rights_state == "owned" and card.epistemic_state in {"observed", "inherited"}
    )


def review_evidence_card(connection: sqlite3.Connection, card_id: int, *, reviewer: str, usage_gate: str) -> EvidenceCard:
    if not isinstance(card_id, int) or isinstance(card_id, bool) or card_id < 1:
        raise EvidenceValidationError("card_id must be a positive integer")
    clean_reviewer = _text(reviewer, "reviewer", limit=200)
    if usage_gate not in _USAGE_GATES:
        raise EvidenceValidationError("invalid usage_gate")
    connection.execute("SAVEPOINT evidence_review")
    try:
        row = connection.execute(_SELECT + " WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise EvidenceValidationError("evidence card was not found")
        card = _snapshot(row)
        if card.usage_gate != "needs_review":
            raise EvidenceValidationError("evidence card is not awaiting review")
        if usage_gate == "approved" and (card.rights_state != "owned" or card.epistemic_state not in {"observed", "inherited"}):
            raise EvidenceApprovalError("only owned observed/inherited evidence can be approved")
        update = connection.execute(
            "UPDATE evidence_cards SET usage_gate = ?, reviewer = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ? AND usage_gate = 'needs_review'",
            (usage_gate, clean_reviewer, card_id),
        )
        if update.rowcount != 1:
            raise EvidenceValidationError("evidence card changed during review")
        connection.execute(
            "INSERT INTO audit_events (event_type, entity_type, entity_id, event_data_json) VALUES ('evidence_reviewed', 'evidence_card', ?, json_object('reviewer', ?, 'usage_gate', ?))",
            (card_id, clean_reviewer, usage_gate),
        )
    except BaseException:
        connection.execute("ROLLBACK TO evidence_review")
        connection.execute("RELEASE evidence_review")
        raise
    connection.execute("RELEASE evidence_review")
    row = connection.execute(_SELECT + " WHERE id = ?", (card_id,)).fetchone()
    assert row is not None
    return _snapshot(row)
