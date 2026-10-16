"""Tests for smell accept/defer governance."""

from migrate_framework.models import MigrationProject
from migrate_framework.pipeline.scope import (
    decide_smell,
    enrich_diagnosis_with_decisions,
    filter_smells_for_planning,
    smell_key,
)


def test_smell_accepted_remains_visible() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        metadata={
            "diagnosis": {
                "smells": [
                    {"type": "shared_database", "services": ["svc-a", "svc-b"], "description": "Shared DB"},
                ]
            }
        },
        approval_gates=MigrationProject.default_gates(),
    )
    key = smell_key(project.metadata["diagnosis"]["smells"][0])
    decide_smell(
        project, key, "shared_database", "accepted", "architect",
        affected_services=["svc-a", "svc-b"],
        reason_code="acceptable_risk",
        reason_text="Business-critical; defer refactor",
    )

    enriched = enrich_diagnosis_with_decisions(project)
    smell = enriched["smells"][0]
    assert smell["governance_status"] == "accepted"
    assert smell["type"] == "shared_database"

    planning = filter_smells_for_planning(enriched["smells"])
    assert len(planning) == 0


def test_smell_deferred_stays_in_planning() -> None:
    smells = [{"type": "sync_rest_chain", "services": ["a"], "governance_status": "deferred"}]
    assert len(filter_smells_for_planning(smells)) == 1
