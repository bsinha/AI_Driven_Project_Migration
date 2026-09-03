"""Tests for scoped recommend gate and planner integration."""

from migrate_framework.migration.planner import plan_migration
from migrate_framework.models import BoundedContextTarget, Landscape, MigrationProject
from migrate_framework.pipeline.scope import decide_item, init_program_phases, recommend_gate_clear, resolve_active_scope


def _adrs() -> list[dict]:
    return [
        {"id": "a1", "title": "ADR-1", "target_context": "Ctx A", "affected_services": ["s1"], "mandatory": True},
        {"id": "a2", "title": "ADR-2", "target_context": "Ctx B", "affected_services": ["s2"], "mandatory": True},
        {"id": "a3", "title": "ADR-3", "target_context": "Ctx C", "affected_services": ["s3"], "mandatory": True},
        {"id": "a4", "title": "ADR-4", "target_context": "Ctx D", "affected_services": ["s4"], "mandatory": True},
    ]


def test_recommend_gate_clear_after_pilot_approval() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        metadata={"adrs": _adrs()},
        approval_gates=MigrationProject.default_gates(),
    )
    init_program_phases(project)

    cleared, _ = recommend_gate_clear(project)
    assert cleared

    decide_item(project, "a1", "adr", "approved", "arch", reason_code="scope_accepted", reason_text="ok")
    decide_item(project, "a2", "adr", "approved", "arch", reason_code="scope_accepted", reason_text="ok")
    decide_item(project, "a3", "adr", "deferred", "arch", reason_code="scope_defer", reason_text="later")
    decide_item(project, "a4", "adr", "deferred", "arch", reason_code="scope_defer", reason_text="later")

    cleared, msg = recommend_gate_clear(project)
    assert cleared, msg


def test_recommend_gate_blocked_when_mandatory_undecided() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        metadata={"adrs": _adrs()},
        approval_gates=MigrationProject.default_gates(),
    )
    init_program_phases(project)
    decide_item(project, "a1", "adr", "approved", "arch", reason_code="scope_accepted", reason_text="ok")

    cleared, msg = recommend_gate_clear(project)
    assert not cleared
    assert msg


def test_plan_respects_active_scope() -> None:
    landscape = Landscape(
        target_bounded_contexts=[
            BoundedContextTarget(name="Ctx A", services=["s1"]),
            BoundedContextTarget(name="Ctx B", services=["s2"]),
            BoundedContextTarget(name="Ctx C", services=["s3"]),
        ]
    )
    project = MigrationProject(name="Test", source_root="/tmp", landscape=landscape, metadata={"adrs": _adrs()}, approval_gates=MigrationProject.default_gates())
    decide_item(project, "a1", "adr", "approved", "arch", reason_code="scope_accepted", reason_text="ok")
    decide_item(project, "a2", "adr", "approved", "arch", reason_code="scope_accepted", reason_text="ok")
    decide_item(project, "a3", "adr", "deferred", "arch", reason_code="scope_defer", reason_text="later")

    scope = resolve_active_scope(project)
    phases = plan_migration(_adrs(), landscape, active_scope=scope)
    deferred = [p for p in phases if p.get("status") == "deferred"]
    active = [p for p in phases if p.get("status") == "active" and p.get("services")]
    assert len(deferred) >= 1
    assert len(active) == 2


def test_capability_matrix_deferred_status() -> None:
    from migrate_framework.models import EvidenceItem
    from migrate_framework.vv.capability_matrix import build_capability_matrix, matrix_summary

    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        evidence=[EvidenceItem(type="service", source="test", subject="s3")],
        metadata={"adrs": _adrs()},
        approval_gates=MigrationProject.default_gates(),
    )
    decide_item(project, "a3", "adr", "deferred", "arch", reason_code="scope_defer", reason_text="later")
    matrix = build_capability_matrix(project)
    summary = matrix_summary(matrix)
    row = next(r for r in matrix if r["as_is_service"] == "s3")
    assert row["status"] == "deferred"
    assert summary["deferred"] >= 1
