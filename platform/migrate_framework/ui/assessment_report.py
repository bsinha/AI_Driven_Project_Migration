"""In-app migration assessment report viewer with download actions."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from migrate_framework.models import MigrationProject
from migrate_framework.reporting.pipeline_report import (
    generate_html_report,
    generate_markdown_report,
    report_filename,
)


def _project_signature(project: MigrationProject) -> str:
    """Cache-bust when pipeline runs or artifacts change."""
    index = project.metadata.get("artifact_index") or {}
    artifact_count = sum(len(entries) for entries in index.values())
    gate_state = ",".join(
        f"{gate.stage.value}:{'1' if gate.approved else '0'}" for gate in (project.approval_gates or [])
    )
    return f"{len(project.stage_runs)}:{artifact_count}:{project.current_stage.value}:{gate_state}"


@st.cache_data(show_spinner="Generating assessment…")
def _cached_report_content(project_id: str, signature: str) -> tuple[str, str, str]:
    from migrate_framework.pipeline.project_store import ProjectStore

    project = ProjectStore().load_project(project_id)
    return (
        generate_markdown_report(project),
        generate_html_report(project, embed=False),
        generate_html_report(project, embed=True),
    )


def render_assessment_report(project: MigrationProject) -> None:
    """Full migration assessment report with in-app view and download actions."""
    st.subheader("Migration assessment report")
    st.caption(
        "Evidence-backed summary of pipeline findings, architecture decisions, and migration plan. "
        "Review on this page or download to share."
    )

    report_md, report_html, report_html_embed = _cached_report_content(project.id, _project_signature(project))
    md_filename = report_filename(project, "md")
    html_filename = report_filename(project, "html")

    tool1, tool2, tool3 = st.columns([1, 1, 2])
    with tool1:
        st.download_button(
            "Download Markdown",
            data=report_md,
            file_name=md_filename,
            mime="text/markdown",
            use_container_width=True,
            key="assessment-download-md",
        )
    with tool2:
        st.download_button(
            "Download HTML",
            data=report_html,
            file_name=html_filename,
            mime="text/html",
            use_container_width=True,
            key="assessment-download-html",
        )
    with tool3:
        st.caption(f"Files: `{md_filename}` · `{html_filename}`")

    view_mode = st.radio(
        "Assessment view",
        ["Rendered report", "Printable HTML"],
        horizontal=True,
        help="Rendered report is easiest to read in the app. Printable HTML matches the downloaded file.",
    )

    st.divider()

    if view_mode == "Printable HTML":
        st.caption("Preview uses a fixed light document theme so it stays readable in dark mode.")
        components.html(report_html_embed, height=900, scrolling=True)
    else:
        st.markdown(report_md)
