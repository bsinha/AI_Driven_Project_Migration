"""Program phase dashboard — 8-stage matrix and readiness."""

from __future__ import annotations

import streamlit as st

from migrate_framework.models import MigrationProject, PipelineStage
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.phase_snapshot import (
    compare_phase_diagnose,
    phase_readiness_score,
    phase_stage_matrix,
)
from migrate_framework.pipeline.scope import init_program_phases, resolve_active_scope


def render_phase_close_controls(orch: PipelineOrchestrator, project: MigrationProject) -> None:
    """Close program phase with confirmation — UI parity with phase-close CLI."""
    phase = project.current_program_phase()
    if phase <= 0:
        st.info("Baseline phase (0) is the estate snapshot. Run wave 1 scope decisions before closing a phase.")
        return

    readiness = phase_readiness_score(project, phase)
    st.markdown("#### Close program phase")
    st.caption(f"Current active phase: **{phase}** · Readiness: **{readiness['readiness_score']}%**")

    with st.form("phase-close-form"):
        closed_by = st.text_input("Closed by", value=st.session_state.get("decision_by", "architect"))
        notes = st.text_area("Closure notes (optional)", placeholder="Stakeholder sign-off, validation summary, etc.")
        confirm = st.checkbox(f"I confirm phase {phase} validation is complete")
        if st.form_submit_button("Close phase and advance"):
            if not confirm:
                st.error("Confirm validation before closing the phase.")
            else:
                try:
                    orch.close_program_phase(project.id, phase, closed_by=closed_by)
                    st.success(f"Closed phase {phase}. Advanced to phase {phase + 1}.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_phase_dashboard(project: MigrationProject, completed: set[PipelineStage], orch: PipelineOrchestrator | None = None) -> None:
    init_program_phases(project)
    scope_meta = project.metadata.get("program_scope", {})
    phases = scope_meta.get("phases", [])
    current = project.current_program_phase()

    st.subheader("Migration program phases")
    st.caption(
        "Each program phase can run the eight-stage pipeline for a scoped slice of the estate. "
        "Snapshots and readiness scores apply to any project."
    )

    phase_options = [p.get("phase", 0) for p in phases] or [0]
    selected_phase = st.selectbox(
        "View phase",
        options=phase_options,
        format_func=lambda p: next(
            (f"Phase {p}: {e.get('name', '')} ({e.get('status', 'pending')})" for e in phases if e.get("phase") == p),
            f"Phase {p}",
        ),
        key="program-phase-select",
    )

    active_scope = resolve_active_scope(project, selected_phase)
    readiness = phase_readiness_score(project, selected_phase)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness", f"{readiness['readiness_score']}%")
    c2.metric("In-scope contexts", len(active_scope.get("contexts", [])))
    c3.metric("In-scope services", len(active_scope.get("services", [])))
    c4.metric("Approved ADRs", len(active_scope.get("adrs", [])))

    if readiness.get("factors"):
        st.warning("Readiness factors: " + "; ".join(readiness["factors"]))

    st.markdown("#### Eight-stage matrix")
    matrix = phase_stage_matrix(project, selected_phase)
    rows = []
    for row in matrix:
        metrics = row.get("metrics") or {}
        key_metric = (
            metrics.get("smell_count")
            or metrics.get("evidence_count")
            or metrics.get("adr_count")
            or metrics.get("phase_count")
            or metrics.get("task_count")
            or "—"
        )
        rows.append(
            {
                "stage": row["stage"],
                "completed": "✓" if row["completed"] else "○",
                "gate": row["gate_status"],
                "key_metric": key_metric,
                "snapshot": row.get("snapshot_at") or "—",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if PipelineStage.DIAGNOSE in completed:
        st.markdown("#### Diagnose comparison vs baseline")
        comparison = compare_phase_diagnose(project, selected_phase)
        d1, d2, d3 = st.columns(3)
        d1.metric("Baseline smells (open)", comparison.get("baseline_smell_count", 0))
        d2.metric("Current smells (open)", comparison.get("current_smell_count", 0))
        delta = comparison.get("smell_delta", 0)
        d3.metric("Delta", delta, delta_color="inverse" if delta < 0 else "off")

    deferred = active_scope.get("deferred_adrs", [])
    if deferred:
        st.markdown("#### Deferred ADRs (AS-IS retained)")
        st.dataframe(
            [{"title": a.get("title"), "context": a.get("target_context")} for a in deferred],
            use_container_width=True,
            hide_index=True,
        )

    if orch is not None:
        from migrate_framework.ui.scope_wizard import render_phase_context_assignment

        st.divider()
        render_phase_context_assignment(orch, project)
        render_phase_close_controls(orch, project)
