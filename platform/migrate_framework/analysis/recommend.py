"""Architecture Decision Record (ADR) generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from migrate_framework.models import EvidenceItem, new_id


def recommend(
    hypotheses: list[dict[str, Any]],
    diagnosis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate ADRs from ranked hypotheses and diagnosis."""
    adrs: list[dict[str, Any]] = []
    ranked = sorted(hypotheses, key=lambda h: h.get("confidence", 0), reverse=True)

    for idx, hyp in enumerate(ranked[:5], start=1):
        affected = hyp.get("affected_services", [])
        mandatory = idx <= 3 or hyp.get("confidence", 0) >= 0.75
        adrs.append(
            {
                "id": new_id("adr"),
                "number": idx,
                "title": f"ADR-{idx:03d}: {hyp['title']}",
                "status": "proposed",
                "date": datetime.now(timezone.utc).isoformat(),
                "context": hyp.get("rationale", ""),
                "decision": hyp.get("description", ""),
                "consequences": _consequences(hyp, diagnosis),
                "target_context": hyp.get("target_context"),
                "affected_services": affected,
                "confidence": hyp.get("confidence", 0.7),
                "mandatory": mandatory,
                "blocks_gate": mandatory,
                "as_is_summary": _as_is_summary(affected, diagnosis),
                "to_be_preview": _to_be_preview(hyp.get("target_context"), affected),
                "benefit_if_accepted": _benefit_if_accepted(hyp, diagnosis),
                "risk_if_rejected": _risk_if_rejected(hyp, mandatory),
            }
        )

    if diagnosis.get("database_sharing"):
        adrs.append(
            {
                "id": new_id("adr"),
                "number": len(adrs) + 1,
                "title": f"ADR-{len(adrs)+1:03d}: Database per bounded context",
                "status": "proposed",
                "date": datetime.now(timezone.utc).isoformat(),
                "context": "Multiple services share logical databases.",
                "decision": (
                    "Assign one schema/database per bounded context; use views or "
                    "read replicas during transition."
                ),
                "consequences": [
                    "Requires data migration scripts",
                    "Eliminates cross-service FK coupling",
                    "Improves team autonomy",
                ],
                "target_context": "Cross-cutting",
                "affected_services": [],
                "confidence": 0.9,
                "mandatory": True,
                "blocks_gate": True,
                "as_is_summary": "Shared databases detected across services.",
                "to_be_preview": "One database/schema per bounded context.",
                "benefit_if_accepted": "Removes shared-database coupling smell.",
                "risk_if_rejected": "Data coupling remains; recommend gate blocked for consolidation phases.",
            }
        )

    return adrs


def _as_is_summary(affected: list[str], diagnosis: dict[str, Any]) -> str:
    if not affected:
        return "Cross-cutting architectural constraint."
    sharing = diagnosis.get("database_sharing", {})
    shared = [db for db, svcs in sharing.items() if any(s in svcs for s in affected)]
    if shared:
        return f"{len(affected)} service(s); shared DB: {', '.join(shared)}"
    return f"{len(affected)} granular service(s) in current estate."


def _to_be_preview(target_context: str | None, affected: list[str]) -> str:
    ctx = target_context or "Bounded context"
    slug = str(ctx).lower().replace(" ", "-")
    return f"Consolidate into **{ctx}** (`target-contexts/{slug}/`) with unified API surface."


def _benefit_if_accepted(hypothesis: dict[str, Any], diagnosis: dict[str, Any]) -> str:
    n = len(hypothesis.get("affected_services", []))
    smells = len(diagnosis.get("smells", []))
    parts = []
    if n:
        parts.append(f"Reduces deployable units by consolidating {n} service(s)")
    if smells:
        parts.append(f"Addresses architectural smells ({smells} detected in estate)")
    return "; ".join(parts) or "Improves domain alignment and team ownership."


def _risk_if_rejected(hypothesis: dict[str, Any], mandatory: bool) -> str:
    if mandatory:
        return "Mandatory ADR — rejection blocks migration plan approval for this scope."
    return "Optional ADR — may defer to a later migration phase."


def _consequences(hypothesis: dict[str, Any], diagnosis: dict[str, Any]) -> list[str]:
    consequences = [
        f"Consolidates {len(hypothesis.get('affected_services', []))} services",
        "Requires API versioning during transition",
    ]
    if diagnosis.get("smells"):
        consequences.append(f"Addresses {len(diagnosis['smells'])} detected smells")
    return consequences


def adrs_to_evidence(adrs: list[dict[str, Any]]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            type="architecture_decision",
            source="recommend",
            subject=adr["title"],
            confidence=adr.get("confidence", 0.8),
            attributes=adr,
            tags=["adr", adr.get("target_context", "")],
        )
        for adr in adrs
    ]
