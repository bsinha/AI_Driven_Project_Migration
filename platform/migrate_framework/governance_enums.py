"""Governance enums and constants (no dependency on other framework modules)."""

from __future__ import annotations

from enum import Enum

CONFIDENCE_APPROVAL_THRESHOLD = 0.7
ESCALATION_REJECTION_THRESHOLD = 3

GATE_REASON_CODES: list[str] = [
    "insufficient_evidence",
    "wrong_boundary",
    "risk_too_high",
    "sme_disagreement",
    "scope_defer",
    "executive_waiver",
    "low_confidence",
    "other",
]


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
