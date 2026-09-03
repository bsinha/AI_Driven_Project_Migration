"""Generate stakeholder-ready pipeline reports from migration projects."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from migrate_framework.branding import PRODUCT_NAME, REPORT_FOOTER
from migrate_framework.models import PIPELINE_STAGE_ORDER, MigrationProject, PipelineStage

STAGE_TITLES: dict[str, str] = {
    "discover": "Discovery",
    "ingest": "Evidence Ingestion",
    "graph": "Service Graph",
    "diagnose": "Architecture Diagnosis",
    "hypothesize": "Migration Hypotheses",
    "recommend": "Architecture Decisions",
    "plan": "Migration Plan",
    "playbook": "Developer Playbook",
}


def _load_artifact_file(path: str) -> Any | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _latest_artifact(
    artifact_index: dict[str, list[dict[str, Any]]],
    stage: str,
    name: str,
) -> Any | None:
    entries = [entry for entry in artifact_index.get(stage, []) if entry.get("name") == name]
    if not entries:
        return None
    path = entries[-1].get("path", "")
    return _load_artifact_file(path) if path else None


def _artifact_bundle(project: MigrationProject) -> dict[str, Any]:
    index = project.metadata.get("artifact_index", {})
    return {
        "discovery": _latest_artifact(index, "discover", "discovery") or project.metadata.get("discovery"),
        "ingest_summary": _latest_artifact(index, "ingest", "ingest-summary"),
        "service_graph": _latest_artifact(index, "graph", "service-graph"),
        "diagnosis": _latest_artifact(index, "diagnose", "diagnosis") or project.metadata.get("diagnosis"),
        "hypotheses": _latest_artifact(index, "hypothesize", "hypotheses") or project.metadata.get("hypotheses"),
        "adrs": _latest_artifact(index, "recommend", "adrs") or project.metadata.get("adrs"),
        "plan": _latest_artifact(index, "plan", "migration-plan") or project.metadata.get("plan"),
        "playbook": _latest_artifact(index, "playbook", "playbook") or project.metadata.get("playbook"),
    }


def _completed_stages(project: MigrationProject) -> set[PipelineStage]:
    return {run.stage for run in project.stage_runs if run.status == "completed"}


def _gate_rows(project: MigrationProject) -> list[dict[str, str]]:
    gates = project.approval_gates or MigrationProject.default_gates()
    rows: list[dict[str, str]] = []
    for gate in gates:
        if gate.approved:
            status = "Approved"
        elif gate.required:
            status = "Pending sign-off"
        else:
            status = "Optional"
        rows.append(
            {
                "stage": gate.stage.value,
                "required": "Yes" if gate.required else "No",
                "status": status,
                "approved_by": gate.approved_by or "—",
            }
        )
    return rows


def _smell_service_label(smell: dict[str, Any]) -> str:
    smell_type = smell.get("type") or smell.get("smell") or ""
    services = smell.get("services")
    subject = smell.get("subject")

    if smell.get("service"):
        return str(smell["service"])
    if isinstance(services, list) and services:
        if smell_type == "sync_rest_chain":
            return " → ".join(str(item) for item in services)
        if smell_type == "shared_database":
            return ", ".join(str(item) for item in services)
        if len(services) == 1:
            return str(services[0])
        return ", ".join(str(item) for item in services)
    if subject is not None:
        return str(subject)
    return "—"


def _service_names(services: list[Any] | None) -> list[str]:
    names: list[str] = []
    for item in services or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("id") or item.get("name") or item))
    return names


def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _executive_summary(project: MigrationProject, bundle: dict[str, Any]) -> list[str]:
    diagnosis = bundle.get("diagnosis") or {}
    discovery = bundle.get("discovery") or {}
    hypotheses = bundle.get("hypotheses") or []
    plan = bundle.get("plan") or []
    completed = _completed_stages(project)

    service_count = diagnosis.get("service_count") or discovery.get("service_count") or "—"
    smell_count = len(diagnosis.get("smells") or [])
    total_weeks = sum(phase.get("duration_weeks", 0) for phase in plan if isinstance(phase, dict))

    return [
        "## Executive Summary",
        "",
        f"- **Services analyzed:** {service_count}",
        f"- **Architecture smells detected:** {smell_count}",
        f"- **Migration hypotheses:** {len(hypotheses) if isinstance(hypotheses, list) else 0}",
        f"- **Migration phases proposed:** {len(plan) if isinstance(plan, list) else 0}"
        + (f" ({total_weeks} weeks total)" if total_weeks else ""),
        f"- **Pipeline stages completed:** {len(completed)} / {len(PIPELINE_STAGE_ORDER)}",
        "",
    ]


def generate_markdown_report(project: MigrationProject) -> str:
    """Build a stakeholder-ready Markdown report for a migration project."""
    bundle = _artifact_bundle(project)
    completed = _completed_stages(project)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"# Migration Assessment Report: {project.name}",
        "",
        f"**Project ID:** `{project.id}`  ",
        f"**Generated:** {generated_at}  ",
        f"**Source repository:** `{project.source_root}`  ",
        f"**Technology stack:** {project.tech_stack.primary_stack()}  ",
        f"**Current pipeline stage:** {project.current_stage.value}  ",
        "",
    ]
    lines.extend(_executive_summary(project, bundle))

    lines.extend(["## Pipeline Status", ""])
    stage_rows = []
    for stage in PIPELINE_STAGE_ORDER:
        if stage in completed:
            run_status = "Completed"
        elif project.current_stage == stage:
            run_status = "In progress"
        else:
            run_status = "Not started"
        gate = project.gate_for(stage)
        if gate is None:
            for candidate in (project.approval_gates or MigrationProject.default_gates()):
                if candidate.stage == stage:
                    gate = candidate
                    break
        if gate and gate.approved:
            gate_status = "Approved"
        elif gate and gate.required:
            gate_status = "Pending"
        else:
            gate_status = "Optional"
        stage_rows.append([STAGE_TITLES.get(stage.value, stage.value), run_status, gate_status])
    lines.extend(_markdown_table(["Stage", "Execution", "Approval gate"], stage_rows))
    lines.append("")

    discovery = bundle.get("discovery")
    if discovery:
        lines.extend(["## Discovery", ""])
        lines.append(f"- Primary stack: **{discovery.get('primary_stack', '—')}**")
        lines.append(f"- Services discovered: **{discovery.get('service_count', '—')}**")
        lines.append(f"- Target bounded contexts: **{discovery.get('target_bounded_contexts', '—')}**")
        langs = ", ".join(discovery.get("languages") or []) or "—"
        frameworks = ", ".join(discovery.get("frameworks") or []) or "—"
        lines.append(f"- Languages: {langs}")
        lines.append(f"- Frameworks: {frameworks}")
        lines.append("")

    ingest_summary = bundle.get("ingest_summary")
    if ingest_summary:
        lines.extend(["## Evidence Collection", ""])
        lines.append(f"- Evidence items collected: **{ingest_summary.get('evidence_count', '—')}**")
        lines.append(f"- Adapter stack: **{ingest_summary.get('adapters_used', '—')}**")
        lines.append("")

    diagnosis = bundle.get("diagnosis")
    if diagnosis:
        metrics = diagnosis.get("metrics") or {}
        smells = diagnosis.get("smells") or []
        coupling = diagnosis.get("coupling") or {}
        lines.extend(["## Architecture Health", ""])
        lines.append(f"- Services: **{diagnosis.get('service_count', '—')}**")
        lines.append(f"- Smells: **{len(smells)}**")
        lines.append(f"- Sync call chains: **{len(coupling.get('sync_chains') or [])}**")
        lines.append(f"- Graph density: **{metrics.get('density', 0):.4f}**")
        lines.append("")
        if smells:
            lines.append("### Top architecture smells")
            lines.append("")
            smell_rows = [
                [_smell_service_label(smell), smell.get("type") or smell.get("smell") or "—", smell.get("severity", "—")]
                for smell in smells[:15]
            ]
            lines.extend(_markdown_table(["Service / scope", "Smell", "Severity"], smell_rows))
            lines.append("")
        preview = diagnosis.get("recommendations_preview") or []
        if preview:
            lines.append("### Recommended actions")
            lines.append("")
            for item in preview:
                lines.append(f"- {item}")
            lines.append("")

    hypotheses = bundle.get("hypotheses")
    if isinstance(hypotheses, list) and hypotheses:
        lines.extend(["## Migration Hypotheses", ""])
        for hyp in hypotheses:
            confidence = hyp.get("confidence")
            title = hyp.get("title", "Hypothesis")
            if confidence is not None:
                lines.append(f"### {title} ({confidence:.0%} confidence)")
            else:
                lines.append(f"### {title}")
            lines.append("")
            if hyp.get("description"):
                lines.append(hyp["description"])
                lines.append("")
            lines.append(f"- **Target context:** {hyp.get('target_context', '—')}")
            services = _service_names(hyp.get("affected_services"))
            if services:
                lines.append(f"- **Affected services:** {', '.join(services)}")
            lines.append("")

    adrs = bundle.get("adrs")
    if isinstance(adrs, list) and adrs:
        lines.extend(["## Architecture Decision Records", ""])
        for adr in adrs:
            title = adr.get("title") or f"ADR-{adr.get('number', '?')}"
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"**Status:** {adr.get('status', 'proposed')}  ")
            lines.append(f"**Target context:** {adr.get('target_context', '—')}  ")
            lines.append("")
            if adr.get("decision"):
                lines.append("**Decision**")
                lines.append("")
                lines.append(adr["decision"])
                lines.append("")
            consequences = adr.get("consequences") or []
            if consequences:
                lines.append("**Consequences**")
                lines.append("")
                for item in consequences:
                    lines.append(f"- {item}")
                lines.append("")
            services = _service_names(adr.get("affected_services"))
            if services:
                lines.append(f"**Affected services:** {', '.join(services)}")
                lines.append("")

    plan = bundle.get("plan")
    if isinstance(plan, list) and plan:
        lines.extend(["## Migration Plan", ""])
        for phase in plan:
            lines.append(
                f"### Phase {phase.get('phase')}: {phase.get('name')} "
                f"({phase.get('duration_weeks', '?')} weeks, risk: {phase.get('risk', '—')})"
            )
            lines.append("")
            if phase.get("objective"):
                lines.append(phase["objective"])
                lines.append("")
            services = phase.get("services") or []
            if services:
                lines.append(f"**Services:** {', '.join(services)}")
                lines.append("")
            tasks = phase.get("tasks") or []
            if tasks:
                lines.append("**Key tasks**")
                lines.append("")
                for task in tasks:
                    lines.append(f"- {task}")
                lines.append("")

    playbook = bundle.get("playbook")
    if isinstance(playbook, list) and playbook:
        lines.extend(["## Developer Playbook Summary", ""])
        lines.append(f"Total manual tasks: **{len(playbook)}**")
        lines.append("")
        by_category: dict[str, list[dict[str, Any]]] = {}
        for task in playbook:
            category = str(task.get("category") or "other")
            by_category.setdefault(category, []).append(task)
        for category in sorted(by_category):
            tasks = by_category[category]
            lines.append(f"### {category.replace('_', ' ').title()} ({len(tasks)} tasks)")
            lines.append("")
            for task in tasks[:8]:
                owner = task.get("owner", "—")
                lines.append(f"- {task.get('task')} _(owner: {owner})_")
            if len(tasks) > 8:
                lines.append(f"- _…and {len(tasks) - 8} more_")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            REPORT_FOOTER,
            "",
        ]
    )
    return "\n".join(lines)


def _inline_format(text: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(text):
        start = text.find("**", index)
        if start == -1:
            result.append(html.escape(text[index:]))
            break
        result.append(html.escape(text[index:start]))
        end = text.find("**", start + 2)
        if end == -1:
            result.append(html.escape(text[start:]))
            break
        result.append(f"<strong>{html.escape(text[start + 2:end])}</strong>")
        index = end + 2
    return "".join(result)


def _markdown_to_html_paragraphs(text: str) -> str:
    chunks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("|"):
            rows = [line.strip() for line in block.splitlines() if line.strip()]
            if len(rows) >= 2:
                headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
                body_rows = rows[2:]
                table_html = ["<table><thead><tr>"]
                table_html.extend(f"<th>{html.escape(col)}</th>" for col in headers)
                table_html.append("</tr></thead><tbody>")
                for row in body_rows:
                    cells = [cell.strip() for cell in row.strip("|").split("|")]
                    table_html.append("<tr>")
                    table_html.extend(f"<td>{html.escape(cell)}</td>" for cell in cells)
                    table_html.append("</tr>")
                table_html.append("</tbody></table>")
                chunks.append("".join(table_html))
                continue
        if block.startswith("### "):
            chunks.append(f"<h3>{html.escape(block[4:])}</h3>")
        elif block.startswith("## "):
            chunks.append(f"<h2>{html.escape(block[3:])}</h2>")
        elif block.startswith("# "):
            chunks.append(f"<h1>{html.escape(block[2:])}</h1>")
        elif block.startswith("- "):
            items = block.splitlines()
            chunks.append("<ul>" + "".join(f"<li>{_inline_format(item[2:])}</li>" for item in items) + "</ul>")
        else:
            chunks.append(f"<p>{_inline_format(block)}</p>")
    return "\n".join(chunks)


def generate_html_report(project: MigrationProject) -> str:
    """Build a printable HTML report for stakeholders."""
    markdown = generate_markdown_report(project)
    body = _markdown_to_html_paragraphs(markdown)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(PRODUCT_NAME)} — {html.escape(project.name)}</title>
  <style>
    body {{
      font-family: Georgia, "Times New Roman", serif;
      color: #1f2933;
      max-width: 920px;
      margin: 2rem auto;
      padding: 0 1.5rem 3rem;
      line-height: 1.55;
    }}
    h1, h2, h3 {{ color: #102a43; }}
    h1 {{ border-bottom: 3px solid #243b53; padding-bottom: 0.4rem; }}
    h2 {{ margin-top: 2rem; border-bottom: 1px solid #d9e2ec; padding-bottom: 0.25rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      font-size: 0.95rem;
    }}
    th, td {{
      border: 1px solid #d9e2ec;
      padding: 0.55rem 0.65rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f0f4f8; }}
    p {{ margin: 0.6rem 0; }}
    ul {{ padding-left: 1.25rem; }}
    @media print {{
      body {{ margin: 0; max-width: none; }}
    }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def report_filename(project: MigrationProject, extension: str) -> str:
    slug = project.id.replace("proj-", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"migration-report-{slug}-{timestamp}.{extension}"
