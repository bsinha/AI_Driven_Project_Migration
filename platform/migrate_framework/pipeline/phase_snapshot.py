"""Phase-scoped stage snapshots and readiness scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from migrate_framework.analysis.diagnose_compare import compare_diagnose
from migrate_framework.models import MigrationProject, PIPELINE_STAGE_ORDER, PipelineStage
from migrate_framework.pipeline.governance import stage_summary_metrics
from migrate_framework.pipeline.scope import enrich_diagnosis_with_decisions, init_program_phases, resolve_active_scope


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot_stage(project: MigrationProject, stage: PipelineStage, phase: int | None = None) -> dict[str, Any]:
    """Capture stage summary metrics for a program phase."""
    init_program_phases(project)
    active_phase = phase if phase is not None else project.current_program_phase()
    snapshots = project.metadata.setdefault("phase_snapshots", {})
    phase_key = str(active_phase)
    phase_bucket = snapshots.setdefault(phase_key, {})

    payload = {
        "captured_at": _utc_now_iso(),
        "metrics": stage_summary_metrics(project, stage),
        "stage": stage.value,
        "phase": active_phase,
    }
    phase_bucket[stage.value] = payload
    return payload


def get_phase_snapshots(project: MigrationProject, phase: int) -> dict[str, Any]:
    return project.metadata.get("phase_snapshots", {}).get(str(phase), {})


def phase_stage_matrix(project: MigrationProject, phase: int | None = None) -> list[dict[str, Any]]:
    """Eight-stage matrix row for UI — one row per pipeline stage."""
    active_phase = phase if phase is not None else project.current_program_phase()
    snapshots = get_phase_snapshots(project, active_phase)
    completed = {r.stage for r in project.stage_runs if r.status == "completed"}
    rows: list[dict[str, Any]] = []

    for stage in PIPELINE_STAGE_ORDER:
        snap = snapshots.get(stage.value, {})
        metrics = snap.get("metrics") or stage_summary_metrics(project, stage)
        gate = project.gate_for(stage)
        rows.append(
            {
                "stage": stage.value,
                "completed": stage in completed,
                "gate_status": gate.status.value if gate else "n/a",
                "gate_required": gate.required if gate else False,
                "metrics": metrics,
                "snapshot_at": snap.get("captured_at"),
            }
        )
    return rows


def phase_readiness_score(project: MigrationProject, phase: int | None = None) -> dict[str, Any]:
    """Composite confidence score for a program phase (0–100)."""
    from migrate_framework.pipeline.scope import pending_mandatory_items, recommend_gate_clear

    active_phase = phase if phase is not None else project.current_program_phase()
    score = 100
    factors: list[str] = []

    cleared, gate_msg = recommend_gate_clear(project, active_phase)
    if not cleared:
        score -= 25
        factors.append(gate_msg or "Recommend gate items unresolved")

    pending = pending_mandatory_items(project, active_phase)
    if pending:
        score -= min(20, len(pending) * 5)
        factors.append(f"{len(pending)} mandatory item(s) pending")

    vv = project.metadata.get("capability_matrix_summary", {})
    coverage = float(vv.get("coverage_pct", 0))
    if coverage < 100 and vv.get("total_capabilities", 0) > 0:
        penalty = int((100 - coverage) / 5)
        score -= min(25, penalty)
        factors.append(f"V&V coverage {coverage}%")

    snapshots = project.metadata.get("phase_snapshots", {})
    baseline_diag = snapshots.get("0", {}).get("diagnose", {}).get("metrics")
    current_diag = snapshots.get(str(active_phase), {}).get("diagnose", {}).get("metrics")
    if baseline_diag and current_diag:
        base_smells = baseline_diag.get("smell_count", 0)
        curr_smells = current_diag.get("smell_count", 0)
        if curr_smells > base_smells:
            score -= 15
            factors.append("Smell count increased vs baseline")

    playbook = project.metadata.get("playbook", [])
    pending_tasks = sum(1 for t in playbook if t.get("status") == "pending" and t.get("mandatory"))
    if pending_tasks:
        score -= min(15, pending_tasks * 3)
        factors.append(f"{pending_tasks} mandatory playbook task(s) open")

    score = max(0, min(100, score))
    return {
        "phase": active_phase,
        "readiness_score": score,
        "factors": factors,
        "recommend_gate_clear": cleared,
        "vv_coverage_pct": coverage,
    }


def close_phase(project: MigrationProject, phase: int, closed_by: str = "operator") -> dict[str, Any]:
    """Mark a program phase complete and advance to the next wave."""
    init_program_phases(project)
    scope = project.metadata["program_scope"]
    phases = scope.get("phases", [])
    now = _utc_now_iso()

    for entry in phases:
        if entry.get("phase") == phase:
            entry["status"] = "completed"
            entry["completed_at"] = now
        elif entry.get("phase") == phase + 1:
            entry["status"] = "active"
            entry["started_at"] = now

    scope["current_phase"] = phase + 1
    project.metadata.setdefault("phase_history", []).append(
        {"phase": phase, "closed_at": now, "closed_by": closed_by}
    )
    return {"closed_phase": phase, "next_phase": phase + 1, "closed_at": now}


def store_diagnose_baseline(project: MigrationProject) -> dict[str, Any]:
    """Snapshot enriched diagnosis as phase-0 baseline for compare."""
    diagnosis = enrich_diagnosis_with_decisions(project)
    project.metadata["diagnosis_baseline"] = diagnosis
    snapshot_stage(project, PipelineStage.DIAGNOSE, phase=0)
    bucket = project.metadata.setdefault("phase_snapshots", {}).setdefault("0", {})
    bucket["diagnose"] = {
        "captured_at": _utc_now_iso(),
        "metrics": {
            "smell_count": len([s for s in diagnosis.get("smells", []) if s.get("governance_status", "open") == "open"]),
            "service_count": diagnosis.get("service_count", 0),
        },
        "payload_ref": "metadata.diagnosis",
    }
    scope = init_program_phases(project)
    scope["baseline_snapshot_id"] = "0"
    return bucket["diagnose"]


def compare_phase_diagnose(project: MigrationProject, phase: int | None = None) -> dict[str, Any]:
    """Compare current diagnosis to baseline for the active phase scope."""
    active_phase = phase if phase is not None else project.current_program_phase()
    baseline_raw = project.metadata.get("phase_snapshots", {}).get("0", {}).get("diagnose")
    current = enrich_diagnosis_with_decisions(project)
    baseline_diag = enrich_diagnosis_with_decisions(project, project.metadata.get("diagnosis_baseline", project.metadata.get("diagnosis", {})))
    if not project.metadata.get("diagnosis_baseline") and project.metadata.get("diagnosis"):
        baseline_diag = enrich_diagnosis_with_decisions(project, project.metadata["diagnosis"])

    scope = resolve_active_scope(project, active_phase)
    comparison = compare_diagnose(
        baseline_diag if baseline_diag.get("smells") else {"smells": [], "metrics": baseline_raw.get("metrics", {}) if baseline_raw else {}},
        current,
        scope_services=scope.get("services"),
    )
    comparison["phase"] = active_phase
    return comparison
