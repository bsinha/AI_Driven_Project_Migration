"""Streamlit helpers for interactive Plotly charts."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.models import PipelineStage
from migrate_framework.ui.navigation import set_guided_stage


def streamlit_plotly_theme() -> dict[str, str]:
    """Plotly layout colors aligned with Streamlit light/dark theme."""
    light = {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#f0f2f6",
        "text_color": "#262730",
    }
    dark = {
        "paper_bgcolor": "#0e1117",
        "plot_bgcolor": "#262730",
        "text_color": "#fafafa",
    }
    try:
        theme = st.context.theme
        base = getattr(theme, "base", "light")
        palette = dark if base == "dark" else light
        if getattr(theme, "backgroundColor", None):
            palette = palette.copy()
            palette["paper_bgcolor"] = theme.backgroundColor
        if getattr(theme, "secondaryBackgroundColor", None):
            palette = palette.copy()
            palette["plot_bgcolor"] = theme.secondaryBackgroundColor
        if getattr(theme, "textColor", None):
            palette = palette.copy()
            palette["text_color"] = theme.textColor
        return palette
    except Exception:
        return light


def streamlit_chart_label_color() -> str:
    """High-contrast label color for Plotly charts on Streamlit background."""
    return streamlit_plotly_theme()["text_color"]


def render_plotly_sankey_chart(fig: Any, *, key: str) -> None:
    """Render Sankey via native Streamlit Plotly (static layout — avoids relayout hangs)."""
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=key,
        theme="streamlit",
        config={
            "staticPlot": True,
            "displayModeBar": False,
            "responsive": True,
        },
    )


def render_plotly_chart(
    fig: Any,
    *,
    key: str,
    on_select: bool = False,
    theme: str | None = "streamlit",
) -> Any | None:
    """Render a Plotly figure; return first selected point customdata when on_select=True."""
    if on_select:
        state = st.plotly_chart(
            fig,
            use_container_width=True,
            key=key,
            on_select="rerun",
            selection_mode="points",
            theme=theme,
        )
        if state and state.selection and state.selection.points:
            point = state.selection.points[0]
            custom = point.get("customdata")
            if custom is not None:
                return str(custom)
        return None
    st.plotly_chart(fig, use_container_width=True, key=key, theme=theme)
    return None


def navigate_to_pipeline_stage(stage_value: str) -> None:
    """Jump to Pipeline tab focused on a stage (from chart selection)."""
    try:
        stage = PipelineStage(stage_value)
    except ValueError:
        return
    set_guided_stage(stage)
    st.session_state.main_tab = "Pipeline"
    st.session_state.pipeline_content_view = "stage"
    st.session_state.selected_pipeline_stage = stage.value
    st.rerun()


def handle_stage_chart_selection(selected: str | None, key_prefix: str) -> None:
    if not selected:
        return
    last = st.session_state.get(f"{key_prefix}_last_nav")
    if last == selected:
        return
    st.session_state[f"{key_prefix}_last_nav"] = selected
    navigate_to_pipeline_stage(selected)
