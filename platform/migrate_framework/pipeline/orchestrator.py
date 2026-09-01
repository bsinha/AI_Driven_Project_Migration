"""Eight-stage pipeline orchestrator with human approval gates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import os

from dotenv import load_dotenv

from migrate_framework.analysis.diagnose import diagnose
from migrate_framework.analysis.hypothesize import hypothesize, hypotheses_to_evidence
from migrate_framework.analysis.recommend import adrs_to_evidence, recommend
from migrate_framework.graph.builder import build_networkx_graph, build_service_graph, graph_metrics
from migrate_framework.ingestion.discover import discover_project
from migrate_framework.ingestion.registry import DEFAULT_REGISTRY
from migrate_framework.migration.playbook import build_playbook, playbook_to_evidence
from migrate_framework.migration.planner import phases_to_evidence, plan_migration
from migrate_framework.models import GateDecisionAction, MigrationProject, PIPELINE_STAGE_ORDER, PipelineStage, StageRun
from migrate_framework.pipeline.governance import (
    add_evidence_gap_playbook_task,
    confidence_blocks_approval,
    record_gate_decision,
    save_adr_version,
)
from migrate_framework.pipeline.project_store import ProjectStore
from migrate_framework.vv.capability_matrix import build_capability_matrix, matrix_summary

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

    def approve(
        self,
        project_id: str,
        stage: PipelineStage,
        approved_by: str = "operator",
        notes: str | None = None,
        reason_code: str | None = None,
        reason_text: str | None = None,
        allow_low_confidence: bool = False,
    ) -> MigrationProject:
        project = self.store.load_project(project_id)
        if project.gate_for(stage) is None:
            raise ValueError(f"No approval gate for stage {stage.value}")

        blocked, message = confidence_blocks_approval(project, stage)
        if blocked and not allow_low_confidence:
            raise ValueError(message)

        record_gate_decision(
            project,
            stage,
            GateDecisionAction.APPROVE,
            approved_by,
            reason_code=reason_code,
            reason_text=reason_text,
            notes=notes,
        )
        self.store.save_project(project)
        return project

    def reject(
        self,
        project_id: str,
        stage: PipelineStage,
        rejected_by: str,
        reason_code: str,
        reason_text: str,
        notes: str | None = None,
    ) -> MigrationProject:
        project = self.store.load_project(project_id)
        if project.gate_for(stage) is None:
            raise ValueError(f"No approval gate for stage {stage.value}")
        record_gate_decision(
            project,
            stage,
            GateDecisionAction.REJECT,
            rejected_by,
            reason_code=reason_code,
            reason_text=reason_text,
            notes=notes,
        )
        self.store.save_project(project)
        return project

    def waive(
        self,
        project_id: str,
        stage: PipelineStage,
        waived_by: str,
        reason_code: str,
        reason_text: str,
        notes: str | None = None,
    ) -> MigrationProject:
        project = self.store.load_project(project_id)
        if project.gate_for(stage) is None:
            raise ValueError(f"No approval gate for stage {stage.value}")
        record_gate_decision(
            project,
            stage,
            GateDecisionAction.WAIVE,
            waived_by,
            reason_code=reason_code,
            reason_text=reason_text,
            notes=notes,
        )
        self.store.save_project(project)
        return project

    def modify_adrs(
        self,
        project_id: str,
        modified_by: str,
        reason_code: str,
        reason_text: str,
        adrs: list[dict[str, Any]] | None = None,
    ) -> MigrationProject:
        project = self.store.load_project(project_id)
        save_adr_version(project, reason_text, modified_by)
        if adrs is not None:
            project.metadata["adrs"] = adrs
        record_gate_decision(
            project,
            PipelineStage.RECOMMEND,
            GateDecisionAction.MODIFY,
            modified_by,
            reason_code=reason_code,
            reason_text=reason_text,
            notes="ADR set modified — re-approval required",
        )
        self.store.save_artifact(project, PipelineStage.RECOMMEND, "adrs", project.metadata["adrs"], extension="yaml")
        self.store.save_project(project)
        return project

    def request_evidence(
        self,
        project_id: str,
        description: str,
        requested_by: str = "operator",
    ) -> MigrationProject:
        project = self.store.load_project(project_id)
        task = add_evidence_gap_playbook_task(project, description)
        self.store.save_project(project)
        record_gate_decision(
            project,
            PipelineStage.HYPOTHESIZE,
            GateDecisionAction.MODIFY,
            requested_by,
            reason_code="insufficient_evidence",
            reason_text=description,
            notes="Evidence gap task added to playbook",
            item_id=task["id"],
            item_type="evidence_gap",
        )
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
        use_multi = os.getenv("MULTI_LLM", "").lower() in {"1", "true", "yes"}
        if use_multi:
            from migrate_framework.analysis.hypothesize import _normalize_hypothesis
            from migrate_framework.analysis.llm_providers import configured_providers, run_multi_provider_hypotheses

            if configured_providers():
                multi = run_multi_provider_hypotheses(diagnosis, project.landscape)
                project.metadata["hypotheses_multi"] = multi
                raw = multi.get("synthesized", {}).get("hypotheses", [])
                hypotheses = [_normalize_hypothesis(h) for h in raw]
            else:
                hypotheses = hypothesize(diagnosis, project.landscape, project.evidence)
        else:
            hypotheses = hypothesize(diagnosis, project.landscape, project.evidence)
        project.evidence.extend(hypotheses_to_evidence(hypotheses))
        self.store.save_artifact(project, PipelineStage.HYPOTHESIZE, "hypotheses", hypotheses)
        project.metadata["hypotheses"] = hypotheses
        if project.metadata.get("hypotheses_multi"):
            self.store.save_artifact(
                project,
                PipelineStage.HYPOTHESIZE,
                "hypotheses-multi",
                project.metadata["hypotheses_multi"],
            )
        return {"hypothesis_count": len(hypotheses), "source": hypotheses[0].get("source") if hypotheses else "none"}

    def _run_recommend(self, project: MigrationProject) -> dict[str, Any]:
        diagnosis = project.metadata.get("diagnosis", {})
        hypotheses = project.metadata.get("hypotheses", [])
        adrs = recommend(hypotheses, diagnosis)
        project.evidence.extend(adrs_to_evidence(adrs))
        self.store.save_artifact(project, PipelineStage.RECOMMEND, "adrs", adrs, extension="yaml")
        project.metadata["adrs"] = adrs
        matrix = build_capability_matrix(project)
        project.metadata["capability_matrix"] = matrix
        project.metadata["capability_matrix_summary"] = matrix_summary(matrix)
        self.store.save_artifact(project, PipelineStage.RECOMMEND, "capability-matrix", matrix)
        return {"adr_count": len(adrs), "vv_coverage_pct": matrix_summary(matrix).get("coverage_pct")}

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
