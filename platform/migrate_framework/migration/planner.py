"""Phased migration plan generation."""

from __future__ import annotations

from typing import Any

from migrate_framework.models import EvidenceItem, Landscape, new_id


def plan_migration(
    adrs: list[dict[str, Any]],
    landscape: Landscape | None,
    diagnosis: dict[str, Any] | None = None,
    active_scope: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a phased migration plan from ADRs and landscape.

    When *active_scope* is provided, only approved contexts are active phases;
    deferred contexts appear as deferred stubs without blocking execution.
    """
    phases: list[dict[str, Any]] = []
    in_scope_contexts = set(active_scope.get("contexts", [])) if active_scope else None
    deferred_adr_titles = {
        a.get("title") for a in (active_scope or {}).get("deferred_adrs", [])
    }

    if landscape and landscape.target_bounded_contexts:
        active_idx = 0
        for ctx in landscape.target_bounded_contexts:
            related_adrs = [a for a in adrs if a.get("target_context") == ctx.name]
            if in_scope_contexts is not None and ctx.name not in in_scope_contexts:
                if any(a.get("title") in deferred_adr_titles for a in related_adrs) or related_adrs:
                    phases.append(
                        {
                            "id": new_id("phase"),
                            "phase": len(phases) + 1,
                            "name": f"Extract {ctx.name}",
                            "objective": f"Deferred — consolidate {len(ctx.services)} services into {ctx.name}.",
                            "services": ctx.services,
                            "duration_weeks": 0,
                            "dependencies": [],
                            "adrs": [a["title"] for a in related_adrs],
                            "tasks": [],
                            "risk": "deferred",
                            "status": "deferred",
                        }
                    )
                continue

            active_idx += 1
            phases.append(
                {
                    "id": new_id("phase"),
                    "phase": active_idx,
                    "name": f"Extract {ctx.name}",
                    "objective": f"Consolidate {len(ctx.services)} services into {ctx.name} bounded context.",
                    "services": ctx.services,
                    "duration_weeks": _estimate_duration(len(ctx.services)),
                    "dependencies": _phase_dependencies(active_idx, landscape.target_bounded_contexts),
                    "adrs": [a["title"] for a in related_adrs],
                    "tasks": _phase_tasks(ctx.name, ctx.services),
                    "risk": _phase_risk(ctx.services, diagnosis or {}),
                    "status": "active",
                }
            )
    else:
        scope_adrs = active_scope.get("adrs", adrs) if active_scope else adrs[:4]
        for idx, adr in enumerate(scope_adrs, start=1):
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
                    "status": "active",
                }
            )

        for adr in adrs:
            if adr in scope_adrs:
                continue
            phases.append(
                {
                    "id": new_id("phase"),
                    "phase": len(phases) + 1,
                    "name": adr.get("title", "Deferred phase"),
                    "objective": adr.get("decision", ""),
                    "services": adr.get("affected_services", []),
                    "duration_weeks": 0,
                    "dependencies": [],
                    "adrs": [adr["title"]],
                    "tasks": [],
                    "risk": "deferred",
                    "status": "deferred",
                }
            )

    active_phases = [p for p in phases if p.get("status") != "deferred"]
    if active_phases:
        phases.append(
            {
                "id": new_id("phase"),
                "phase": len(phases) + 1,
                "name": "Decommission legacy services",
                "objective": "Retire strangler-routed legacy endpoints and shared databases.",
                "services": [],
                "duration_weeks": 2,
                "dependencies": [p["phase"] for p in active_phases],
                "adrs": [],
                "tasks": ["Traffic drain", "Archive databases", "Remove deployments"],
                "risk": "low",
                "status": "active",
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
