"""AS-IS → TO-BE comparative migration map (architecture comparison + consolidation flow)."""

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

VIZ_COMPARATIVE = "Architecture comparison"
VIZ_CONSOLIDATION = "Consolidation flow"


def resolve_plan_phases(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Plan phases from project metadata (list or nested dict)."""
    plan = metadata.get("plan")
    if isinstance(plan, list):
        return plan
    migration_plan = metadata.get("migration_plan")
    if isinstance(migration_plan, dict):
        return list(migration_plan.get("phases") or [])
    if isinstance(migration_plan, list):
        return migration_plan
    return []


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


def collapse_sankey_edges(migration_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One link per AS-IS service for Sankey (ADR wins over plan phase over unmapped)."""
    priority = {"adr": 0, "phase": 1, "unmapped": 2}
    by_source: dict[str, dict[str, Any]] = {}
    for edge in migration_edges:
        src = str(edge["source"])
        kind = str(edge.get("kind") or "adr")
        existing = by_source.get(src)
        if existing is None or priority.get(kind, 9) < priority.get(str(existing.get("kind")), 9):
            by_source[src] = edge
    return list(by_source.values())


def build_as_is_architecture_rows(bounded_contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """AS-IS structure: bounded contexts and their deployables."""
    rows: list[dict[str, Any]] = []
    for ctx in bounded_contexts:
        services = [str(s) for s in (ctx.get("services") or [])]
        rows.append(
            {
                "bounded_context": str(ctx.get("context") or "Context"),
                "deployable_count": len(services),
                "deployables": ", ".join(_short_service_label(s) for s in services[:6])
                + ("…" if len(services) > 6 else ""),
            }
        )
    return rows


def build_to_be_architecture_rows(
    adrs: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """TO-BE structure: target contexts from ADRs (consolidation targets, not AS-IS service counts)."""
    grouped: dict[str, dict[str, Any]] = {}
    for adr in adrs:
        ctx = str(adr.get("target_context") or "")
        if not ctx or ctx == "Cross-cutting":
            continue
        bucket = grouped.setdefault(
            ctx,
            {
                "bounded_context": ctx,
                "as_is_sources": set(),
                "adrs": [],
                "to_be_preview": adr.get("to_be_preview") or "",
            },
        )
        for svc in adr.get("affected_services") or []:
            bucket["as_is_sources"].add(str(svc))
        title = adr.get("title")
        if title and title not in bucket["adrs"]:
            bucket["adrs"].append(str(title))

    if not grouped and migration_edges:
        for edge in collapse_sankey_edges(migration_edges):
            if edge.get("target") == "Unmapped":
                continue
            target = _normalize_tobe_label(str(edge["target"]))
            bucket = grouped.setdefault(
                target,
                {"bounded_context": target, "as_is_sources": set(), "adrs": [], "to_be_preview": ""},
            )
            bucket["as_is_sources"].add(str(edge["source"]))

    rows: list[dict[str, Any]] = []
    for ctx_name in sorted(grouped):
        item = grouped[ctx_name]
        sources = sorted(item["as_is_sources"])
        # Consolidation ADR: N AS-IS deployables → typically 1 TO-BE deployable per bounded context.
        to_be_count = 1 if sources else 0
        rows.append(
            {
                "bounded_context": ctx_name,
                "to_be_deployables": to_be_count,
                "as_is_sources": len(sources),
                "consolidating_from": ", ".join(_short_service_label(s) for s in sources[:6])
                + ("…" if len(sources) > 6 else ""),
                "adrs": "; ".join(item["adrs"][:2]) + ("…" if len(item["adrs"]) > 2 else ""),
                "to_be": (str(item["to_be_preview"])[:80] + "…")
                if len(str(item["to_be_preview"])) > 80
                else item["to_be_preview"],
            }
        )
    return rows


def _normalize_tobe_label(target: str) -> str:
    if target.startswith("Extract "):
        return target[8:]
    return target


def render_architecture_comparison(
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]],
    diagnosis: dict[str, Any] | None = None,
) -> None:
    """Side-by-side AS-IS vs TO-BE structure tables — the comparative architecture story."""
    as_is_rows = build_as_is_architecture_rows(bounded_contexts)
    to_be_rows = build_to_be_architecture_rows(adrs, migration_edges)
    if not as_is_rows and not to_be_rows:
        return

    st.markdown("#### Architecture comparison")
    st.caption(
        "Compare **structural** AS-IS (bounded contexts and current deployables) with proposed TO-BE contexts. "
        "AS-IS **deployable_count** is services running today; TO-BE **to_be_deployables** is the consolidated "
        "target (usually 1 per context). **as_is_sources** lists how many current services roll into that target."
    )

    if diagnosis:
        smells = diagnosis.get("smells") or []
        open_smells = [s for s in smells if s.get("governance_status", "open") == "open"]
        shared_db = diagnosis.get("database_sharing") or {}
        chains = (diagnosis.get("coupling") or {}).get("chains") or []
        h1, h2, h3 = st.columns(3)
        h1.metric("AS-IS smells (open)", len(open_smells))
        h2.metric("Shared databases", len(shared_db))
        h3.metric("Sync chains", len(chains))

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**AS-IS estate**")
        if as_is_rows:
            st.dataframe(as_is_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("Run **discover** and **ingest** for AS-IS contexts.")
    with col_right:
        st.markdown("**TO-BE (proposed)**")
        if to_be_rows:
            st.dataframe(to_be_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("Run **recommend** to generate TO-BE bounded contexts from ADRs.")


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


def _render_transition_diagram(
    chart_key: str,
    bounded_contexts: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    diagnosis: dict[str, Any] | None = None,
    *,
    chart_height: int = 480,
) -> None:
    render_architecture_comparison(bounded_contexts, adrs, migration_edges, diagnosis)

    viz_mode = st.radio(
        "Diagram view",
        [VIZ_COMPARATIVE, VIZ_CONSOLIDATION],
        horizontal=True,
        index=0,
        key=f"{chart_key}-viz-mode",
        help=(
            f"**{VIZ_COMPARATIVE}**: AS-IS contexts/services vs TO-BE targets with migration arrows. "
            f"**{VIZ_CONSOLIDATION}**: how many deployables map into each target (scope story only)."
        ),
    )

    try:
        if viz_mode == VIZ_CONSOLIDATION:
            st.caption(
                "Consolidation flow shows **which service names roll into which target** — "
                "useful for pilot scope, not a full architecture diagram."
            )
            from migrate_framework.ui.plotly_widgets import streamlit_plotly_theme

            theme = streamlit_plotly_theme()
            sankey_edges = collapse_sankey_edges(migration_edges)
            fig = build_plotly_migration_sankey(
                sankey_edges,
                label_color=theme["text_color"],
                paper_bgcolor=theme["paper_bgcolor"],
                plot_bgcolor=theme["plot_bgcolor"],
            )
            render_plotly_sankey_chart(fig, key=f"{chart_key}-transition-sankey")
            legend_rows = build_migration_legend_rows(sankey_edges)
            with st.expander("Service → target mapping table", expanded=False):
                st.dataframe(legend_rows, use_container_width=True, hide_index=True)
        else:
            st.caption(
                "Left: AS-IS bounded contexts (group boxes) and deployables. "
                "Right: TO-BE target contexts. Arrows show approved migration mapping."
            )
            fig = build_plotly_side_by_side_transition(
                bounded_contexts,
                migration_edges,
                height=chart_height,
            )
            render_plotly_chart(fig, key=f"{chart_key}-transition-side")
    except RuntimeError as exc:
        st.warning(str(exc))


def render_as_is_to_be_map(
    chart_key: str,
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
    *,
    chart_height: int = 480,
    diagnosis: dict[str, Any] | None = None,
) -> None:
    """Summary metrics, architecture comparison tables, and diagram (comparative or consolidation)."""
    migration_edges = build_migration_edges(bounded_contexts, adrs, plan_phases)
    render_transition_summary(bounded_contexts, migration_edges, adrs, plan_phases)

    if not bounded_contexts and not migration_edges:
        return

    fragment = getattr(st, "fragment", None)
    diagram_args = (
        chart_key,
        bounded_contexts,
        migration_edges,
        adrs,
        diagnosis,
    )
    if fragment is not None:
        fragment(_render_transition_diagram)(
            *diagram_args,
            chart_height=chart_height,
        )
    else:
        _render_transition_diagram(
            *diagram_args,
            chart_height=chart_height,
        )
