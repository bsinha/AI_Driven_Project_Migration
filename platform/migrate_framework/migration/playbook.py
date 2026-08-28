"""Stage 8 playbook — operational migration guide tasks."""

from __future__ import annotations

from typing import Any

from migrate_framework.models import EvidenceItem, new_id


PLAYBOOK_TEMPLATE: list[dict[str, str]] = [
    {
        "category": "preparation",
        "task": "Validate discovery evidence against production topology",
        "owner": "platform-team",
    },
    {
        "category": "preparation",
        "task": "Establish feature flags / strangler routing in API gateway",
        "owner": "platform-team",
    },
    {
        "category": "data",
        "task": "Export shared database schemas and document cross-service FKs",
        "owner": "data-team",
    },
    {
        "category": "data",
        "task": "Create per-bounded-context migration scripts with rollback",
        "owner": "data-team",
    },
    {
        "category": "implementation",
        "task": "Scaffold target bounded context service(s) from migration plan",
        "owner": "feature-team",
    },
    {
        "category": "implementation",
        "task": "Implement anti-corruption layer for legacy REST clients",
        "owner": "feature-team",
    },
    {
        "category": "testing",
        "task": "Run contract tests against legacy OpenAPI specs",
        "owner": "qa-team",
    },
    {
        "category": "testing",
        "task": "Execute load tests on consolidated endpoints",
        "owner": "qa-team",
    },
    {
        "category": "cutover",
        "task": "Enable shadow traffic to new context services",
        "owner": "platform-team",
    },
    {
        "category": "cutover",
        "task": "Progressive traffic shift with monitoring dashboards",
        "owner": "platform-team",
    },
    {
        "category": "decommission",
        "task": "Archive legacy service databases after retention period",
        "owner": "data-team",
    },
    {
        "category": "decommission",
        "task": "Remove legacy deployments from docker-compose / K8s manifests",
        "owner": "platform-team",
    },
]


def build_playbook(
    phases: list[dict[str, Any]],
    adrs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate playbook tasks for stage 8 execution."""
    tasks: list[dict[str, Any]] = []

    for template in PLAYBOOK_TEMPLATE:
        tasks.append(
            {
                "id": new_id("task"),
                "category": template["category"],
                "task": template["task"],
                "owner": template["owner"],
                "status": "pending",
                "phase": None,
            }
        )

    for phase in phases:
        for task_name in phase.get("tasks", []):
            tasks.append(
                {
                    "id": new_id("task"),
                    "category": "phase-specific",
                    "task": task_name,
                    "owner": "feature-team",
                    "status": "pending",
                    "phase": phase.get("phase"),
                    "context": phase.get("name"),
                }
            )

    if adrs:
        tasks.append(
            {
                "id": new_id("task"),
                "category": "governance",
                "task": f"Review and approve {len(adrs)} ADRs with architecture board",
                "owner": "architecture",
                "status": "pending",
                "phase": None,
            }
        )

    return tasks


def playbook_to_evidence(tasks: list[dict[str, Any]]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            type="playbook_task",
            source="playbook",
            subject=task["task"],
            attributes=task,
            tags=["playbook", task.get("category", "")],
        )
        for task in tasks
    ]
