"""Streamlit helpers for interactive Plotly charts."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from migrate_framework.models import PipelineStage
from migrate_framework.ui.interactive_graphs import _GRAPH_THEME
from migrate_framework.ui.navigation import set_guided_stage
from migrate_framework.ui.visualizations import _safe_id


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
    """Embed Sankey with client-side theme (Plotly iframe labels ignore Streamlit theme)."""
    layout_height = fig.layout.height if fig.layout.height else 480
    render_id = _safe_id(key)
    fig_dict = json.loads(fig.to_json())
    themes_json = json.dumps(_GRAPH_THEME)
    spec_json = json.dumps(fig_dict)

    html = f"""
<div id="{render_id}_wrap" class="ctx-atlas-sankey" style="width:100%;min-height:{layout_height}px;"></div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
(function() {{
  const THEMES = {themes_json};
  const spec = {spec_json};
  const wrap = document.getElementById("{render_id}_wrap");

  function parseRgb(color) {{
    const m = String(color).match(/[\\d.]+/g);
    if (!m || m.length < 3) return null;
    return {{ r: Number(m[0]), g: Number(m[1]), b: Number(m[2]) }};
  }}
  function isDarkBackground(color) {{
    const rgb = parseRgb(color);
    if (!rgb) return false;
    const lum = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    return lum < 0.45;
  }}
  function resolveTheme() {{
    try {{
      const parentBody = window.parent && window.parent.document && window.parent.document.body;
      if (parentBody) {{
        const parentBg = getComputedStyle(parentBody).backgroundColor;
        return isDarkBackground(parentBg) ? THEMES.dark : THEMES.light;
      }}
    }} catch (err) {{}}
    return THEMES.light;
  }}
  function applyTheme(gd, theme) {{
    wrap.style.background = theme.canvas_bg;
    Plotly.relayout(gd, {{
      paper_bgcolor: theme.canvas_bg,
      plot_bgcolor: theme.canvas_bg,
      font: {{ color: theme.node_label, size: 14 }},
      title: {{ font: {{ color: theme.node_label, size: 16 }} }},
    }});
    const root = gd.querySelector(".main-svg") || gd;
    root.querySelectorAll("text").forEach((el) => {{
      el.setAttribute("fill", theme.node_label);
      el.style.fill = theme.node_label;
      el.setAttribute("stroke", "none");
      el.style.stroke = "none";
    }});
    root.querySelectorAll("rect.bg").forEach((rect) => {{
      rect.setAttribute("fill", theme.canvas_bg);
    }});
  }}

  Plotly.newPlot(wrap, spec.data, spec.layout, {{ responsive: true, displayModeBar: false }}).then((gd) => {{
    const theme = resolveTheme();
    applyTheme(gd, theme);
    gd.on("plotly_afterplot", () => applyTheme(gd, resolveTheme()));
  }});
}})();
</script>
"""
    components.html(html, height=int(layout_height) + 48, scrolling=False)


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
