"""Tests for dashboard metric reconciliation helpers."""

from __future__ import annotations

from migrate_framework.ui.metric_reconciliation import (
    open_diagnosis_smell_rows,
    service_reconciliation_message,
    services_not_in_bounded_contexts,
    services_on_shared_databases,
    shared_database_cluster_count,
    smell_reconciliation_message,
)


def _sample_ingest() -> dict:
    return {
        "service_count": 16,
        "service_catalogue": [{"service": f"svc-{i}"} for i in range(16)],
        "shared_databases": [
            {"database": "customer_db", "services": ["a", "b", "c"]},
            {"database": "account_db", "services": ["d", "e"]},
        ],
        "landscape_smells": [{"smell": "x"}] * 21,
        "bounded_contexts": [
            {"context": "Ctx", "services": [f"svc-{i}" for i in range(15)]},
        ],
    }


def test_services_not_in_bounded_contexts() -> None:
    ingest = _sample_ingest()
    contexts = ingest["bounded_contexts"]
    missing = services_not_in_bounded_contexts(ingest, contexts)
    assert missing == ["svc-15"]


def test_shared_db_counts() -> None:
    ingest = _sample_ingest()
    assert shared_database_cluster_count(ingest) == 2
    assert services_on_shared_databases(ingest) == {"a", "b", "c", "d", "e"}


def test_service_reconciliation_message_when_gap() -> None:
    ingest = _sample_ingest()
    msg = service_reconciliation_message(ingest, ingest["bounded_contexts"])
    assert msg is not None
    assert "16" in msg
    assert "15" in msg
    assert "svc-15" in msg


def test_smell_reconciliation_message() -> None:
    ingest = _sample_ingest()
    diagnosis = {"smells": [{"governance_status": "open"}] * 45}
    msg = smell_reconciliation_message(ingest, diagnosis)
    assert msg is not None
    assert "21" in msg
    assert "45" in msg


def test_open_diagnosis_smell_rows_excludes_accepted() -> None:
    diagnosis = {
        "smells": [
            {"governance_status": "open"},
            {"governance_status": "accepted"},
        ]
    }
    assert len(open_diagnosis_smell_rows(diagnosis)) == 1
