from __future__ import annotations

import pytest

from fiverr_seller_os.studio import EvidenceRef, GigDraft, PackageDraft, preflight_gig


def _draft(**changes):
    values = {
        "title": "I will build a local Python workflow",
        "description": "I will build a small Python workflow from your documented requirements.",
        "tags": ("python", "automation"),
        "packages": (PackageDraft("Starter", "One local workflow"),),
        "requirements": ("A written description of the desired workflow",),
    }
    values.update(changes)
    return GigDraft(**values)


def test_preflight_is_deterministic_and_accepts_approved_evidence():
    draft = _draft()
    evidence = (EvidenceRef("ev-1", "approved", "Local workflow demo", "low"),)

    first = preflight_gig(draft, evidence)
    second = preflight_gig(draft, evidence)

    assert first == second
    assert first.evidence_ids == ("ev-1",)
    assert first.findings == ()
    assert first.ready_for_human_review is True


def test_preflight_flags_unsupported_claim_when_no_approved_evidence_exists():
    draft = _draft(description="I am an expert with 10 years of proven results and certified delivery.")

    report = preflight_gig(draft, (EvidenceRef("ev-1", "needs_review", "Unreviewed demo"),))

    assert "unsupported_claim" in {finding.code for finding in report.findings}
    assert "missing_evidence" in {finding.code for finding in report.findings}
    assert report.ready_for_human_review is False
    assert report.evidence_ids == ()


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Message me at seller@example.com and pay by crypto.", "contact_or_payment_leakage"),
        ("I guarantee your revenue will double.", "guarantee"),
    ],
)
def test_preflight_flags_contact_payment_and_guarantee_language(text, code):
    report = preflight_gig(_draft(description=text), ())

    assert code in {finding.code for finding in report.findings}


def test_draft_enforces_description_and_package_limits():
    with pytest.raises(ValueError, match="1200"):
        _draft(description="x" * 1201)
    with pytest.raises(ValueError, match="three"):
        _draft(
            packages=(
                PackageDraft("One", "x"),
                PackageDraft("Two", "x"),
                PackageDraft("Three", "x"),
                PackageDraft("Four", "x"),
            )
        )


def test_preflight_does_not_call_network_or_retain_external_content():
    report = preflight_gig(
        _draft(),
        (EvidenceRef("ev-1", "blocked", "Private source", "high"),),
    )

    assert report.evidence_ids == ()
    assert report.manual_review_notes
    assert all("Private source" not in note for note in report.manual_review_notes)


def test_preflight_excludes_approved_but_unusable_evidence():
    report = preflight_gig(
        _draft(),
        (EvidenceRef("ev-private", "approved", "private", "low", "private", "observed"),),
    )
    assert report.evidence_ids == ()
    assert any(finding.code == "missing_evidence" for finding in report.findings)


def test_draft_limits_tags_and_requires_nonempty_package_fields():
    with pytest.raises(ValueError, match="tags"):
        _draft(tags=("one", "two", "three", "four", "five", "six"))
    with pytest.raises(ValueError, match="package"):
        _draft(packages=(PackageDraft("", "scope"),))
