"""Architecture diagnosis: coupling, cohesion, smell detection."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from migrate_framework.graph.builder import build_networkx_graph, build_service_graph, graph_metrics
from migrate_framework.models import EvidenceItem, Landscape


def diagnose(evidence: list[EvidenceItem], landscape: Landscape | None = None) -> dict[str, Any]:
    """Analyze evidence for coupling, cohesion, and architectural smells."""
    service_graph = build_service_graph(evidence)
    g = build_networkx_graph(service_graph)
    metrics = graph_metrics(g)

    service_ids = _service_ids(evidence, landscape)
    db_usage = _database_sharing(evidence, service_ids)
    coupling = _coupling_analysis(g, service_ids)
    cohesion = _cohesion_analysis(evidence, landscape)
    smells = _detect_smells(evidence, db_usage, coupling, landscape)

    return {
        "metrics": metrics,
        "coupling": coupling,
        "cohesion": cohesion,
        "database_sharing": db_usage,
        "smells": smells,
        "service_count": len(service_ids),
        "recommendations_preview": _preview_recommendations(smells, db_usage),
    }


def _service_ids(evidence: list[EvidenceItem], landscape: Landscape | None) -> list[str]:
    if landscape and landscape.services:
        return [s.id for s in landscape.services]
    services = {e.subject for e in evidence if e.type == "service"}
    return sorted(services)


def _database_sharing(evidence: list[EvidenceItem], service_ids: list[str]) -> dict[str, list[str]]:
    db_to_services: dict[str, set[str]] = defaultdict(set)
    for item in evidence:
        if item.type == "service" and item.attributes.get("database"):
            db_to_services[item.attributes["database"]].add(item.subject)
        if item.type == "database_table":
            db = item.attributes.get("database")
            svc = item.attributes.get("service")
            if db and svc:
                db_to_services[db].add(svc)
    return {db: sorted(svcs) for db, svcs in db_to_services.items() if len(svcs) > 1}


def _coupling_analysis(g: nx.DiGraph, service_ids: list[str]) -> dict[str, Any]:
    subgraph = g.subgraph([s for s in service_ids if s in g]).copy()
    chains = []
    for src in service_ids:
        if src not in subgraph:
            continue
        for tgt in service_ids:
            if src == tgt or tgt not in subgraph:
                continue
            try:
                if nx.has_path(subgraph, src, tgt):
                    path = nx.shortest_path(subgraph, src, tgt)
                    if len(path) > 2:
                        chains.append(path)
            except nx.NetworkXNoPath:
                continue

    in_deg = dict(subgraph.in_degree())
    out_deg = dict(subgraph.out_degree())
    highly_coupled = [
        s for s in service_ids
        if in_deg.get(s, 0) + out_deg.get(s, 0) >= 4
    ]

    return {
        "sync_chains": chains[:20],
        "highly_coupled_services": highly_coupled,
        "avg_fan_in": sum(in_deg.values()) / max(len(in_deg), 1),
        "avg_fan_out": sum(out_deg.values()) / max(len(out_deg), 1),
    }


def _cohesion_analysis(evidence: list[EvidenceItem], landscape: Landscape | None) -> dict[str, Any]:
    if not landscape:
        return {"contexts": [], "fragmentation_score": 0.0}

    contexts = []
    total_services = len(landscape.services)
    for ctx in landscape.target_bounded_contexts:
        ctx_services = ctx.services
        shared_dbs = _context_shared_databases(evidence, ctx_services)
        contexts.append(
            {
                "name": ctx.name,
                "service_count": len(ctx_services),
                "services": ctx_services,
                "shared_databases_in_context": shared_dbs,
                "cohesion_score": round(1.0 - (len(shared_dbs) * 0.15), 2),
            }
        )

    fragmentation = total_services / max(len(landscape.target_bounded_contexts), 1)
    return {
        "contexts": contexts,
        "fragmentation_score": round(fragmentation, 2),
        "target_context_count": len(landscape.target_bounded_contexts),
    }


def _context_shared_databases(evidence: list[EvidenceItem], services: list[str]) -> list[str]:
    db_counts: Counter[str] = Counter()
    for item in evidence:
        if item.type == "service" and item.subject in services:
            db = item.attributes.get("database")
            if db:
                db_counts[db] += 1
    return [db for db, count in db_counts.items() if count > 1]


def _detect_smells(
    evidence: list[EvidenceItem],
    db_usage: dict[str, list[str]],
    coupling: dict[str, Any],
    landscape: Landscape | None,
) -> list[dict[str, Any]]:
    smells: list[dict[str, Any]] = []

    for db, services in db_usage.items():
        smells.append(
            {
                "type": "shared_database",
                "severity": "high",
                "subject": db,
                "services": services,
                "description": f"Database '{db}' is shared by {len(services)} services.",
            }
        )

    for chain in coupling.get("sync_chains", []):
        smells.append(
            {
                "type": "sync_rest_chain",
                "severity": "medium",
                "subject": "->".join(chain),
                "services": chain,
                "description": f"Sync call chain of length {len(chain)} detected.",
            }
        )

    manifest_smells = [
        e for e in evidence if e.type == "landscape_smell"
    ]
    for item in manifest_smells:
        smells.append(
            {
                "type": item.attributes.get("smell", "unknown"),
                "severity": "medium",
                "subject": item.attributes.get("service"),
                "description": f"Manifest smell: {item.attributes.get('smell')}",
                "source": "landscape-manifest",
            }
        )

    if landscape:
        for svc in landscape.services:
            if len(svc.smells) > 2:
                smells.append(
                    {
                        "type": "granular_decomposition",
                        "severity": "high",
                        "subject": svc.id,
                        "description": f"Service '{svc.id}' accumulates {len(svc.smells)} smells.",
                    }
                )

    return smells


def _preview_recommendations(smells: list[dict], db_usage: dict[str, list[str]]) -> list[str]:
    recs = []
    if db_usage:
        recs.append("Consolidate shared databases into per-bounded-context schemas.")
    if any(s["type"] == "sync_rest_chain" for s in smells):
        recs.append("Replace synchronous REST chains with events or orchestrated sagas.")
    if any(s["type"] == "granular_decomposition" for s in smells):
        recs.append("Merge over-decomposed customer microservices into a Customer Management context.")
    return recs
