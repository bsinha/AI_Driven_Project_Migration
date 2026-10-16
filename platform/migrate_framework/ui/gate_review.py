"""Stage context shown in approval gate review before sign-off."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.models import MigrationProject, PipelineStage
from migrate_framework.ui.artifact_views import STAGE_TITLES, render_ingest_summary, render_stage_gate_review


def reason_codes_for_action(action: str) -> list[str]:
    from migrate_framework.governance_enums import (
        GATE_APPROVE_REASON_CODES,
        GATE_REJECT_REASON_CODES,
        GATE_WAIVE_REASON_CODES,
    )

    if action == "approve":
        return GATE_APPROVE_REASON_CODES
    if action == "reject":
        return GATE_REJECT_REASON_CODES
    if action == "waive":
        return GATE_WAIVE_REASON_CODES
    return GATE_APPROVE_REASON_CODES


def render_gate_review_context(project: MigrationProject, stage: PipelineStage) -> None:
    """Show artifacts and metrics the reviewer needs before approve / reject / waive."""
    stage_key = stage.value
    st.markdown(f"**Review: {STAGE_TITLES.get(stage_key, stage_key)}**")
    st.caption(
        "Review the stage output below before recording a gate decision. "
        "Use **Pipeline Progress** for full artifacts and raw JSON."
    )

    # Stage run summary (ingest summary artifact is richer after re-run)
    runs = [r for r in project.stage_runs if r.stage == stage and r.status == "completed"]
    if runs:
        summary = runs[-1].summary or {}
        if summary and stage != PipelineStage.INGEST:
            st.json(summary)
        elif summary and stage == PipelineStage.INGEST and summary.get("service_catalogue"):
            render_ingest_summary(summary)

    artifact_index = project.metadata.get("artifact_index", {})
    if artifact_index.get(stage_key):
        st.markdown("---")
        if not render_stage_gate_review(stage_key, artifact_index):
            st.info("No readable artifacts for this stage yet.")
    else:
        st.warning("Stage has not produced saved artifacts. Run the stage before sign-off.")

    if stage == PipelineStage.INGEST:
        st.caption(
            f"Total evidence in project: **{len(project.evidence)}** items · "
            f"Stack: **{project.tech_stack.primary_stack()}**"
        )

    if stage == PipelineStage.RECOMMEND:
        low = project.metadata.get("adrs", [])
        if low:
            confidences = [a.get("confidence", 0) for a in low if isinstance(a, dict)]
            if confidences:
                st.caption(f"ADR confidence range: **{min(confidences):.0%}** – **{max(confidences):.0%}**")
