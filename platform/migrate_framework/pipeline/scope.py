"""Program scope resolution — generic for any migration project."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from migrate_framework.governance_enums import GATE_REASON_CODES, ITEM_DECISION_STATUSES
from migrate_framework.models import (
    GateDecisionAction,
    ItemDecision,
    MigrationProject,
    PipelineStage,
    ProgramPhase,
    SmellDecision,
    new_id,
)
from migrate_framework.pipeline.governance import record_gate_decision


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_program_phases(project: MigrationProject) -> dict[str, Any]:
    """Initialize baseline + placeholder execution phases from landscape."""
    if project.metadata.get("program_scope"):
        return project.metadata["program_scope"]

    phases: list[dict[str, Any]] = [
        {
            "phase": 0,
            "name": "Baseline",
            "status": "active",
            "in_scope_contexts": [],
            "started_at": _utc_now_iso(),
        }
    ]

    contexts = []
    if project.landscape and project.landscape.target_bounded_contexts:
        contexts = [ctx.name for ctx in project.landscape.target_bounded_contexts]

    for idx, ctx_name in enumerate(contexts, start=1):
        phases.append(
            {
                "phase": idx,
                "name": f"Wave {idx}: {ctx_name}",
                "status": "pending",
                "in_scope_contexts": [],
            }
        )

    scope = {"current_phase": 0, "phases": phases, "baseline_snapshot_id": None}
    project.metadata["program_scope"] = scope
    return scope


def _upsert_item_decision(project: MigrationProject, decision: ItemDecision) -> None:
    decisions = project.metadata.setdefault("item_decisions", [])
    decisions[:] = [d for d in decisions if not (d.get("item_id") == decision.item_id and d.get("item_type") == decision.item_type)]
    decisions.append(decision.model_dump(mode="json"))


def _upsert_smell_decision(project: MigrationProject, decision: SmellDecision) -> None:
    decisions = project.metadata.setdefault("smell_decisions", [])
    decisions[:] = [d for d in decisions if d.get("smell_key") != decision.smell_key]
    decisions.append(decision.model_dump(mode="json"))


def decide_item(
    project: MigrationProject,
    item_id: str,
    item_type: str,
    decision: str,
    decision_by: str,
    reason_code: str | None = None,
    reason_text: str | None = None,
    scope_phase: int | None = None,
    blocks_gate: bool | None = None,
) -> ItemDecision:
    """Record approve / defer / reject for an ADR, bounded context, or plan phase."""
    if decision not in ITEM_DECISION_STATUSES:
        raise ValueError(f"Invalid decision '{decision}'; expected one of {ITEM_DECISION_STATUSES}")
    if reason_code and reason_code not in GATE_REASON_CODES:
        raise ValueError(f"Unknown reason_code: {reason_code}")
    if decision in {"deferred", "rejected"} and not (reason_text or "").strip():
        raise ValueError("reason_text is required for deferred or rejected items")

    phase = scope_phase if scope_phase is not None else max(project.current_program_phase(), 1)
    if blocks_gate is None:
        blocks_gate = decision == "rejected"

    record = ItemDecision(
        item_id=item_id,
        item_type=item_type,
        decision=decision,
        scope_phase=phase,
        reason_code=reason_code,
        reason_text=reason_text,
        decision_by=decision_by,
        blocks_gate=blocks_gate,
    )
    _upsert_item_decision(project, record)

    action = GateDecisionAction.APPROVE if decision == "approved" else GateDecisionAction.MODIFY
    if decision == "rejected":
        action = GateDecisionAction.REJECT

    record_gate_decision(
        project,
        PipelineStage.RECOMMEND,
        action,
        decision_by,
        reason_code=reason_code,
        reason_text=reason_text or f"Item {item_id} marked {decision}",
        item_id=item_id,
        item_type=item_type,
    )
    return record


def decide_smell(
    project: MigrationProject,
    smell_key: str,
    smell_type: str,
    decision: str,
    decision_by: str,
    affected_services: list[str] | None = None,
    reason_code: str | None = None,
    reason_text: str | None = None,
    revisit_phase: int | None = None,
) -> SmellDecision:
    """Record open / accepted / deferred for a detected smell."""
    from migrate_framework.governance_enums import SMELL_DECISION_STATUSES

    if decision not in SMELL_DECISION_STATUSES:
        raise ValueError(f"Invalid smell decision '{decision}'")
    if decision in {"accepted", "deferred"} and not (reason_text or "").strip():
        raise ValueError("reason_text is required when accepting or deferring a smell")
    if reason_code and reason_code not in GATE_REASON_CODES:
        raise ValueError(f"Unknown reason_code: {reason_code}")

    record = SmellDecision(
        smell_key=smell_key,
        smell_type=smell_type,
        affected_services=affected_services or [],
        decision=decision,
        reason_code=reason_code,
        reason_text=reason_text,
        decision_by=decision_by,
        revisit_phase=revisit_phase,
    )
    _upsert_smell_decision(project, record)

    record_gate_decision(
        project,
        PipelineStage.DIAGNOSE,
        GateDecisionAction.MODIFY,
        decision_by,
        reason_code=reason_code or "acceptable_risk",
        reason_text=reason_text or f"Smell {smell_type} marked {decision}",
        item_id=smell_key,
        item_type="smell",
    )
    return record


def _decision_for_item(project: MigrationProject, item_id: str, item_type: str) -> ItemDecision | None:
    for entry in reversed(project.item_decisions()):
        if entry.item_id == item_id and entry.item_type == item_type:
            return entry
    return None


def _adr_item_id(adr: dict[str, Any]) -> str:
    return str(adr.get("id") or adr.get("title") or new_id("adr"))


def approved_adrs(project: MigrationProject, phase: int | None = None) -> list[dict[str, Any]]:
    """ADRs approved for the given program phase (or current active wave)."""
    adrs = project.metadata.get("adrs", [])
    adr_decisions = [d for d in project.item_decisions() if d.item_type == "adr"]
    if not adr_decisions:
        return list(adrs)

    active_phase = phase if phase is not None else max(project.current_program_phase(), 1)
    approved: list[dict[str, Any]] = []

    for adr in adrs:
        item_id = _adr_item_id(adr)
        decision = _decision_for_item(project, item_id, "adr")
        if decision is None:
            continue
        if decision.decision == "approved" and decision.scope_phase <= active_phase:
            approved.append(adr)
    return approved


def deferred_adrs(project: MigrationProject) -> list[dict[str, Any]]:
    adrs = project.metadata.get("adrs", [])
    deferred_ids = {
        d.item_id for d in project.item_decisions() if d.item_type == "adr" and d.decision == "deferred"
    }
    return [adr for adr in adrs if _adr_item_id(adr) in deferred_ids]


def resolve_active_scope(project: MigrationProject, phase: int | None = None) -> dict[str, Any]:
    """Return in-scope services, contexts, and ADRs for the active program phase."""
    init_program_phases(project)
    active_phase = phase if phase is not None else max(project.current_program_phase(), 1)

    scope_meta = project.metadata.get("program_scope", {})
    phase_entry = next((p for p in scope_meta.get("phases", []) if p.get("phase") == active_phase), None)
    explicit_contexts = list(phase_entry.get("in_scope_contexts") or []) if phase_entry else []

    in_scope_adrs = approved_adrs(project, active_phase)
    if not in_scope_adrs and active_phase == 0:
        in_scope_adrs = list(project.metadata.get("adrs", []))

    contexts: set[str] = set(explicit_contexts)
    services: set[str] = set()

    for adr in in_scope_adrs:
        ctx = adr.get("target_context")
        if ctx and ctx != "Cross-cutting":
            contexts.add(ctx)
        for svc in adr.get("affected_services", []):
            services.add(str(svc))

    if not contexts and project.landscape:
        for ctx in project.landscape.target_bounded_contexts:
            decision = _decision_for_item(project, ctx.name, "bounded_context")
            if decision and decision.decision == "approved" and decision.scope_phase <= active_phase:
                contexts.add(ctx.name)
                services.update(ctx.services)
            elif not decision and ctx.name in explicit_contexts:
                contexts.add(ctx.name)
                services.update(ctx.services)

    if not services and contexts and project.landscape:
        for ctx in project.landscape.target_bounded_contexts:
            if ctx.name in contexts:
                services.update(ctx.services)

    return {
        "phase": active_phase,
        "contexts": sorted(contexts),
        "services": sorted(services),
        "adrs": in_scope_adrs,
        "deferred_adrs": deferred_adrs(project),
    }


def pending_mandatory_items(project: MigrationProject, phase: int | None = None) -> list[dict[str, Any]]:
    """Mandatory ADRs/contexts without a resolved decision for the active phase."""
    adr_decisions = [d for d in project.item_decisions() if d.item_type == "adr"]
    if not adr_decisions:
        return []

    active_phase = phase if phase is not None else max(project.current_program_phase(), 1)
    pending: list[dict[str, Any]] = []

    for adr in project.metadata.get("adrs", []):
        if not adr.get("mandatory"):
            continue
        if adr.get("target_context") == "Cross-cutting":
            continue
        item_id = _adr_item_id(adr)
        decision = _decision_for_item(project, item_id, "adr")
        if decision is None:
            pending.append({"item_id": item_id, "item_type": "adr", "title": adr.get("title"), "status": "undecided"})
        elif decision.decision == "deferred":
            continue
        elif decision.decision == "rejected":
            pending.append({"item_id": item_id, "item_type": "adr", "title": adr.get("title"), "status": "rejected"})
        elif decision.decision != "approved":
            pending.append({"item_id": item_id, "item_type": "adr", "title": adr.get("title"), "status": decision.decision})

    return pending


def recommend_gate_clear(project: MigrationProject, phase: int | None = None) -> tuple[bool, str | None]:
    """True when all mandatory in-scope items are approved or formally deferred."""
    pending = pending_mandatory_items(project, phase)
    blocking = [p for p in pending if p.get("status") in {"undecided", "rejected"}]
    if blocking:
        titles = ", ".join(p.get("title", p["item_id"]) for p in blocking[:3])
        return False, f"Mandatory items unresolved for recommend gate: {titles}"
    return True, None


def smell_decision_map(project: MigrationProject) -> dict[str, SmellDecision]:
    return {d.smell_key: d for d in project.smell_decisions()}


def smell_key(smell: dict[str, Any], index: int = 0) -> str:
    """Stable unique id per smell row (index disambiguates duplicate type+service combos)."""
    smell_type = smell.get("type", "unknown")
    services = smell.get("services") or smell.get("affected_services") or []
    svc_part = "-".join(sorted(str(s) for s in services[:3])) or "global"
    return f"{smell_type}:{svc_part}:{index}"


def enrich_diagnosis_with_decisions(project: MigrationProject, diagnosis: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach governance_status to each smell without changing detection."""
    base = dict(diagnosis or project.metadata.get("diagnosis") or {})
    decisions = smell_decision_map(project)
    enriched_smells = []
    for idx, smell in enumerate(base.get("smells", [])):
        key = smell_key(smell, idx)
        decision = decisions.get(key)
        enriched = {**smell, "smell_key": key, "governance_status": decision.decision if decision else "open"}
        if decision:
            enriched["governance_reason"] = decision.reason_text
            enriched["revisit_phase"] = decision.revisit_phase
        enriched_smells.append(enriched)
    base["smells"] = enriched_smells
    return base


def filter_smells_for_planning(smells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude accepted smells from planning; deferred smells remain visible."""
    return [s for s in smells if s.get("governance_status", "open") not in {"accepted"}]


def set_phase_contexts(project: MigrationProject, phase: int, context_names: list[str]) -> None:
    """Assign bounded contexts to a program phase."""
    init_program_phases(project)
    scope = project.metadata["program_scope"]
    for entry in scope.get("phases", []):
        if entry.get("phase") == phase:
            entry["in_scope_contexts"] = list(context_names)
            return
    scope.setdefault("phases", []).append(
        {"phase": phase, "name": f"Wave {phase}", "status": "pending", "in_scope_contexts": list(context_names)}
    )
