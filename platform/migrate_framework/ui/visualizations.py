"""Chart and diagram builders for pipeline visual UX (no Streamlit imports)."""

from __future__ import annotations

import json
import re
from typing import Any

import networkx as nx

try:
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover
    go = None  # type: ignore[assignment,misc]

from migrate_framework.governance_enums import GateDecisionStatus
from migrate_framework.models import PIPELINE_STAGE_ORDER, MigrationProject, PipelineStage
from migrate_framework.ui.gate_display import approval_gates_for_display, gate_status_display


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


_MERMAID_RESERVED_IDS = frozenset(
    {"graph", "subgraph", "end", "style", "class", "click", "linkstyle", "classdef", "direction"}
)


def _mermaid_node_id(value: str, prefix: str = "n") -> str:
    """Node id safe for Mermaid flowchart (reserved words like 'graph' break parsing)."""
    base = _safe_id(value)
    if not base:
        base = "node"
    if base in _MERMAID_RESERVED_IDS or not re.match(r"^[A-Za-z_]", base):
        base = f"{prefix}_{base}"
    elif not base.startswith(f"{prefix}_"):
        base = f"{prefix}_{base}"
    return base


def _mermaid_safe_label(value: str, max_len: int = 56) -> str:
    """ASCII-safe label for Mermaid node text (no quotes or unicode punctuation)."""
    text = str(value or "")
    text = text.replace('"', "'").replace("\n", " ").replace("\r", " ")
    text = text.replace("—", "-").replace("–", "-").replace("·", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _gate_short_label(gate: Any, completed: set[PipelineStage]) -> str:
    label, _ = gate_status_display(gate, completed)
    plain = re.sub(r":\w+\[", "", label)
    plain = plain.replace("]", "").replace("[", "")
    return _mermaid_safe_label(plain, 28)


def _is_deployable_service_node(node: dict[str, Any]) -> bool:
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


def _service_color(
    service_id: str,
    ingest_summary: dict[str, Any] | None,
    color_mode: str,
) -> str:
    palette = [
        "#4C78A8",
        "#F58518",
        "#E45756",
        "#72B7B2",
        "#54A24B",
        "#EECA3B",
        "#B279A2",
        "#FF9DA6",
    ]
    if not ingest_summary:
        return palette[hash(service_id) % len(palette)]

    catalogue = {row["service"]: row for row in ingest_summary.get("service_catalogue") or []}
    row = catalogue.get(service_id, {})
    if color_mode == "risk":
        smell_ids = row.get("smell_ids") or []
        if any(s == "shared_database" for s in smell_ids):
            return "#E45756"
        if smell_ids:
            return "#F58518"
        return "#54A24B"
    if color_mode == "team":
        team = str(row.get("team") or service_id)
        return palette[hash(team) % len(palette)]
    return palette[hash(service_id) % len(palette)]


def build_plotly_service_graph(
    graph_payload: dict[str, Any],
    ingest_summary: dict[str, Any] | None = None,
    *,
    color_mode: str = "risk",
    focus_services: set[str] | None = None,
    highlight_services: set[str] | None = None,
) -> Any:
    if go is None:
        raise RuntimeError("plotly is required for service graph visualization")

    nodes = graph_payload.get("nodes", [])
    edges = graph_payload.get("edges", [])
    deployable = [n for n in nodes if _is_deployable_service_node(n)]
    if focus_services:
        deployable = [n for n in deployable if n.get("id") in focus_services]
    service_ids = {n.get("id") for n in deployable}
    highlight_services = highlight_services or set()

    g = nx.DiGraph()
    for node in deployable:
        g.add_node(node.get("id"))
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src in service_ids and tgt in service_ids:
            g.add_edge(src, tgt)

    if not g.nodes:
        return go.Figure()

    pos = nx.spring_layout(g, seed=42, k=1.8)
    catalogue = {row["service"]: row for row in (ingest_summary or {}).get("service_catalogue") or []}

    edge_x, edge_y = [], []
    for src, tgt in g.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, texts, colors, hovers, customdata, sizes = [], [], [], [], [], [], []
    for node_id in g.nodes():
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        texts.append(str(node_id).replace("-service", ""))
        attrs = next((n.get("attributes", {}) for n in deployable if n.get("id") == node_id), {})
        db = attrs.get("database") or "—"
        cat = catalogue.get(node_id, {})
        smells = cat.get("documented_smells", "—")
        apis = cat.get("api_endpoints", 0)
        colors.append(_service_color(node_id, ingest_summary, color_mode))
        hovers.append(f"<b>{node_id}</b><br>DB: {db}<br>Smells: {smells}<br>APIs: {apis}")
        customdata.append(node_id)
        sizes.append(26 if node_id in highlight_services else 18)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        hovertext=hovers,
        hoverinfo="text",
        customdata=customdata,
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2 if highlight_services else 1, color="#333"),
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        dragmode="pan",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=480,
        title="Service dependency graph (AS-IS)",
    )
    return fig


def _plotly_network_figure(
    g: nx.DiGraph,
    *,
    title: str,
    node_colors: dict[str, str],
    node_hovers: dict[str, str],
    node_labels: dict[str, str],
    node_customdata: dict[str, str],
    height: int = 400,
) -> Any:
    if go is None:
        raise RuntimeError("plotly is required")
    if not g.nodes:
        return go.Figure()

    pos = nx.spring_layout(g, seed=7, k=1.4)
    edge_x, edge_y = [], []
    for src, tgt in g.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.2, color="#aaa"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, texts, colors, hovers, custom = [], [], [], [], [], []
    for node_id in g.nodes():
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        texts.append(node_labels.get(node_id, str(node_id)))
        colors.append(node_colors.get(node_id, "#4C78A8"))
        hovers.append(node_hovers.get(node_id, str(node_id)))
        custom.append(node_customdata.get(node_id, node_id))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        hovertext=hovers,
        hoverinfo="text",
        customdata=custom,
        marker=dict(size=16, color=colors, line=dict(width=1, color="#333")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        dragmode="pan",
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=height,
        title=title,
    )
    return fig


def build_plotly_pipeline_journey(
    project: MigrationProject,
    completed: set[PipelineStage],
) -> Any:
    if go is None:
        raise RuntimeError("plotly is required")

    gates = {g.stage: g for g in approval_gates_for_display(project)}
    stages = list(PIPELINE_STAGE_ORDER)
    xs = list(range(len(stages)))
    ys = [0] * len(stages)
    colors, labels, hovers, customdata = [], [], [], []

    status_colors = {
        "done": "#54A24B",
        "current": "#F58518",
        "pending": "#B0B0B0",
    }

    for stage in stages:
        if stage in completed:
            status = "done"
        elif stage == project.current_stage:
            status = "current"
        else:
            status = "pending"
        gate = gates.get(stage)
        gate_note = ""
        if gate:
            gate_note = f" ({_gate_short_label(gate, completed)})"
        labels.append(stage.value)
        hovers.append(f"<b>{stage.value}</b>{gate_note}<br>Click to open stage")
        colors.append(status_colors[status])
        customdata.append(stage.value)

    edge_x, edge_y = [], []
    for i in range(len(stages) - 1):
        edge_x.extend([xs[i], xs[i + 1], None])
        edge_y.extend([0, 0, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=3, color="#ccc"),
        hoverinfo="none",
    )
    node_trace = go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        text=labels,
        textposition="top center",
        hovertext=hovers,
        hoverinfo="text",
        customdata=customdata,
        marker=dict(size=22, color=colors, line=dict(width=2, color="#333")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        dragmode=False,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, len(stages) - 0.5]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.6, 0.8]),
        height=220,
        title="Pipeline journey (click a stage to open)",
    )
    return fig


def build_plotly_bounded_context_tree(
    bank_name: str,
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
    show_services: bool = True,
) -> Any:
    highlight_services = highlight_services or set()
    root = bank_name or "Landscape"
    g = nx.DiGraph()
    g.add_node(root)
    node_colors: dict[str, str] = {root: "#2C3E50"}
    node_hovers: dict[str, str] = {root: f"<b>{root}</b> estate root"}
    node_labels: dict[str, str] = {root: root}
    node_customdata: dict[str, str] = {root: root}

    palette = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B", "#B279A2"]
    for index, ctx in enumerate(bounded_contexts):
        ctx_name = str(ctx.get("context") or "Context")
        g.add_node(ctx_name)
        g.add_edge(root, ctx_name)
        color = palette[index % len(palette)]
        node_colors[ctx_name] = color
        svc_list = ctx.get("services") or []
        node_hovers[ctx_name] = f"<b>{ctx_name}</b><br>{len(svc_list)} services"
        node_labels[ctx_name] = ctx_name
        node_customdata[ctx_name] = ctx_name
        if show_services:
            for svc in svc_list:
                svc = str(svc)
                g.add_node(svc)
                g.add_edge(ctx_name, svc)
                if svc in highlight_services:
                    node_colors[svc] = "#E45756"
                else:
                    node_colors[svc] = color
                node_hovers[svc] = f"<b>{svc}</b><br>Context: {ctx_name}"
                node_labels[svc] = svc.replace("-service", "")
                node_customdata[svc] = svc

    layers: dict[int, list[str]] = {0: [root]}
    for ctx in bounded_contexts:
        ctx_name = str(ctx.get("context") or "Context")
        layers.setdefault(1, []).append(ctx_name)
        if show_services:
            for svc in ctx.get("services") or []:
                layers.setdefault(2, []).append(str(svc))

    pos: dict[str, tuple[float, float]] = {}
    for layer, nodes in layers.items():
        sorted_nodes = sorted(nodes)
        width = max(len(sorted_nodes), 1)
        for index, node in enumerate(sorted_nodes):
            pos[node] = (index - (width - 1) / 2, -layer * 1.2)

    if not g.nodes:
        return go.Figure()

    edge_x, edge_y = [], []
    for src, tgt in g.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.2, color="#bbb"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, texts, colors, hovers, custom, sizes = [], [], [], [], [], [], []
    for node_id in g.nodes():
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        texts.append(node_labels[node_id])
        colors.append(node_colors[node_id])
        hovers.append(node_hovers[node_id])
        custom.append(node_customdata[node_id])
        sizes.append(24 if node_id in highlight_services else 16)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        hovertext=hovers,
        hoverinfo="text",
        customdata=custom,
        marker=dict(size=sizes, color=colors, line=dict(width=1, color="#333")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        dragmode="pan",
        margin=dict(l=10, r=10, t=36, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=420 if show_services else 280,
        title="Bounded-context tree (top-down; red = shared DB)" if show_services else "Bounded contexts (services hidden)",
    )
    return fig


def build_plotly_sync_chains(coupling: dict[str, Any], limit: int = 6) -> Any:
    chains = coupling.get("sync_chains", [])[:limit]
    if not chains:
        fig = go.Figure()
        fig.update_layout(title="No synchronous call chains detected", height=280)
        return fig

    g = nx.DiGraph()
    node_colors: dict[str, str] = {}
    node_hovers: dict[str, str] = {}
    node_labels: dict[str, str] = {}
    node_customdata: dict[str, str] = {}

    for chain in chains:
        for left, right in zip(chain, chain[1:], strict=False):
            left, right = str(left), str(right)
            g.add_edge(left, right)
            for node in (left, right):
                node_colors[node] = "#4C78A8"
                node_hovers[node] = f"<b>{node}</b> sync chain participant"
                node_labels[node] = node.replace("-service", "")
                node_customdata[node] = node

    return _plotly_network_figure(
        g,
        title="Synchronous call chains",
        node_colors=node_colors,
        node_hovers=node_hovers,
        node_labels=node_labels,
        node_customdata=node_customdata,
        height=300,
    )


ASIS_CTX_PREFIX = "asis_ctx::"
TOBE_NODE_PREFIX = "tobe::"


def _short_service_label(service_id: str) -> str:
    return service_id.replace("-service", "")


def _normalize_sankey_target(target: str) -> str:
    if target.startswith("Extract "):
        return target[8:]
    return target


def _migration_edge_traces(
    edges: list[tuple[str, str]],
    positions: dict[str, tuple[float, float]],
    *,
    color: str,
    dash: str,
    width: float,
) -> go.Scatter:
    edge_x, edge_y = [], []
    for src, tgt in edges:
        if src not in positions or tgt not in positions:
            continue
        x0, y0 = positions[src]
        x1, y1 = positions[tgt]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    return go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=width, color=color, dash=dash),
        hoverinfo="none",
        mode="lines",
    )


def build_plotly_side_by_side_transition(
    bounded_contexts: list[dict[str, Any]],
    migration_edges: list[dict[str, Any]],
    *,
    height: int = 480,
) -> Any:
    """Left: AS-IS contexts + services; right: TO-BE targets; cross-links show consolidation."""
    if go is None:
        raise RuntimeError("plotly is required")

    positions: dict[str, tuple[float, float]] = {}
    node_colors: dict[str, str] = {}
    node_hovers: dict[str, str] = {}
    node_labels: dict[str, str] = {}
    node_sizes: dict[str, float] = {}

    asis_internal: list[tuple[str, str]] = []
    migration_adr: list[tuple[str, str]] = []
    migration_phase: list[tuple[str, str]] = []
    migration_unmapped: list[tuple[str, str]] = []

    y_cursor = 0.0
    ctx_palette = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B", "#B279A2"]

    for index, ctx in enumerate(bounded_contexts):
        ctx_name = str(ctx.get("context") or "Context")
        ctx_id = f"{ASIS_CTX_PREFIX}{ctx_name}"
        color = ctx_palette[index % len(ctx_palette)]
        services = [str(s) for s in (ctx.get("services") or [])]
        service_ys: list[float] = []

        for svc in services:
            positions[svc] = (-2.0, y_cursor)
            node_colors[svc] = color
            node_hovers[svc] = f"<b>{svc}</b><br>AS-IS · {ctx_name}"
            node_labels[svc] = _short_service_label(svc)
            node_sizes[svc] = 14
            service_ys.append(y_cursor)
            asis_internal.append((ctx_id, svc))
            y_cursor += 1.0

        ctx_y = sum(service_ys) / len(service_ys) if service_ys else y_cursor
        positions[ctx_id] = (-4.0, ctx_y)
        node_colors[ctx_id] = color
        node_hovers[ctx_id] = f"<b>{ctx_name}</b><br>{len(services)} service(s)"
        node_labels[ctx_id] = ctx_name
        node_sizes[ctx_id] = 20
        y_cursor += 0.5

    tobe_targets = sorted({str(e["target"]) for e in migration_edges})
    for index, target in enumerate(tobe_targets):
        node_id = f"{TOBE_NODE_PREFIX}{target}"
        positions[node_id] = (4.0, float(index))
        if target == "Unmapped":
            node_colors[node_id] = "#B0B0B0"
        else:
            node_colors[node_id] = "#54A24B"
        node_hovers[node_id] = f"<b>TO-BE</b><br>{target}"
        node_labels[node_id] = target if len(target) <= 32 else target[:29] + "..."
        node_sizes[node_id] = 22

    for edge in migration_edges:
        src = str(edge["source"])
        tgt_id = f"{TOBE_NODE_PREFIX}{edge['target']}"
        kind = str(edge.get("kind") or "adr")
        pair = (src, tgt_id)
        if kind == "phase":
            migration_phase.append(pair)
        elif kind == "unmapped":
            migration_unmapped.append(pair)
        else:
            migration_adr.append(pair)

    traces: list[Any] = []
    if asis_internal:
        traces.append(
            _migration_edge_traces(asis_internal, positions, color="#bbb", dash="solid", width=1.2)
        )
    if migration_adr:
        traces.append(
            _migration_edge_traces(migration_adr, positions, color="#4C78A8", dash="dash", width=2.0)
        )
    if migration_phase:
        traces.append(
            _migration_edge_traces(migration_phase, positions, color="#EECA3B", dash="dot", width=1.8)
        )
    if migration_unmapped:
        traces.append(
            _migration_edge_traces(migration_unmapped, positions, color="#B0B0B0", dash="dash", width=1.5)
        )

    node_ids = list(positions.keys())
    node_x = [positions[n][0] for n in node_ids]
    node_y = [positions[n][1] for n in node_ids]
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[node_labels[n] for n in node_ids],
        textposition="top center",
        hovertext=[node_hovers[n] for n in node_ids],
        hoverinfo="text",
        customdata=node_ids,
        marker=dict(
            size=[node_sizes[n] for n in node_ids],
            color=[node_colors[n] for n in node_ids],
            line=dict(width=1, color="#333"),
        ),
    )
    traces.append(node_trace)

    fig = go.Figure(data=traces)
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        dragmode="pan",
        margin=dict(l=20, r=20, t=48, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=max(height, int(y_cursor * 28 + 80)),
        title="AS-IS → TO-BE architecture comparison",
        annotations=[
            dict(x=-3.0, y=1.02, xref="x", yref="paper", text="AS-IS", showarrow=False, font=dict(size=14)),
            dict(x=4.0, y=1.02, xref="x", yref="paper", text="TO-BE", showarrow=False, font=dict(size=14)),
        ],
    )
    return fig


def build_plotly_migration_sankey(
    migration_edges: list[dict[str, Any]],
    *,
    label_color: str = "#262730",
    paper_bgcolor: str = "#ffffff",
    plot_bgcolor: str = "#f0f2f6",
) -> Any:
    if go is None:
        raise RuntimeError("plotly is required")
    if not migration_edges:
        fig = go.Figure()
        fig.update_layout(title="No migration mapping", height=360)
        return fig

    labels: list[str] = []
    label_index: dict[str, int] = {}
    node_sides: list[str] = []

    def register(label: str, side: str) -> int:
        key = f"{side}::{label}"
        if key not in label_index:
            label_index[key] = len(labels)
            display = label if len(label) <= 34 else f"{label[:31]}..."
            if side == "tobe" and display.startswith("Extract "):
                display = display[8:]
            prefix = "AS-IS" if side == "asis" else "TO-BE"
            labels.append(f"{prefix}: {display}")
            node_sides.append(side)
        return label_index[key]

    sources: list[int] = []
    targets: list[int] = []
    values: list[int] = []
    link_colors: list[str] = []

    kind_colors = {
        "adr": "rgba(76, 120, 168, 0.55)",
        "phase": "rgba(238, 202, 59, 0.55)",
        "unmapped": "rgba(176, 176, 176, 0.45)",
    }

    for edge in migration_edges:
        src_label = _short_service_label(str(edge["source"]))
        tgt_label = _normalize_sankey_target(str(edge["target"]))
        kind = str(edge.get("kind") or "adr")
        src_i = register(src_label, "asis")
        tgt_i = register(tgt_label, "tobe")
        sources.append(src_i)
        targets.append(tgt_i)
        values.append(1)
        link_colors.append(kind_colors.get(kind, kind_colors["adr"]))

    node_colors: list[str] = []
    for i, side in enumerate(node_sides):
        if side == "asis":
            node_colors.append("rgb(55, 95, 138)")
        elif labels[i].startswith("TO-BE: Unmapped"):
            node_colors.append("rgb(120, 120, 120)")
        else:
            node_colors.append("rgb(52, 128, 72)")

    label_count = len(labels)
    max_label_len = max((len(lbl) for lbl in labels), default=20)
    side_margin = min(220, max(72, max_label_len * 5))
    fig = go.Figure(
        go.Sankey(
            arrangement="perpendicular",
            orientation="h",
            hoverlabel=dict(
                bgcolor=plot_bgcolor,
                bordercolor=label_color,
                font=dict(color=label_color, size=13),
            ),
            node=dict(
                label=labels,
                hovertemplate="<b>%{label}</b><extra></extra>",
                pad=20,
                thickness=20,
                color=node_colors,
                line=dict(color="rgba(80, 80, 80, 0.5)", width=0.6),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
            ),
        )
    )
    fig.update_layout(
        title=dict(text="AS-IS → TO-BE consolidation flow", font=dict(size=16, color=label_color)),
        font=dict(size=14, color=label_color),
        height=max(480, label_count * 40 + 120),
        margin=dict(l=side_margin, r=side_margin, t=56, b=36),
        paper_bgcolor=paper_bgcolor,
        plot_bgcolor=plot_bgcolor,
        template=None,
        uirevision="migration-sankey",
    )
    return fig


def build_plotly_as_is_to_be(
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
) -> Any:
    """Deprecated hub graph — delegates to side-by-side layout."""
    from migrate_framework.ui.transition_map import build_migration_edges

    edges = build_migration_edges(bounded_contexts, adrs, plan_phases)
    return build_plotly_side_by_side_transition(bounded_contexts, edges)


def build_plotly_smell_summary(smells: list[dict[str, Any]]) -> Any:
    if go is None:
        raise RuntimeError("plotly is required")
    if not smells:
        fig = go.Figure()
        fig.update_layout(title="No smells documented", height=280)
        return fig

    from collections import Counter

    counts = Counter()
    for row in smells:
        label = row.get("summary_label") or row.get("title") or row.get("smell") or row.get("type") or "unknown"
        counts[str(label)] += 1

    labels = list(counts.keys())
    values = list(counts.values())
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color="#E45756",
            hovertemplate="<b>%{y}</b><br>count: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=36, b=10),
        height=max(280, len(labels) * 28 + 60),
        title="Smell distribution",
        xaxis_title="Count",
        yaxis=dict(autorange="reversed"),
    )
    return fig


def build_plotly_gate_donut(
    project: MigrationProject,
    completed: set[PipelineStage],
) -> Any:
    if go is None:
        raise RuntimeError("plotly is required")

    cleared, pending, waived = 0, 0, 0
    for gate in approval_gates_for_display(project):
        if gate.status == GateDecisionStatus.WAIVED:
            waived += 1
        elif gate.is_cleared():
            cleared += 1
        else:
            pending += 1

    labels = ["Cleared", "Pending", "Waived"]
    values = [cleared, pending, waived]
    colors = ["#54A24B", "#F58518", "#B0B0B0"]
    if sum(values) == 0:
        fig = go.Figure()
        fig.update_layout(title="No approval gates", height=280)
        return fig

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=colors),
            hovertemplate="<b>%{label}</b><br>%{value}<extra></extra>",
        )
    )
    fig.update_layout(title="Approval gates", height=280, showlegend=True)
    return fig


def build_plotly_plan_timeline(plan_phases: list[dict[str, Any]]) -> Any:
    """Horizontal phase timeline for plan / playbook stages."""
    if go is None:
        raise RuntimeError("plotly is required")
    if not plan_phases:
        fig = go.Figure()
        fig.update_layout(title="No migration phases", height=220)
        return fig

    labels = []
    risks = []
    colors = []
    risk_color = {"high": "#E45756", "medium": "#F58518", "low": "#54A24B"}
    for phase in plan_phases[:12]:
        name = str(phase.get("name") or phase.get("phase") or "Phase")
        labels.append(name[:32] + ("..." if len(name) > 32 else ""))
        risk = str(phase.get("risk") or "medium").lower()
        risks.append(risk)
        colors.append(risk_color.get(risk, "#4C78A8"))

    xs = list(range(len(labels)))
    fig = go.Figure(
        go.Bar(
            x=xs,
            y=[1] * len(labels),
            text=labels,
            textposition="outside",
            marker_color=colors,
            hovertext=[f"{labels[i]} ({risks[i]})" for i in range(len(labels))],
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title="Migration phase timeline",
        height=260,
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0, 1.8]),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def build_mermaid_pipeline_journey(
    project: MigrationProject,
    completed: set[PipelineStage],
) -> str:
    lines = ["flowchart LR"]
    node_lines: list[str] = []
    edge_lines: list[str] = []
    class_lines: list[str] = []
    gates = {g.stage: g for g in approval_gates_for_display(project)}
    for index, stage in enumerate(PIPELINE_STAGE_ORDER):
        sid = _mermaid_node_id(stage.value, "stage")
        if stage in completed:
            status = "done"
        elif stage == project.current_stage:
            status = "current"
        else:
            status = "pending"
        gate = gates.get(stage)
        gate_note = ""
        if gate:
            gate_note = f" - {_gate_short_label(gate, completed)}"
        label = _mermaid_safe_label(f"{stage.value}{gate_note}")
        node_lines.append(f"  {sid}[\"{label}\"]")
        class_lines.append(f"  class {sid} {status}")
        if index > 0:
            prev = _mermaid_node_id(PIPELINE_STAGE_ORDER[index - 1].value, "stage")
            edge_lines.append(f"  {prev} --> {sid}")
    lines.extend(node_lines)
    lines.extend(edge_lines)
    lines.extend(class_lines)
    lines.extend(
        [
            "  classDef done fill:#d4edda,stroke:#28a745",
            "  classDef current fill:#fff3cd,stroke:#ffc107",
            "  classDef pending fill:#f8f9fa,stroke:#6c757d",
        ]
    )
    return "\n".join(lines)


def build_mermaid_bounded_context_map(
    bank_name: str,
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
) -> str:
    """Flowchart tree — more reliable than mindmap for names with spaces."""
    highlight_services = highlight_services or set()
    root_id = _mermaid_node_id(bank_name or "landscape", "bank")
    lines = [
        "flowchart TB",
        f"  {root_id}[\"{_mermaid_safe_label(bank_name or 'Landscape')}\"]",
    ]
    for ctx in bounded_contexts:
        ctx_name = str(ctx.get("context") or "Context")
        ctx_id = _mermaid_node_id(ctx_name, "ctx")
        lines.append(f"  {root_id} --> {ctx_id}")
        lines.append(f"  {ctx_id}[\"{_mermaid_safe_label(ctx_name)}\"]")
        for service in ctx.get("services") or []:
            svc = str(service)
            svc_id = _mermaid_node_id(svc, "svc")
            marker = " !" if svc in highlight_services else ""
            lines.append(f"  {ctx_id} --> {svc_id}")
            lines.append(f"  {svc_id}[\"{_mermaid_safe_label(svc)}{marker}\"]")
    return "\n".join(lines)


def build_mermaid_sync_chains(coupling: dict[str, Any], limit: int = 6) -> str:
    chains = coupling.get("sync_chains", [])[:limit]
    if not chains:
        return "flowchart LR\n  empty[\"No sync chains detected\"]"
    nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    for chain in chains:
        for left, right in zip(chain, chain[1:], strict=False):
            nodes.add(str(left))
            nodes.add(str(right))
            edges.append((str(left), str(right)))
    lines = ["flowchart LR"]
    for node in sorted(nodes):
        nid = _mermaid_node_id(node, "svc")
        lines.append(f"  {nid}[\"{_mermaid_safe_label(node)}\"]")
    for src, tgt in edges:
        lines.append(f"  {_mermaid_node_id(src, 'svc')} --> {_mermaid_node_id(tgt, 'svc')}")
    return "\n".join(lines)


def build_mermaid_as_is_to_be(
    bounded_contexts: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    plan_phases: list[dict[str, Any]] | None = None,
) -> str:
    lines = ["flowchart TB", "  subgraph asis_sg [AS-IS granular services]"]
    for ctx in bounded_contexts:
        ctx_id = _mermaid_node_id(str(ctx.get("context")), "ctx")
        ctx_label = _mermaid_safe_label(str(ctx.get("context")))
        lines.append(f"    subgraph {ctx_id} [\"{ctx_label}\"]")
        for svc in (ctx.get("services") or [])[:8]:
            svc_id = _mermaid_node_id(str(svc), "svc")
            lines.append(f"      {svc_id}[\"{_mermaid_safe_label(str(svc))}\"]")
        lines.append("    end")
    lines.append("  end")
    lines.append("  subgraph tobe_sg [TO-BE proposals]")
    for adr in adrs[:6]:
        title = _mermaid_safe_label(str(adr.get("title") or "ADR"))
        adr_id = _mermaid_node_id(title, "adr")
        lines.append(f"    {adr_id}[\"{title}\"]")
    lines.append("  end")
    lines.append("  asis_sg --> tobe_sg")
    if plan_phases:
        for phase in plan_phases[:4]:
            name = _mermaid_safe_label(str(phase.get("name") or phase.get("phase") or "Phase"))
            phase_id = _mermaid_node_id(name, "phase")
            lines.append(f"  tobe_sg --> {phase_id}[\"{name}\"]")
    return "\n".join(lines)


def mermaid_html(chart_id: str, mermaid_src: str, height: int = 360) -> str:
    escaped = json.dumps(mermaid_src)
    render_id = _safe_id(chart_id)
    wrap_id = f"{render_id}_wrap"
    return f"""
<div id="{wrap_id}" style="width:100%;min-height:{height}px;"></div>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' }});
  const src = {escaped};
  const wrap = document.getElementById('{wrap_id}');
  try {{
    const {{ svg }} = await mermaid.render('{render_id}', src);
    wrap.innerHTML = svg;
  }} catch (err) {{
    wrap.innerHTML = '<p style="color:#b00020;font-size:0.9rem;">Diagram could not be rendered: '
      + err.message + '</p>';
  }}
</script>
"""
