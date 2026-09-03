"""AS-IS → TO-BE comparative migration map (summary + side-by-side / Sankey)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from migrate_framework.ui.context_map import count_mapped_services
from migrate_framework.ui.plotly_widgets import render_plotly_chart, render_plotly_sankey_chart
from migrate_framework.ui.visualizations import (
    _short_service_label,
    build_plotly_migration_sankey,
    build_plotly_side_by_side_transition,
)


def _all_services(bounded_contexts: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for ctx in bounded_contexts:
        for svc in ctx.get("services") or []:
            s = str(svc)
            if s not in seen:
                seen.add(s)
                ordered.append(s)
    return ordered


def build_migration_edges(
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic service → target edges from ADRs, plan phases, and unmapped fallbacks."""
    edges: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, kind: str, **extra: Any) -> None:
        key = (source, target, kind)
        if key in seen_keys:
            return
        seen_keys.add(key)
        row: dict[str, Any] = {"source": source, "target": target, "kind": kind}
        row.update(extra)
        edges.append(row)

    for adr in adrs:
        target = str(adr.get("target_context") or adr.get("title") or "TO-BE proposal")
        for svc in adr.get("affected_services") or []:
            add_edge(
                str(svc),
                target,
                "adr",
                adr_id=adr.get("id"),
                adr_title=adr.get("title"),
            )

    for phase in plan_phases or []:
        target = str(phase.get("name") or phase.get("phase") or "Phase")
        for svc in phase.get("services") or []:
            add_edge(str(svc), target, "phase", phase_name=target)

    mapped_sources = {e["source"] for e in edges}
    for svc in _all_services(bounded_contexts):
        if svc not in mapped_sources:
            add_edge(svc, "Unmapped", "unmapped")

    return edges


def build_migration_legend_rows(migration_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Readable AS-IS → TO-BE rows for Sankey legend table."""
    return [
        {
            "as_is_service": _short_service_label(str(edge["source"])),
            "to_be_target": str(edge["target"]),
            "mapping": str(edge.get("kind") or "adr"),
        }
        for edge in sorted(migration_edges, key=lambda row: (row["target"], row["source"]))
    ]


def build_transition_summary_metrics(
    bounded_contexts: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    service_count = count_mapped_services(bounded_contexts)
    targets = {e["target"] for e in migration_edges if e["target"] != "Unmapped"}
    mapped_count = len({e["source"] for e in migration_edges if e["kind"] != "unmapped"})
    unmapped_count = sum(1 for e in migration_edges if e["kind"] == "unmapped")
    mandatory_adrs = sum(1 for adr in adrs if adr.get("mandatory"))
    phase_count = len(plan_phases or [])
    ratio = round(service_count / max(len(targets), 1), 1) if service_count else 0.0
    return {
        "service_count": service_count,
        "target_context_count": len(targets),
        "mapped_services": mapped_count,
        "unmapped_services": unmapped_count,
        "consolidation_ratio": ratio,
        "mandatory_adrs": mandatory_adrs,
        "phase_count": phase_count,
    }


def render_transition_summary(
    bounded_contexts: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
) -> None:
    if not bounded_contexts and not migration_edges:
        st.caption("No transition data yet. Run **recommend** and **plan** for AS-IS → TO-BE mapping.")
        return

    metrics = build_transition_summary_metrics(
        bounded_contexts, migration_edges, adrs, plan_phases
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AS-IS services", metrics["service_count"])
    m2.metric("TO-BE targets", metrics["target_context_count"])
    m3.metric("Consolidation ratio", f"{metrics['consolidation_ratio']}:1")
    m4.metric("Mandatory ADRs", metrics["mandatory_adrs"])

    if metrics["unmapped_services"]:
        st.caption(
            f"{metrics['unmapped_services']} service(s) not yet mapped to a TO-BE target "
            "(shown as **Unmapped** in the diagram)."
        )


def render_as_is_to_be_map(
    chart_key: str,
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
    *,
    chart_height: int = 480,
) -> None:
    """Summary strip + side-by-side or Sankey comparative transition diagram."""
    migration_edges = build_migration_edges(bounded_contexts, adrs, plan_phases)
    render_transition_summary(bounded_contexts, migration_edges, adrs, plan_phases)

    if not bounded_contexts and not migration_edges:
        return

    viz_mode = st.radio(
        "Diagram view",
        ["Side-by-side", "Flow (Sankey)"],
        horizontal=True,
        key=f"{chart_key}-viz-mode",
        help="Side-by-side shows AS-IS contexts/services vs TO-BE targets with migration arrows.",
    )

    try:
        if viz_mode == "Flow (Sankey)":
            fig = build_plotly_migration_sankey(migration_edges)
            render_plotly_sankey_chart(fig, key=f"{chart_key}-transition")
            legend_rows = build_migration_legend_rows(migration_edges)
            with st.expander("Migration mapping labels", expanded=True):
                st.caption(
                    "Sankey flow bands show consolidation volume; read service → target names here "
                    "(avoids unreadable on-chart Plotly labels)."
                )
                st.dataframe(legend_rows, use_container_width=True, hide_index=True)
        else:
            fig = build_plotly_side_by_side_transition(
                bounded_contexts,
                migration_edges,
                height=chart_height,
            )
            render_plotly_chart(fig, key=f"{chart_key}-transition")
    except RuntimeError as exc:
        st.warning(str(exc))
