"""Tests for interactive HTML graph builders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from migrate_framework.ui.interactive_graphs import (
    build_cytoscape_service_graph_html,
    build_radial_mindmap_html,
)


@pytest.fixture
def graph_payload() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / "projects" / "proj-af9edb10e11c" / "artifacts" / "graph" / "service-graph.json"
    if not path.exists():
        pytest.skip("sample graph artifact missing")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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
