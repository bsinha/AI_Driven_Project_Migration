"""Tests for bounded-context summary + tree."""

from __future__ import annotations

from migrate_framework.ui.context_map import (
    build_context_summary_rows,
    count_mapped_services,
)
from migrate_framework.ui.visualizations import build_plotly_bounded_context_tree


def test_build_context_summary_rows() -> None:
    contexts = [
        {
            "context": "Customer Management",
            "services": ["customer-identity-service", "customer-address-service"],
        },
        {"context": "Payments", "services": ["payment-initiation-service"]},
    ]
    rows = build_context_summary_rows(
        contexts,
        highlight_services={"customer-identity-service"},
    )
    assert len(rows) == 2
    assert rows[0]["bounded_context"] == "Customer Management"
    assert rows[0]["services"] == 2
    assert rows[0]["shared_db_services"] == 1
    assert rows[1]["services"] == 1


def test_count_mapped_services_unique() -> None:
    contexts = [
        {"context": "A", "services": ["svc-a", "svc-b"]},
        {"context": "B", "services": ["svc-b"]},
    ]
    assert count_mapped_services(contexts) == 2


def test_bounded_context_tree_contexts_only() -> None:
    contexts = [
        {"context": "Customer Management", "services": ["customer-identity-service"]},
    ]
    fig_full = build_plotly_bounded_context_tree("Bank", contexts, show_services=True)
    fig_ctx = build_plotly_bounded_context_tree("Bank", contexts, show_services=False)
    assert len(fig_full.data) >= 2
    assert len(fig_ctx.data) >= 2
    full_trace = fig_full.data[-1]
    ctx_trace = fig_ctx.data[-1]
    assert len(full_trace.x) > len(ctx_trace.x)
