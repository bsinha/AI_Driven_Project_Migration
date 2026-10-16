"""CLI for migrate-framework."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from migrate_framework.branding import PRODUCT_NAME, PRODUCT_TAGLINE
from migrate_framework.governance_enums import GATE_REASON_CODES, ITEM_DECISION_STATUSES, ITEM_TYPES, SMELL_DECISION_STATUSES
from migrate_framework.models import PIPELINE_STAGE_ORDER, PipelineStage
from migrate_framework.pipeline.orchestrator import PipelineOrchestrator
from migrate_framework.pipeline.project_store import ProjectStore
from migrate_framework.reporting.pipeline_report import (
    generate_html_report,
    generate_markdown_report,
    report_filename,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_init(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    source = str(Path(args.source).resolve())
    landscape = str(Path(args.landscape).resolve()) if args.landscape else None
    project = orch.init_project(args.name, source, landscape)
    print(json.dumps({"project_id": project.id, "name": project.name, "source_root": source}, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    stage = PipelineStage(args.stage.lower())
    if args.through:
        until = PipelineStage(args.through.lower())
        project = orch.run_through(args.project_id, until, auto_approve=args.auto_approve)
    else:
        project = orch.run_stage(args.project_id, stage)
    print(json.dumps({"project_id": project.id, "stage": project.current_stage.value, "status": "completed"}, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    stage = PipelineStage(args.stage.lower())
    project = orch.approve(
        args.project_id,
        stage,
        approved_by=args.by,
        notes=args.notes,
        reason_code=args.reason_code,
        reason_text=args.reason_text,
        allow_low_confidence=args.allow_low_confidence,
    )
    gate = project.gate_for(stage)
    print(
        json.dumps(
            {
                "project_id": project.id,
                "stage": stage.value,
                "status": gate.status.value if gate else None,
                "approved": gate.approved if gate else False,
            },
            indent=2,
        )
    )
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    stage = PipelineStage(args.stage.lower())
    project = orch.reject(args.project_id, stage, args.by, args.reason_code, args.reason_text, args.notes)
    gate = project.gate_for(stage)
    print(json.dumps({"project_id": project.id, "stage": stage.value, "status": gate.status.value}, indent=2))
    return 0


def cmd_waive(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    stage = PipelineStage(args.stage.lower())
    project = orch.waive(args.project_id, stage, args.by, args.reason_code, args.reason_text, args.notes)
    gate = project.gate_for(stage)
    print(json.dumps({"project_id": project.id, "stage": stage.value, "status": gate.status.value}, indent=2))
    return 0


def cmd_request_evidence(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    project = orch.request_evidence(args.project_id, args.description, args.by)
    print(json.dumps({"project_id": project.id, "playbook_tasks": len(project.metadata.get("playbook", []))}, indent=2))
    return 0


def cmd_scope_decide(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    project = orch.decide_scope_item(
        args.project_id,
        args.item_id,
        args.item_type,
        args.decision,
        decision_by=args.by,
        reason_code=args.reason_code,
        reason_text=args.reason_text,
        scope_phase=args.scope_phase,
    )
    from migrate_framework.pipeline.scope import pending_mandatory_items, recommend_gate_clear

    cleared, msg = recommend_gate_clear(project)
    print(
        json.dumps(
            {
                "project_id": project.id,
                "item_id": args.item_id,
                "decision": args.decision,
                "recommend_gate_clear": cleared,
                "message": msg,
            },
            indent=2,
        )
    )
    return 0


def cmd_smell_decide(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    project = orch.decide_smell_item(
        args.project_id,
        args.smell_key,
        args.smell_type,
        args.decision,
        decision_by=args.by,
        affected_services=args.services.split(",") if args.services else None,
        reason_code=args.reason_code,
        reason_text=args.reason_text,
        revisit_phase=args.revisit_phase,
    )
    print(json.dumps({"project_id": project.id, "smell_key": args.smell_key, "decision": args.decision}, indent=2))
    return 0


def cmd_phase_close(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    project = orch.close_program_phase(args.project_id, args.phase, closed_by=args.by)
    from migrate_framework.pipeline.phase_snapshot import phase_readiness_score

    readiness = phase_readiness_score(project, args.phase)
    print(json.dumps({"project_id": project.id, "closed_phase": args.phase, "readiness": readiness}, indent=2))
    return 0


def cmd_phase_set_contexts(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    names = [n.strip() for n in args.contexts.split(",") if n.strip()]
    project = orch.set_program_phase_contexts(args.project_id, args.phase, names)
    print(json.dumps({"project_id": project.id, "phase": args.phase, "contexts": names}, indent=2))
    return 0


def cmd_scope_decide_batch(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    decisions = payload if isinstance(payload, list) else payload.get("decisions", [])
    project = orch.decide_scope_items(args.project_id, decisions, decision_by=args.by)
    from migrate_framework.pipeline.scope import recommend_gate_clear

    cleared, msg = recommend_gate_clear(project)
    print(
        json.dumps(
            {
                "project_id": project.id,
                "count": len(decisions),
                "recommend_gate_clear": cleared,
                "message": msg,
            },
            indent=2,
        )
    )
    return 0


def cmd_scope_pilot(args: argparse.Namespace) -> int:
    """Approve listed ADR ids and defer all other scopable ADRs."""
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    store = ProjectStore()
    project = store.load_project(args.project_id)
    approve_ids = {x.strip() for x in args.approve.split(",") if x.strip()}
    from migrate_framework.pipeline.scope import _adr_item_id

    adrs = [a for a in project.metadata.get("adrs", []) if a.get("target_context") != "Cross-cutting"]
    decisions = []
    for adr in adrs:
        item_id = _adr_item_id(adr)
        if item_id in approve_ids or adr.get("id") in approve_ids:
            decisions.append(
                {
                    "item_id": item_id,
                    "item_type": "adr",
                    "decision": "approved",
                    "reason_code": "scope_accepted",
                    "reason_text": args.approve_reason,
                    "scope_phase": args.scope_phase,
                }
            )
        else:
            decisions.append(
                {
                    "item_id": item_id,
                    "item_type": "adr",
                    "decision": "deferred",
                    "reason_code": "scope_defer",
                    "reason_text": args.defer_reason,
                    "scope_phase": args.scope_phase,
                }
            )
    project = orch.decide_scope_items(args.project_id, decisions, decision_by=args.by)
    from migrate_framework.pipeline.scope import recommend_gate_clear

    cleared, msg = recommend_gate_clear(project)
    print(
        json.dumps(
            {
                "project_id": project.id,
                "approved": len(approve_ids),
                "deferred": len(adrs) - len(approve_ids),
                "recommend_gate_clear": cleared,
                "message": msg,
            },
            indent=2,
        )
    )
    return 0


def cmd_smell_decide_batch(args: argparse.Namespace) -> int:
    load_dotenv(_repo_root() / ".env")
    orch = PipelineOrchestrator()
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    decisions = payload if isinstance(payload, list) else payload.get("decisions", [])
    project = orch.decide_smell_items(args.project_id, decisions, decision_by=args.by)
    print(json.dumps({"project_id": project.id, "count": len(decisions)}, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = ProjectStore()
    projects = store.list_projects()
    print(json.dumps({"projects": projects}, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    store = ProjectStore()
    project = store.load_project(args.project_id)
    payload = {
        "id": project.id,
        "name": project.name,
        "current_stage": project.current_stage.value,
        "tech_stack": project.tech_stack.model_dump(),
        "gates": [
            {
                "stage": g.stage.value,
                "required": g.required,
                "approved": g.approved,
                "status": g.status.value,
                "iteration_round": g.iteration_round,
            }
            for g in project.approval_gates
        ],
        "completed_stages": [r.stage.value for r in project.stage_runs if r.status == "completed"],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    store = ProjectStore()
    project = store.load_project(args.project_id)
    if args.format == "html":
        content = generate_html_report(project)
        extension = "html"
    else:
        content = generate_markdown_report(project)
        extension = "md"

    filename = report_filename(project, extension)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = store.project_path(project.id) / "artifacts" / filename

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(json.dumps({"project_id": project.id, "path": str(output_path), "format": args.format}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate-framework",
        description=f"{PRODUCT_NAME} — {PRODUCT_TAGLINE}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Initialize a migration project")
    init_p.add_argument("--name", required=True)
    init_p.add_argument("--source", required=True, help="Path to source repository")
    init_p.add_argument("--landscape", help="Path to landscape-manifest.yaml")
    init_p.set_defaults(func=cmd_init)

    run_p = sub.add_parser("run", help="Run a pipeline stage")
    run_p.add_argument("--project-id", required=True)
    run_p.add_argument("--stage", required=True, choices=[s.value for s in PIPELINE_STAGE_ORDER])
    run_p.add_argument("--through", choices=[s.value for s in PIPELINE_STAGE_ORDER], help="Run through this stage")
    run_p.add_argument("--auto-approve", action="store_true")
    run_p.set_defaults(func=cmd_run)

    approve_p = sub.add_parser("approve", help="Approve a stage gate")
    approve_p.add_argument("--project-id", required=True)
    approve_p.add_argument("--stage", required=True, choices=[s.value for s in PIPELINE_STAGE_ORDER])
    approve_p.add_argument("--by", default="operator")
    approve_p.add_argument("--notes")
    approve_p.add_argument("--reason-code", choices=GATE_REASON_CODES)
    approve_p.add_argument("--reason-text")
    approve_p.add_argument("--allow-low-confidence", action="store_true")
    approve_p.set_defaults(func=cmd_approve)

    reject_p = sub.add_parser("reject", help="Reject a stage gate (blocks pipeline)")
    reject_p.add_argument("--project-id", required=True)
    reject_p.add_argument("--stage", required=True, choices=[s.value for s in PIPELINE_STAGE_ORDER])
    reject_p.add_argument("--by", default="operator")
    reject_p.add_argument("--reason-code", required=True, choices=GATE_REASON_CODES)
    reject_p.add_argument("--reason-text", required=True)
    reject_p.add_argument("--notes")
    reject_p.set_defaults(func=cmd_reject)

    waive_p = sub.add_parser("waive", help="Waive a required gate with documented exception")
    waive_p.add_argument("--project-id", required=True)
    waive_p.add_argument("--stage", required=True, choices=[s.value for s in PIPELINE_STAGE_ORDER])
    waive_p.add_argument("--by", default="operator")
    waive_p.add_argument("--reason-code", required=True, choices=GATE_REASON_CODES)
    waive_p.add_argument("--reason-text", required=True)
    waive_p.add_argument("--notes")
    waive_p.set_defaults(func=cmd_waive)

    evidence_p = sub.add_parser("request-evidence", help="Add SME evidence-gap playbook task")
    evidence_p.add_argument("--project-id", required=True)
    evidence_p.add_argument("--description", required=True)
    evidence_p.add_argument("--by", default="operator")
    evidence_p.set_defaults(func=cmd_request_evidence)

    scope_p = sub.add_parser("scope-decide", help="Approve, defer, or reject a scope item (ADR, context)")
    scope_p.add_argument("--project-id", required=True)
    scope_p.add_argument("--item-id", required=True)
    scope_p.add_argument("--item-type", required=True, choices=ITEM_TYPES)
    scope_p.add_argument("--decision", required=True, choices=ITEM_DECISION_STATUSES)
    scope_p.add_argument("--by", default="operator")
    scope_p.add_argument("--reason-code", choices=GATE_REASON_CODES)
    scope_p.add_argument("--reason-text")
    scope_p.add_argument("--scope-phase", type=int)
    scope_p.set_defaults(func=cmd_scope_decide)

    smell_p = sub.add_parser("smell-decide", help="Accept, defer, or reopen an architectural smell")
    smell_p.add_argument("--project-id", required=True)
    smell_p.add_argument("--smell-key", required=True)
    smell_p.add_argument("--smell-type", required=True)
    smell_p.add_argument("--decision", required=True, choices=SMELL_DECISION_STATUSES)
    smell_p.add_argument("--by", default="operator")
    smell_p.add_argument("--services", help="Comma-separated affected services")
    smell_p.add_argument("--reason-code", choices=GATE_REASON_CODES)
    smell_p.add_argument("--reason-text")
    smell_p.add_argument("--revisit-phase", type=int)
    smell_p.set_defaults(func=cmd_smell_decide)

    phase_p = sub.add_parser("phase-close", help="Close a migration program phase and advance")
    phase_p.add_argument("--project-id", required=True)
    phase_p.add_argument("--phase", type=int, required=True)
    phase_p.add_argument("--by", default="operator")
    phase_p.set_defaults(func=cmd_phase_close)

    ctx_p = sub.add_parser("phase-set-contexts", help="Assign bounded contexts to a program phase")
    ctx_p.add_argument("--project-id", required=True)
    ctx_p.add_argument("--phase", type=int, required=True)
    ctx_p.add_argument("--contexts", required=True, help="Comma-separated bounded context names")
    ctx_p.set_defaults(func=cmd_phase_set_contexts)

    batch_scope_p = sub.add_parser("scope-decide-batch", help="Batch scope decisions from JSON file")
    batch_scope_p.add_argument("--project-id", required=True)
    batch_scope_p.add_argument("--file", required=True, help="JSON array of decision objects")
    batch_scope_p.add_argument("--by", default="operator")
    batch_scope_p.set_defaults(func=cmd_scope_decide_batch)

    pilot_p = sub.add_parser("scope-pilot", help="Approve ADR ids for pilot; defer the rest")
    pilot_p.add_argument("--project-id", required=True)
    pilot_p.add_argument("--approve", required=True, help="Comma-separated ADR item ids to approve")
    pilot_p.add_argument("--approve-reason", default="Approved for pilot program scope")
    pilot_p.add_argument("--defer-reason", default="Deferred to a later migration wave")
    pilot_p.add_argument("--scope-phase", type=int, default=1)
    pilot_p.add_argument("--by", default="operator")
    pilot_p.set_defaults(func=cmd_scope_pilot)

    batch_smell_p = sub.add_parser("smell-decide-batch", help="Batch smell decisions from JSON file")
    batch_smell_p.add_argument("--project-id", required=True)
    batch_smell_p.add_argument("--file", required=True)
    batch_smell_p.add_argument("--by", default="operator")
    batch_smell_p.set_defaults(func=cmd_smell_decide_batch)

    list_p = sub.add_parser("list", help="List migration projects")
    list_p.set_defaults(func=cmd_list)

    status_p = sub.add_parser("status", help="Show project status")
    status_p.add_argument("--project-id", required=True)
    status_p.set_defaults(func=cmd_status)

    report_p = sub.add_parser("report", help="Generate migration assessment report")
    report_p.add_argument("--project-id", required=True)
    report_p.add_argument("--format", choices=["md", "html"], default="md")
    report_p.add_argument("--output", help="Output file path (default: project artifacts folder)")
    report_p.set_defaults(func=cmd_report)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
