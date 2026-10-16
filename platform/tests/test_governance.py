"""Tests for governance, V&V, and enriched ADRs."""

from migrate_framework.analysis.recommend import recommend
from migrate_framework.governance_enums import GateDecisionStatus
from migrate_framework.models import GateDecisionAction, MigrationProject, PipelineStage
from migrate_framework.pipeline.governance import (
    record_gate_decision,
    rejection_count,
    update_escalation,
)
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.vv.capability_matrix import build_capability_matrix, matrix_summary


def test_reject_blocks_gate_clearance() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", approval_gates=MigrationProject.default_gates())
    gate = project.gate_for(PipelineStage.RECOMMEND)
    record_gate_decision(
        project,
        PipelineStage.RECOMMEND,
        GateDecisionAction.REJECT,
        "architect",
        reason_code="wrong_boundary",
        reason_text="Customer scope too broad",
    )
    assert gate is not None
    assert gate.status == GateDecisionStatus.REJECTED
    assert not gate.is_cleared()
    assert not project.is_stage_approved(PipelineStage.RECOMMEND)


def test_waive_clears_required_gate() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", approval_gates=MigrationProject.default_gates())
    record_gate_decision(
        project,
        PipelineStage.PLAN,
        GateDecisionAction.WAIVE,
        "executive",
        reason_code="executive_waiver",
        reason_text="Proceed with documented risk",
    )
    assert project.is_stage_approved(PipelineStage.PLAN)


def test_escalation_after_repeated_rejections() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", approval_gates=MigrationProject.default_gates())
    for _ in range(3):
        record_gate_decision(
            project,
            PipelineStage.RECOMMEND,
            GateDecisionAction.REJECT,
            "architect",
            reason_code="wrong_boundary",
            reason_text="Still wrong",
        )
    assert rejection_count(project, PipelineStage.RECOMMEND) == 3
    assert update_escalation(project, PipelineStage.RECOMMEND)
    assert project.governance_meta().get("needs_escalation")


def test_adr_mandatory_and_benefit_fields() -> None:
    hyps = [
        {
            "title": "Consolidate Customer",
            "description": "Merge customer services",
            "target_context": "Customer Management",
            "confidence": 0.85,
            "rationale": "Shared DB",
            "affected_services": ["a", "b"],
        }
    ]
    adrs = recommend(hyps, {"smells": [{"type": "shared_database"}], "database_sharing": {"customer_db": ["a", "b"]}})
    assert adrs[0]["mandatory"] is True
    assert adrs[0]["benefit_if_accepted"]
    assert adrs[0]["as_is_summary"]


def test_capability_matrix_from_services(tmp_path) -> None:
    from migrate_framework.models import EvidenceItem

    project = MigrationProject(
        name="Test",
        source_root=str(tmp_path),
        evidence=[
            EvidenceItem(type="service", source="test", subject="customer-identity-service"),
        ],
        metadata={
            "plan": [
                {
                    "name": "Extract Customer Management",
                    "services": ["customer-identity-service"],
                }
            ],
        },
    )
    matrix = build_capability_matrix(project)
    summary = matrix_summary(matrix)
    assert summary["total_capabilities"] >= 1
    assert summary["mapped"] >= 1


def test_orchestrator_reject_and_request_evidence(tmp_path) -> None:
    store_root = tmp_path / "projects"
    orch = PipelineOrchestrator()
    orch.store.base_dir = store_root
    project = orch.init_project("Gov", str(tmp_path))
    orch.reject(
        project.id,
        PipelineStage.RECOMMEND,
        "architect",
        "wrong_boundary",
        "Boundary incorrect",
    )
    loaded = orch.store.load_project(project.id)
    assert loaded.gate_for(PipelineStage.RECOMMEND).status == GateDecisionStatus.REJECTED

    orch.request_evidence(project.id, "Need production trace sample", "architect")
    loaded = orch.store.load_project(project.id)
    assert any("SME evidence" in t.get("task", "") for t in loaded.metadata.get("playbook", []))
