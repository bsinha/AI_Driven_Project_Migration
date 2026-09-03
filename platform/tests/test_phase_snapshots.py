"""Tests for phase snapshots and diagnose compare."""

from migrate_framework.analysis.diagnose_compare import compare_diagnose
from migrate_framework.models import MigrationProject, PipelineStage, StageRun
from migrate_framework.pipeline.phase_snapshot import (
    close_phase,
    phase_readiness_score,
    phase_stage_matrix,
    snapshot_stage,
    store_diagnose_baseline,
)


def test_snapshot_stage_matrix() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", approval_gates=MigrationProject.default_gates())
    project.metadata["program_scope"] = {"current_phase": 0, "phases": [{"phase": 0, "name": "Baseline", "status": "active"}]}
    project.stage_runs.append(StageRun(stage=PipelineStage.DIAGNOSE, status="completed"))
    snapshot_stage(project, PipelineStage.DIAGNOSE, phase=0)
    matrix = phase_stage_matrix(project, 0)
    assert len(matrix) == 8
    assert matrix[3]["stage"] == "diagnose"


def test_compare_diagnose_improved() -> None:
    baseline = {"smells": [{"type": "a", "governance_status": "open"}], "metrics": {}}
    current = {"smells": [], "metrics": {}}
    result = compare_diagnose(baseline, current)
    assert result["improved"] is True
    assert result["smell_delta"] == -1


def test_close_phase_advances() -> None:
    project = MigrationProject(name="Test", source_root="/tmp")
    project.metadata["program_scope"] = {
        "current_phase": 1,
        "phases": [
            {"phase": 0, "name": "Baseline", "status": "completed"},
            {"phase": 1, "name": "Wave 1", "status": "active"},
            {"phase": 2, "name": "Wave 2", "status": "pending"},
        ],
    }
    result = close_phase(project, 1)
    assert result["next_phase"] == 2
    assert project.metadata["program_scope"]["current_phase"] == 2


def test_readiness_score() -> None:
    project = MigrationProject(name="Test", source_root="/tmp", approval_gates=MigrationProject.default_gates())
    project.metadata["program_scope"] = {"current_phase": 0, "phases": []}
    score = phase_readiness_score(project)
    assert 0 <= score["readiness_score"] <= 100


def test_store_diagnose_baseline() -> None:
    project = MigrationProject(
        name="Test",
        source_root="/tmp",
        metadata={"diagnosis": {"smells": [{"type": "x"}], "service_count": 5}},
        approval_gates=MigrationProject.default_gates(),
    )
    store_diagnose_baseline(project)
    assert "diagnosis_baseline" in project.metadata
    assert project.metadata["program_scope"]["baseline_snapshot_id"] == "0"
