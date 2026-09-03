"""Bounded-context summary strip + top-down tree (replaces radial mind-map)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.ui.plotly_widgets import render_plotly_chart
from migrate_framework.ui.visualizations import build_plotly_bounded_context_tree


def build_context_summary_rows(
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic summary rows for bounded contexts (testable without Streamlit)."""
    highlight_services = highlight_services or set()
    rows: list[dict[str, Any]] = []
    for ctx in bounded_contexts:
        ctx_name = str(ctx.get("context") or "Context")
        services = [str(s) for s in (ctx.get("services") or [])]
        shared_db_count = sum(1 for s in services if s in highlight_services)
        rows.append(
            {
                "bounded_context": ctx_name,
                "services": len(services),
                "shared_db_services": shared_db_count,
            }
        )
    return rows


def count_mapped_services(bounded_contexts: list[dict[str, Any]]) -> int:
    seen: set[str] = set()
    for ctx in bounded_contexts:
        for svc in ctx.get("services") or []:
            seen.add(str(svc))
    return len(seen)


def render_bounded_context_summary(
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
) -> None:
    """Metrics + table: how many contexts and which they are."""
    if not bounded_contexts:
        st.caption("No bounded contexts yet. Run **discover** and **ingest**.")
        return

    highlight_services = highlight_services or set()
    context_count = len(bounded_contexts)
    service_count = count_mapped_services(bounded_contexts)

    m1, m2, m3 = st.columns(3)
    m1.metric("Bounded contexts", context_count)
    m2.metric("Services mapped", service_count)
    m3.metric("Shared-DB services", len(highlight_services))

    rows = build_context_summary_rows(bounded_contexts, highlight_services=highlight_services)
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_bounded_context_map(
    chart_key: str,
    bank_name: str,
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
    tree_height: int = 420,
) -> None:
    """Summary strip + interactive top-down Plotly tree."""
    highlight_services = highlight_services or set()

    render_bounded_context_summary(bounded_contexts, highlight_services=highlight_services)

    if not bounded_contexts:
        return

    show_services = st.checkbox(
        "Show services in tree",
        value=True,
        key=f"{chart_key}-show-services",
        help="Hide service nodes to focus on bounded-context names only.",
    )

    try:
        fig = build_plotly_bounded_context_tree(
            bank_name,
            bounded_contexts,
            highlight_services=highlight_services,
            show_services=show_services,
        )
        render_plotly_chart(fig, key=f"{chart_key}-context-tree")
    except RuntimeError as exc:
        st.warning(str(exc))
