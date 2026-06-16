"""The in-memory Labeled Property Graph (LPG) — creel's runtime source of truth.

Per decision D1 the model is an LPG: nodes and edges each have a **stable string
id**, one or more type labels, and a typed attribute bag. Edges are first-class —
they carry their own identity and attributes, so parallel edges of the same type
between the same endpoints (two distinct fundings) stay distinguishable.

:class:`Graph` is a thin, ergonomic wrapper over ``networkx.MultiDiGraph``: the
MultiDiGraph gives us multi-edges and per-edge attribute dicts for free, while the
wrapper enforces creel's invariants (globally-unique edge ids, typed accessors).

Example
-------
>>> g = Graph()
>>> _ = g.add_node("d:gov-x", types=("donor",), attributes={"name": "Government X"})
>>> _ = g.add_node("p:wash", types=("project",), attributes={"title": "WASH"})
>>> _ = g.add_edge("f:1", source="d:gov-x", target="p:wash", type="funds",
...                 attributes={"amount": 1_000_000, "currency": "USD"})
>>> _ = g.add_edge("f:2", source="d:gov-x", target="p:wash", type="funds",
...                 attributes={"amount": 500_000, "currency": "USD"})
>>> sorted(e.id for e in g.edges_between("d:gov-x", "p:wash"))   # parallel edges kept
['f:1', 'f:2']
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Optional, Sequence

import networkx as nx


@dataclass(frozen=True)
class Node:
    """An immutable view of a graph node: its id, type label(s), and attributes."""

    id: str
    types: tuple[str, ...]
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """An immutable view of a graph edge: a first-class, identity-bearing relation."""

    id: str
    source: str
    target: str
    type: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


class Graph:
    """A labeled property (multi-)graph with stable ids on nodes and edges.

    Edge ids are unique across the whole graph (not merely per node pair); this is
    what makes the canonical JSON edge-by-id map and per-element provenance possible
    (decision D4/D8).
    """

    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        #: edge_id -> (source, target) for O(1) edge lookup by id.
        self._edge_index: dict[str, tuple[str, str]] = {}
        #: Separable audit sidecar: element id -> evidence record (D8). Populated by
        #: the facade; deliberately NOT part of the canonical JSON (joined on demand).
        self.evidence: dict[str, Any] = {}
        #: Free-form run report (e.g. skipped edges, unbound elements) attached by
        #: the facade; also excluded from canonical JSON.
        self.report: dict[str, Any] = {}

    # -- construction ------------------------------------------------------
    def add_node(
        self,
        node_id: str,
        *,
        types: Sequence[str] = (),
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> Node:
        """Add (or merge into) a node. Re-adding an id merges types/attributes.

        Merging makes extraction idempotent: the same entity surfaced by two
        extractors lands on one node rather than duplicating.
        """
        types = tuple(types)
        attributes = dict(attributes or {})
        if self._g.has_node(node_id):
            data = self._g.nodes[node_id]
            merged_types = tuple(dict.fromkeys((*data.get("types", ()), *types)))
            data["types"] = merged_types
            data["attributes"] = {**data.get("attributes", {}), **attributes}
        else:
            self._g.add_node(node_id, types=types, attributes=attributes)
        return self.node(node_id)

    def add_edge(
        self,
        edge_id: str,
        *,
        source: str,
        target: str,
        type: str,
        attributes: Optional[Mapping[str, Any]] = None,
    ) -> Edge:
        """Add a typed edge with an explicit, globally-unique id.

        Raises ``ValueError`` if ``edge_id`` already exists (edge identity is
        sacred) or if an endpoint is missing.
        """
        if edge_id in self._edge_index:
            raise ValueError(f"duplicate edge id: {edge_id!r}")
        for endpoint in (source, target):
            if not self._g.has_node(endpoint):
                raise ValueError(
                    f"edge {edge_id!r} endpoint {endpoint!r} is not a node in the graph"
                )
        self._g.add_edge(
            source,
            target,
            key=edge_id,
            id=edge_id,
            type=type,
            attributes=dict(attributes or {}),
        )
        self._edge_index[edge_id] = (source, target)
        return self.edge(edge_id)

    # -- access ------------------------------------------------------------
    def has_node(self, node_id: str) -> bool:
        """True if a node with this id exists."""
        return self._g.has_node(node_id)

    def has_edge(self, edge_id: str) -> bool:
        """True if an edge with this id exists."""
        return edge_id in self._edge_index

    def node(self, node_id: str) -> Node:
        """Return the :class:`Node` view, or raise ``KeyError``."""
        if not self._g.has_node(node_id):
            raise KeyError(node_id)
        data = self._g.nodes[node_id]
        return Node(node_id, tuple(data.get("types", ())), dict(data.get("attributes", {})))

    def edge(self, edge_id: str) -> Edge:
        """Return the :class:`Edge` view, or raise ``KeyError``."""
        if edge_id not in self._edge_index:
            raise KeyError(edge_id)
        u, v = self._edge_index[edge_id]
        data = self._g.edges[u, v, edge_id]
        return Edge(edge_id, u, v, data["type"], dict(data.get("attributes", {})))

    def nodes(self) -> Iterator[Node]:
        """Iterate over all nodes."""
        for node_id in self._g.nodes:
            yield self.node(node_id)

    def edges(self) -> Iterator[Edge]:
        """Iterate over all edges."""
        for edge_id in self._edge_index:
            yield self.edge(edge_id)

    def nodes_of_type(self, type_id: str) -> Iterator[Node]:
        """Iterate over nodes carrying ``type_id`` as one of their labels."""
        for node in self.nodes():
            if type_id in node.types:
                yield node

    def edges_of_type(self, type_id: str) -> Iterator[Edge]:
        """Iterate over edges of relation type ``type_id``."""
        for edge in self.edges():
            if edge.type == type_id:
                yield edge

    def edges_between(self, source: str, target: str) -> Iterator[Edge]:
        """Iterate over all (parallel) edges from ``source`` to ``target``."""
        if not self._g.has_edge(source, target):
            return
        for key in self._g[source][target]:
            yield self.edge(key)

    # -- sizing ------------------------------------------------------------
    @property
    def number_of_nodes(self) -> int:
        """Count of nodes."""
        return self._g.number_of_nodes()

    @property
    def number_of_edges(self) -> int:
        """Count of edges."""
        return len(self._edge_index)

    def to_networkx(self) -> nx.MultiDiGraph:
        """Return a copy of the underlying ``networkx.MultiDiGraph``."""
        return self._g.copy()

    def __repr__(self) -> str:
        return f"Graph(nodes={self.number_of_nodes}, edges={self.number_of_edges})"
