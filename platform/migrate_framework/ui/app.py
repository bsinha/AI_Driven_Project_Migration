"""Streamlit dashboard for migration pipeline."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from migrate_framework.branding import PRODUCT_NAME, PRODUCT_TAGLINE
from migrate_framework.models import (
    PIPELINE_STAGE_ORDER,
    ApprovalGate,
    MigrationProject,
    PipelineStage,
)
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.project_store import ProjectStore
from migrate_framework.ui.artifact_views import STAGE_TITLES, render_artifacts, render_stage_artifacts
from migrate_framework.ui.gate_display import approval_gates_for_display, gate_status_display
from migrate_framework.ui.dashboard import render_migration_dashboard
from migrate_framework.ui.guided_review import render_guided_review
from migrate_framework.ui.landscape_overview import render_landscape_overview
from migrate_framework.ui.navigation import (
    init_navigation_state,
    MAIN_TABS,
    build_breadcrumb_parts,
    render_breadcrumb,
    render_classification_filters,
)
from migrate_framework.ui.governance_panel import render_governance_panel, render_role_selector, role_allows
from migrate_framework.ui.phase_dashboard import render_phase_dashboard
from migrate_framework.ui.playbook_execution import render_playbook_execution
from migrate_framework.ui.smell_governance import render_smell_governance
from migrate_framework.ui.stakeholder_report import render_stakeholder_report
from migrate_framework.pipeline.governance import stage_summary_metrics

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_STAGE_UI: dict[PipelineStage, tuple[str, str]] = {
    PipelineStage.DISCOVER: ("🔎", "Discover"),
    PipelineStage.INGEST: ("📥", "Ingest"),
    PipelineStage.GRAPH: ("🕸️", "Graph"),
    PipelineStage.DIAGNOSE: ("🩺", "Diagnose"),
    PipelineStage.HYPOTHESIZE: ("💡", "Hypothesize"),
    PipelineStage.RECOMMEND: ("📋", "Recommend"),
    PipelineStage.PLAN: ("🗺️", "Plan"),
    PipelineStage.PLAYBOOK: ("📘", "Playbook"),
}


def _completed_stages(project: MigrationProject) -> set[PipelineStage]:
    return {r.stage for r in project.stage_runs if r.status == "completed"}


def _gate_status_display(gate: ApprovalGate, completed: set[PipelineStage]) -> tuple[str, str]:
    return gate_status_display(gate, completed)


def _init_session_state() -> None:
    if "pipeline_content_view" not in st.session_state:
        st.session_state.pipeline_content_view = "all"
    if "selected_pipeline_stage" not in st.session_state:
        st.session_state.selected_pipeline_stage = PipelineStage.DISCOVER.value


def _stage_status_marker(stage: PipelineStage, completed: set[PipelineStage], current: PipelineStage) -> str:
    if stage in completed:
        return "✓"
    if stage == current:
        return "▶"
    return "○"


def _render_pipeline_selector(
    completed: set[PipelineStage],
    current: PipelineStage,
) -> None:
    cols = st.columns(len(PIPELINE_STAGE_ORDER) + 1)
    for index, stage in enumerate(PIPELINE_STAGE_ORDER):
        icon, label = _STAGE_UI[stage]
        marker = _stage_status_marker(stage, completed, current)
        selected = (
            st.session_state.pipeline_content_view == "stage"
            and st.session_state.selected_pipeline_stage == stage.value
        )
        with cols[index]:
            if st.button(
                f"{marker} {icon} {label}",
                key=f"pipeline-select-{stage.value}",
                use_container_width=True,
                type="primary" if selected else "secondary",
                help=f"View {STAGE_TITLES.get(stage.value, stage.value)} output",
            ):
                st.session_state.pipeline_content_view = "stage"
                st.session_state.selected_pipeline_stage = stage.value
                st.rerun()

    with cols[-1]:
        view_all_selected = st.session_state.pipeline_content_view == "all"
        if st.button(
            "📑 View all",
            key="pipeline-select-all",
            use_container_width=True,
            type="primary" if view_all_selected else "secondary",
            help="Show outputs from every completed stage",
        ):
            st.session_state.pipeline_content_view = "all"
            st.rerun()

    st.caption("✓ completed · ▶ current · ○ not started · Click a stage to focus its output")


def _render_stage_gate(
    orch: PipelineOrchestrator,
    project: MigrationProject,
    stage_key: str,
    completed: set[PipelineStage],
) -> None:
    stage = PipelineStage(stage_key)
    gate = project.gate_for(stage)
    if gate is None:
        for candidate in approval_gates_for_display(project):
            if candidate.stage == stage:
                gate = candidate
                break
    if gate is None:
        return

    status_label, status_help = _gate_status_display(gate, completed)
    role = "required" if gate.required else "optional"
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        st.markdown(f"**Approval gate** ({role})")
    with c2:
        st.markdown(status_label, help=status_help)
    with c3:
        if gate.required and not gate.is_cleared():
            if st.button(f"Approve {stage.value}", key=f"approve-stage-panel-{stage.value}"):
                orch.approve(project.id, stage)
                st.rerun()
        elif not gate.required and stage in completed and not gate.is_cleared():
            if st.button(f"Record sign-off ({stage.value})", key=f"approve-optional-{stage.value}"):
                orch.approve(project.id, stage)
                st.rerun()


def _short_path(path: str, max_len: int = 48) -> str:
    if len(path) <= max_len:
        return path
    return f"…{path[-(max_len - 1):]}"


def _render_stage_content(
    orch: PipelineOrchestrator,
    project: MigrationProject,
    completed: set[PipelineStage],
) -> None:
    stage_key = st.session_state.selected_pipeline_stage
    icon, label = _STAGE_UI[PipelineStage(stage_key)]
    st.markdown(f"### {icon} {STAGE_TITLES.get(stage_key, label)}")

    if PipelineStage(stage_key) in completed:
        st.success("Stage completed")
    elif project.current_stage.value == stage_key:
        st.warning("Current stage — not yet completed")
    else:
        st.info("Not started")

    _render_stage_gate(orch, project, stage_key, completed)

    metrics = stage_summary_metrics(project, PipelineStage(stage_key))
    if metrics:
        st.caption("Stage analytics")
        st.json(metrics)

    render_stage_artifacts(stage_key, project.metadata.get("artifact_index", {}))


def _render_all_content(project: MigrationProject) -> None:
    st.markdown("### 📑 All pipeline outputs")
    render_artifacts(project.metadata.get("artifact_index", {}))


st.set_page_config(page_title=PRODUCT_NAME, layout="wide")
_init_session_state()

store = ProjectStore()
orch = PipelineOrchestrator()
projects = store.list_projects()

st.sidebar.header("Project")
selected = st.sidebar.selectbox(
    "Active project",
    options=["— new —"] + projects,
    key="sidebar_project_select",
)

ui_role = render_role_selector()
init_navigation_state(ui_role)

st.title(PRODUCT_NAME)
st.caption(PRODUCT_TAGLINE)

project: MigrationProject | None = None

if selected == "— new —":
    st.subheader("Initialize project")
    nc1, nc2, nc3 = st.columns(3)
    with nc1:
        name = st.text_input("Project name", value="EuroSA Bank Migration")
    with nc2:
        source = st.text_input("Source root", value="../sample-bank")
    with nc3:
        landscape = st.text_input("Landscape manifest", value="../sample-bank/landscape-manifest.yaml")
    if st.button("Initialize project"):
        project = orch.init_project(name, str(Path(source).resolve()), str(Path(landscape).resolve()))
        st.success(f"Created project {project.id}")
        st.rerun()
else:
    project = store.load_project(selected)
    meta = st.columns([1.1, 2.2, 0.7])
    with meta[0]:
        st.markdown(f"**ID** `{project.id}`")
    with meta[1]:
        st.markdown(f"**Source** `{_short_path(project.source_root, 64)}`")
    with meta[2]:
        st.markdown(f"**Stack** {project.tech_stack.primary_stack()}")

if project:
    completed = _completed_stages(project)
    from migrate_framework.ui.landscape_overview import _ingest_summary as load_ingest_summary

    ingest_data = load_ingest_summary(project)
    context_options = [
        str(ctx["context"]) for ctx in (ingest_data.get("bounded_contexts") or []) if ctx.get("context")
    ]
    render_classification_filters(context_options)
    render_breadcrumb(
        build_breadcrumb_parts(
            project.name,
            stage_label=st.session_state.main_tab,
            filter_context=st.session_state.get("filter_context", "All"),
        )
    )

    tab_labels = MAIN_TABS.copy()
    if not role_allows(ui_role, "playbook"):
        tab_labels = [t for t in tab_labels if t != "Playbook"]
    if not role_allows(ui_role, "gates"):
        tab_labels = [t for t in tab_labels if t != "Governance"]
    if not role_allows(ui_role, "phases"):
        tab_labels = [t for t in tab_labels if t != "Phases"]

    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs, strict=False)}

    if "Dashboard" in tab_map:
        with tab_map["Dashboard"]:
            render_migration_dashboard(project, completed)

    if "Guided Review" in tab_map:
        with tab_map["Guided Review"]:
            render_guided_review(orch, project, completed)

    if "Landscape" in tab_map:
        with tab_map["Landscape"]:
            render_landscape_overview(project, completed)

    if "Pipeline" in tab_map:
        with tab_map["Pipeline"]:
            st.subheader("Pipeline Progress")
            _render_pipeline_selector(completed, project.current_stage)

            st.subheader("Run Stage")
            rc1, rc2, rc3, rc4 = st.columns([1.2, 1.2, 1, 1])
            with rc1:
                stage_to_run = st.selectbox("Stage", [s.value for s in PIPELINE_STAGE_ORDER])
            with rc2:
                through = st.selectbox("Run through (optional)", ["—"] + [s.value for s in PIPELINE_STAGE_ORDER])
            with rc3:
                auto_approve = st.checkbox("Auto-approve gates")
            with rc4:
                st.write("")
                run_clicked = st.button("Run pipeline", use_container_width=True)

            if run_clicked:
                try:
                    if through != "—":
                        orch.run_through(project.id, PipelineStage(through), auto_approve=auto_approve)
                    else:
                        orch.run_stage(project.id, PipelineStage(stage_to_run))
                    st.success("Stage completed")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

            with st.expander("Approval gates summary", expanded=False):
                st.caption(
                    "Full gate review with evidence is in the **Governance** tab."
                )
                for gate in approval_gates_for_display(project):
                    c1, c2 = st.columns([2, 3])
                    with c1:
                        role = "required" if gate.required else "optional"
                        st.write(f"**{gate.stage.value}** ({role})")
                    with c2:
                        status_label, status_help = _gate_status_display(gate, completed)
                        st.markdown(status_label, help=status_help)

            st.divider()
            if st.session_state.pipeline_content_view == "stage":
                _render_stage_content(orch, project, completed)
            else:
                _render_all_content(project)

    if "Phases" in tab_map:
        with tab_map["Phases"]:
            render_phase_dashboard(project, completed, orch=orch)
            if role_allows(ui_role, "gates"):
                st.divider()
                render_smell_governance(orch, project)

    if "Governance" in tab_map:
        with tab_map["Governance"]:
            render_governance_panel(orch, project, ui_role, completed)

    if "Report" in tab_map:
        with tab_map["Report"]:
            render_stakeholder_report(project)

    if "Playbook" in tab_map:
        with tab_map["Playbook"]:
            if PipelineStage.PLAYBOOK in completed:
                render_playbook_execution(project, store)
            else:
                st.info("Run the **playbook** stage to enable guided execution.")

st.sidebar.header("Stakeholder report")
st.sidebar.caption("Open the **Report** tab to view and download the full assessment.")
