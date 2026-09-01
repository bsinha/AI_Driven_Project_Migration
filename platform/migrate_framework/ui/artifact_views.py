"""Readable Streamlit renderers for pipeline stage artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from migrate_framework.models import PIPELINE_STAGE_ORDER


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

    return {
        "service": service_label,
        "smell": smell_type,
        "severity": smell.get("severity", "—"),
    }


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
    c1, c2 = st.columns(2)
    c1.metric("Evidence items", data.get("evidence_count", 0))
    c2.metric("Adapter stack", data.get("adapters_used", "—"))


def render_evidence_breakdown(data: list[Any]) -> None:
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
            [{"source": key, "count": value} for key, value in sources.most_common()],
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


def render_service_graph(data: dict[str, Any]) -> None:
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


def _render_stage_body(
    stage_key: str,
    artifact_index: dict[str, list[dict[str, Any]]],
    *,
    show_raw_files: bool = True,
) -> bool:
    entries = artifact_index.get(stage_key, [])
    if not entries:
        return False

    artifact_name, renderer = _STAGE_RENDERERS.get(stage_key, (None, None))
    primary = _latest_artifact(artifact_index, stage_key, artifact_name) if artifact_name else None

    if primary and renderer:
        data = _load(primary.get("path", ""))
        if data is not None:
            renderer(data)
        else:
            st.warning(f"Could not load {primary.get('name')} artifact.")

    if stage_key == "ingest":
        evidence_entry = _latest_artifact(artifact_index, stage_key, "evidence")
        if evidence_entry:
            st.markdown("---")
            st.markdown("**Evidence collection breakdown**")
            evidence_data = _load(evidence_entry.get("path", ""))
            if isinstance(evidence_data, list):
                render_evidence_breakdown(evidence_data)

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
    if not _render_stage_body(stage_key, artifact_index):
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
            _render_stage_body(stage_key, artifact_index)

    if not rendered:
        st.info("No artifacts saved yet. Run pipeline stages to generate outputs.")
