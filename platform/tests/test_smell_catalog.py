"""Tests for architecture smell catalog."""

from __future__ import annotations

from migrate_framework.analysis.smell_catalog import enrich_landscape_smell, smell_definition, smell_summary_label


def test_smell_definition_known_smell() -> None:
    meta = smell_definition("shared_database")
    assert meta["title"] == "Shared database"
    assert "ownership" in meta["description"].lower()


def test_enrich_landscape_smell_adds_context() -> None:
    row = enrich_landscape_smell(
        "shared_database",
        "customer-identity-service",
        service_record={"database": "customer_db", "team": "customer-squad"},
        db_to_services={"customer_db": ["customer-identity-service", "customer-address-service"]},
    )
    assert row["title"] == "Shared database"
    assert row["database"] == "customer_db"
    assert row["shared_with"] == ["customer-address-service"]
    assert "customer_db" in row["summary_label"]
    assert "customer-address-service" in row["summary_label"]


def test_smell_summary_label_shared_database() -> None:
    label = smell_summary_label(
        "shared_database",
        "account-lifecycle-service",
        service_record={"database": "account_db"},
        db_to_services={
            "account_db": [
                "account-service",
                "account-rules-service",
                "account-lifecycle-service",
            ]
        },
    )
    assert "account_db" in label
    assert "account-service" in label
    assert "account-rules-service" in label
    assert "account-lifecycle-service" not in label.split("shared with")[1]
