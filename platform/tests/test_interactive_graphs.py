"""Tests for interactive HTML graph builders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from migrate_framework.ui.interactive_graphs import (
    build_cytoscape_service_graph_html,
    build_radial_mindmap_html,
    graph_metric_summary,
)


@pytest.fixture
def graph_payload() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / "projects" / "proj-af9edb10e11c" / "artifacts" / "graph" / "service-graph.json"
    if not path.exists():
        pytest.skip("sample graph artifact missing")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_graph_metric_summary_separates_deployables_from_knowledge_graph() -> None:
    payload = {
        "nodes": [
            {"id": "a-service", "kind": "service", "attributes": {"evidence_type": "service", "port": 8080}},
            {"id": "b-service", "kind": "service", "attributes": {"evidence_type": "service", "port": 8081}},
            {"id": "db:shared", "kind": "database", "attributes": {"evidence_type": "database"}},
            {"id": "api:/health", "kind": "api", "attributes": {"evidence_type": "api_endpoint"}},
        ],
        "edges": [{"source": "a-service", "target": "db:shared", "kind": "stores_in"}],
        "metrics": {
            "node_count": 4,
            "edge_count": 1,
            "service_nodes": 2,
            "density": 0.5,
        },
    }
    summary = graph_metric_summary(payload)
    assert summary["deployable_services"] == 2
    assert summary["knowledge_graph_nodes"] == 4
    assert summary["knowledge_graph_edges"] == 1


def test_cytoscape_service_graph_contains_node_ids(graph_payload: dict) -> None:
    html = build_cytoscape_service_graph_html(
        graph_payload,
        chart_id="test-svc-graph",
        highlight_services={"customer-identity-service"},
    )
    assert html
    assert "cytoscape" in html
    assert "test-svc-graph" in html
    assert "customer-identity-service" in html
    assert '"highlight": true' in html or '"highlight":true' in html.replace(" ", "")


def test_cytoscape_empty_graph_message() -> None:
    html = build_cytoscape_service_graph_html({"nodes": [], "edges": []})
    assert "No deployable services" in html


def test_cytoscape_embeds_client_theme_resolver(graph_payload: dict) -> None:
    html = build_cytoscape_service_graph_html(graph_payload, chart_id="theme-graph")
    assert "_resolveTheme" in html
    assert '"canvas_bg"' in html
    assert "#fafafa" in html
    assert "#262730" in html


def test_cytoscape_dark_theme_background() -> None:
    html = build_cytoscape_service_graph_html(
        {
            "nodes": [
                {
                    "id": "a-service",
                    "kind": "service",
                    "attributes": {"evidence_type": "service", "port": 8080},
                }
            ],
            "edges": [],
        },
        chart_id="dark-graph",
        theme_type="dark",
    )
    assert "#262730" in html


def test_graph_theme_colors_dark() -> None:
    from migrate_framework.ui.interactive_graphs import graph_theme_colors

    dark = graph_theme_colors("dark")
    assert dark["canvas_bg"] == "#262730"
    html = build_cytoscape_service_graph_html({"nodes": [], "edges": []})
    assert "No deployable services" in html


def test_radial_mindmap_contains_context_and_services() -> None:
    contexts = [
        {
            "context": "Customer Management",
            "services": ["customer-identity-service", "customer-profile-service"],
        }
    ]
    html = build_radial_mindmap_html(
        "EuroSA Bank",
        contexts,
        chart_id="test-mindmap",
        highlight_services={"customer-identity-service"},
    )
    assert html
    assert "d3" in html
    assert "test-mindmap" in html
    assert "Customer Management" in html
    assert "customer-identity-service" in html
    assert '"highlight": true' in html or '"highlight":true' in html.replace(" ", "")


def test_radial_mindmap_empty_contexts() -> None:
    html = build_radial_mindmap_html("EuroSA Bank", [])
    assert "No bounded contexts" in html
