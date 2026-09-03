"""Landscape visual hub — interactive Plotly diagrams."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.models import MigrationProject, PipelineStage
from migrate_framework.reporting.ingest_evidence import summarize_ingest_evidence
from migrate_framework.ui.artifact_views import _latest_artifact, _load
from migrate_framework.ui.classified_panels import render_stage_l1_summary
from migrate_framework.ui.interactive_graphs import render_interactive_service_graph, render_radial_context_map
from migrate_framework.ui.plotly_widgets import handle_stage_chart_selection, render_plotly_chart
from migrate_framework.ui.taxonomy import (
    classify_service,
    filter_services_by_context,
    filter_smells_by_risk,
    RiskClass,
)
from migrate_framework.ui.visualizations import (
    build_plotly_as_is_to_be,
    build_plotly_pipeline_journey,
    build_plotly_smell_summary,
    build_plotly_sync_chains,
)


def _ingest_summary(project: MigrationProject) -> dict[str, Any]:
    index = project.metadata.get("artifact_index", {})
    evidence_entry = _latest_artifact(index, "ingest", "evidence")
    if evidence_entry:
        data = _load(evidence_entry.get("path", ""))
        if isinstance(data, list):
            return summarize_ingest_evidence(data, adapters_used=project.tech_stack.primary_stack())
    summary_entry = _latest_artifact(index, "ingest", "ingest-summary")
    if summary_entry:
        data = _load(summary_entry.get("path", ""))
        if isinstance(data, dict):
            return data
    return {}


def _graph_payload(project: MigrationProject) -> dict[str, Any] | None:
    entry = _latest_artifact(project.metadata.get("artifact_index", {}), "graph", "service-graph")
    if not entry:
        return None
    data = _load(entry.get("path", ""))
    return data if isinstance(data, dict) else None


def _diagnosis(project: MigrationProject) -> dict[str, Any]:
    entry = _latest_artifact(project.metadata.get("artifact_index", {}), "diagnose", "diagnosis")
    if not entry:
        return project.metadata.get("diagnosis", {}) or {}
    data = _load(entry.get("path", ""))
    return data if isinstance(data, dict) else {}


def _focus_services(ingest: dict[str, Any]) -> set[str] | None:
    filter_ctx = st.session_state.get("filter_context", "All")
    if filter_ctx == "All":
        return None
    contexts = ingest.get("bounded_contexts") or []
    catalogue = [row["service"] for row in ingest.get("service_catalogue") or []]
    return set(filter_services_by_context(catalogue, filter_ctx, contexts))


def render_landscape_overview(project: MigrationProject, completed: set[PipelineStage]) -> None:
    st.markdown("### Landscape overview")
    st.caption(
        "Interactive diagrams — drag service nodes, explore the radial context map. "
        "Click a pipeline stage to open **Pipeline**. Tables remain under **Pipeline** and **Governance**."
    )

    ingest = _ingest_summary(project)
    contexts = ingest.get("bounded_contexts") or []
    bank_name = project.landscape.name if project.landscape else "EuroSA Bank"
    shared_db_services: set[str] = set()
    for row in ingest.get("shared_databases") or []:
        for svc in row.get("services") or []:
            shared_db_services.add(svc)

    with st.expander("Pipeline journey", expanded=True):
        journey = build_plotly_pipeline_journey(project, completed)
        selected = render_plotly_chart(journey, key="landscape-journey", on_select=True)
        handle_stage_chart_selection(selected, "landscape_journey")

    col_left, col_right = st.columns(2)

    with col_left:
        with st.expander("Bounded-context map", expanded=True):
            if contexts:
                render_radial_context_map(
                    "landscape-context-mindmap",
                    bank_name,
                    contexts,
                    highlight_services=shared_db_services,
                )
            else:
                st.info("Run **discover** and **ingest** to populate bounded contexts.")

    with col_right:
        with st.expander("Service dependency graph", expanded=True):
            graph_payload = _graph_payload(project)
            if graph_payload:
                render_interactive_service_graph(
                    "landscape-service-graph",
                    graph_payload,
                    ingest,
                    color_mode=st.session_state.get("graph_color_mode", "risk"),
                    focus_services=_focus_services(ingest),
                    highlight_services=shared_db_services,
                )
            else:
                st.info("Run the **graph** stage to build the interactive service graph.")

    diagnosis = _diagnosis(project)
    smells = ingest.get("landscape_smells") or diagnosis.get("smells") or []
    risk_filter = st.session_state.get("filter_risk", "all")
    if risk_filter != "all":
        smells = filter_smells_by_risk(smells, RiskClass(risk_filter))

    with st.expander("Smell and risk summary", expanded=False):
        if smells:
            overview = [
                {
                    "service": s.get("service") or s.get("subject"),
                    "smell": s.get("summary_label") or s.get("title") or s.get("smell") or s.get("type"),
                    "severity": s.get("severity", "—"),
                    "database": s.get("database") or "—",
                    "shared_with": ", ".join(s.get("shared_with") or []) or "—",
                }
                for s in smells[:30]
            ]
            st.dataframe(overview, use_container_width=True, hide_index=True)
        else:
            st.caption("No smells documented yet.")

    if diagnosis.get("coupling"):
        with st.expander("Synchronous call chains", expanded=False):
            chains_fig = build_plotly_sync_chains(diagnosis.get("coupling", {}))
            render_plotly_chart(chains_fig, key="landscape-sync-chains")

    adrs = project.metadata.get("adrs", [])
    plan = project.metadata.get("migration_plan", {}) or {}
    phases = plan.get("phases") if isinstance(plan, dict) else []
    if contexts or adrs:
        with st.expander("AS-IS → TO-BE transition map", expanded=False):
            transition = build_plotly_as_is_to_be(contexts, adrs, phases or [])
            render_plotly_chart(transition, key="landscape-transition")

    if ingest.get("shared_databases"):
        with st.expander("Shared database clusters", expanded=False):
            st.dataframe(ingest["shared_databases"], use_container_width=True, hide_index=True)

    with st.expander("L1 — Classified entity list (filtered)", expanded=False):
        catalogue = ingest.get("service_catalogue") or []
        filter_ctx = st.session_state.get("filter_context", "All")
        if filter_ctx != "All":
            catalogue = [
                row for row in catalogue
                if classify_service(row["service"], ingest).get("context") == filter_ctx
            ]
        if catalogue:
            rows = [
                {
                    "service": row["service"],
                    "context": classify_service(row["service"], ingest)["context"],
                    "risk": classify_service(row["service"], ingest)["risk"],
                    "smells": row.get("smell_count", 0),
                    "apis": row.get("api_endpoints", 0),
                }
                for row in catalogue[:40]
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption("Use sidebar filters to narrow context and risk. Open **Pipeline** for full service catalogue.")
        else:
            st.caption("Run **ingest** to populate the classified service list.")

    current_stage = project.current_stage
    with st.expander("L1 — Stage classified summary", expanded=False):
        render_stage_l1_summary(
            current_stage,
            project,
            ingest,
            diagnosis,
            _graph_payload(project),
            key_prefix="landscape",
        )
