"""Pure deterministic Gig draft preflight for Seller OS v3."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class PackageDraft:
    name: str
    scope: str


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    id: str
    usage_gate: str
    label: str
    uncertainty: str = "unknown"


@dataclass(frozen=True, slots=True)
class GigDraft:
    title: str
    description: str
    tags: tuple[str, ...]
    packages: tuple[PackageDraft, ...]
    requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title is required")
        if not isinstance(self.description, str) or not self.description.strip() or len(self.description) > 1200:
            raise ValueError("description must be 1-1200 characters")
        if not 1 <= len(self.packages) <= 3:
            raise ValueError("packages must contain one to three packages")


@dataclass(frozen=True, slots=True)
class PreflightFinding:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PreflightReport:
    evidence_ids: tuple[str, ...]
    findings: tuple[PreflightFinding, ...]
    manual_review_notes: tuple[str, ...]
    ready_for_human_review: bool


_PATTERNS = (
    ("contact_or_payment_leakage", re.compile(r"(?i)(?:\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|pay by|crypto|paypal|telegram|whatsapp)"), "Remove contact or off-platform payment instructions."),
    ("guarantee", re.compile(r"(?i)\b(?:guarantee|guaranteed|double your revenue|certain results)\b"), "Replace guarantees with a bounded deliverable."),
    ("unsupported_claim", re.compile(r"(?i)\b(?:expert|certified|\d+\s+years|proven results?)\b"), "Support credentials or outcome claims with approved evidence."),
)


def preflight_gig(draft: GigDraft, evidence: tuple[EvidenceRef, ...]) -> PreflightReport:
    findings: list[PreflightFinding] = []
    text = " ".join((draft.title, draft.description, *(tag for tag in draft.tags), *(p.scope for p in draft.packages), *(draft.requirements)))
    for code, pattern, message in _PATTERNS:
        if pattern.search(text):
            findings.append(PreflightFinding(code, message))
    usable = tuple(ref for ref in evidence if ref.usage_gate == "approved")
    if not usable:
        findings.append(PreflightFinding("missing_evidence", "At least one approved evidence reference is required."))
    ids = tuple(ref.id for ref in usable)
    notes = ("Review evidence coverage and current Fiverr rules before copying.",)
    return PreflightReport(ids, tuple(findings), notes, not findings)
