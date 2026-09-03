"""L1 classified summary panels (progressive disclosure layer above L2 tables)."""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from migrate_framework.models import MigrationProject, PipelineStage
from migrate_framework.pipeline.governance import stage_summary_metrics
from migrate_framework.ui.taxonomy import classify_smell_risk, filter_entities, stage_visual_spec


def _metric_cards(items: list[tuple[str, str]], columns: int = 4) -> None:
    cols = st.columns(min(columns, len(items)) or 1)
    for index, (label, value) in enumerate(items):
        with cols[index % len(cols)]:
            st.metric(label, value)


def render_stage_l1_summary(
    stage: PipelineStage,
    project: MigrationProject,
    ingest: dict[str, Any],
    diagnosis: dict[str, Any],
    graph_payload: dict[str, Any] | None,
    *,
    key_prefix: str = "l1",
) -> None:
    """Render classified L1 cards for the current pipeline stage."""
    spec = stage_visual_spec(stage)
    panels = spec.get("l1_panels") or []
    if not panels:
        return

    st.markdown("**Classified summary**")
    filter_ctx = st.session_state.get("filter_context", "All")
    filter_risk = st.session_state.get("filter_risk", "all")
    contexts = ingest.get("bounded_contexts") or []

    if "stack_stats" in panels:
        service_count = ingest.get("service_count")
        if service_count is None:
            discovery = project.metadata.get("discovery") or {}
            service_count = discovery.get("service_count", "—")
        _metric_cards([
            ("Primary stack", project.tech_stack.primary_stack()),
            ("Services", str(service_count)),
            ("Contexts", str(ingest.get("bounded_context_count", len(contexts)))),
        ])

    if "context_count" in panels and contexts:
        rows = [{"context": c.get("context"), "services": len(c.get("services") or [])} for c in contexts[:8]]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if "evidence_coverage" in panels:
        coverage = ingest.get("coverage") or []
        if coverage:
            st.dataframe(coverage, use_container_width=True, hide_index=True)
        by_type = ingest.get("by_type") or {}
        if by_type:
            st.caption("Evidence by type: " + ", ".join(f"{k} ({v})" for k, v in sorted(by_type.items())))

    if "shared_db" in panels and ingest.get("shared_databases"):
        st.dataframe(ingest["shared_databases"], use_container_width=True, hide_index=True)

    if "readiness" in panels and ingest.get("readiness"):
        readiness = ingest["readiness"]
        score = ingest.get("readiness_score", "—")
        _metric_cards([("Readiness score", str(score))])
        checklist = {k.replace("_", " ").title(): ("✓" if v else "○") for k, v in readiness.items()}
        st.json(checklist)

    if "graph_metrics" in panels and graph_payload:
        metrics = graph_payload.get("metrics") or {}
        nodes = graph_payload.get("nodes") or []
        edges = graph_payload.get("edges") or []
        _metric_cards([
            ("Nodes", str(metrics.get("node_count", len(nodes)))),
            ("Edges", str(metrics.get("edge_count", len(edges)))),
            ("Density", f"{metrics.get('density', 0):.4f}"),
        ])

    if "node_kinds" in panels and graph_payload:
        kinds = Counter(n.get("kind", "—") for n in graph_payload.get("nodes") or [])
        edge_kinds = Counter(e.get("kind", "—") for e in graph_payload.get("edges") or [])
        st.caption("Node kinds: " + ", ".join(f"{k} ({v})" for k, v in kinds.most_common(6)))
        st.caption("Edge kinds: " + ", ".join(f"{k} ({v})" for k, v in edge_kinds.most_common(6)))

    if "smell_severity" in panels:
        smells = ingest.get("landscape_smells") or diagnosis.get("smells") or []
        smells = filter_entities(
            smells,
            context=filter_ctx,
            min_risk=filter_risk,
            bounded_contexts=contexts,
        )
        if smells:
            severity_counts = Counter(
                classify_smell_risk(str(s.get("smell") or s.get("type") or "")).value
                for s in smells
            )
            _metric_cards([(level, str(severity_counts.get(level, 0))) for level in ["high", "medium", "low"]])
        else:
            st.caption("No smells in current filter scope.")

    if "coupling_metrics" in panels and diagnosis.get("coupling"):
        coupling = diagnosis["coupling"]
        chains = coupling.get("sync_chains") or []
        _metric_cards([
            ("Sync chains", str(len(chains))),
            ("Max chain depth", str(coupling.get("max_chain_depth", "—"))),
        ])

    if "hypothesis_bands" in panels:
        hypotheses = project.metadata.get("hypotheses") or []
        if hypotheses:
            mandatory = sum(1 for h in hypotheses if h.get("mandatory"))
            optional = len(hypotheses) - mandatory
            high_conf = sum(1 for h in hypotheses if float(h.get("confidence", 0)) >= 0.8)
            _metric_cards([
                ("Hypotheses", str(len(hypotheses))),
                ("Mandatory", str(mandatory)),
                ("Optional", str(optional)),
                ("High confidence", str(high_conf)),
            ])
        else:
            st.caption("Run **hypothesize** to generate migration hypotheses.")

    if "adr_confidence" in panels:
        adrs = project.metadata.get("adrs") or []
        if adrs:
            mandatory = sum(1 for a in adrs if a.get("mandatory"))
            high_conf = sum(1 for a in adrs if float(a.get("confidence", 0)) >= 0.8)
            _metric_cards([
                ("ADRs", str(len(adrs))),
                ("Mandatory", str(mandatory)),
                ("High confidence", str(high_conf)),
            ])
            preview = [
                {
                    "title": a.get("title", "—"),
                    "mandatory": a.get("mandatory", False),
                    "confidence": a.get("confidence", "—"),
                }
                for a in adrs[:6]
            ]
            st.dataframe(preview, use_container_width=True, hide_index=True)
        else:
            st.caption("Run **recommend** to generate ADRs.")

    if "phase_risk" in panels:
        plan = project.metadata.get("migration_plan", {}) or {}
        phases = plan.get("phases") if isinstance(plan, dict) else []
        if phases:
            risk_counts = Counter(str(p.get("risk") or "medium") for p in phases)
            _metric_cards([(r, str(c)) for r, c in risk_counts.most_common(4)])
        else:
            st.caption("Run **plan** to generate migration phases.")

    if "compatibility" in panels:
        plan = project.metadata.get("migration_plan", {}) or {}
        layers = plan.get("compatibility_layers") if isinstance(plan, dict) else []
        if layers:
            st.dataframe(layers[:8], use_container_width=True, hide_index=True)
        else:
            st.caption("Compatibility layers appear in the migration plan artifact.")

    if "task_categories" in panels:
        playbook = project.metadata.get("playbook") or []
        if playbook:
            cats = Counter(str(t.get("category") or "other") for t in playbook)
            _metric_cards([(c.replace("_", " "), str(n)) for c, n in cats.most_common(4)])
            gap = sum(1 for t in playbook if t.get("evidence_gap"))
            if gap:
                st.caption(f"{gap} task(s) flagged with evidence gaps.")
        else:
            st.caption("Run **playbook** to generate developer tasks.")

    metrics = stage_summary_metrics(project, stage)
    if metrics and key_prefix:
        with st.expander("Stage analytics", expanded=False):
            st.json(metrics)

    st.caption("Expand **Full stage detail** below for complete L2 tables and raw artifacts.")
