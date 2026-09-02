"""Shared approval-gate status labels for Streamlit."""

from __future__ import annotations

from migrate_framework.governance_enums import GateDecisionStatus
from migrate_framework.models import ApprovalGate, MigrationProject, PipelineStage


def approval_gates_for_display(project: MigrationProject) -> list[ApprovalGate]:
    if project.approval_gates:
        return project.approval_gates
    return MigrationProject.default_gates()


def gate_status_display(
    gate: ApprovalGate,
    completed: set[PipelineStage],
) -> tuple[str, str]:
    """Return (markdown status label, streamlit help tooltip)."""
    if gate.status == GateDecisionStatus.REJECTED:
        return ":red[Rejected]", gate.reason_text or "Rejected — pipeline blocked until rework and re-approval."
    if gate.status == GateDecisionStatus.MODIFIED:
        return ":orange[Modified — pending re-approval]", gate.reason_text or "Artifacts modified; approve after review."
    if gate.status == GateDecisionStatus.WAIVED:
        return ":blue[Waived (exception)]", gate.reason_text or "Formal waiver recorded; pipeline may proceed."

    if not gate.required:
        if gate.is_cleared():
            return ":green[Signed off (optional)]", "Optional gate — formal sign-off recorded."
        if gate.stage in completed:
            return (
                ":blue[Completed — sign-off optional]",
                "Stage finished successfully. This gate does not block the pipeline; "
                "you may record an optional sign-off for audit.",
            )
        return ":blue[Optional — not started]", "This stage does not block the pipeline."

    if gate.is_cleared():
        return ":green[Approved]", "Human sign-off recorded for this required stage."

    if gate.stage in completed:
        return ":orange[Pending sign-off]", "Stage finished; architect approval is still required."

    return ":orange[Pending]", "Approval required before later required stages can proceed."


def gate_expander_title(gate: ApprovalGate, completed: set[PipelineStage]) -> str:
    """Short title for gate expanders (no raw enum values)."""
    label, _ = gate_status_display(gate, completed)
    # Strip streamlit color markup for expander title
    plain = label.replace(":green[", "").replace(":blue[", "").replace(":orange[", "").replace(":red[", "").replace("]", "")
    role = "required" if gate.required else "optional"
    execution = "executed" if gate.stage in completed else "not run"
    return f"{gate.stage.value} · {plain} · {role} · {execution}"
