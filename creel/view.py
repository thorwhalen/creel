"""Projections of the graph into views — "one model, many views" (decision D15).

These are *not* renderers; they are deterministic, dependency-free projections of the
canonical graph into the shapes downstream consumers and tools want: flat records
and per-type tables (for DataFrames/reports), DOT and Mermaid (zero-config
visualisation), and Cytoscape.js elements (the reference interactive view). Concrete
renderers (PNG/PPTX/HTML) live in consumer packages on top of these.

All projections are deterministic (nodes/edges id-sorted) so output is stable and
git-diffable.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from creel.graph.model import Edge, Graph, Node


def _nodes(graph: Graph) -> list[Node]:
    return sorted(graph.nodes(), key=lambda n: n.id)


def _edges(graph: Graph) -> list[Edge]:
    return sorted(graph.edges(), key=lambda e: e.id)


def to_node_edge_records(graph: Graph) -> dict[str, list[dict[str, Any]]]:
    """Flatten the graph to ``{"nodes": [...], "edges": [...]}`` of plain records.

    Each node record is ``{"id", "types", **attributes}``; each edge record is
    ``{"id", "type", "source", "target", **attributes}``. Ideal input for a
    DataFrame, a table renderer, or a CSV export.
    """
    return {
        "nodes": [{"id": n.id, "types": list(n.types), **dict(n.attributes)} for n in _nodes(graph)],
        "edges": [
            {"id": e.id, "type": e.type, "source": e.source, "target": e.target, **dict(e.attributes)}
            for e in _edges(graph)
        ],
    }


def to_table(graph: Graph, type_id: str) -> list[dict[str, Any]]:
    """Rows for a single node-type *or* edge-type — one record per element.

    Returns node rows if ``type_id`` is a node-type present in the graph, else edge
    rows for that edge-type (else an empty list).
    """
    node_rows = [{"id": n.id, **dict(n.attributes)} for n in _nodes(graph) if type_id in n.types]
    if node_rows:
        return node_rows
    return [
        {"id": e.id, "source": e.source, "target": e.target, **dict(e.attributes)}
        for e in _edges(graph)
        if e.type == type_id
    ]


def _node_label(node: Node, label_attr: str | None) -> str:
    if label_attr and label_attr in node.attributes:
        return str(node.attributes[label_attr])
    return node.id


def to_dot(graph: Graph, *, label_attr: str | None = None) -> str:
    """Render the graph as Graphviz DOT (a directed multigraph)."""
    lines = ["digraph creel {", "  rankdir=LR;"]
    for node in _nodes(graph):
        lines.append(f'  "{node.id}" [label="{_escape(_node_label(node, label_attr))}"];')
    for edge in _edges(graph):
        lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{_escape(edge.type)}"];')
    lines.append("}")
    return "\n".join(lines)


def to_mermaid(graph: Graph, *, label_attr: str | None = None) -> str:
    """Render the graph as a Mermaid ``flowchart`` (ids aliased to be Mermaid-safe)."""
    alias = {node.id: f"n{i}" for i, node in enumerate(_nodes(graph))}
    lines = ["flowchart LR"]
    for node in _nodes(graph):
        lines.append(f'  {alias[node.id]}["{_escape(_node_label(node, label_attr))}"]')
    for edge in _edges(graph):
        if edge.source in alias and edge.target in alias:
            lines.append(f"  {alias[edge.source]} -->|{_escape(edge.type)}| {alias[edge.target]}")
    return "\n".join(lines)


def to_cytoscape(graph: Graph) -> dict[str, Any]:
    """Project to Cytoscape.js ``elements`` (the reference interactive-view shape).

    Node ``data`` is near-isomorphic to the canonical node object, which is why
    Cytoscape is the natural default interactive view (decision D15).
    """
    return {
        "elements": {
            "nodes": [
                {"data": {"id": n.id, "label": n.types[0] if n.types else "",
                          "types": list(n.types), **dict(n.attributes)}}
                for n in _nodes(graph)
            ],
            "edges": [
                {"data": {"id": e.id, "source": e.source, "target": e.target, "type": e.type,
                          **dict(e.attributes)}}
                for e in _edges(graph)
            ],
        }
    }


def to_embedding_records(graph: Graph) -> list[dict[str, Any]]:
    """RAG-readiness: one ``{"id","kind","type","text"}`` record per element (EPIC 8.1).

    ``text`` is a compact natural-language rendering of the element (type + attributes;
    for edges, the relation and its endpoints) suitable for embedding into a vector
    index, so the extracted graph flows into graph+vector RAG without coupling.
    """
    records: list[dict[str, Any]] = []
    for node in _nodes(graph):
        attrs = "; ".join(f"{k}={v}" for k, v in sorted(node.attributes.items()))
        type_label = node.types[0] if node.types else "node"
        records.append({"id": node.id, "kind": "node", "type": type_label,
                        "text": f"{type_label}: {attrs}".strip(": ").strip()})
    for edge in _edges(graph):
        attrs = "; ".join(f"{k}={v}" for k, v in sorted(edge.attributes.items()))
        tail = f" ({attrs})" if attrs else ""
        records.append({"id": edge.id, "kind": "edge", "type": edge.type,
                        "text": f"{edge.source} {edge.type} {edge.target}{tail}"})
    return records


def _escape(text: str) -> str:
    """Escape double-quotes and newlines for DOT/Mermaid string contexts."""
    return re.sub(r'[\n"]', " ", str(text))
