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
                "affected_services": hyp.get("affected_services", []),
                "confidence": hyp.get("confidence", 0.7),
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
            }
        )

    return adrs


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
