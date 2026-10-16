"""Tests for program scope resolution."""

from migrate_framework.models import BoundedContextTarget, Landscape, MigrationProject
from migrate_framework.pipeline.scope import (
    _adr_item_id,
    decide_item,
    init_program_phases,
    resolve_active_scope,
)


def _sample_adrs() -> list[dict]:
    return [
        {
            "id": "adr-1",
            "title": "ADR-001: Customer",
            "target_context": "Customer Management",
            "affected_services": ["svc-a", "svc-b"],
            "mandatory": True,
        },
        {
            "id": "adr-2",
            "title": "ADR-002: Account",
            "target_context": "Account Management",
            "affected_services": ["svc-c"],
            "mandatory": True,
        },
        {
            "id": "adr-3",
            "title": "ADR-003: Payments",
            "target_context": "Payments",
            "affected_services": ["svc-d"],
            "mandatory": True,
        },
        {
            "id": "adr-4",
            "title": "ADR-004: Risk",
            "target_context": "Risk",
            "affected_services": ["svc-e"],
            "mandatory": False,
        },
    ]


def test_init_program_phases_from_landscape() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        landscape=Landscape(
            target_bounded_contexts=[
                BoundedContextTarget(name="Customer Management", services=["svc-a"]),
                BoundedContextTarget(name="Payments", services=["svc-d"]),
            ]
        ),
    )
    scope = init_program_phases(project)
    assert scope["current_phase"] == 0
    assert len(scope["phases"]) == 3  # baseline + 2 waves


def test_resolve_active_scope_after_partial_approval() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        metadata={"adrs": _sample_adrs()},
        approval_gates=MigrationProject.default_gates(),
    )
    init_program_phases(project)
    decide_item(project, "adr-1", "adr", "approved", "architect", reason_code="scope_accepted", reason_text="Pilot")
    decide_item(project, "adr-2", "adr", "approved", "architect", reason_code="scope_accepted", reason_text="Pilot")
    decide_item(
        project, "adr-3", "adr", "deferred", "architect",
        reason_code="scope_defer", reason_text="Phase 2",
    )

    scope = resolve_active_scope(project, phase=1)
    assert len(scope["adrs"]) == 2
    assert "Customer Management" in scope["contexts"]
    assert "Account Management" in scope["contexts"]
    assert len(scope["deferred_adrs"]) == 1


def test_legacy_mode_all_adrs_when_no_decisions() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", metadata={"adrs": _sample_adrs()})
    scope = resolve_active_scope(project)
    assert len(scope["adrs"]) == 4


def test_adr_item_id_fallback() -> None:
    adr = {"title": "ADR-999: Foo"}
    assert _adr_item_id(adr) == "ADR-999: Foo"
