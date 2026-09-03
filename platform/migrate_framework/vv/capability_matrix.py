"""Verification & validation — capability traceability matrix."""

from __future__ import annotations

from typing import Any

from migrate_framework.models import EvidenceItem, MigrationProject, new_id


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def _as_is_from_evidence(evidence: list[EvidenceItem]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in evidence:
        if item.type != "api_operation":
            continue
        op = item.attributes.get("operation") or item.attributes.get("method") or "—"
        path = item.attributes.get("path") or item.subject
        service = item.attributes.get("service") or item.attributes.get("owner_service") or "unknown"
        key = f"{service}:{op}:{path}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "id": item.id,
                "capability": f"{op} {path}".strip(),
                "as_is_service": service,
                "as_is_endpoint": path,
                "evidence_ref": item.id,
                "confidence": item.confidence,
            }
        )

    # Fallback: service inventory when no OpenAPI operations parsed
    if not rows:
        for item in evidence:
            if item.type != "service":
                continue
            rows.append(
                {
                    "id": new_id("cap"),
                    "capability": f"Service surface: {item.subject}",
                    "as_is_service": item.subject,
                    "as_is_endpoint": "—",
                    "evidence_ref": item.id,
                    "confidence": item.confidence,
                }
            )

    return rows


def _to_be_mapping(project: MigrationProject) -> dict[str, str]:
    from migrate_framework.pipeline.scope import resolve_active_scope

    mapping: dict[str, str] = {}
    scope = resolve_active_scope(project)
    for adr in scope.get("adrs", []):
        ctx = adr.get("target_context", "")
        for svc in adr.get("affected_services", []):
            mapping[str(svc)] = ctx

    for phase in project.metadata.get("plan", []):
        if phase.get("status") == "deferred":
            continue
        context = phase.get("name", "").replace("Extract ", "")
        for svc in phase.get("services", []):
            mapping[str(svc)] = context
    return mapping


def _service_deferred(project: MigrationProject, service: str) -> bool:
    from migrate_framework.pipeline.scope import deferred_adrs, resolve_active_scope

    scope = resolve_active_scope(project)
    if service in scope.get("services", []):
        return False
    for adr in deferred_adrs(project):
        if service in adr.get("affected_services", []):
            return True
    return False


def build_capability_matrix(project: MigrationProject) -> list[dict[str, Any]]:
    """AS-IS capabilities mapped to TO-BE bounded contexts."""
    as_is_rows = _as_is_from_evidence(project.evidence)
    to_be_map = _to_be_mapping(project)
    playbook = project.metadata.get("playbook", [])
    contract_tasks = {
        t.get("context"): t.get("id")
        for t in playbook
        if "contract" in str(t.get("task", "")).lower()
    }

    matrix: list[dict[str, Any]] = []
    for row in as_is_rows:
        service = row["as_is_service"]
        if _service_deferred(project, service):
            status = "deferred"
            to_be_context = "deferred (AS-IS retained)"
        else:
            to_be_context = to_be_map.get(service, "unmapped")
            status = "mapped" if to_be_context != "unmapped" else "gap"
        matrix.append(
            {
                **row,
                "to_be_context": to_be_context,
                "to_be_endpoint": f"unified-api/{_slug(to_be_context)}" if status == "mapped" else "—",
                "status": status,
                "validation": contract_tasks.get(to_be_context, "pending"),
                "mandatory": status == "gap",
            }
        )

    return matrix


def matrix_summary(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(matrix)
    mapped = sum(1 for row in matrix if row.get("status") == "mapped")
    gaps = sum(1 for row in matrix if row.get("status") == "gap")
    deferred = sum(1 for row in matrix if row.get("status") == "deferred")
    return {
        "total_capabilities": total,
        "mapped": mapped,
        "gaps": gaps,
        "deferred": deferred,
        "coverage_pct": round((mapped / total) * 100, 1) if total else 0.0,
    }
