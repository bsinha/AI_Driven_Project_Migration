"""CLI for migrate-framework."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

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
    project = orch.approve(args.project_id, stage, approved_by=args.by, notes=args.notes)
    gate = project.gate_for(stage)
    print(json.dumps({"project_id": project.id, "stage": stage.value, "approved": gate.approved if gate else False}, indent=2))
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
            {"stage": g.stage.value, "required": g.required, "approved": g.approved}
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
    parser = argparse.ArgumentParser(prog="migrate-framework", description="Microservice-to-DDD migration framework")
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
    approve_p.set_defaults(func=cmd_approve)

    list_p = sub.add_parser("list", help="List migration projects")
    list_p.set_defaults(func=cmd_list)

    status_p = sub.add_parser("status", help="Show project status")
    status_p.add_argument("--project-id", required=True)
    status_p.set_defaults(func=cmd_status)

    report_p = sub.add_parser("report", help="Generate stakeholder migration report")
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
