from __future__ import annotations

import ast
import inspect

import pytest


def test_missing_required_facts_are_not_quote_ready() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake("I need an MCP server.")

    assert result.quote_ready is False
    assert result.missing_questions == (
        "What outcome do you want this work to achieve?",
        "What is your current process?",
        "What inputs will the solution receive?",
        "What output do you expect?",
    )


def test_adequate_normal_request_has_a_structured_quote_ready_result() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake(
        "Our goal is to replace a manual workflow. Currently staff export a CSV from our database. "
        "The server will receive CSV inputs and generate a weekly report as its output."
    )

    assert result.quote_ready is True
    assert result.missing_questions == ()
    assert result.technical_comfort == "unknown"
    assert result.delivery_profile.documentation_level == "standard"
    assert result.scope_assumptions == (
        "The quoted scope covers only the described workflow and interfaces.",
    )


def test_generic_keywords_do_not_count_as_required_fact_evidence() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake("I want a report from my data, not sure how.")

    assert result.quote_ready is False
    assert "What outcome do you want this work to achieve?" in result.missing_questions
    assert "What is your current process?" in result.missing_questions
    assert result.scope_assumptions == ()


def test_technical_terms_without_self_identification_remain_unknown() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake(
        "Goal: reduce handoffs. Current process: staff manually send updates. "
        "Inputs: rows from a spreadsheet. Expected output: a daily email. "
        "Could this use an MCP server, API, or repo?"
    )

    assert result.technical_comfort == "unknown"
    assert result.delivery_profile.documentation_level == "standard"


def test_self_identified_developer_is_technical() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake("I am a developer and can run the CLI to configure this.")

    assert result.technical_comfort == "technical"


def test_credential_dependent_request_warns_about_customer_owned_least_privilege_access() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake(
        "Goal: automate invoice processing. Current process: staff copy invoices from a spreadsheet. "
        "Inputs: spreadsheet rows through an API integration. Expected output: a processed invoice report. "
        "The service will require credentials configured by the customer."
    )

    assert "Customer-owned, least-privilege access is required; do not provide passwords, cookies, or tokens." in result.risks
    assert "Customers own their services" in result.delivery_profile.credential_policy
    assert "never provide or store passwords, cookies, or tokens" in result.delivery_profile.credential_policy


def test_obvious_secret_submission_is_rejected_without_echoing_it() -> None:
    from fiverr_seller_os.intake import SensitiveBuyerInputError, analyze_buyer_intake

    submitted_secret = "sk_live_DO_NOT_RETAIN_1234567890"

    with pytest.raises(SensitiveBuyerInputError) as raised:
        analyze_buyer_intake(f"Please use my API key: {submitted_secret}")

    assert submitted_secret not in str(raised.value)


def test_password_assignment_written_in_plain_language_is_rejected() -> None:
    from fiverr_seller_os.intake import SensitiveBuyerInputError, analyze_buyer_intake

    submitted_secret = "do-not-retain-this-password"

    with pytest.raises(SensitiveBuyerInputError) as raised:
        analyze_buyer_intake(f"My password is {submitted_secret}")

    assert submitted_secret not in str(raised.value)


@pytest.mark.parametrize(
    "submission",
    (
        "Authorization: Basic dXNlcjpwYXNzd29yZA==",
        "AWS secret access key: AKIAIOSFODNN7EXAMPLE",
        "Google API key: AIzaSyDUMMYKEYWITHENOUGHCHARACTERS123456",
        "OpenAI API key: sk-proj-DO_NOT_RETAIN_1234567890",
    ),
)
def test_obvious_provider_or_basic_credentials_are_rejected_without_echoing(submission: str) -> None:
    from fiverr_seller_os.intake import SensitiveBuyerInputError, analyze_buyer_intake

    with pytest.raises(SensitiveBuyerInputError) as raised:
        analyze_buyer_intake(submission)

    assert submission not in str(raised.value)


def test_public_key_reference_is_not_rejected() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    result = analyze_buyer_intake(
        "Goal: verify signatures. Current process: the app verifies webhooks. "
        "Inputs: signed webhook payloads. Expected output: verification status. "
        "Use the published public key pk_live_1234567890ABCDE."
    )

    assert result.quote_ready is True


def test_same_input_produces_an_equal_derived_result() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    request = (
        "Goal: reduce support work. Current process: staff triage emails manually. "
        "Inputs: support emails. Expected output: a daily summary."
    )

    assert analyze_buyer_intake(request) == analyze_buyer_intake(request)


def test_intake_analysis_has_no_persistence_imports() -> None:
    import fiverr_seller_os.intake as intake

    tree = ast.parse(inspect.getsource(intake))
    imported_modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported_modules.isdisjoint({"sqlite3", "store", "pathlib"})


def test_result_does_not_retain_or_return_the_buyer_raw_text() -> None:
    from fiverr_seller_os.intake import analyze_buyer_intake

    raw_request = (
        "Goal: reduce support work. Current process: staff triage email manually. "
        "Inputs: support emails. Expected output: a daily summary. "
        "UNIQUE_BUYER_WORDING_7821"
    )

    result = analyze_buyer_intake(raw_request)

    assert "UNIQUE_BUYER_WORDING_7821" not in repr(result)
    assert not hasattr(result, "request")
    assert not hasattr(result.delivery_profile, "source_text")
