"""Deterministic classification taxonomy for visual UX and filtering."""

from __future__ import annotations

from enum import Enum
from typing import Any

from migrate_framework.analysis.smell_catalog import smell_definition
from migrate_framework.models import PIPELINE_STAGE_ORDER, PipelineStage


class EvidenceCategory(str, Enum):
    SERVICE = "service"
    API = "api"
    SCHEMA = "schema"
    DEPENDENCY = "dependency"
    SMELL = "smell"
    CONTEXT = "context"
    ADR = "adr"
    PLAN = "plan"
    PLAYBOOK = "playbook"
    METRICS = "metrics"


class RiskClass(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class EntityType(str, Enum):
    SERVICE = "service"
    SMELL = "smell"
    ADR = "adr"
    PLAN_PHASE = "plan_phase"
    PLAYBOOK_TASK = "playbook_task"
    CONTEXT = "context"


# Maps entity type → pipeline stage + primary artifact name for L2 drill-down.
ENTITY_REGISTRY: dict[str, dict[str, str]] = {
    EntityType.SERVICE.value: {"stage": "ingest", "artifact": "evidence"},
    EntityType.SMELL.value: {"stage": "diagnose", "artifact": "diagnosis"},
    EntityType.CONTEXT.value: {"stage": "discover", "artifact": "discovery"},
    EntityType.ADR.value: {"stage": "recommend", "artifact": "adrs"},
    EntityType.PLAN_PHASE.value: {"stage": "plan", "artifact": "migration-plan"},
    EntityType.PLAYBOOK_TASK.value: {"stage": "playbook", "artifact": "playbook"},
}

STAGE_L1_PANELS: dict[PipelineStage, list[str]] = {
    PipelineStage.DISCOVER: ["stack_stats", "context_count"],
    PipelineStage.INGEST: ["evidence_coverage", "shared_db", "readiness"],
    PipelineStage.GRAPH: ["graph_metrics", "node_kinds"],
    PipelineStage.DIAGNOSE: ["smell_severity", "coupling_metrics"],
    PipelineStage.HYPOTHESIZE: ["hypothesis_bands"],
    PipelineStage.RECOMMEND: ["adr_confidence"],
    PipelineStage.PLAN: ["phase_risk", "compatibility"],
    PipelineStage.PLAYBOOK: ["task_categories"],
}

_EVIDENCE_TYPE_MAP: dict[str, EvidenceCategory] = {
    "service": EvidenceCategory.SERVICE,
    "api_endpoint": EvidenceCategory.API,
    "database": EvidenceCategory.SCHEMA,
    "database_table": EvidenceCategory.SCHEMA,
    "http_dependency": EvidenceCategory.DEPENDENCY,
    "trace_span": EvidenceCategory.DEPENDENCY,
    "landscape_smell": EvidenceCategory.SMELL,
    "bounded_context": EvidenceCategory.CONTEXT,
}


def classify_evidence_type(evidence_type: str) -> EvidenceCategory:
    return _EVIDENCE_TYPE_MAP.get(evidence_type, EvidenceCategory.METRICS)


def classify_smell_risk(smell_id: str) -> RiskClass:
    severity = smell_definition(smell_id).get("severity", "medium")
    if severity == "high":
        return RiskClass.HIGH
    if severity == "low":
        return RiskClass.LOW
    return RiskClass.MEDIUM


def stage_index(stage: PipelineStage) -> int:
    return PIPELINE_STAGE_ORDER.index(stage)


def next_incomplete_stage(
    completed: set[PipelineStage],
    project_gates_cleared: dict[PipelineStage, bool],
) -> PipelineStage | None:
    for stage in PIPELINE_STAGE_ORDER:
        if stage not in completed:
            return stage
        gate_needed = stage in {
            PipelineStage.INGEST,
            PipelineStage.DIAGNOSE,
            PipelineStage.HYPOTHESIZE,
            PipelineStage.RECOMMEND,
            PipelineStage.PLAN,
        }
        if gate_needed and not project_gates_cleared.get(stage, False):
            return stage
    return None


def stage_visual_components(stage: PipelineStage) -> list[str]:
    mapping: dict[PipelineStage, list[str]] = {
        PipelineStage.DISCOVER: ["journey", "context_map"],
        PipelineStage.INGEST: ["journey", "service_graph", "context_map", "smell_overlay"],
        PipelineStage.GRAPH: ["journey", "service_graph", "smell_overlay"],
        PipelineStage.DIAGNOSE: ["journey", "service_graph", "smell_overlay", "sync_chains"],
        PipelineStage.HYPOTHESIZE: ["journey"],
        PipelineStage.RECOMMEND: ["journey", "as_is_to_be"],
        PipelineStage.PLAN: ["journey", "as_is_to_be", "plan_timeline"],
        PipelineStage.PLAYBOOK: ["journey", "plan_timeline"],
    }
    return mapping.get(stage, ["journey"])


def filter_services_by_context(
    service_ids: list[str],
    context_name: str,
    bounded_contexts: list[dict[str, Any]],
) -> list[str]:
    for ctx in bounded_contexts:
        if ctx.get("context") == context_name:
            members = set(ctx.get("services") or [])
            return [sid for sid in service_ids if sid in members]
    return service_ids


def classify_evidence_item(item: dict[str, Any]) -> list[str]:
    """Return classification tags for a single evidence item."""
    item_type = str(item.get("type") or "")
    category = classify_evidence_type(item_type)
    tags = [category.value]
    if item_type == "landscape_smell":
        smell_id = str((item.get("attributes") or {}).get("smell") or "")
        if smell_id:
            tags.append(f"risk:{classify_smell_risk(smell_id).value}")
    return tags


def classify_service(service_id: str, ingest_summary: dict[str, Any]) -> dict[str, Any]:
    """Roll up context, smells, and risk for a service from ingest summary."""
    catalogue = {row["service"]: row for row in ingest_summary.get("service_catalogue") or []}
    row = catalogue.get(service_id, {})
    smell_ids = row.get("smell_ids") or []
    risks = [classify_smell_risk(str(s)) for s in smell_ids if s]
    top_risk = RiskClass.NONE
    order = [RiskClass.NONE, RiskClass.LOW, RiskClass.MEDIUM, RiskClass.HIGH]
    for risk in risks:
        if order.index(risk) > order.index(top_risk):
            top_risk = risk
    context = "—"
    for ctx in ingest_summary.get("bounded_contexts") or []:
        if service_id in (ctx.get("services") or []):
            context = str(ctx.get("context") or "—")
            break
    return {
        "service": service_id,
        "context": context,
        "smell_count": row.get("smell_count", 0),
        "smell_ids": smell_ids,
        "risk": top_risk.value,
        "api_endpoints": row.get("api_endpoints", 0),
    }


def stage_visual_spec(stage: PipelineStage) -> dict[str, Any]:
    """L0 visual components and L1 panel ids for a pipeline stage."""
    return {
        "l0_components": stage_visual_components(stage),
        "l1_panels": STAGE_L1_PANELS.get(stage, []),
    }


def filter_entities(
    entities: list[dict[str, Any]],
    *,
    context: str = "All",
    min_risk: str = "all",
    bounded_contexts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Apply sidebar classification filters to entity rows."""
    if not entities:
        return []
    result = list(entities)
    if context != "All" and bounded_contexts:
        members = set()
        for ctx in bounded_contexts:
            if ctx.get("context") == context:
                members.update(ctx.get("services") or [])
        if members:
            result = [
                row for row in result
                if row.get("service") in members or row.get("subject") in members
            ]
    if min_risk != "all":
        try:
            threshold = RiskClass(min_risk)
            result = filter_smells_by_risk(result, threshold)
        except ValueError:
            pass
    return result


def filter_smells_by_risk(
    smells: list[dict[str, Any]],
    min_risk: RiskClass,
) -> list[dict[str, Any]]:
    order = [RiskClass.NONE, RiskClass.LOW, RiskClass.MEDIUM, RiskClass.HIGH]
    threshold = order.index(min_risk)
    result = []
    for row in smells:
        smell_id = str(row.get("smell") or row.get("type") or "")
        risk = classify_smell_risk(smell_id) if smell_id else RiskClass.NONE
        if order.index(risk) >= threshold:
            result.append(row)
    return result


_EVIDENCE_TYPE_MAP
