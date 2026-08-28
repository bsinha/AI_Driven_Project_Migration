"""Service dependency graph models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    SERVICE = "service"
    DATABASE = "database"
    TABLE = "table"
    API = "api"
    TEAM = "team"
    BOUNDED_CONTEXT = "bounded_context"
    SMELL = "smell"


class EdgeKind(str, Enum):
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    STORES_IN = "stores_in"
    OWNS = "owns"
    EXPOSES = "exposes"
    TARGETS = "targets"
    BELONGS_TO = "belongs_to"


class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    attributes: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    weight: float = 1.0
    attributes: dict = Field(default_factory=dict)


class ServiceGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}
