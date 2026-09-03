"""Interactive migration dashboard — KPIs and Plotly visual hub."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.models import PIPELINE_STAGE_ORDER, MigrationProject, PipelineStage
from migrate_framework.ui.artifact_views import STAGE_TITLES
from migrate_framework.ui.gate_display import approval_gates_for_display
from migrate_framework.ui.landscape_overview import _diagnosis, _graph_payload, _ingest_summary
from migrate_framework.ui.context_map import render_bounded_context_map
from migrate_framework.ui.interactive_graphs import render_interactive_service_graph
from migrate_framework.ui.plotly_widgets import handle_stage_chart_selection, render_plotly_chart
from migrate_framework.ui.taxonomy import filter_services_by_context, filter_smells_by_risk, RiskClass
from migrate_framework.ui.transition_map import render_as_is_to_be_map, resolve_plan_phases
from migrate_framework.ui.visualizations import (
    build_plotly_gate_donut,
    build_plotly_pipeline_journey,
    build_plotly_smell_summary,
    build_plotly_sync_chains,
)


def _focus_services(ingest: dict[str, Any]) -> set[str] | None:
    filter_ctx = st.session_state.get("filter_context", "All")
    if filter_ctx == "All":
        return None
    contexts = ingest.get("bounded_contexts") or []
    catalogue = [row["service"] for row in ingest.get("service_catalogue") or []]
    filtered = filter_services_by_context(catalogue, filter_ctx, contexts)
    return set(filtered)


def _filtered_smells(ingest: dict[str, Any], diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    smells = ingest.get("landscape_smells") or diagnosis.get("smells") or []
    risk_filter = st.session_state.get("filter_risk", "all")
    if risk_filter != "all":
        smells = filter_smells_by_risk(smells, RiskClass(risk_filter))
    return smells


def _gates_pending(project: MigrationProject) -> int:
    return sum(1 for g in approval_gates_for_display(project) if not g.is_cleared())


def render_migration_dashboard(project: MigrationProject, completed: set[PipelineStage]) -> None:
    st.markdown("### Overview")
    st.caption(
        "Interactive overview — drag service nodes, explore the bounded-context map, "
        "and click a **pipeline stage** to jump to the Pipeline tab."
    )

    ingest = _ingest_summary(project)
    diagnosis = _diagnosis(project)
    smells = _filtered_smells(ingest, diagnosis)
    contexts = ingest.get("bounded_contexts") or []
    bank_name = project.landscape.name if project.landscape else "EuroSA Bank"
    shared_db_services: set[str] = set()
    for row in ingest.get("shared_databases") or []:
        for svc in row.get("services") or []:
            shared_db_services.add(svc)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("Services", ingest.get("service_count", 0))
    with k2:
        st.metric("Smells", len(smells))
    with k3:
        st.metric("Shared DBs", len(ingest.get("shared_databases") or []))
    with k4:
        st.metric("Gates pending", _gates_pending(project))
    with k5:
        st.metric("Stages done", f"{len(completed)}/{len(PIPELINE_STAGE_ORDER)}")
    with k6:
        st.metric("Readiness", ingest.get("readiness_score", "—"))

    journey = build_plotly_pipeline_journey(project, completed)
    selected = render_plotly_chart(journey, key="dashboard-journey", on_select=True)
    handle_stage_chart_selection(selected, "dashboard_journey")

    graph_main, graph_side = st.columns([2.2, 1])
    graph_payload = _graph_payload(project)
    focus = _focus_services(ingest)

    with graph_main:
        if graph_payload:
            render_interactive_service_graph(
                "dashboard-service-graph",
                graph_payload,
                ingest,
                color_mode=st.session_state.get("graph_color_mode", "risk"),
                focus_services=focus,
                highlight_services=shared_db_services,
            )
        else:
            st.info("Run the **graph** stage to populate the interactive service dependency graph.")

    with graph_side:
        smell_fig = build_plotly_smell_summary(smells)
        render_plotly_chart(smell_fig, key="dashboard-smells")
        gate_fig = build_plotly_gate_donut(project, completed)
        render_plotly_chart(gate_fig, key="dashboard-gates")

    ctx_col, chain_col = st.columns(2)
    with ctx_col:
        if contexts:
            render_bounded_context_map(
                "dashboard-context-map",
                bank_name,
                contexts,
                highlight_services=shared_db_services,
            )
        else:
            st.info("Run **discover** and **ingest** for bounded-context map.")

    with chain_col:
        if diagnosis.get("coupling"):
            chains_fig = build_plotly_sync_chains(diagnosis.get("coupling", {}))
            render_plotly_chart(chains_fig, key="dashboard-sync-chains")
        else:
            st.caption("Synchronous call chains appear after **diagnose**.")

    adrs = project.metadata.get("adrs", [])
    phases = resolve_plan_phases(project.metadata)
    if contexts or adrs:
        render_as_is_to_be_map(
            "dashboard-transition",
            contexts,
            adrs,
            phases,
            diagnosis=diagnosis,
        )

    current = project.current_stage
    icon_stage = STAGE_TITLES.get(current.value, current.value)
    if current not in completed:
        st.info(f"**Next action:** complete **{icon_stage}** or review pending gates in **Governance**.")
