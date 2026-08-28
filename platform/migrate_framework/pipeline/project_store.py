"""Persist migration project artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from migrate_framework.models import MigrationProject, PipelineStage


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def projects_dir(base: Path | None = None) -> Path:
    root = base or _repo_root()
    path = root / "platform" / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ProjectStore:
    """Save and load migration projects and stage artifacts."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = projects_dir(base_dir)

    def project_path(self, project_id: str) -> Path:
        path = self.base_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_project(self, project: MigrationProject) -> Path:
        path = self.project_path(project.id)
        project_file = path / "project.json"
        project_file.write_text(
            project.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return project_file

    def load_project(self, project_id: str) -> MigrationProject:
        project_file = self.project_path(project_id) / "project.json"
        if not project_file.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        return MigrationProject.model_validate_json(project_file.read_text(encoding="utf-8"))

    def list_projects(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        return sorted(
            p.name for p in self.base_dir.iterdir()
            if p.is_dir() and (p / "project.json").exists()
        )

    def save_artifact(
        self,
        project: MigrationProject,
        stage: PipelineStage,
        name: str,
        payload: Any,
        extension: str = "json",
    ) -> str:
        stage_dir = self.project_path(project.id) / "artifacts" / stage.value
        stage_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = stage_dir / f"{name}.{extension}"

        if extension == "json":
            artifact_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        elif extension in {"yaml", "yml"}:
            artifact_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        else:
            artifact_path.write_text(str(payload), encoding="utf-8")

        rel = str(artifact_path.relative_to(self.base_dir.parent.parent))
        if rel not in project.metadata.setdefault("artifacts", []):
            project.metadata.setdefault("artifact_index", {}).setdefault(stage.value, []).append(
                {"name": name, "path": str(artifact_path), "saved_at": datetime.now(timezone.utc).isoformat()}
            )
        return str(artifact_path)

    def save_evidence(self, project: MigrationProject, stage: PipelineStage) -> str:
        payload = [e.model_dump(mode="json") for e in project.evidence]
        return self.save_artifact(project, stage, "evidence", payload)
