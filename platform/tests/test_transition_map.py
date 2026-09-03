"""Tests for AS-IS → TO-BE transition map helpers."""

from __future__ import annotations

from migrate_framework.ui.transition_map import (
    build_migration_edges,
    build_migration_legend_rows,
    build_transition_summary_metrics,
)
from migrate_framework.ui.visualizations import (
    build_plotly_migration_sankey,
    build_plotly_side_by_side_transition,
)


def _sample_contexts() -> list[dict]:
    return [
        {
            "context": "Customer Management",
            "services": [
                "customer-identity-service",
                "customer-address-service",
                "customer-contact-service",
            ],
        },
        {
            "context": "Account Management",
            "services": ["account-service"],
        },
    ]


def _sample_adrs() -> list[dict]:
    return [
        {
            "id": "adr-1",
            "title": "ADR-001: Customer consolidation",
            "target_context": "Customer Management",
            "affected_services": [
                "customer-identity-service",
                "customer-address-service",
                "customer-contact-service",
            ],
            "mandatory": True,
        },
        {
            "id": "adr-2",
            "title": "ADR-002: Account consolidation",
            "target_context": "Account Management",
            "affected_services": ["account-service"],
            "mandatory": False,
        },
    ]


def test_build_migration_edges_from_adrs() -> None:
    contexts = _sample_contexts()
    adrs = _sample_adrs()
    edges = build_migration_edges(contexts, adrs, [])
    adr_edges = [e for e in edges if e["kind"] == "adr"]
    assert len(adr_edges) == 4
    assert any(
        e["source"] == "customer-identity-service" and e["target"] == "Customer Management"
        for e in adr_edges
    )


def test_build_migration_edges_unmapped() -> None:
    contexts = _sample_contexts()
    edges = build_migration_edges(contexts, [], [])
    assert len(edges) == 4
    assert all(e["kind"] == "unmapped" for e in edges)


def test_build_migration_legend_rows() -> None:
    contexts = _sample_contexts()
    adrs = _sample_adrs()
    edges = build_migration_edges(contexts, adrs, [])
    rows = build_migration_legend_rows(edges)
    assert len(rows) == 4
    assert "customer-identity" in {r["as_is_service"] for r in rows}
    assert "Customer Management" in {r["to_be_target"] for r in rows}


def test_build_migration_edges_phase_mapping() -> None:
    contexts = _sample_contexts()
    phases = [
        {
            "name": "Customer Management",
            "services": ["customer-identity-service"],
        },
    ]
    edges = build_migration_edges(contexts, [], phases)
    assert any(e["kind"] == "phase" for e in edges)


def test_transition_summary_metrics() -> None:
    contexts = _sample_contexts()
    adrs = _sample_adrs()
    edges = build_migration_edges(contexts, adrs, [])
    metrics = build_transition_summary_metrics(contexts, edges, adrs, [])
    assert metrics["service_count"] == 4
    assert metrics["target_context_count"] == 2
    assert metrics["mandatory_adrs"] == 1
    assert metrics["consolidation_ratio"] == 2.0


def test_side_by_side_transition_figure() -> None:
    contexts = _sample_contexts()
    edges = build_migration_edges(contexts, _sample_adrs(), [])
    fig = build_plotly_side_by_side_transition(contexts, edges)
    assert len(fig.data) >= 2
    node_trace = fig.data[-1]
    assert len(node_trace.x) >= 6


def test_migration_sankey_figure() -> None:
    contexts = _sample_contexts()
    edges = build_migration_edges(contexts, _sample_adrs(), [])
    fig = build_plotly_migration_sankey(edges)
    assert len(fig.data) == 1
    assert fig.data[0].link.value
