"""Opt-in REA capture Evidence adapter tests.

The checked-in example is a documented-shape fixture, not live REA output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from migrate_framework.ingestion.adapters.shared.rea_capture_adapter import (
    REA_EVIDENCE_ENV,
    ReaCaptureAdapter,
    ReaCaptureInputError,
)
from migrate_framework.ingestion.registry import AdapterRegistry
from migrate_framework.ingestion.adapters.shared.trace_adapter import TraceAdapter
from migrate_framework.ingestion.adapters.shared.openapi_adapter import OpenApiAdapter
from migrate_framework.models import TechStackProfile
from migrate_framework.reporting.ingest_evidence import summarize_ingest_evidence


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "rea_har_evidence.documented-shape.example.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_maps_observed_request_and_preserves_provenance_without_payloads() -> None:
    evidence = ReaCaptureAdapter.parse(_fixture(), root=ROOT)

    capture, request = evidence
    assert capture.type == "network_capture"
    assert capture.attributes["coverage_status"] == "unknown"
    assert capture.attributes["record_count_usable"] == 1
    assert request.type == "api_endpoint"
    assert request.source == "rea_capture"
    assert request.subject == "payment-initiation-service:POST /api/payment_initiation"
    assert request.attributes["service"] == "payment-initiation-service"
    assert request.attributes["response_status"] == 201
    assert request.attributes["rea"]["provider"] == "REA"
    assert request.attributes["rea"]["provider_record_id"] == "0"
    assert request.attributes["rea"]["artifact_sha256"] == _fixture()["artifact"]["sha256"]
    assert request.attributes["rea"]["classification"] == "observed_request_record"
    assert [(rel.relation, rel.target) for rel in request.relations] == [
        ("exposes", "payment-initiation-service")
    ]
    serialized = request.model_dump_json()
    for secret in ("fixture-secret-token", "fixture-session-secret", "fixture-customer-data", "customerId=", "?"):
        assert secret not in serialized
    assert "runtime" not in request.tags
    assert "depends_on" not in [relation.relation for relation in request.relations]


def test_repeat_ingestion_has_stable_ids() -> None:
    first = ReaCaptureAdapter.parse(_fixture(), root=ROOT)
    second = ReaCaptureAdapter.parse(_fixture(), root=ROOT)
    assert [item.id for item in first] == [item.id for item in second]


def test_missing_coverage_is_unknown_and_empty_capture_is_retained() -> None:
    payload = _fixture()
    payload["normalized_result"] = {"records": []}
    evidence = ReaCaptureAdapter.parse(payload, root=ROOT)
    assert len(evidence) == 1
    assert evidence[0].type == "network_capture"
    assert evidence[0].attributes["coverage_status"] == "unknown"
    assert evidence[0].attributes["record_count_usable"] == 0


@pytest.mark.parametrize(
    "payload",
    [None, [], {"operation": "inspect_artifact"}, {"operation": "inspect_web_network_capture"}],
)
def test_rejects_malformed_or_unsupported_evidence(payload) -> None:
    with pytest.raises(ReaCaptureInputError):
        ReaCaptureAdapter.parse(payload, root=ROOT)


def test_duplicate_record_ordinals_are_rejected() -> None:
    payload = _fixture()
    payload["normalized_result"]["records"].append(
        payload["normalized_result"]["records"][0]
    )
    with pytest.raises(ReaCaptureInputError, match="Duplicate REA producer record ordinal"):
        ReaCaptureAdapter.parse(payload, root=ROOT)


def test_sensitive_and_identifier_like_path_segments_are_redacted() -> None:
    safe = ReaCaptureAdapter._safe_url(
        "https://user:password@example.test/api/customers/123456789012345678901234?token=secret"
    )
    assert safe == ("example.test", 443, "/api/customers/{redacted}")
    personal = ReaCaptureAdapter._safe_url(
        "https://example.test/api/customer/alex@example.test/+1-212-555-0199"
    )
    assert personal == ("example.test", 443, "/api/customer/{redacted}/{redacted}")


def test_rejects_non_har_provider_evidence() -> None:
    payload = _fixture()
    payload["parameters"]["format"] = "saz"
    with pytest.raises(ReaCaptureInputError, match="HAR inspection Evidence only"):
        ReaCaptureAdapter.parse(payload, root=ROOT)


def test_registry_keeps_provider_disabled_unless_path_is_configured(monkeypatch, tmp_path: Path) -> None:
    registry = AdapterRegistry()
    profile = TechStackProfile(languages=["java"], frameworks=["spring-boot"])
    (tmp_path / "landscape-manifest.yaml").write_text(
        "bank:\n  name: test\nservices: []\n", encoding="utf-8"
    )
    monkeypatch.delenv(REA_EVIDENCE_ENV, raising=False)
    assert "rea_capture" not in {adapter.name for adapter in registry.adapters_for(tmp_path, profile)}

    monkeypatch.setenv(REA_EVIDENCE_ENV, str(FIXTURE))
    assert "rea_capture" in {adapter.name for adapter in registry.adapters_for(tmp_path, profile)}


def test_observed_capture_does_not_create_runtime_trace_readiness() -> None:
    items = ReaCaptureAdapter.parse(_fixture(), root=ROOT)
    summary = summarize_ingest_evidence([item.model_dump(mode="json") for item in items])
    assert summary["by_source"]["rea_capture"] == 2
    assert summary["readiness"]["runtime_traces_present"] is False
    assert summary["observed_api_endpoint_count"] == 1
    assert summary["declared_api_endpoint_count"] == 0


def test_ingest_summary_keeps_openapi_declarations_separate_from_observations() -> None:
    service_root = ROOT / "sample-bank" / "granular-services" / "payment-initiation-service"
    items = OpenApiAdapter().collect(service_root, TechStackProfile())
    items.extend(ReaCaptureAdapter.parse(_fixture(), root=ROOT))
    summary = summarize_ingest_evidence([item.model_dump(mode="json") for item in items])
    assert summary["declared_api_endpoint_count"] == 3
    assert summary["observed_api_endpoint_count"] == 1
    assert summary["unclassified_api_endpoint_count"] == 0


def test_application_config_dependencies_are_not_reported_as_runtime_traces(tmp_path: Path) -> None:
    cfg = tmp_path / "sample-bank" / "granular-services" / "payment-initiation-service" / "src" / "main" / "resources" / "application.yml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        "spring:\n  application:\n    name: payment-initiation-service\neurosa:\n  downstream:\n    account-service: http://localhost:8106\n",
        encoding="utf-8",
    )
    evidence = TraceAdapter().collect(tmp_path, TechStackProfile())
    trace_span = next(item for item in evidence if item.type == "trace_span")
    assert "configured" in trace_span.tags
    assert "runtime" not in trace_span.tags
    summary = summarize_ingest_evidence([item.model_dump(mode="json") for item in evidence])
    assert summary["readiness"]["static_dependencies_present"] is True
    assert summary["readiness"]["runtime_traces_present"] is False


def test_output_types_and_relations_are_in_evidence_schema() -> None:
    schema = json.loads((ROOT / "metadata" / "evidence-schema.json").read_text(encoding="utf-8"))
    allowed_types = set(schema["properties"]["type"]["enum"])
    allowed_relations = set(
        schema["properties"]["relations"]["items"]["properties"]["relation"]["enum"]
    )
    for item in ReaCaptureAdapter.parse(_fixture(), root=ROOT):
        assert item.type in allowed_types
        assert all(rel.relation in allowed_relations for rel in item.relations)


def test_collect_reads_configured_json_artifact(monkeypatch) -> None:
    monkeypatch.setenv(REA_EVIDENCE_ENV, str(FIXTURE))
    evidence = ReaCaptureAdapter().collect(ROOT, TechStackProfile())
    assert [item.type for item in evidence] == ["network_capture", "api_endpoint"]


def test_malformed_json_file_has_actionable_error(monkeypatch, tmp_path: Path) -> None:
    malformed = tmp_path / "rea.json"
    malformed.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv(REA_EVIDENCE_ENV, str(malformed))
    with pytest.raises(ReaCaptureInputError, match="valid UTF-8 JSON"):
        ReaCaptureAdapter().collect(tmp_path, TechStackProfile())


def test_missing_configured_artifact_has_actionable_error(monkeypatch, tmp_path: Path) -> None:
    adapter = ReaCaptureAdapter()
    missing = tmp_path / "missing-rea-output.json"
    monkeypatch.setenv(REA_EVIDENCE_ENV, str(missing))
    with pytest.raises(FileNotFoundError, match=REA_EVIDENCE_ENV):
        adapter.collect(tmp_path, TechStackProfile())
