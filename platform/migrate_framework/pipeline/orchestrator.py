"""Eight-stage pipeline orchestrator with human approval gates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from migrate_framework.analysis.diagnose import diagnose
from migrate_framework.analysis.hypothesize import hypothesize, hypotheses_to_evidence
from migrate_framework.analysis.recommend import adrs_to_evidence, recommend
from migrate_framework.graph.builder import build_networkx_graph, build_service_graph, graph_metrics
from migrate_framework.ingestion.discover import discover_project
from migrate_framework.ingestion.registry import DEFAULT_REGISTRY
from migrate_framework.migration.playbook import build_playbook, playbook_to_evidence
from migrate_framework.migration.planner import phases_to_evidence, plan_migration
from migrate_framework.models import MigrationProject, PIPELINE_STAGE_ORDER, PipelineStage, StageRun
from migrate_framework.pipeline.project_store import ProjectStore

load_dotenv()


class PipelineOrchestrator:
    """Run migration pipeline stages with approval gate enforcement."""

    def __init__(self, store: ProjectStore | None = None) -> None:
        self.store = store or ProjectStore()

    def init_project(
        self,
        name: str,
        source_root: str,
        landscape_path: str | None = None,
    ) -> MigrationProject:
        project = MigrationProject(
            name=name,
            source_root=source_root,
            landscape_path=landscape_path,
            approval_gates=MigrationProject.default_gates(),
        )
        self.store.save_project(project)
        return project

    def approve(self, project_id: str, stage: PipelineStage, approved_by: str = "operator", notes: str | None = None) -> MigrationProject:
        project = self.store.load_project(project_id)
        gate = project.gate_for(stage)
        if gate is None:
            raise ValueError(f"No approval gate for stage {stage.value}")
        gate.approved = True
        gate.approved_at = datetime.now(timezone.utc)
        gate.approved_by = approved_by
        gate.notes = notes
        self.store.save_project(project)
        return project

    def can_run(self, project: MigrationProject, stage: PipelineStage) -> tuple[bool, str]:
        idx = PIPELINE_STAGE_ORDER.index(stage)
        if idx > 0:
            prev = PIPELINE_STAGE_ORDER[idx - 1]
            prev_runs = [r for r in project.stage_runs if r.stage == prev and r.status == "completed"]
            if not prev_runs:
                return False, f"Previous stage '{prev.value}' has not completed."
            if not project.is_stage_approved(prev):
                return False, f"Previous stage '{prev.value}' requires human approval."
        return True, "ok"

    def run_stage(self, project_id: str, stage: PipelineStage) -> MigrationProject:
        project = self.store.load_project(project_id)
        ok, reason = self.can_run(project, stage)
        if not ok:
            raise RuntimeError(reason)

        run = StageRun(stage=stage, status="running")
        project.stage_runs.append(run)

        handler = _STAGE_HANDLERS.get(stage)
        if handler is None:
            raise ValueError(f"Unknown stage: {stage}")

        summary = handler(self, project)
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.summary = summary
        project.current_stage = stage
        self.store.save_project(project)
        return project

    def run_through(self, project_id: str, until: PipelineStage, auto_approve: bool = False) -> MigrationProject:
        project = self.store.load_project(project_id)
        for stage in PIPELINE_STAGE_ORDER:
            if PIPELINE_STAGE_ORDER.index(stage) > PIPELINE_STAGE_ORDER.index(until):
                break
            gate = project.gate_for(stage)
            if auto_approve and gate and gate.required and not gate.approved:
                self.approve(project_id, stage, approved_by="auto")
                project = self.store.load_project(project_id)
            project = self.run_stage(project_id, stage)
        return project

    def _run_discover(self, project: MigrationProject) -> dict[str, Any]:
        discover_project(project)
        summary = project.metadata.get("discovery", {})
        self.store.save_artifact(project, PipelineStage.DISCOVER, "discovery", summary)
        return summary

    def _run_ingest(self, project: MigrationProject) -> dict[str, Any]:
        evidence, profile = DEFAULT_REGISTRY.collect_all(project.repo_root(), project.tech_stack)
        project.evidence = evidence
        project.tech_stack = profile
        self.store.save_evidence(project, PipelineStage.INGEST)
        summary = {"evidence_count": len(evidence), "adapters_used": profile.primary_stack()}
        self.store.save_artifact(project, PipelineStage.INGEST, "ingest-summary", summary)
        return summary

    def _run_graph(self, project: MigrationProject) -> dict[str, Any]:
        sg = build_service_graph(project.evidence)
        g = build_networkx_graph(sg)
        metrics = graph_metrics(g)
        payload = {
            "nodes": [n.model_dump() for n in sg.nodes],
            "edges": [e.model_dump() for e in sg.edges],
            "metrics": metrics,
        }
        self.store.save_artifact(project, PipelineStage.GRAPH, "service-graph", payload)
        return metrics

    def _run_diagnose(self, project: MigrationProject) -> dict[str, Any]:
        result = diagnose(project.evidence, project.landscape)
        self.store.save_artifact(project, PipelineStage.DIAGNOSE, "diagnosis", result)
        project.metadata["diagnosis"] = result
        return {"smell_count": len(result.get("smells", [])), **result.get("metrics", {})}

    def _run_hypothesize(self, project: MigrationProject) -> dict[str, Any]:
        diagnosis = project.metadata.get("diagnosis") or diagnose(project.evidence, project.landscape)
        hypotheses = hypothesize(diagnosis, project.landscape, project.evidence)
        project.evidence.extend(hypotheses_to_evidence(hypotheses))
        self.store.save_artifact(project, PipelineStage.HYPOTHESIZE, "hypotheses", hypotheses)
        project.metadata["hypotheses"] = hypotheses
        return {"hypothesis_count": len(hypotheses), "source": hypotheses[0].get("source") if hypotheses else "none"}

    def _run_recommend(self, project: MigrationProject) -> dict[str, Any]:
        diagnosis = project.metadata.get("diagnosis", {})
        hypotheses = project.metadata.get("hypotheses", [])
        adrs = recommend(hypotheses, diagnosis)
        project.evidence.extend(adrs_to_evidence(adrs))
        self.store.save_artifact(project, PipelineStage.RECOMMEND, "adrs", adrs, extension="yaml")
        project.metadata["adrs"] = adrs
        return {"adr_count": len(adrs)}

    def _run_plan(self, project: MigrationProject) -> dict[str, Any]:
        adrs = project.metadata.get("adrs", [])
        diagnosis = project.metadata.get("diagnosis", {})
        phases = plan_migration(adrs, project.landscape, diagnosis)
        project.evidence.extend(phases_to_evidence(phases))
        self.store.save_artifact(project, PipelineStage.PLAN, "migration-plan", phases)
        project.metadata["plan"] = phases
        return {"phase_count": len(phases)}

    def _run_playbook(self, project: MigrationProject) -> dict[str, Any]:
        phases = project.metadata.get("plan", [])
        adrs = project.metadata.get("adrs", [])
        tasks = build_playbook(phases, adrs)
        project.evidence.extend(playbook_to_evidence(tasks))
        self.store.save_artifact(project, PipelineStage.PLAYBOOK, "playbook", tasks)
        project.metadata["playbook"] = tasks
        return {"task_count": len(tasks)}


_STAGE_HANDLERS = {
    PipelineStage.DISCOVER: PipelineOrchestrator._run_discover,
    PipelineStage.INGEST: PipelineOrchestrator._run_ingest,
    PipelineStage.GRAPH: PipelineOrchestrator._run_graph,
    PipelineStage.DIAGNOSE: PipelineOrchestrator._run_diagnose,
    PipelineStage.HYPOTHESIZE: PipelineOrchestrator._run_hypothesize,
    PipelineStage.RECOMMEND: PipelineOrchestrator._run_recommend,
    PipelineStage.PLAN: PipelineOrchestrator._run_plan,
    PipelineStage.PLAYBOOK: PipelineOrchestrator._run_playbook,
}
