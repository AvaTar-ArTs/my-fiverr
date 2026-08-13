"""Deterministic, local-only buyer-intake analysis.

This module deliberately does not persist input, call a network service, or
attempt to contact Fiverr.  Its result contains only derived guidance, never
the buyer's submitted text.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


TechnicalComfort = Literal["nontechnical", "mixed", "technical", "unknown"]


class SensitiveBuyerInputError(ValueError):
    """Raised when buyer intake appears to include an actual credential."""


@dataclass(frozen=True, slots=True)
class DeliveryProfile:
    """Derived handoff guidance with no buyer-provided content."""

    technical_comfort: TechnicalComfort
    documentation_level: Literal["guided", "standard", "technical"]
    setup_guidance: bool
    credential_policy: str


@dataclass(frozen=True, slots=True)
class BuyerIntakeAnalysis:
    """Safe, typed outcome of analysing one unpersisted buyer request."""

    missing_questions: tuple[str, ...]
    risks: tuple[str, ...]
    scope_assumptions: tuple[str, ...]
    technical_comfort: TechnicalComfort
    quote_ready: bool
    delivery_profile: DeliveryProfile


_MISSING_FACT_QUESTIONS = (
    ("outcome", "What outcome do you want this work to achieve?"),
    ("process", "What is your current process?"),
    ("inputs", "What inputs will the solution receive?"),
    ("output", "What output do you expect?"),
)
_CREDENTIAL_POLICY = (
    "Customers own their services and must use least-privilege access; never provide or store passwords, "
    "cookies, or tokens."
)
_CREDENTIAL_RISK = (
    "Customer-owned, least-privilege access is required; do not provide passwords, cookies, or tokens."
)
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[ _-]?key|client[ _-]?secret|access[ _-]?token|password|token|secret|cookie)"
    r"\s*(?:[:=]|\bis\b)\s*\S+"
)
_BEARER_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S+")
_BASIC_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*:\s*basic\s+[A-Za-z0-9+/]{8,}={0,2}\b")
_OPENAI_PRIVATE_KEY = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b", re.IGNORECASE)
_GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")
_AWS_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\baws\s+(?:secret\s+)?access\s+key\s*[:=]\s*(?:AKIA|ASIA)[0-9A-Z]{12,}\b"
)
_COMMON_PRIVATE_TOKEN = re.compile(r"\b(?:ghp|xox[baprs])_[A-Za-z0-9_-]{12,}\b", re.IGNORECASE)


def analyze_buyer_intake(request: str) -> BuyerIntakeAnalysis:
    """Return deterministic quote-readiness guidance for a buyer's request.

    The caller remains responsible for retaining (or discarding) the raw
    request.  This function returns no raw request text or extracted values.
    """
    if not isinstance(request, str):
        raise TypeError("request must be a string")
    if _appears_to_contain_secret(request):
        raise SensitiveBuyerInputError(
            "Sensitive credential-like input was rejected. Do not provide passwords, cookies, or tokens."
        )
    normalized = request.casefold()
    missing_questions = tuple(
        question for fact, question in _MISSING_FACT_QUESTIONS if not _has_fact(normalized, fact)
    )
    technical_comfort = _technical_comfort(normalized)
    risks = (_CREDENTIAL_RISK,) if _mentions_credentials(normalized) else ()
    return BuyerIntakeAnalysis(
        missing_questions=missing_questions,
        risks=risks,
        scope_assumptions=(
            ("The quoted scope covers only the described workflow and interfaces.",)
            if not missing_questions
            else ()
        ),
        technical_comfort=technical_comfort,
        quote_ready=not missing_questions,
        delivery_profile=_delivery_profile(technical_comfort),
    )


def _has_fact(text: str, fact: str) -> bool:
    if fact == "outcome":
        return bool(
            re.search(
                r"\b(?:goal|want|need|aim|achieve)\b\s*(?:is\s+)?(?:to\s+|:\s*)?"
                r"(?:automate|reduce|replace|improve|create|build|send|generate|track|verify)\b\s+\w+",
                text,
            )
        )
    if fact == "process":
        return bool(
            re.search(
                r"\b(?:current(?:ly)?|today|at present)\b[^.]{0,100}\b(?:manual(?:ly)?|staff|team|we|i|app|process|workflow|export|copy|send|review|triage|use|work)\b",
                text,
            )
            or re.search(
                r"\b(?:staff|team|we|i)\b[^.]{0,60}\b(?:manually|currently|today|export|copy|send|review|triage)\b",
                text,
            )
        )
    if fact == "inputs":
        return bool(
            re.search(
                r"\b(?:inputs?|data|rows?|records?|files?|csv|json|spreadsheet|database|api|emails?|webhooks?|documents?)\b",
                text,
            )
            or re.search(r"\bfrom\s+(?:the\s+)?(?:[a-z0-9_-]+\s+)?(?:data|database|api|csv|file|spreadsheet|email|webhook)\b", text)
        )
    if fact == "output":
        return bool(
            re.search(
                r"\b(?:output|deliver(?:able|y)?|report|summary|dashboard|email|csv|json|pdf|file|notification|status)\b",
                text,
            )
        )
    raise ValueError(f"unknown required fact: {fact}")


def _technical_comfort(text: str) -> TechnicalComfort:
    if any(term in text for term in ("i am not technical", "nontechnical", "no-code", "no code", "not a developer")):
        return "nontechnical"
    if re.search(r"\b(?:i am|i'm|we are|our team is|as a)\s+(?:a\s+)?(?:developer|engineer|programmer)\b", text):
        return "technical"
    if re.search(r"\b(?:can|comfortable to|able to)\s+(?:run|use|configure)\s+(?:the\s+)?(?:terminal|cli|command line)\b", text):
        return "technical"
    if re.search(r"\b(?:have|own)\s+(?:a\s+)?(?:repo|repository|codebase)\b[^.]{0,80}\b(?:can|will)\s+configure\b", text):
        return "technical"
    if re.search(
        r"\b(?:build|implement|develop)\s+(?:a\s+)?(?:python|typescript|javascript)\s+(?:mcp\s+)?(?:server|integration|service)\b",
        text,
    ):
        return "technical"
    return "unknown"


def _mentions_credentials(text: str) -> bool:
    return any(term in text for term in ("credential", "credentials", "authentication", "api access", "oauth"))


def _appears_to_contain_secret(text: str) -> bool:
    return bool(
        _CREDENTIAL_ASSIGNMENT.search(text)
        or _BEARER_AUTHORIZATION.search(text)
        or _BASIC_AUTHORIZATION.search(text)
        or _OPENAI_PRIVATE_KEY.search(text)
        or _GOOGLE_API_KEY.search(text)
        or _AWS_SECRET_ASSIGNMENT.search(text)
        or _COMMON_PRIVATE_TOKEN.search(text)
    )


def _delivery_profile(comfort: TechnicalComfort) -> DeliveryProfile:
    if comfort == "technical":
        level: Literal["guided", "standard", "technical"] = "technical"
        setup_guidance = False
    elif comfort == "nontechnical":
        level = "guided"
        setup_guidance = True
    else:
        level = "standard"
        setup_guidance = True
    return DeliveryProfile(
        technical_comfort=comfort,
        documentation_level=level,
        setup_guidance=setup_guidance,
        credential_policy=_CREDENTIAL_POLICY,
    )
