"""Stage 1 — discover repository landscape and tech stack."""

from __future__ import annotations

from pathlib import Path

from migrate_framework.ingestion.adapters.shared.metadata_adapter import MetadataAdapter
from migrate_framework.ingestion.registry import DEFAULT_REGISTRY, detect_stack
from migrate_framework.models import MigrationProject, PipelineStage, StageRun


def discover_project(project: MigrationProject) -> MigrationProject:
    """Run discovery: tech stack detection and landscape manifest loading."""
    root = project.repo_root()
    profile = detect_stack(root)
    project.tech_stack = profile

    landscape_path = project.landscape_path
    if landscape_path:
        manifest_root = Path(landscape_path).resolve().parent
    else:
        manifest_root = root

    landscape = MetadataAdapter.load_landscape(manifest_root)
    if landscape is None:
        landscape = MetadataAdapter.load_landscape(root)

    project.landscape = landscape

    service_count = len(landscape.services) if landscape else 0
    context_count = len(landscape.target_bounded_contexts) if landscape else 0

    run = StageRun(
        stage=PipelineStage.DISCOVER,
        status="completed",
        summary={
            "primary_stack": profile.primary_stack(),
            "languages": profile.languages,
            "frameworks": profile.frameworks,
            "service_count": service_count,
            "target_bounded_contexts": context_count,
            "landscape_loaded": landscape is not None,
        },
    )
    project.stage_runs.append(run)
    project.current_stage = PipelineStage.DISCOVER
    project.metadata["discovery"] = run.summary
    return project
