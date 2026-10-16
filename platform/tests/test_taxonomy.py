"""Tests for UI taxonomy classification."""

from __future__ import annotations

from migrate_framework.models import PipelineStage
from migrate_framework.ui.taxonomy import (
    classify_evidence_item,
    classify_service,
    classify_smell_risk,
    ENTITY_REGISTRY,
    EvidenceCategory,
    classify_evidence_type,
    filter_entities,
    stage_visual_components,
    stage_visual_spec,
    RiskClass,
)


def test_classify_evidence_type() -> None:
    assert classify_evidence_type("api_endpoint") == EvidenceCategory.API
    assert classify_evidence_type("landscape_smell") == EvidenceCategory.SMELL


def test_classify_evidence_item_tags() -> None:
    tags = classify_evidence_item(
        {"type": "landscape_smell", "attributes": {"smell": "shared_database"}},
    )
    assert "smell" in tags
    assert "risk:high" in tags


def test_classify_service_rolls_up_context() -> None:
    ingest = {
        "service_catalogue": [{"service": "a-service", "smell_count": 1, "smell_ids": ["shared_database"]}],
        "bounded_contexts": [{"context": "Payments", "services": ["a-service"]}],
    }
    info = classify_service("a-service", ingest)
    assert info["context"] == "Payments"
    assert info["risk"] == "high"


def test_stage_visual_spec() -> None:
    spec = stage_visual_spec(PipelineStage.PLAN)
    assert "plan_timeline" in spec["l0_components"]
    assert "phase_risk" in spec["l1_panels"]


def test_entity_registry_has_service() -> None:
    assert ENTITY_REGISTRY["service"]["stage"] == "ingest"


def test_filter_entities_by_context() -> None:
    smells = [
        {"service": "a-service", "smell": "shared_database"},
        {"service": "b-service", "smell": "customer_in_api_name"},
    ]
    contexts = [{"context": "Payments", "services": ["a-service"]}]
    filtered = filter_entities(smells, context="Payments", bounded_contexts=contexts)
    assert len(filtered) == 1
    assert filtered[0]["service"] == "a-service"


def test_classify_smell_risk() -> None:
    assert classify_smell_risk("shared_database") == RiskClass.HIGH
    assert classify_smell_risk("customer_in_api_name") == RiskClass.LOW


def test_stage_visual_components_ingest() -> None:
    components = stage_visual_components(PipelineStage.INGEST)
    assert "service_graph" in components
    assert "context_map" in components
    assert "smell_overlay" in components
