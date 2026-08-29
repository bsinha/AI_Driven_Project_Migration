"""Build NetworkX graph from collected evidence."""

from __future__ import annotations

from typing import Any

import networkx as nx

from migrate_framework.graph.model import EdgeKind, GraphEdge, GraphNode, NodeKind, ServiceGraph
from migrate_framework.models import EvidenceItem


TYPE_TO_NODE_KIND: dict[str, NodeKind] = {
    "service": NodeKind.SERVICE,
    "deployment_unit": NodeKind.SERVICE,
    "database": NodeKind.DATABASE,
    "database_table": NodeKind.TABLE,
    "api_endpoint": NodeKind.API,
    "team_ownership": NodeKind.TEAM,
    "bounded_context": NodeKind.BOUNDED_CONTEXT,
    "landscape_smell": NodeKind.SMELL,
}

RELATION_TO_EDGE: dict[str, EdgeKind] = {
    "depends_on": EdgeKind.DEPENDS_ON,
    "calls": EdgeKind.CALLS,
    "stores_in": EdgeKind.STORES_IN,
    "owns": EdgeKind.OWNS,
    "exposes": EdgeKind.EXPOSES,
    "targets": EdgeKind.TARGETS,
    "belongs_to": EdgeKind.BELONGS_TO,
}

# Evidence types that describe relationships or metadata — not graph nodes themselves.
_SKIP_NODE_EVIDENCE_TYPES = frozenset({"http_dependency", "trace_span", "config_property", "build_artifact"})


def build_service_graph(evidence: list[EvidenceItem]) -> ServiceGraph:
    """Convert evidence items into a typed service graph."""
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def ensure_node(node_id: str, kind: NodeKind, label: str | None = None, **attrs: Any) -> None:
        if node_id not in nodes:
            nodes[node_id] = GraphNode(id=node_id, kind=kind, label=label or node_id, attributes=attrs)
        elif attrs:
            nodes[node_id].attributes.update(attrs)

    for item in evidence:
        if item.type in _SKIP_NODE_EVIDENCE_TYPES:
            _add_relationship_evidence(item, evidence, ensure_node, edges)
            continue

        kind = TYPE_TO_NODE_KIND.get(item.type, NodeKind.SERVICE)
        node_id = _node_id(item)
        ensure_node(node_id, kind, label=item.subject, source=item.source, evidence_type=item.type, **item.attributes)

        for rel in item.relations:
            edge_kind = RELATION_TO_EDGE.get(rel.relation, EdgeKind.DEPENDS_ON)
            target_kind = _infer_target_kind(rel.target, evidence)
            ensure_node(rel.target, target_kind, label=rel.target)
            edges.append(
                GraphEdge(
                    source=node_id,
                    target=rel.target,
                    kind=edge_kind,
                    attributes={"relation": rel.relation, "evidence_id": item.id},
                )
            )

    return ServiceGraph(nodes=list(nodes.values()), edges=edges)


def build_networkx_graph(service_graph: ServiceGraph) -> nx.DiGraph:
    """Build a NetworkX DiGraph from a ServiceGraph."""
    g = nx.DiGraph()
    for node in service_graph.nodes:
        g.add_node(node.id, kind=node.kind.value, label=node.label, **node.attributes)
    for edge in service_graph.edges:
        g.add_edge(
            edge.source,
            edge.target,
            kind=edge.kind.value,
            weight=edge.weight,
            **edge.attributes,
        )
    return g


def graph_metrics(g: nx.DiGraph) -> dict[str, Any]:
    """Compute basic graph metrics."""
    service_nodes = [n for n, d in g.nodes(data=True) if _is_deployable_service(n, d)]
    subgraph = g.subgraph(service_nodes) if service_nodes else g
    metrics: dict[str, Any] = {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "service_nodes": len(service_nodes),
        "density": float(nx.density(subgraph)) if subgraph.number_of_nodes() > 1 else 0.0,
    }
    if subgraph.number_of_nodes() > 0:
        in_degrees = dict(subgraph.in_degree())
        out_degrees = dict(subgraph.out_degree())
        metrics["max_in_degree"] = max(in_degrees.values()) if in_degrees else 0
        metrics["max_out_degree"] = max(out_degrees.values()) if out_degrees else 0
        metrics["avg_degree"] = sum(d for _, d in subgraph.degree()) / max(subgraph.number_of_nodes(), 1)
    return metrics


def _node_id(item: EvidenceItem) -> str:
    if item.type in {"service", "deployment_unit", "framework"}:
        return item.subject
    if item.type == "database":
        return f"db:{item.subject}"
    if item.type == "database_table":
        return f"table:{item.subject}"
    if item.type == "bounded_context":
        return f"ctx:{item.subject}"
    if item.type == "landscape_smell":
        return item.subject
    return item.id


def _infer_target_kind(target: str, evidence: list[EvidenceItem]) -> NodeKind:
    for item in evidence:
        if item.subject == target:
            return TYPE_TO_NODE_KIND.get(item.type, NodeKind.SERVICE)
    if target.startswith("db:") or target.endswith("_db"):
        return NodeKind.DATABASE
    if target.endswith("-service"):
        return NodeKind.SERVICE
    return NodeKind.SERVICE


def _dependency_source(item: EvidenceItem) -> str | None:
    source_id = item.attributes.get("from") or item.attributes.get("service")
    if source_id:
        return str(source_id)
    if "->" in item.subject:
        return item.subject.split("->", 1)[0]
    return None


def _add_relationship_evidence(
    item: EvidenceItem,
    evidence: list[EvidenceItem],
    ensure_node,
    edges: list[GraphEdge],
) -> None:
    """Turn dependency/trace/config evidence into edges between real entities."""
    source_id = _dependency_source(item)
    if source_id:
        ensure_node(source_id, NodeKind.SERVICE, label=source_id)

    for rel in item.relations:
        edge_kind = RELATION_TO_EDGE.get(rel.relation, EdgeKind.DEPENDS_ON)
        target_kind = _infer_target_kind(rel.target, evidence)
        ensure_node(rel.target, target_kind, label=rel.target)
        if source_id:
            edges.append(
                GraphEdge(
                    source=source_id,
                    target=rel.target,
                    kind=edge_kind,
                    attributes={"relation": rel.relation, "evidence_id": item.id, "evidence_type": item.type},
                )
            )


def _is_deployable_service(node_id: str, data: dict[str, Any]) -> bool:
    evidence_type = data.get("evidence_type")
    if evidence_type in {"service", "deployment_unit"}:
        return True
    if evidence_type in _SKIP_NODE_EVIDENCE_TYPES:
        return False
    if node_id.startswith("ev-"):
        return False
    if node_id.endswith("-service"):
        return True
    return data.get("kind") == "service" and ":" not in node_id
