"""Phased migration plan generation."""

from __future__ import annotations

from typing import Any

from migrate_framework.models import EvidenceItem, Landscape, new_id


def plan_migration(
    adrs: list[dict[str, Any]],
    landscape: Landscape | None,
    diagnosis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a phased migration plan from ADRs and landscape."""
    phases: list[dict[str, Any]] = []

    if landscape and landscape.target_bounded_contexts:
        for idx, ctx in enumerate(landscape.target_bounded_contexts, start=1):
            related_adrs = [a for a in adrs if a.get("target_context") == ctx.name]
            phases.append(
                {
                    "id": new_id("phase"),
                    "phase": idx,
                    "name": f"Extract {ctx.name}",
                    "objective": f"Consolidate {len(ctx.services)} services into {ctx.name} bounded context.",
                    "services": ctx.services,
                    "duration_weeks": _estimate_duration(len(ctx.services)),
                    "dependencies": _phase_dependencies(idx, landscape.target_bounded_contexts),
                    "adrs": [a["title"] for a in related_adrs],
                    "tasks": _phase_tasks(ctx.name, ctx.services),
                    "risk": _phase_risk(ctx.services, diagnosis or {}),
                }
            )
    else:
        for idx, adr in enumerate(adrs[:4], start=1):
            phases.append(
                {
                    "id": new_id("phase"),
                    "phase": idx,
                    "name": adr.get("title", f"Phase {idx}"),
                    "objective": adr.get("decision", ""),
                    "services": adr.get("affected_services", []),
                    "duration_weeks": 4,
                    "dependencies": [] if idx == 1 else [idx - 1],
                    "adrs": [adr["title"]],
                    "tasks": ["Analyze", "Design", "Implement", "Validate"],
                    "risk": "medium",
                }
            )

    phases.append(
        {
            "id": new_id("phase"),
            "phase": len(phases) + 1,
            "name": "Decommission legacy services",
            "objective": "Retire strangler-routed legacy endpoints and shared databases.",
            "services": [],
            "duration_weeks": 2,
            "dependencies": list(range(1, len(phases) + 1)),
            "adrs": [],
            "tasks": ["Traffic drain", "Archive databases", "Remove deployments"],
            "risk": "low",
        }
    )

    return phases


def _estimate_duration(service_count: int) -> int:
    if service_count <= 3:
        return 4
    if service_count <= 5:
        return 6
    return 8


def _phase_dependencies(phase_num: int, contexts: list) -> list[int]:
    if phase_num == 1:
        return []
    if phase_num == 2:
        return [1]
    return [phase_num - 1]


def _phase_tasks(context_name: str, services: list[str]) -> list[str]:
    return [
        f"Map {context_name} aggregate roots",
        f"Design unified API for {len(services)} services",
        "Create schema migration scripts",
        "Implement anti-corruption layers",
        "Run parallel-run validation",
        "Cut over traffic via gateway routes",
    ]


def _phase_risk(services: list[str], diagnosis: dict[str, Any]) -> str:
    shared = diagnosis.get("database_sharing", {})
    for db, svcs in shared.items():
        if any(s in svcs for s in services):
            return "high"
    return "medium"


def phases_to_evidence(phases: list[dict[str, Any]]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            type="migration_phase",
            source="planner",
            subject=phase["name"],
            attributes=phase,
            tags=["migration", "phase"],
        )
        for phase in phases
    ]
