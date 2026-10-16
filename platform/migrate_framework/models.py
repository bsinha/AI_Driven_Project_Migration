"""Migration framework core models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from migrate_framework.governance_enums import (
    CONFIDENCE_APPROVAL_THRESHOLD,
    ESCALATION_REJECTION_THRESHOLD,
    GATE_REASON_CODES,
    GateDecisionAction,
    GateDecisionStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "ev") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class PipelineStage(str, Enum):
    """Eight-stage migration pipeline."""

    DISCOVER = "discover"
    INGEST = "ingest"
    GRAPH = "graph"
    DIAGNOSE = "diagnose"
    HYPOTHESIZE = "hypothesize"
    RECOMMEND = "recommend"
    PLAN = "plan"
    PLAYBOOK = "playbook"


PIPELINE_STAGE_ORDER: list[PipelineStage] = list(PipelineStage)


class EvidenceRelation(BaseModel):
    relation: str
    target: str


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    type: str
    source: str
    subject: str
    collected_at: datetime = Field(default_factory=_utc_now)
    confidence: float = 1.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    relations: list[EvidenceRelation] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TechStackProfile(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    deployment: list[str] = Field(default_factory=list)
    detected_files: list[str] = Field(default_factory=list)

    def primary_stack(self) -> str:
        if "spring-boot" in self.frameworks:
            return "java-spring"
        if "aspnetcore" in self.frameworks:
            return "dotnet"
        if "java" in self.languages:
            return "java"
        if "csharp" in self.languages or "dotnet" in self.languages:
            return "dotnet"
        return "unknown"


class LandscapeService(BaseModel):
    id: str
    port: int | None = None
    database: str | None = None
    tables: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    team: str | None = None
    smells: list[str] = Field(default_factory=list)
    region_notes: str | None = None


class BoundedContextTarget(BaseModel):
    name: str
    services: list[str] = Field(default_factory=list)


class Landscape(BaseModel):
    name: str = "Unknown"
    regions: list[str] = Field(default_factory=list)
    currencies: list[str] = Field(default_factory=list)
    services: list[LandscapeService] = Field(default_factory=list)
    target_bounded_contexts: list[BoundedContextTarget] = Field(default_factory=list)
    source_path: str | None = None


class StageRun(BaseModel):
    stage: PipelineStage
    started_at: datetime = Field(default_factory=_utc_now)
    completed_at: datetime | None = None
    status: str = "pending"
    artifact_paths: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class GateDecisionRecord(BaseModel):
    """Immutable audit entry for gate and governance actions."""

    id: str = Field(default_factory=lambda: new_id("dec"))
    stage: PipelineStage
    action: GateDecisionAction
    decision_by: str
    decision_at: datetime = Field(default_factory=_utc_now)
    reason_code: str | None = None
    reason_text: str | None = None
    notes: str | None = None
    iteration_round: int = 0
    item_id: str | None = None
    item_type: str | None = None


class WaiverRecord(BaseModel):
    """Formal exception allowing progress despite a mandatory item."""

    id: str = Field(default_factory=lambda: new_id("wvr"))
    item_id: str
    item_type: str
    title: str
    reason_code: str
    reason_text: str
    waived_by: str
    waived_at: datetime = Field(default_factory=_utc_now)
    stage: PipelineStage | None = None


class ItemDecision(BaseModel):
    """Per-item governance decision (ADR, bounded context, etc.)."""

    item_id: str
    item_type: str
    decision: str
    scope_phase: int = 1
    reason_code: str | None = None
    reason_text: str | None = None
    decision_by: str = "operator"
    decision_at: datetime = Field(default_factory=_utc_now)
    blocks_gate: bool = False


class SmellDecision(BaseModel):
    """Human decision on a detected architectural smell."""

    smell_key: str
    smell_type: str
    affected_services: list[str] = Field(default_factory=list)
    decision: str = "open"
    reason_code: str | None = None
    reason_text: str | None = None
    decision_by: str = "operator"
    decision_at: datetime = Field(default_factory=_utc_now)
    revisit_phase: int | None = None


class ProgramPhase(BaseModel):
    """Migration program increment (baseline or execution wave)."""

    phase: int
    name: str
    status: str = "pending"
    in_scope_contexts: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ApprovalGate(BaseModel):
    stage: PipelineStage
    required: bool = True
    approved: bool = False
    status: GateDecisionStatus = GateDecisionStatus.PENDING
    approved_at: datetime | None = None
    approved_by: str | None = None
    notes: str | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    iteration_round: int = 0

    def is_cleared(self) -> bool:
        """Gate allows pipeline progression (approved or formally waived)."""
        if self.status in {GateDecisionStatus.APPROVED, GateDecisionStatus.WAIVED}:
            return True
        return self.approved and self.status == GateDecisionStatus.PENDING


class MigrationProject(BaseModel):
    id: str = Field(default_factory=lambda: new_id("proj"))
    name: str
    source_root: str
    landscape_path: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    current_stage: PipelineStage = PipelineStage.DISCOVER
    tech_stack: TechStackProfile = Field(default_factory=TechStackProfile)
    landscape: Landscape | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    stage_runs: list[StageRun] = Field(default_factory=list)
    approval_gates: list[ApprovalGate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def repo_root(self) -> Path:
        return Path(self.source_root).resolve()

    def gate_for(self, stage: PipelineStage) -> ApprovalGate | None:
        for gate in self.approval_gates:
            if gate.stage == stage:
                return gate
        return None

    def is_stage_approved(self, stage: PipelineStage) -> bool:
        gate = self.gate_for(stage)
        if gate is None or not gate.required:
            return True
        return gate.is_cleared()

    def decision_log(self) -> list[GateDecisionRecord]:
        raw = self.metadata.get("decision_log", [])
        return [GateDecisionRecord.model_validate(entry) for entry in raw]

    def waiver_registry(self) -> list[WaiverRecord]:
        raw = self.metadata.get("waiver_registry", [])
        return [WaiverRecord.model_validate(entry) for entry in raw]

    def governance_meta(self) -> dict[str, Any]:
        return self.metadata.setdefault("governance", {})

    def item_decisions(self) -> list[ItemDecision]:
        raw = self.metadata.get("item_decisions", [])
        return [ItemDecision.model_validate(entry) for entry in raw]

    def smell_decisions(self) -> list[SmellDecision]:
        raw = self.metadata.get("smell_decisions", [])
        return [SmellDecision.model_validate(entry) for entry in raw]

    def program_phases(self) -> list[ProgramPhase]:
        scope = self.metadata.get("program_scope", {})
        raw = scope.get("phases", [])
        return [ProgramPhase.model_validate(entry) for entry in raw]

    def current_program_phase(self) -> int:
        return int(self.metadata.get("program_scope", {}).get("current_phase", 0))

    @staticmethod
    def default_gates() -> list[ApprovalGate]:
        return [
            ApprovalGate(stage=PipelineStage.DISCOVER, required=False),
            ApprovalGate(stage=PipelineStage.INGEST, required=True),
            ApprovalGate(stage=PipelineStage.GRAPH, required=False),
            ApprovalGate(stage=PipelineStage.DIAGNOSE, required=True),
            ApprovalGate(stage=PipelineStage.HYPOTHESIZE, required=True),
            ApprovalGate(stage=PipelineStage.RECOMMEND, required=True),
            ApprovalGate(stage=PipelineStage.PLAN, required=True),
            ApprovalGate(stage=PipelineStage.PLAYBOOK, required=False),
        ]


# Re-export governance symbols for backward-compatible imports from models.
__all__ = [
    "CONFIDENCE_APPROVAL_THRESHOLD",
    "ESCALATION_REJECTION_THRESHOLD",
    "GATE_REASON_CODES",
    "GateDecisionAction",
    "GateDecisionStatus",
    "ApprovalGate",
    "EvidenceItem",
    "MigrationProject",
    "PipelineStage",
    "PIPELINE_STAGE_ORDER",
]
