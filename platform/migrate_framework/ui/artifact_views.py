"""Readable Streamlit renderers for pipeline stage artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from migrate_framework.analysis.smell_catalog import smell_definition
from migrate_framework.models import PIPELINE_STAGE_ORDER
from migrate_framework.reporting.ingest_evidence import SOURCE_LABELS, summarize_ingest_evidence

@st.cache_data(show_spinner=False)
def load_artifact_file(path: str, mtime_ns: int) -> Any:
    """Load JSON or YAML artifact; mtime_ns busts cache when the file changes."""
    _ = mtime_ns
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _artifact_mtime(path: str) -> int:
    file_path = Path(path)
    if not file_path.exists():
        return 0
    return file_path.stat().st_mtime_ns


def _load(path: str) -> Any | None:
    if not path or not Path(path).exists():
        return None
    return load_artifact_file(path, _artifact_mtime(path))


def _service_names(services: list[Any] | None) -> list[str]:
    names: list[str] = []
    for item in services or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("id") or item.get("name") or item))
    return names


def _latest_artifact(
    artifact_index: dict[str, list[dict[str, Any]]],
    stage: str,
    name: str | None = None,
) -> dict[str, Any] | None:
    entries = artifact_index.get(stage, [])
    if name:
        entries = [entry for entry in entries if entry.get("name") == name]
    return entries[-1] if entries else None


def _risk_badge(risk: str) -> str:
    colors = {"high": "red", "medium": "orange", "low": "green"}
    color = colors.get(str(risk).lower(), "gray")
    return f":{color}[{risk}]"


def _smell_table_row(smell: dict[str, Any]) -> dict[str, str]:
    smell_type = smell.get("type") or smell.get("smell") or "—"
    meta = smell_definition(str(smell_type)) if smell_type != "—" else {}
    services = smell.get("services")
    subject = smell.get("subject")

    if smell.get("service"):
        service_label = str(smell["service"])
    elif isinstance(services, list) and services:
        if smell_type == "sync_rest_chain":
            service_label = " → ".join(str(s) for s in services)
        elif smell_type == "shared_database":
            service_label = ", ".join(str(s) for s in services)
        elif len(services) == 1:
            service_label = str(services[0])
        else:
            service_label = ", ".join(str(s) for s in services)
    elif subject is not None:
        service_label = str(subject)
    else:
        service_label = "—"

    description = smell.get("description") or meta.get("description", "—")
    return {
        "service": service_label,
        "smell": meta.get("title") or smell_type,
        "severity": smell.get("severity", meta.get("severity", "—")),
        "meaning": description,
    }


def render_landscape_smells(smells: list[dict[str, Any]]) -> None:
    """Explain manifest smells with catalog definitions and estate-specific context."""
    if not smells:
        return

    st.markdown("**Documented landscape smells**")
    st.caption(
        "Smells are intentional architecture risks from the landscape manifest. "
        "Review what each one means before approving ingest."
    )

    overview = [
        {
            "service": row.get("service"),
            "smell": row.get("summary_label") or row.get("title") or row.get("smell"),
            "severity": row.get("severity", "—"),
            "database": row.get("database") or "—",
            "shared_with": ", ".join(row.get("shared_with") or []) or "—",
        }
        for row in smells
    ]
    st.dataframe(overview, use_container_width=True, hide_index=True)

    with st.expander("What each smell means (definitions & migration impact)", expanded=True):
        for row in smells:
            smell_id = row.get("smell", "—")
            title = row.get("summary_label") or row.get("title") or smell_id
            severity = str(row.get("severity", "medium"))
            st.markdown(
                f"**{row.get('service')}** — {title} "
                f"({_risk_badge(severity)}) · `{smell_id}`"
            )
            st.write(row.get("description", "—"))
            st.markdown(f"**Migration impact:** {row.get('migration_impact', '—')}")
            st.markdown(f"**What to verify:** {row.get('what_to_verify', '—')}")
            if row.get("context") and row.get("context") != "—":
                st.markdown(f"**In this estate:** {row.get('context')}")
            st.divider()


def render_service_catalogue(summary: dict[str, Any]) -> None:
    """Per-service documented smells and full OpenAPI paths for ingest review."""
    rows = summary.get("service_catalogue") or []
    if not rows:
        return

    api_fallback = summary.get("api_endpoints_by_service") or {}
    landscape_smells = summary.get("landscape_smells") or []

    overview = [
        {
            "service": row["service"],
            "documented_smells": row.get("documented_smells", "—"),
            "api_endpoints": row.get("api_endpoints") or len(row.get("api_paths") or [])
            or len(api_fallback.get(row["service"], [])),
            "outbound_http": row.get("outbound_http", 0),
            "runtime_calls": row.get("runtime_calls", 0),
        }
        for row in rows
    ]

    st.markdown("**Service catalogue**")
    st.caption(
        "Documented smells and API counts per service. "
        "Expand below for smell IDs and the full endpoint list."
    )
    st.dataframe(overview, use_container_width=True, hide_index=True)

    with st.expander("Smells and API endpoints per service", expanded=True):
        for row in rows:
            service_id = row["service"]
            st.markdown(f"**{service_id}**")

            smell_ids = list(row.get("smell_ids") or [])
            if not smell_ids:
                smell_ids = [
                    str(s.get("smell"))
                    for s in landscape_smells
                    if s.get("service") == service_id and s.get("smell")
                ]

            if smell_ids:
                st.markdown("**Documented smells**")
                smell_details = {
                    d.get("smell"): d for d in (row.get("smell_details") or [])
                }
                landscape_by_smell = {
                    s.get("smell"): s
                    for s in landscape_smells
                    if s.get("service") == service_id
                }
                for smell_id in smell_ids:
                    detail = smell_details.get(smell_id) or landscape_by_smell.get(smell_id)
                    label = (
                        (detail or {}).get("summary_label")
                        or smell_definition(str(smell_id)).get("title", smell_id)
                    )
                    st.caption(f"- {label} (`{smell_id}`)")
            else:
                st.caption("No manifest smells documented for this service.")

            api_paths = list(row.get("api_paths") or [])
            if not api_paths:
                api_paths = list(api_fallback.get(service_id, []))

            if api_paths:
                st.markdown(f"**API endpoints ({len(api_paths)})**")
                for path in api_paths:
                    st.caption(path)
            else:
                st.caption("No OpenAPI endpoints collected for this service.")

            st.divider()


def render_discovery(data: dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Services discovered", data.get("service_count", 0))
    c2.metric("Target contexts", data.get("target_bounded_contexts", 0))
    c3.metric("Primary stack", data.get("primary_stack", "—"))
    c4.metric("Landscape", "Loaded" if data.get("landscape_loaded") else "Missing")

    langs = ", ".join(data.get("languages", [])) or "—"
    frameworks = ", ".join(data.get("frameworks", [])) or "—"
    st.caption(f"Languages: **{langs}** · Frameworks: **{frameworks}**")


def render_ingest_summary(data: dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidence items", data.get("evidence_count", 0))
    c2.metric("Services", data.get("service_count", "—"))
    c3.metric("Bounded contexts", data.get("bounded_context_count", "—"))
    c4.metric("Readiness", data.get("readiness_score", "—"))

    if data.get("adapters_used"):
        st.caption(f"Adapter stack: **{data.get('adapters_used')}**")

    readiness = data.get("readiness") or {}
    if readiness:
        labels = {
            "services_discovered": "Services in landscape",
            "openapi_present": "REST / OpenAPI surface",
            "schema_present": "SQL schema / tables",
            "static_dependencies_present": "Static HTTP dependencies",
            "runtime_traces_present": "Runtime trace calls",
            "landscape_smells_documented": "Documented architecture smells",
            "bounded_contexts_mapped": "Target bounded contexts",
            "all_services_have_openapi": "Every service has OpenAPI",
        }
        st.markdown("**Evidence readiness for downstream stages**")
        for key, ok in readiness.items():
            icon = "✓" if ok else "✗"
            st.markdown(f"- {icon} {labels.get(key, key)}")


def render_ingest_evidence_review(data: list[Any]) -> None:
    """Rich ingest evidence for gate sign-off and pipeline progress."""
    if not data:
        st.info("No evidence payload in artifact.")
        return

    summary = summarize_ingest_evidence(data)
    render_ingest_summary(summary)

    shared = summary.get("shared_databases") or []
    if shared:
        st.markdown("**Shared databases (migration risk)**")
        st.dataframe(shared, use_container_width=True, hide_index=True)

    smells = summary.get("landscape_smells") or []
    if smells:
        render_landscape_smells(smells)

    contexts = summary.get("bounded_contexts") or []
    if contexts:
        st.markdown("**Target bounded contexts**")
        st.dataframe(
            [
                {
                    "context": row.get("context"),
                    "services": ", ".join(row.get("services") or []),
                }
                for row in contexts
            ],
            use_container_width=True,
            hide_index=True,
        )

    if summary.get("service_catalogue"):
        render_service_catalogue(summary)

    coverage = summary.get("coverage") or []
    if coverage:
        st.markdown("**Adapter coverage**")
        st.dataframe(coverage, use_container_width=True, hide_index=True)

    http_deps = summary.get("http_dependencies") or []
    if http_deps:
        st.markdown("**Static HTTP dependencies**")
        st.dataframe(http_deps, use_container_width=True, hide_index=True)

    traces = summary.get("runtime_trace_calls") or []
    if traces:
        st.markdown("**Runtime trace calls**")
        st.dataframe(traces, use_container_width=True, hide_index=True)

    missing_openapi = summary.get("services_without_openapi") or []
    if missing_openapi:
        st.warning(
            f"{len(missing_openapi)} service(s) have no OpenAPI evidence: "
            + ", ".join(missing_openapi)
        )

    db_tables = summary.get("database_tables") or {}
    if db_tables:
        with st.expander("Database tables by schema", expanded=False):
            for db_name, tables in db_tables.items():
                st.markdown(f"**{db_name}** ({len(tables)} tables)")
                st.caption(", ".join(tables[:20]) + (" …" if len(tables) > 20 else ""))


def render_evidence_breakdown(data: list[Any]) -> None:
    """Compact type/source counts (used when full review is not shown)."""
    if not data:
        st.info("No evidence payload in artifact.")
        return

    types = Counter(
        item.get("type") or item.get("evidence_type") or item.get("kind") or "unknown"
        for item in data
        if isinstance(item, dict)
    )
    sources = Counter(
        (item.get("source") or item.get("attributes", {}).get("source") or "unknown")
        for item in data
        if isinstance(item, dict)
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Evidence by type**")
        st.dataframe(
            [{"type": key, "count": value} for key, value in types.most_common()],
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        st.markdown("**Evidence by source**")
        st.dataframe(
            [
                {
                    "source": key,
                    "label": SOURCE_LABELS.get(key, key),
                    "count": value,
                }
                for key, value in sources.most_common()
            ],
            use_container_width=True,
            hide_index=True,
        )


def _is_deployable_service_node(node: dict[str, Any]) -> bool:
    """True for actual microservices, not internal evidence records (ev-*)."""
    attrs = node.get("attributes", {})
    evidence_type = attrs.get("evidence_type")
    if evidence_type in {"service", "deployment_unit"}:
        return True
    if evidence_type in {"http_dependency", "trace_span", "config_property", "build_artifact"}:
        return False

    node_id = str(node.get("id", ""))
    if node_id.startswith("ev-"):
        return False
    if node.get("kind") != "service":
        return False
    return node_id.endswith("-service") or attrs.get("port") is not None


def render_service_graph(data: dict[str, Any], *, chart_key: str = "artifact-graph-service-graph") -> None:
    metrics = data.get("metrics", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    deployable_nodes = [node for node in nodes if _is_deployable_service_node(node)]
    dependency_nodes = [
        node for node in nodes
        if node.get("attributes", {}).get("evidence_type") == "http_dependency"
    ]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Graph nodes", metrics.get("node_count", len(nodes)))
    c2.metric("Graph edges", metrics.get("edge_count", len(edges)))
    c3.metric("Deployable services", len(deployable_nodes))
    c4.metric("Density", f"{metrics.get('density', 0):.4f}")

    try:
        from migrate_framework.ui.interactive_graphs import render_interactive_service_graph

        render_interactive_service_graph(
            chart_key,
            data,
            color_mode=st.session_state.get("graph_color_mode", "risk"),
        )
    except ImportError:
        pass

    services = [
        {
            "service": node.get("id"),
            "database": node.get("attributes", {}).get("database", "—"),
            "team": node.get("attributes", {}).get("team", "—"),
            "port": node.get("attributes", {}).get("port", "—"),
        }
        for node in deployable_nodes
    ]
    if services:
        st.markdown("**Deployable services**")
        st.dataframe(services, use_container_width=True, hide_index=True)

    service_ids = {row["service"] for row in services}
    rest_edges = [
        {
            "from": edge.get("source"),
            "to": edge.get("target"),
            "kind": edge.get("kind"),
        }
        for edge in edges
        if edge.get("source") in service_ids and edge.get("target") in service_ids
    ][:25]
    if rest_edges:
        st.markdown("**Service-to-service dependencies** (sample)")
        st.dataframe(rest_edges, use_container_width=True, hide_index=True)

    if dependency_nodes:
        st.caption(
            f"{len(dependency_nodes)} internal evidence record(s) (IDs like `ev-…`) were folded into "
            "dependency edges and are hidden from the service list. Re-run the **graph** stage to rebuild "
            "the graph without those pseudo-service nodes."
        )


def render_diagnosis(data: dict[str, Any]) -> None:
    metrics = data.get("metrics", {})
    smells = data.get("smells", [])
    coupling = data.get("coupling", {})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Services", data.get("service_count", metrics.get("service_nodes", 0)))
    c2.metric("Smells", len(smells))
    c3.metric("Sync chains", len(coupling.get("sync_chains", [])))
    c4.metric("Avg degree", f"{metrics.get('avg_degree', 0):.2f}")

    if smells:
        smell_rows = [_smell_table_row(smell) for smell in smells[:20]]
        st.markdown("**Top architecture smells**")
        st.dataframe(smell_rows, use_container_width=True, hide_index=True)

    chains = coupling.get("sync_chains", [])[:8]
    if chains:
        st.markdown("**Synchronous call chains**")
        for idx, chain in enumerate(chains, start=1):
            st.write(f"{idx}. {' → '.join(chain)}")


def render_hypotheses(data: list[dict[str, Any]]) -> None:
    for hyp in data:
        confidence = hyp.get("confidence", 0)
        with st.expander(f"{hyp.get('title', 'Hypothesis')} ({confidence:.0%})"):
            st.write(hyp.get("description", ""))
            st.caption(f"Target context: **{hyp.get('target_context', '—')}** · Source: {hyp.get('source', 'unknown')}")
            services = _service_names(hyp.get("affected_services"))
            if services:
                st.markdown("Affected services: " + ", ".join(f"`{name}`" for name in services))


def render_adrs(data: list[dict[str, Any]]) -> None:
    for adr in data:
        confidence = adr.get("confidence")
        mandatory = adr.get("mandatory", False)
        title = adr.get("title") or f"ADR-{adr.get('number', '?')}"
        badge = " **mandatory**" if mandatory else " optional"
        label = f"{title}{badge}"
        if confidence is not None:
            label += f" ({confidence:.0%})"
        with st.expander(label):
            st.markdown(
                f"**Status:** {adr.get('status', 'proposed')} · "
                f"**Context:** {adr.get('target_context', '—')} · "
                f"**Blocks gate:** {adr.get('blocks_gate', mandatory)}"
            )
            if adr.get("as_is_summary"):
                st.markdown(f"**AS-IS:** {adr.get('as_is_summary')}")
            if adr.get("to_be_preview"):
                st.markdown(f"**TO-BE:** {adr.get('to_be_preview')}")
            if adr.get("benefit_if_accepted"):
                st.success(f"Benefit if accepted: {adr.get('benefit_if_accepted')}")
            if adr.get("risk_if_rejected"):
                st.warning(f"Risk if rejected: {adr.get('risk_if_rejected')}")
            st.write("**Decision**")
            st.write(adr.get("decision", ""))
            consequences = adr.get("consequences") or []
            if consequences:
                st.write("**Consequences**")
                for item in consequences:
                    st.markdown(f"- {item}")
            services = _service_names(adr.get("affected_services"))
            if services:
                st.markdown("**Affected services:** " + ", ".join(f"`{name}`" for name in services))


def render_migration_plan(data: list[dict[str, Any]]) -> None:
    total_weeks = sum(phase.get("duration_weeks", 0) for phase in data)
    c1, c2, c3 = st.columns(3)
    c1.metric("Phases", len(data))
    c2.metric("Total duration (weeks)", total_weeks)
    c3.metric("High-risk phases", sum(1 for phase in data if str(phase.get("risk", "")).lower() == "high"))

    for phase in data:
        risk = phase.get("risk", "—")
        header = f"Phase {phase.get('phase')}: {phase.get('name')} · {phase.get('duration_weeks', '?')} weeks · {_risk_badge(risk)}"
        with st.expander(header):
            st.write(phase.get("objective", ""))
            services = phase.get("services") or []
            if services:
                st.markdown("**Services:** " + ", ".join(f"`{name}`" for name in services))
            deps = phase.get("dependencies") or []
            if deps:
                st.caption(f"Depends on phase(s): {', '.join(str(d) for d in deps)}")
            tasks = phase.get("tasks") or []
            if tasks:
                st.markdown("**Tasks**")
                for task in tasks:
                    st.markdown(f"- {task}")


def render_playbook(data: list[dict[str, Any]]) -> None:
    categories = Counter(task.get("category", "other") for task in data)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total tasks", len(data))
    c2.metric("Categories", len(categories))
    c3.metric("Pending", sum(1 for task in data if task.get("status") == "pending"))

    for category, count in sorted(categories.items()):
        with st.expander(f"{category.replace('_', ' ').title()} ({count} tasks)"):
            rows = [
                {
                    "task": task.get("task"),
                    "owner": task.get("owner", "—"),
                    "phase": task.get("phase") if task.get("phase") is not None else "—",
                    "status": task.get("status", "—"),
                }
                for task in data
                if task.get("category") == category
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)


_STAGE_RENDERERS: dict[str, tuple[str | None, Any]] = {
    "discover": ("discovery", render_discovery),
    "ingest": ("ingest-summary", render_ingest_summary),
    "graph": ("service-graph", render_service_graph),
    "diagnose": ("diagnosis", render_diagnosis),
    "hypothesize": ("hypotheses", render_hypotheses),
    "recommend": ("adrs", render_adrs),
    "plan": ("migration-plan", render_migration_plan),
    "playbook": ("playbook", render_playbook),
}

_STAGE_TITLES: dict[str, str] = {
    "discover": "Discovery",
    "ingest": "Evidence ingestion",
    "graph": "Service graph",
    "diagnose": "Architecture diagnosis",
    "hypothesize": "Migration hypotheses",
    "recommend": "Architecture decisions",
    "plan": "Migration plan",
    "playbook": "Developer playbook",
}

STAGE_TITLES = _STAGE_TITLES


def render_stage_gate_review(stage_key: str, artifact_index: dict[str, list[dict[str, Any]]]) -> bool:
    """Compact stage output for approval gate review (no raw file popovers)."""
    return _render_stage_body(
        stage_key,
        artifact_index,
        show_raw_files=False,
        widget_key_prefix="gate-review",
    )


def _render_stage_body(
    stage_key: str,
    artifact_index: dict[str, list[dict[str, Any]]],
    *,
    show_raw_files: bool = True,
    widget_key_prefix: str = "artifact",
) -> bool:
    entries = artifact_index.get(stage_key, [])
    if not entries:
        return False

    artifact_name, renderer = _STAGE_RENDERERS.get(stage_key, (None, None))
    primary = _latest_artifact(artifact_index, stage_key, artifact_name) if artifact_name else None
    evidence_entry = _latest_artifact(artifact_index, stage_key, "evidence") if stage_key == "ingest" else None

    if primary and renderer and not (stage_key == "ingest" and evidence_entry):
        data = _load(primary.get("path", ""))
        if data is not None:
            if renderer is render_service_graph:
                renderer(
                    data,
                    chart_key=f"{widget_key_prefix}-{stage_key}-service-graph",
                )
            else:
                renderer(data)
        else:
            st.warning(f"Could not load {primary.get('name')} artifact.")

    if stage_key == "ingest":
        if evidence_entry:
            evidence_data = _load(evidence_entry.get("path", ""))
            if isinstance(evidence_data, list):
                if primary and renderer:
                    st.markdown("---")
                render_ingest_evidence_review(evidence_data)
        elif primary is None:
            return False

    if show_raw_files:
        st.markdown("---")
        st.caption("Saved files")
        for entry in entries:
            saved_at = entry.get("saved_at", "")
            path = entry.get("path", "")
            st.markdown(f"- `{entry.get('name')}` · {saved_at}")
            raw = _load(path)
            if raw is not None:
                with st.popover(f"View raw `{entry.get('name')}`"):
                    st.json(raw)

    return True


def render_stage_artifacts(stage_key: str, artifact_index: dict[str, list[dict[str, Any]]]) -> None:
    """Render readable content for a single pipeline stage."""
    if not _render_stage_body(stage_key, artifact_index, widget_key_prefix="pipeline-stage"):
        st.info(f"No **{_STAGE_TITLES.get(stage_key, stage_key)}** output yet. Run this stage to generate artifacts.")


def render_artifacts(artifact_index: dict[str, list[dict[str, Any]]]) -> None:
    """Render pipeline artifacts grouped by stage with readable summaries."""
    if not artifact_index:
        st.info("No artifacts saved yet. Run pipeline stages to generate outputs.")
        return

    rendered = False
    for stage in PIPELINE_STAGE_ORDER:
        stage_key = stage.value
        entries = artifact_index.get(stage_key, [])
        if not entries:
            continue

        rendered = True
        with st.expander(
            f"{_STAGE_TITLES.get(stage_key, stage_key.title())} ({len(entries)} file(s))",
            expanded=stage_key in {"recommend", "plan", "playbook"},
        ):
            _render_stage_body(stage_key, artifact_index, widget_key_prefix=f"view-all-{stage_key}")

    if not rendered:
        st.info("No artifacts saved yet. Run pipeline stages to generate outputs.")
