"""Tests for visualization builders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from migrate_framework.ui.visualizations import (
    build_mermaid_bounded_context_map,
    build_mermaid_pipeline_journey,
    build_plotly_bounded_context_tree,
    build_plotly_pipeline_journey,
    build_plotly_service_graph,
    build_plotly_smell_summary,
    mermaid_html,
)


@pytest.fixture
def graph_payload() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / "projects" / "proj-af9edb10e11c" / "artifacts" / "graph" / "service-graph.json"
    if not path.exists():
        pytest.skip("sample graph artifact missing")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_mermaid_html_wraps_source() -> None:
    html = mermaid_html("test-chart", "flowchart LR\n  a-->b")
    assert "test-chart" in html
    assert "mermaid" in html


def test_bounded_context_map() -> None:
    src = build_mermaid_bounded_context_map(
        "EuroSA Bank",
        [{"context": "Customer Management", "services": ["customer-identity-service"]}],
    )
    assert "flowchart TB" in src
    assert "Customer Management" in src
    assert "customer-identity-service" in src
    assert "'" not in src or "Consolidate" not in src


def test_pipeline_journey_avoids_reserved_graph_id() -> None:
    from migrate_framework.models import MigrationProject, PipelineStage

    project = MigrationProject(name="test", source_root="/tmp", landscape_manifest_path="/tmp/m.yaml")
    src = build_mermaid_pipeline_journey(project, set(PipelineStage))
    assert "stage_graph[" in src
    assert "\n  graph[" not in src
    assert src.startswith("flowchart LR")


def test_plotly_pipeline_journey_has_customdata() -> None:
    from migrate_framework.models import MigrationProject, PipelineStage

    project = MigrationProject(name="test", source_root="/tmp", landscape_manifest_path="/tmp/m.yaml")
    fig = build_plotly_pipeline_journey(project, set(PipelineStage))
    assert len(fig.data) >= 2
    node_trace = fig.data[-1]
    assert "graph" in node_trace.customdata


def test_plotly_bounded_context_tree() -> None:
    fig = build_plotly_bounded_context_tree(
        "EuroSA Bank",
        [{"context": "Customer Management", "services": ["customer-identity-service"]}],
    )
    assert len(fig.data) >= 2


def test_plotly_smell_summary() -> None:
    fig = build_plotly_smell_summary(
        [{"smell": "shared_database", "summary_label": "Shared DB"}],
    )
    assert len(fig.data) == 1


def test_plotly_plan_timeline() -> None:
    from migrate_framework.ui.visualizations import build_plotly_plan_timeline

    fig = build_plotly_plan_timeline([{"name": "Phase 1", "risk": "high"}, {"name": "Phase 2", "risk": "low"}])
    assert len(fig.data) == 1


def test_plotly_service_graph_nodes(graph_payload: dict) -> None:
    fig = build_plotly_service_graph(graph_payload)
    assert len(fig.data) >= 1
