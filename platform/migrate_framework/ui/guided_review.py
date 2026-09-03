"""Step-by-step guided pipeline review."""

from __future__ import annotations

import streamlit as st

from migrate_framework.models import PIPELINE_STAGE_ORDER, MigrationProject, PipelineStage
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.ui.artifact_views import STAGE_TITLES, render_stage_artifacts
from migrate_framework.ui.classified_panels import render_stage_l1_summary
from migrate_framework.ui.gate_display import gate_status_display
from migrate_framework.ui.gate_review import render_gate_review_context
from migrate_framework.ui.landscape_overview import _diagnosis, _graph_payload, _ingest_summary
from migrate_framework.ui.navigation import set_guided_stage
from migrate_framework.ui.context_map import render_bounded_context_map
from migrate_framework.ui.interactive_graphs import render_interactive_service_graph
from migrate_framework.ui.plotly_widgets import handle_stage_chart_selection, render_plotly_chart
from migrate_framework.ui.taxonomy import next_incomplete_stage, stage_visual_components
from migrate_framework.ui.transition_map import render_as_is_to_be_map, resolve_plan_phases
from migrate_framework.ui.visualizations import (
    build_plotly_pipeline_journey,
    build_plotly_plan_timeline,
    build_plotly_smell_summary,
    build_plotly_sync_chains,
)


def _gates_cleared(project: MigrationProject) -> dict[PipelineStage, bool]:
    return {gate.stage: gate.is_cleared() for gate in project.approval_gates}


def _render_step_visual(stage: PipelineStage, project: MigrationProject, completed: set[PipelineStage]) -> None:
    ingest = _ingest_summary(project)
    diagnosis = _diagnosis(project)
    components_list = stage_visual_components(stage)
    shared_db_services: set[str] = set()
    for row in ingest.get("shared_databases") or []:
        for svc in row.get("services") or []:
            shared_db_services.add(svc)

    if "journey" in components_list:
        journey = build_plotly_pipeline_journey(project, completed)
        selected = render_plotly_chart(journey, key=f"journey-{stage.value}", on_select=True)
        handle_stage_chart_selection(selected, f"guided_journey_{stage.value}")

    if "context_map" in components_list and ingest.get("bounded_contexts"):
        bank = project.landscape.name if project.landscape else "Landscape"
        render_bounded_context_map(
            f"guided-ctx-{stage.value}",
            bank,
            ingest["bounded_contexts"],
            highlight_services=shared_db_services,
        )

    if "service_graph" in components_list:
        graph_payload = _graph_payload(project)
        if graph_payload:
            render_interactive_service_graph(
                f"guided-svc-{stage.value}",
                graph_payload,
                ingest,
                color_mode=st.session_state.get("graph_color_mode", "risk"),
                highlight_services=shared_db_services,
            )
        else:
            st.caption("Run **graph** for interactive dependency view.")

    if "smell_overlay" in components_list:
        smells = ingest.get("landscape_smells") or diagnosis.get("smells") or []
        if smells:
            smell_fig = build_plotly_smell_summary(smells)
            render_plotly_chart(smell_fig, key=f"smell-overlay-{stage.value}")
            st.caption(
                "Graph color mode (sidebar): **risk** highlights shared DB and documented smells; "
                "**team** and **database** group by ownership and schema."
            )

    if "sync_chains" in components_list:
        if diagnosis.get("coupling"):
            chains = build_plotly_sync_chains(diagnosis["coupling"])
            render_plotly_chart(chains, key=f"sync-{stage.value}")

    if "as_is_to_be" in components_list:
        contexts = ingest.get("bounded_contexts") or []
        adrs = project.metadata.get("adrs", [])
        phases = resolve_plan_phases(project.metadata)
        if contexts or adrs:
            render_as_is_to_be_map(
                f"guided-transition-{stage.value}",
                contexts,
                adrs,
                phases,
                diagnosis=diagnosis,
            )

    if "plan_timeline" in components_list:
        plan = project.metadata.get("migration_plan", {}) or {}
        phases = resolve_plan_phases(project.metadata)
        if phases:
            timeline = build_plotly_plan_timeline(phases)
            render_plotly_chart(timeline, key=f"plan-timeline-{stage.value}")


def render_guided_review(
    orch: PipelineOrchestrator,
    project: MigrationProject,
    completed: set[PipelineStage],
) -> None:
    st.markdown("### Guided review")
    st.caption(
        "Step through each pipeline stage: L0 visuals, L1 classified summary, then L2 tables in **Full stage detail**."
    )

    gates_cleared = _gates_cleared(project)
    suggested = next_incomplete_stage(completed, gates_cleared)
    if suggested and st.session_state.get("guided_step", 0) == 0:
        set_guided_stage(suggested)

    step_index = int(st.session_state.get("guided_step", 0))
    step_index = max(0, min(step_index, len(PIPELINE_STAGE_ORDER) - 1))
    stage = PIPELINE_STAGE_ORDER[step_index]

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("← Previous", disabled=step_index == 0):
            st.session_state.guided_step = step_index - 1
            st.rerun()
    with nav2:
        st.markdown(
            f"**Step {step_index + 1} of {len(PIPELINE_STAGE_ORDER)}** — "
            f"{STAGE_TITLES.get(stage.value, stage.value)}"
        )
        if stage in completed:
            st.success("Stage completed")
        else:
            st.warning("Stage not completed")
        gate = project.gate_for(stage)
        if gate:
            label, help_text = gate_status_display(gate, completed)
            st.markdown(label, help=help_text)
        if suggested and suggested == stage:
            st.info("Continue where you left off — this step needs attention.")
    with nav3:
        if st.button("Next →", disabled=step_index >= len(PIPELINE_STAGE_ORDER) - 1):
            st.session_state.guided_step = step_index + 1
            st.rerun()

    gate = project.gate_for(stage)
    ingest = _ingest_summary(project)
    diagnosis = _diagnosis(project)
    graph_payload = _graph_payload(project)

    with st.expander("L0 — Visual summary", expanded=True):
        _render_step_visual(stage, project, completed)

    with st.expander("L1 — Classified summary", expanded=True):
        render_stage_l1_summary(
            stage,
            project,
            ingest,
            diagnosis,
            graph_payload,
            key_prefix=f"guided-{stage.value}",
        )

    if gate and gate.required and stage in completed and not gate.is_cleared():
        st.warning("This stage requires gate sign-off — review in **Governance** tab or below.")
        render_gate_review_context(project, stage)

    with st.expander("L2 — Full stage detail (tables + artifacts)", expanded=False):
        render_stage_artifacts(stage.value, project.metadata.get("artifact_index", {}))

    action1, action2, action3 = st.columns(3)
    with action1:
        if st.button("Open in Pipeline tab", key=f"open-pipeline-{stage.value}"):
            st.session_state.main_tab = "Pipeline"
            st.session_state.pipeline_content_view = "stage"
            st.session_state.selected_pipeline_stage = stage.value
            st.rerun()
    with action2:
        if st.button("Open Governance", key=f"open-gov-{stage.value}"):
            st.session_state.main_tab = "Governance"
            st.rerun()
    with action3:
        if st.button("Open Landscape", key=f"open-landscape-{stage.value}"):
            st.session_state.main_tab = "Landscape"
            st.rerun()
