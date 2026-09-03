"""Tests for in-app stakeholder report viewer."""

from __future__ import annotations

from migrate_framework.models import MigrationProject, PipelineStage, StageRun, TechStackProfile
from migrate_framework.ui.stakeholder_report import _project_signature


def test_project_signature_changes_with_stage_runs() -> None:
    project = MigrationProject(
        id="proj-test",
        name="Test",
        source_root="/tmp",
    )
    sig1 = _project_signature(project)
    project.stage_runs.append(StageRun(stage=PipelineStage.DISCOVER, status="completed"))
    sig2 = _project_signature(project)
    assert sig1 != sig2
