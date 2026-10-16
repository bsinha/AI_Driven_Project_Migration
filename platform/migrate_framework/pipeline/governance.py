"""Governance: decision audit trail, waivers, escalation, confidence checks."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from migrate_framework.governance_enums import (
    CONFIDENCE_APPROVAL_THRESHOLD,
    ESCALATION_REJECTION_THRESHOLD,
    GATE_REASON_CODES,
    GateDecisionAction,
    GateDecisionStatus,
)
from migrate_framework.models import (
    ApprovalGate,
    GateDecisionRecord,
    MigrationProject,
    PipelineStage,
    WaiverRecord,
    new_id,
)


def confidence_threshold() -> float:
    raw = os.getenv("CONFIDENCE_APPROVAL_THRESHOLD", str(CONFIDENCE_APPROVAL_THRESHOLD))
    try:
        return float(raw)
    except ValueError:
        return CONFIDENCE_APPROVAL_THRESHOLD


def escalation_threshold() -> int:
    raw = os.getenv("ESCALATION_REJECTION_THRESHOLD", str(ESCALATION_REJECTION_THRESHOLD))
    try:
        return int(raw)
    except ValueError:
        return ESCALATION_REJECTION_THRESHOLD


def _append_decision(project: MigrationProject, record: GateDecisionRecord) -> None:
    log = project.metadata.setdefault("decision_log", [])
    log.append(record.model_dump(mode="json"))


def _sync_gate_timestamp(gate: ApprovalGate, by: str, notes: str | None = None) -> None:
    gate.approved_at = datetime.now(timezone.utc)
    gate.approved_by = by
    if notes:
        gate.notes = notes


def _apply_gate_status(
    gate: ApprovalGate,
    status: GateDecisionStatus,
    by: str,
    reason_code: str | None = None,
    reason_text: str | None = None,
    notes: str | None = None,
) -> None:
    gate.status = status
    gate.reason_code = reason_code
    gate.reason_text = reason_text
    gate.approved = status in {GateDecisionStatus.APPROVED, GateDecisionStatus.WAIVED}
    _sync_gate_timestamp(gate, by, notes)


def record_gate_decision(
    project: MigrationProject,
    stage: PipelineStage,
    action: GateDecisionAction,
    decision_by: str,
    reason_code: str | None = None,
    reason_text: str | None = None,
    notes: str | None = None,
    item_id: str | None = None,
    item_type: str | None = None,
) -> GateDecisionRecord:
    gate = project.gate_for(stage)
    if gate is None:
        raise ValueError(f"No approval gate for stage {stage.value}")
    iteration = gate.iteration_round

    if action in {GateDecisionAction.REJECT, GateDecisionAction.MODIFY, GateDecisionAction.WAIVE}:
        if not reason_text or not reason_text.strip():
            raise ValueError(f"reason_text is required for gate action '{action.value}'")
        if reason_code and reason_code not in GATE_REASON_CODES:
            raise ValueError(f"Unknown reason_code: {reason_code}")

    if action == GateDecisionAction.APPROVE and reason_code and reason_code not in GATE_REASON_CODES:
        raise ValueError(f"Unknown reason_code: {reason_code}")

    if action == GateDecisionAction.APPROVE:
        _apply_gate_status(gate, GateDecisionStatus.APPROVED, decision_by, reason_code, reason_text, notes)
    elif action == GateDecisionAction.REJECT:
        gate.iteration_round = iteration + 1
        _apply_gate_status(gate, GateDecisionStatus.REJECTED, decision_by, reason_code, reason_text, notes)
        update_escalation(project, stage)
    elif action == GateDecisionAction.MODIFY:
        gate.iteration_round = iteration + 1
        _apply_gate_status(gate, GateDecisionStatus.MODIFIED, decision_by, reason_code, reason_text, notes)
    elif action == GateDecisionAction.WAIVE:
        _apply_gate_status(gate, GateDecisionStatus.WAIVED, decision_by, reason_code, reason_text, notes)
    elif action == GateDecisionAction.RESET:
        gate.status = GateDecisionStatus.PENDING
        gate.approved = False
        gate.reason_code = None
        gate.reason_text = None
        gate.notes = notes
        _sync_gate_timestamp(gate, decision_by, notes)

    record = GateDecisionRecord(
        stage=stage,
        action=action,
        decision_by=decision_by,
        reason_code=reason_code,
        reason_text=reason_text,
        notes=notes,
        iteration_round=gate.iteration_round,
        item_id=item_id,
        item_type=item_type,
    )
    _append_decision(project, record)
    return record


def rejection_count(project: MigrationProject, stage: PipelineStage) -> int:
    return sum(
        1
        for entry in project.decision_log()
        if entry.stage == stage and entry.action == GateDecisionAction.REJECT
    )


def update_escalation(project: MigrationProject, stage: PipelineStage) -> bool:
    """Mark escalation when rejection threshold exceeded."""
    count = rejection_count(project, stage)
    threshold = escalation_threshold()
    gov = project.governance_meta()
    escalations = gov.setdefault("escalations", [])
    if count >= threshold:
        payload = {
            "stage": stage.value,
            "rejection_count": count,
            "threshold": threshold,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Architecture board escalation recommended — repeated rejections at this gate.",
        }
        if not any(e.get("stage") == stage.value and e.get("rejection_count") == count for e in escalations):
            escalations.append(payload)
        gov["needs_escalation"] = True
        return True
    return False


def needs_escalation(project: MigrationProject) -> bool:
    return bool(project.governance_meta().get("needs_escalation"))


def register_waiver(
    project: MigrationProject,
    item_id: str,
    item_type: str,
    title: str,
    reason_code: str,
    reason_text: str,
    waived_by: str,
    stage: PipelineStage | None = None,
) -> WaiverRecord:
    if not reason_text.strip():
        raise ValueError("reason_text is required for waiver")
    if reason_code not in GATE_REASON_CODES:
        raise ValueError(f"Unknown reason_code: {reason_code}")

    waiver = WaiverRecord(
        item_id=item_id,
        item_type=item_type,
        title=title,
        reason_code=reason_code,
        reason_text=reason_text,
        waived_by=waived_by,
        stage=stage,
    )
    registry = project.metadata.setdefault("waiver_registry", [])
    registry.append(waiver.model_dump(mode="json"))

    record_gate_decision(
        project,
        stage or PipelineStage.RECOMMEND,
        GateDecisionAction.WAIVE,
        waived_by,
        reason_code=reason_code,
        reason_text=reason_text,
        notes=f"Waiver for {item_type}:{item_id}",
        item_id=item_id,
        item_type=item_type,
    )
    return waiver


def save_adr_version(project: MigrationProject, reason_text: str, saved_by: str) -> int:
    """Snapshot current ADRs before modification."""
    adrs = project.metadata.get("adrs", [])
    versions = project.metadata.setdefault("adrs_versions", [])
    version = len(versions) + 1
    versions.append(
        {
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "saved_by": saved_by,
            "reason": reason_text,
            "adrs": adrs,
        }
    )
    project.metadata["adrs_version"] = version
    return version


def lowest_stage_confidence(project: MigrationProject, stage: PipelineStage) -> float | None:
    if stage == PipelineStage.HYPOTHESIZE:
        items = project.metadata.get("hypotheses", [])
    elif stage == PipelineStage.RECOMMEND:
        items = project.metadata.get("adrs", [])
    else:
        return None
    scores = [float(item.get("confidence", 1.0)) for item in items if isinstance(item, dict)]
    return min(scores) if scores else None


def confidence_blocks_approval(project: MigrationProject, stage: PipelineStage) -> tuple[bool, str | None]:
    """Return (blocked, message) when confidence below threshold and no waiver."""
    low = lowest_stage_confidence(project, stage)
    if low is None:
        return False, None
    threshold = confidence_threshold()
    if low >= threshold:
        return False, None

    waived = any(
        w.item_type in {"stage", "confidence"}
        for w in project.waiver_registry()
    )
    if waived or project.gate_for(stage) and project.gate_for(stage).status == GateDecisionStatus.WAIVED:
        return False, None

    return True, (
        f"Lowest confidence {low:.0%} is below threshold {threshold:.0%}. "
        "Add evidence, waive with executive sign-off, or reject and rework."
    )


def stage_summary_metrics(project: MigrationProject, stage: PipelineStage) -> dict[str, Any]:
    """Compact analytics for UI stage panels."""
    metrics: dict[str, Any] = {"stage": stage.value}
    if stage == PipelineStage.INGEST:
        metrics["evidence_count"] = len(project.evidence)
    elif stage == PipelineStage.DIAGNOSE:
        diag = project.metadata.get("diagnosis", {})
        metrics["smell_count"] = len(diag.get("smells", []))
        metrics["service_count"] = diag.get("service_count", 0)
    elif stage == PipelineStage.HYPOTHESIZE:
        hyps = project.metadata.get("hypotheses", [])
        metrics["hypothesis_count"] = len(hyps)
        metrics["lowest_confidence"] = lowest_stage_confidence(project, stage)
    elif stage == PipelineStage.RECOMMEND:
        adrs = project.metadata.get("adrs", [])
        metrics["adr_count"] = len(adrs)
        metrics["mandatory_count"] = sum(1 for a in adrs if a.get("mandatory"))
        metrics["lowest_confidence"] = lowest_stage_confidence(project, stage)
    elif stage == PipelineStage.PLAN:
        phases = project.metadata.get("plan", [])
        metrics["phase_count"] = len(phases)
        metrics["total_weeks"] = sum(p.get("duration_weeks", 0) for p in phases)
    elif stage == PipelineStage.PLAYBOOK:
        tasks = project.metadata.get("playbook", [])
        metrics["task_count"] = len(tasks)
        metrics["pending_tasks"] = sum(1 for t in tasks if t.get("status") == "pending")

    gate = project.gate_for(stage)
    if gate:
        metrics["gate_status"] = gate.status.value
        metrics["iteration_round"] = gate.iteration_round
    metrics["rejection_count"] = rejection_count(project, stage)
    return metrics


def add_evidence_gap_playbook_task(project: MigrationProject, description: str, owner: str = "architecture") -> dict[str, Any]:
    """Append SME evidence-request task to playbook."""
    tasks = project.metadata.setdefault("playbook", [])
    task = {
        "id": new_id("task"),
        "category": "governance",
        "task": f"Collect SME evidence: {description}",
        "owner": owner,
        "status": "pending",
        "phase": None,
        "mandatory": False,
        "task_type": "evidence_gap",
    }
    tasks.append(task)
    return task
