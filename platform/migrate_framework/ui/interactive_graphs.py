"""Interactive HTML graph builders (Cytoscape, D3) for Streamlit embeds."""

from __future__ import annotations

import json
from typing import Any

import streamlit.components.v1 as components

from migrate_framework.ui.visualizations import (
    _is_deployable_service_node,
    _safe_id,
    _service_color,
)

_GRAPH_THEME: dict[str, dict[str, str]] = {
    "light": {
        "canvas_bg": "#fafafa",
        "border": "#e0e0e0",
        "edge": "#888",
        "arrow": "#888",
        "node_border": "#333",
        "node_label": "#262730",
        "selected_border": "#2C3E50",
    },
    "dark": {
        "canvas_bg": "#262730",
        "border": "#464646",
        "edge": "#9aa0a6",
        "arrow": "#9aa0a6",
        "node_border": "#bdc1c6",
        "node_label": "#fafafa",
        "selected_border": "#fafafa",
    },
}


def graph_theme_colors(theme_type: str | None = None) -> dict[str, str]:
    """Resolve canvas/label colors from Streamlit theme type (light/dark)."""
    if theme_type == "dark":
        return _GRAPH_THEME["dark"]
    return _GRAPH_THEME["light"]


def _cytoscape_theme_script(render_id: str) -> str:
    """Client-side theme: read parent app background (iframe bg is not reliable)."""
    themes_json = json.dumps(_GRAPH_THEME)
    return f"""
  const THEMES = {themes_json};
  function _parseRgb(color) {{
    const m = String(color).match(/[\\d.]+/g);
    if (!m || m.length < 3) return null;
    return {{ r: Number(m[0]), g: Number(m[1]), b: Number(m[2]) }};
  }}
  function _isDarkBackground(color) {{
    const rgb = _parseRgb(color);
    if (!rgb) return false;
    const lum = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    return lum < 0.45;
  }}
  function _resolveTheme() {{
    try {{
      const parentBody = window.parent && window.parent.document && window.parent.document.body;
      if (parentBody) {{
        const parentBg = getComputedStyle(parentBody).backgroundColor;
        return _isDarkBackground(parentBg) ? THEMES.dark : THEMES.light;
      }}
    }} catch (err) {{
      /* parent access blocked — default to light canvas */
    }}
    return THEMES.light;
  }}
  const theme = _resolveTheme();
  const container = document.getElementById('{render_id}');
  container.style.background = theme.canvas_bg;
  container.style.borderColor = theme.border;
"""


def interactive_graph_html(chart_id: str, html_content: str, height: int = 480) -> None:
    """Render raw HTML/JS in Streamlit with a unique wrapper id."""
    render_id = _safe_id(chart_id)
    wrapped = f'<div id="{render_id}_root" class="ctx-atlas-graph">{html_content}</div>'
    components.html(wrapped, height=height, scrolling=False)


def _service_graph_elements(
    graph_payload: dict[str, Any],
    ingest_summary: dict[str, Any] | None,
    *,
    color_mode: str,
    focus_services: set[str] | None,
    highlight_services: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = graph_payload.get("nodes", [])
    edges = graph_payload.get("edges", [])
    deployable = [n for n in nodes if _is_deployable_service_node(n)]
    if focus_services:
        deployable = [n for n in deployable if n.get("id") in focus_services]
    service_ids = {n.get("id") for n in deployable}
    catalogue = {row["service"]: row for row in (ingest_summary or {}).get("service_catalogue") or []}

    cy_nodes: list[dict[str, Any]] = []
    for node in deployable:
        node_id = str(node.get("id"))
        attrs = node.get("attributes", {})
        cat = catalogue.get(node_id, {})
        cy_nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": node_id.replace("-service", ""),
                    "color": _service_color(node_id, ingest_summary, color_mode),
                    "highlight": node_id in highlight_services,
                    "db": attrs.get("database") or "—",
                    "smells": cat.get("documented_smells", "—"),
                    "apis": cat.get("api_endpoints", 0),
                }
            }
        )

    cy_edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        src, tgt = str(edge.get("source")), str(edge.get("target"))
        if src in service_ids and tgt in service_ids and (src, tgt) not in seen:
            seen.add((src, tgt))
            cy_edges.append({"data": {"source": src, "target": tgt}})

    return cy_nodes, cy_edges


def build_cytoscape_service_graph_html(
    graph_payload: dict[str, Any],
    ingest_summary: dict[str, Any] | None = None,
    *,
    chart_id: str = "service-graph",
    color_mode: str = "risk",
    focus_services: set[str] | None = None,
    highlight_services: set[str] | None = None,
    height: int = 480,
    theme_type: str | None = None,
) -> str:
    """Cytoscape.js service dependency graph with physics layout."""
    highlight_services = highlight_services or set()
    # theme_type kept for tests; runtime theme resolved in embedded JS from parent app.
    _ = theme_type
    cy_nodes, cy_edges = _service_graph_elements(
        graph_payload,
        ingest_summary,
        color_mode=color_mode,
        focus_services=focus_services,
        highlight_services=highlight_services,
    )
    if not cy_nodes:
        return '<p style="color:#666;font-size:0.9rem;">No deployable services in graph.</p>'

    render_id = _safe_id(chart_id)
    elements = json.dumps(cy_nodes + cy_edges)
    return f"""
<style>
  html, body {{
    margin: 0;
    background: transparent;
  }}
  #{render_id} {{
    width: 100%;
    height: {height}px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background: #fafafa;
  }}
</style>
<div id="{render_id}"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<script>
(function() {{
{_cytoscape_theme_script(render_id)}
  const elements = {elements};
  const cy = cytoscape({{
    container: container,
    elements: elements,
    style: [
      {{
        selector: 'node',
        style: {{
          'label': 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'font-size': '10px',
          'color': theme.node_label,
          'background-color': 'data(color)',
          'width': 28,
          'height': 28,
          'border-width': 2,
          'border-color': theme.node_border,
          'text-margin-y': 4,
        }}
      }},
      {{
        selector: 'node[?highlight]',
        style: {{
          'width': 36,
          'height': 36,
          'border-width': 4,
          'border-color': '#E45756',
          'z-index': 10,
        }}
      }},
      {{
        selector: 'edge',
        style: {{
          'width': 1.5,
          'line-color': theme.edge,
          'target-arrow-color': theme.arrow,
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.8,
        }}
      }},
      {{
        selector: 'node:selected',
        style: {{
          'border-width': 4,
          'border-color': theme.selected_border,
        }}
      }}
    ],
    layout: {{
      name: 'cose',
      animate: true,
      animationDuration: 800,
      nodeRepulsion: 8000,
      idealEdgeLength: 90,
      gravity: 0.25,
      numIter: 1000,
    }},
    wheelSensitivity: 0.2,
  }});

  cy.on('tap', 'node', function(evt) {{
    const n = evt.target;
    const tip = n.data('label') + '\\nDB: ' + n.data('db')
      + '\\nSmells: ' + n.data('smells') + '\\nAPIs: ' + n.data('apis');
    n.popperRef = tip;
  }});
}})();
</script>
"""


def build_radial_mindmap_html(
    bank_name: str,
    bounded_contexts: list[dict[str, Any]],
    *,
    chart_id: str = "context-mindmap",
    highlight_services: set[str] | None = None,
    height: int = 420,
) -> str:
    """D3 radial tree mind-map for bounded contexts and services."""
    highlight_services = highlight_services or set()
    root_name = bank_name or "Landscape"
    children: list[dict[str, Any]] = []
    palette = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B", "#B279A2"]
    for index, ctx in enumerate(bounded_contexts):
        ctx_name = str(ctx.get("context") or "Context")
        svc_nodes = []
        for svc in ctx.get("services") or []:
            svc = str(svc)
            svc_nodes.append(
                {
                    "name": svc.replace("-service", ""),
                    "id": svc,
                    "highlight": svc in highlight_services,
                }
            )
        children.append(
            {
                "name": ctx_name,
                "color": palette[index % len(palette)],
                "children": svc_nodes,
            }
        )

    if not children:
        return '<p style="color:#666;font-size:0.9rem;">No bounded contexts to display.</p>'

    tree_data = {"name": root_name, "children": children}
    render_id = _safe_id(chart_id)
    data_json = json.dumps(tree_data)
    return f"""
<style>
  #{render_id} svg {{ width: 100%; height: {height}px; }}
  #{render_id} .link {{ fill: none; stroke: #bbb; stroke-width: 1.5px; }}
  #{render_id} .node circle {{ stroke: #333; stroke-width: 1.5px; cursor: pointer; }}
  #{render_id} .node text {{ font-size: 11px; font-family: sans-serif; }}
  #{render_id} .node.highlight circle {{
    stroke: #E45756;
    stroke-width: 3px;
    animation: ctx-mm-pulse 1.2s ease-in-out infinite;
  }}
  @keyframes ctx-mm-pulse {{
    0%, 100% {{ r: 6; fill-opacity: 1; }}
    50% {{ r: 9; fill-opacity: 0.85; }}
  }}
  #{render_id} .node.root circle {{ fill: #2C3E50; r: 10; }}
</style>
<div id="{render_id}"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script>
(function() {{
  const data = {data_json};
  const width = document.getElementById('{render_id}').clientWidth || 640;
  const height = {height};
  const radius = Math.min(width, height) / 2 - 40;

  const svg = d3.select('#{render_id}')
    .append('svg')
    .attr('viewBox', [-width / 2, -height / 2, width, height]);

  const root = d3.hierarchy(data);
  root.x0 = 0;
  root.y0 = 0;

  const tree = d3.tree().size([2 * Math.PI, radius]);
  root.descendants().forEach((d, i) => {{ d.id = i; }});
  tree(root);

  const colorOf = (d) => {{
    if (d.depth === 0) return '#2C3E50';
    if (d.depth === 1) return d.data.color || '#4C78A8';
    if (d.data.highlight) return '#E45756';
    const parent = d.parent;
    return parent && parent.data.color ? parent.data.color : '#72B7B2';
  }};

  svg.append('g')
    .selectAll('path')
    .data(root.links())
    .join('path')
    .attr('class', 'link')
    .attr('d', d3.linkRadial()
      .angle(d => d.x)
      .radius(d => d.y));

  const node = svg.append('g')
    .selectAll('g')
    .data(root.descendants())
    .join('g')
    .attr('class', d => {{
      let cls = 'node';
      if (d.depth === 0) cls += ' root';
      if (d.data.highlight) cls += ' highlight';
      return cls;
    }})
    .attr('transform', d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`);

  node.append('circle')
    .attr('r', d => d.depth === 0 ? 10 : (d.data.highlight ? 7 : 5))
    .attr('fill', colorOf);

  node.append('text')
    .attr('dy', '0.31em')
    .attr('x', d => d.x < Math.PI === !d.children ? 8 : -8)
    .attr('text-anchor', d => d.x < Math.PI === !d.children ? 'start' : 'end')
    .attr('transform', d => d.x >= Math.PI ? 'rotate(180)' : null)
    .text(d => d.data.name)
    .clone(true).lower()
    .attr('stroke', 'white')
    .attr('stroke-width', 3);
}})();
</script>
"""


def render_interactive_service_graph(
    chart_key: str,
    graph_payload: dict[str, Any],
    ingest_summary: dict[str, Any] | None = None,
    *,
    color_mode: str = "risk",
    focus_services: set[str] | None = None,
    highlight_services: set[str] | None = None,
    height: int = 480,
) -> None:
    """Build and embed Cytoscape service graph."""
    html = build_cytoscape_service_graph_html(
        graph_payload,
        ingest_summary,
        chart_id=chart_key,
        color_mode=color_mode,
        focus_services=focus_services,
        highlight_services=highlight_services,
        height=height,
    )
    interactive_graph_html(chart_key, html, height=height + 8)


def render_radial_context_map(
    chart_key: str,
    bank_name: str,
    bounded_contexts: list[dict[str, Any]],
    *,
    highlight_services: set[str] | None = None,
    height: int = 420,
) -> None:
    """Deprecated: use render_bounded_context_map in context_map.py."""
    from migrate_framework.ui.context_map import render_bounded_context_map

    render_bounded_context_map(
        chart_key,
        bank_name,
        bounded_contexts,
        highlight_services=highlight_services,
        tree_height=height,
    )
