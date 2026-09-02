"""Tests for ingest evidence summarization."""

from __future__ import annotations

import json
from pathlib import Path

from migrate_framework.reporting.ingest_evidence import summarize_ingest_evidence


def test_summarize_sample_project_evidence() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence_path = root / "projects" / "proj-af9edb10e11c" / "artifacts" / "ingest" / "evidence.json"
    if not evidence_path.exists():
        return

    with evidence_path.open(encoding="utf-8") as handle:
        items = json.load(handle)

    summary = summarize_ingest_evidence(items, adapters_used="java-spring")
    assert summary["evidence_count"] == len(items)
    assert summary["service_count"] >= 1
    assert summary["by_type"]["api_endpoint"] > 0
    assert summary["readiness"]["services_discovered"]
    assert summary["service_catalogue"]
    row_with_smells = next(
        (row for row in summary["service_catalogue"] if row.get("documented_smells") != "—"),
        None,
    )
    assert row_with_smells is not None
    smell = summary["landscape_smells"][0]
    assert smell.get("description")
    assert smell.get("migration_impact")


def test_merge_service_evidence_prefers_metadata() -> None:
    items = [
        {
            "type": "service",
            "source": "metadata",
            "subject": "customer-identity-service",
            "attributes": {
                "port": 8101,
                "database": "customer_db",
                "tables": ["customers"],
                "team": "customer-squad",
            },
        },
        {
            "type": "service",
            "source": "openapi",
            "subject": "customer-identity-service",
            "attributes": {"spec_path": "openapi.yaml", "title": "Customer"},
        },
    ]
    summary = summarize_ingest_evidence(items)
    row = summary["service_catalogue"][0]
    assert row["service"] == "customer-identity-service"
    assert row["documented_smells"] == "—"
    assert row["api_endpoints"] == 0
    assert row["api_paths"] == []


def test_summarize_empty_evidence() -> None:
    summary = summarize_ingest_evidence([])
    assert summary["evidence_count"] == 0
    assert summary["service_count"] == 0
    assert summary["readiness_score"] == "0/8"
