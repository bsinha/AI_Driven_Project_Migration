"""Tests for assisted playbook task execution."""

from migrate_framework.migration.diff_utils import unified_diff
from migrate_framework.migration.task_assistant import assist_playbook_task
from migrate_framework.models import MigrationProject


def test_unified_diff_for_new_file() -> None:
    diff = unified_diff("target-contexts/demo/README.md", None, "# Demo\n")
    assert "target-contexts/demo/README.md" in diff


def test_assist_scaffold_task_generates_files(tmp_path) -> None:
    source = tmp_path / "sample-bank"
    source.mkdir()
    project = MigrationProject(
        id="proj-test",
        name="Test",
        source_root=str(source),
        metadata={
            "plan": [
                {
                    "phase": 1,
                    "name": "Extract Customer Management",
                    "objective": "Consolidate customer services.",
                    "services": ["customer-identity-service", "customer-address-service"],
                }
            ],
            "playbook": [
                {
                    "id": "task-1",
                    "task": "Scaffold target bounded context service(s) from migration plan",
                    "owner": "feature-team",
                    "status": "pending",
                    "phase": 1,
                    "context": "Extract Customer Management",
                    "category": "implementation",
                }
            ],
        },
    )

    proposal = assist_playbook_task(project, project.metadata["playbook"][0])

    assert proposal["files"]
    paths = {entry["path"] for entry in proposal["files"]}
    assert "target-contexts/customer-management/README.md" in paths
    assert all(entry.get("diff") for entry in proposal["files"])
