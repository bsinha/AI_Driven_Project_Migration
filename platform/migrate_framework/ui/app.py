"""Streamlit dashboard for migration pipeline."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from migrate_framework.governance_enums import GateDecisionStatus
from migrate_framework.models import (
    PIPELINE_STAGE_ORDER,
    ApprovalGate,
    MigrationProject,
    PipelineStage,
)
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.project_store import ProjectStore
from migrate_framework.ui.artifact_views import STAGE_TITLES, render_artifacts, render_stage_artifacts
from migrate_framework.ui.governance_panel import render_governance_panel, render_role_selector, role_allows
from migrate_framework.ui.playbook_execution import render_playbook_execution
from migrate_framework.pipeline.governance import stage_summary_metrics
from migrate_framework.reporting.pipeline_report import (
    generate_html_report,
    generate_markdown_report,
    report_filename,
)

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


def _approval_gates_for_display(project: MigrationProject) -> list[ApprovalGate]:
    if project.approval_gates:
        return project.approval_gates
    return MigrationProject.default_gates()


def _gate_status_display(gate: ApprovalGate, completed: set[PipelineStage]) -> tuple[str, str]:
    """Return (markdown status label, streamlit help tooltip)."""
    if gate.status == GateDecisionStatus.REJECTED:
        return ":red[Rejected]", gate.reason_text or "Rejected — pipeline blocked until rework and re-approval."
    if gate.status == GateDecisionStatus.MODIFIED:
        return ":orange[Modified — pending re-approval]", gate.reason_text or "Artifacts modified; approve after review."
    if gate.status == GateDecisionStatus.WAIVED:
        return ":blue[Waived (exception)]", gate.reason_text or "Formal waiver recorded; pipeline may proceed."

    if not gate.required:
        if gate.is_cleared():
            return ":green[Approved (optional)]", "Optional gate — formal sign-off recorded."
        return ":blue[Optional — not required]", "This stage does not block the pipeline; approval is optional."

    if gate.is_cleared():
        return ":green[Approved]", "Human sign-off recorded for this required stage."

    if gate.stage in completed:
        return ":orange[Pending sign-off]", "Stage finished; architect approval is still required."

    return ":orange[Pending]", "Approval required before later required stages can proceed."


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
        for candidate in _approval_gates_for_display(project):
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
        if gate.required and not gate.approved:
            if st.button(f"Approve {stage.value}", key=f"approve-stage-panel-{stage.value}"):
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


st.set_page_config(page_title="Migrate Framework", layout="wide")
_init_session_state()

ui_role = render_role_selector()

st.title("Microservice → DDD Migration Framework")

store = ProjectStore()
orch = PipelineOrchestrator()

projects = store.list_projects()
selected = st.selectbox("Project", options=["— new —"] + projects)

project: MigrationProject | None = None
report_md: str | None = None
report_html: str | None = None

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

    report_md = generate_markdown_report(project)
    report_html = generate_html_report(project)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Download report (Markdown)",
            data=report_md,
            file_name=report_filename(project, "md"),
            mime="text/markdown",
            use_container_width=True,
            help="Shareable summary for architects and stakeholders",
        )
    with dl2:
        st.download_button(
            "Download report (HTML)",
            data=report_html,
            file_name=report_filename(project, "html"),
            mime="text/html",
            use_container_width=True,
            help="Print-ready report; use browser Print to PDF",
        )

if project:
    completed = _completed_stages(project)

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

    with st.expander("Approval gates", expanded=False):
        st.caption(
            "Pipeline progress shows whether a stage ran; gates record human sign-off. "
            "Optional gates (discover, graph, playbook) never block the pipeline."
        )
        for gate in _approval_gates_for_display(project):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                role = "required" if gate.required else "optional"
                st.write(f"**{gate.stage.value}** ({role})")
            with c2:
                status_label, status_help = _gate_status_display(gate, completed)
                st.markdown(status_label, help=status_help)
            with c3:
                if gate.required and not gate.approved:
                    if st.button(f"Approve {gate.stage.value}", key=f"approve-{gate.stage.value}"):
                        orch.approve(project.id, gate.stage)
                        st.rerun()

    st.divider()
    render_governance_panel(orch, project, ui_role)

    st.divider()
    if role_allows(ui_role, "playbook") and PipelineStage.PLAYBOOK in completed:
        render_playbook_execution(project, store)

    st.divider()
    if st.session_state.pipeline_content_view == "stage":
        _render_stage_content(orch, project, completed)
    else:
        _render_all_content(project)

st.sidebar.header("Stakeholder report")
st.sidebar.caption("Download a summary of pipeline findings, ADRs, and migration plan.")
if project and report_md and report_html:
    st.sidebar.download_button(
        "Markdown report",
        data=report_md,
        file_name=report_filename(project, "md"),
        mime="text/markdown",
        use_container_width=True,
    )
    st.sidebar.download_button(
        "HTML report",
        data=report_html,
        file_name=report_filename(project, "html"),
        mime="text/html",
        use_container_width=True,
    )

st.sidebar.header("API")
st.sidebar.code("uvicorn migrate_framework.api.main:app --reload --port 8080")
st.sidebar.header("CLI")
st.sidebar.code("migrate-framework report --project-id <id>")
