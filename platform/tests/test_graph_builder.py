"""Graph builder tests."""

from migrate_framework.graph.builder import build_networkx_graph, build_service_graph
from migrate_framework.models import EvidenceItem, EvidenceRelation


def test_http_dependency_does_not_create_evidence_nodes() -> None:
    evidence = [
        EvidenceItem(
            type="service",
            source="metadata",
            subject="customer-address-service",
            attributes={"port": 8102},
        ),
        EvidenceItem(
            type="service",
            source="metadata",
            subject="customer-identity-service",
            attributes={"port": 8101},
        ),
        EvidenceItem(
            id="ev-9952442c4cea",
            type="http_dependency",
            source="metadata",
            subject="customer-address-service->customer-identity-service",
            attributes={
                "from": "customer-address-service",
                "to": "customer-identity-service",
            },
            relations=[EvidenceRelation(relation="calls", target="customer-identity-service")],
        ),
    ]

    graph = build_service_graph(evidence)
    node_ids = {node.id for node in graph.nodes}

    assert "ev-9952442c4cea" not in node_ids
    assert "customer-address-service" in node_ids
    assert "customer-identity-service" in node_ids
    assert any(
        edge.source == "customer-address-service" and edge.target == "customer-identity-service"
        for edge in graph.edges
    )

    metrics = build_networkx_graph(graph)
    from migrate_framework.graph.builder import graph_metrics

    stats = graph_metrics(metrics)
    assert stats["service_nodes"] == 2
