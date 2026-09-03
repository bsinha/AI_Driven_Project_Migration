"""Governance enums and constants (no dependency on other framework modules)."""

from __future__ import annotations

from enum import Enum

CONFIDENCE_APPROVAL_THRESHOLD = 0.7
ESCALATION_REJECTION_THRESHOLD = 3

GATE_APPROVE_REASON_CODES: list[str] = [
    "evidence_sufficient",
    "scope_accepted",
    "sme_validated",
    "consistent_with_prior_stages",
    "acceptable_risk",
    "other",
]

GATE_REJECT_REASON_CODES: list[str] = [
    "insufficient_evidence",
    "wrong_boundary",
    "risk_too_high",
    "sme_disagreement",
    "low_confidence",
    "inconsistent_with_discovery",
    "other",
]

GATE_WAIVE_REASON_CODES: list[str] = [
    "executive_waiver",
    "scope_defer",
    "acceptable_risk",
    "time_pressure",
    "other",
]

GATE_REASON_CODES: list[str] = sorted(
    set(GATE_APPROVE_REASON_CODES + GATE_REJECT_REASON_CODES + GATE_WAIVE_REASON_CODES)
)

ITEM_DECISION_STATUSES: list[str] = ["approved", "deferred", "rejected"]
SMELL_DECISION_STATUSES: list[str] = ["open", "accepted", "deferred"]
ITEM_TYPES: list[str] = ["adr", "bounded_context", "smell", "plan_phase"]


class GateDecisionStatus(str, Enum):
    """Human gate decision lifecycle."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    WAIVED = "waived"


class GateDecisionAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    WAIVE = "waive"
    RESET = "reset"
