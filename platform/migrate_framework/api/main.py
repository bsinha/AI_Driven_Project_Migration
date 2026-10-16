"""FastAPI REST API for migration framework."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from migrate_framework.branding import PRODUCT_NAME
from migrate_framework.models import PIPELINE_STAGE_ORDER, PipelineStage
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.project_store import ProjectStore

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title=f"{PRODUCT_NAME} API", version="0.1.0")
orch = PipelineOrchestrator()
store = ProjectStore()


class InitRequest(BaseModel):
    name: str
    source_root: str
    landscape_path: str | None = None


class ApproveRequest(BaseModel):
    stage: str
    approved_by: str = "api-user"
    notes: str | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    allow_low_confidence: bool = False


class RejectRequest(BaseModel):
    stage: str
    rejected_by: str = "api-user"
    reason_code: str
    reason_text: str
    notes: str | None = None


class WaiveRequest(BaseModel):
    stage: str
    waived_by: str = "api-user"
    reason_code: str
    reason_text: str
    notes: str | None = None


class RunRequest(BaseModel):
    stage: str
    through: str | None = None
    auto_approve: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/pipeline/stages")
def list_stages() -> list[str]:
    return [s.value for s in PIPELINE_STAGE_ORDER]


@app.post("/projects")
def create_project(body: InitRequest) -> dict[str, Any]:
    project = orch.init_project(body.name, body.source_root, body.landscape_path)
    return {"project_id": project.id, "name": project.name}


@app.get("/projects")
def get_projects() -> dict[str, list[str]]:
    return {"projects": store.list_projects()}


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    try:
        project = store.load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return project.model_dump(mode="json")


@app.get("/projects/{project_id}/status")
def project_status(project_id: str) -> dict[str, Any]:
    try:
        project = store.load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": project.id,
        "current_stage": project.current_stage.value,
        "completed_stages": [r.stage.value for r in project.stage_runs if r.status == "completed"],
        "approval_gates": [
            {
                "stage": g.stage.value,
                "required": g.required,
                "approved": g.approved,
                "status": g.status.value,
                "iteration_round": g.iteration_round,
            }
            for g in project.approval_gates
        ],
        "metadata_keys": list(project.metadata.keys()),
    }


@app.post("/projects/{project_id}/approve")
def approve_stage(project_id: str, body: ApproveRequest) -> dict[str, Any]:
    try:
        stage = PipelineStage(body.stage.lower())
        project = orch.approve(
            project_id,
            stage,
            body.approved_by,
            body.notes,
            body.reason_code,
            body.reason_text,
            body.allow_low_confidence,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    gate = project.gate_for(stage)
    return {"project_id": project.id, "stage": stage.value, "status": gate.status.value if gate else None}


@app.post("/projects/{project_id}/reject")
def reject_stage(project_id: str, body: RejectRequest) -> dict[str, Any]:
    try:
        stage = PipelineStage(body.stage.lower())
        project = orch.reject(project_id, stage, body.rejected_by, body.reason_code, body.reason_text, body.notes)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    gate = project.gate_for(stage)
    return {"project_id": project.id, "stage": stage.value, "status": gate.status.value if gate else None}


@app.post("/projects/{project_id}/waive")
def waive_stage(project_id: str, body: WaiveRequest) -> dict[str, Any]:
    try:
        stage = PipelineStage(body.stage.lower())
        project = orch.waive(project_id, stage, body.waived_by, body.reason_code, body.reason_text, body.notes)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    gate = project.gate_for(stage)
    return {"project_id": project.id, "stage": stage.value, "status": gate.status.value if gate else None}


@app.post("/projects/{project_id}/run")
def run_stage(project_id: str, body: RunRequest) -> dict[str, Any]:
    try:
        if body.through:
            until = PipelineStage(body.through.lower())
            project = orch.run_through(project_id, until, auto_approve=body.auto_approve)
        else:
            stage = PipelineStage(body.stage.lower())
            project = orch.run_stage(project_id, stage)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "project_id": project.id,
        "current_stage": project.current_stage.value,
        "last_summary": project.stage_runs[-1].summary if project.stage_runs else {},
    }


@app.get("/projects/{project_id}/hypotheses")
def get_hypotheses(project_id: str) -> list[dict[str, Any]]:
    project = store.load_project(project_id)
    return project.metadata.get("hypotheses", [])


@app.get("/projects/{project_id}/diagnosis")
def get_diagnosis(project_id: str) -> dict[str, Any]:
    project = store.load_project(project_id)
    return project.metadata.get("diagnosis", {})
