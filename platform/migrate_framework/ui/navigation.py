"""Session state and breadcrumbs for visual navigation."""

from __future__ import annotations

import streamlit as st

from migrate_framework.models import PIPELINE_STAGE_ORDER, PipelineStage

MAIN_TABS = ["Dashboard", "Guided Review", "Landscape", "Pipeline", "Phases", "Governance", "Report", "Playbook"]

ROLE_DEFAULT_TAB: dict[str, str] = {
    "architect": "Guided Review",
    "engineer": "Pipeline",
    "program": "Phases",
}


def init_navigation_state(role: str) -> None:
    if "main_tab" not in st.session_state:
        st.session_state.main_tab = ROLE_DEFAULT_TAB.get(role, "Guided Review")
    if "guided_step" not in st.session_state:
        st.session_state.guided_step = 0
    if "graph_color_mode" not in st.session_state:
        st.session_state.graph_color_mode = "risk"
    if "filter_context" not in st.session_state:
        st.session_state.filter_context = "All"
    if "filter_risk" not in st.session_state:
        st.session_state.filter_risk = "all"


def current_guided_stage() -> PipelineStage:
    index = int(st.session_state.get("guided_step", 0))
    index = max(0, min(index, len(PIPELINE_STAGE_ORDER) - 1))
    return PIPELINE_STAGE_ORDER[index]


def set_guided_stage(stage: PipelineStage) -> None:
    st.session_state.guided_step = PIPELINE_STAGE_ORDER.index(stage)


def render_breadcrumb(parts: list[str]) -> None:
    if not parts:
        return
    st.caption(" · ".join(parts))


def build_breadcrumb_parts(
    project_name: str,
    *,
    stage_label: str | None = None,
    filter_context: str = "All",
) -> list[str]:
    """Breadcrumb trail: project · context · stage."""
    parts = [project_name]
    if filter_context and filter_context != "All":
        parts.append(filter_context)
    if stage_label:
        parts.append(stage_label)
    return parts


def render_classification_filters(context_options: list[str]) -> None:
    st.sidebar.markdown("**Classification filters**")
    st.session_state.filter_context = st.sidebar.selectbox(
        "Bounded context",
        ["All"] + context_options,
        key="sidebar_filter_context",
    )
    st.session_state.filter_risk = st.sidebar.selectbox(
        "Minimum smell risk",
        ["all", "low", "medium", "high"],
        key="sidebar_filter_risk",
    )
    st.session_state.graph_color_mode = st.sidebar.selectbox(
        "Graph color mode",
        ["risk", "team", "database"],
        key="sidebar_graph_color_mode",
    )
