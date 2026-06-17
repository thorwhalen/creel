"""Export adapters — interchange formats for the canonical graph (EPIC 3.4 / 8.4).

Deterministic, **dependency-free** emitters that let the extracted graph flow into the
wider ecosystem without coupling the core to any DB/library (decision D2/D10):

- :func:`to_jgf` — JSON Graph Format (the de-facto JSON interchange).
- :func:`to_graphml` — GraphML (XML; Gephi/yEd/NetworkX).
- :func:`to_cypher` — **parameterized** Cypher statements as *data* (never string
  interpolation — injection-safe; bind the params with a Neo4j driver).
- :func:`to_turtle` — RDF-star Turtle; attributes-on-edges become annotations on
  quoted triples (``<< s p o >>``), the lossless LPG↔RDF-star mapping (report R01).

All outputs are id-sorted → stable and git-diffable.
"""

from __future__ import annotations

import json
from typing import Any

from creel.graph.model import Edge, Graph, Node

CREEL_NS = "https://creel.dev/ns/"


def _nodes(graph: Graph) -> list[Node]:
    return sorted(graph.nodes(), key=lambda n: n.id)


def _edges(graph: Graph) -> list[Edge]:
    return sorted(graph.edges(), key=lambda e: e.id)


# --- JSON Graph Format --------------------------------------------------------
def to_jgf(graph: Graph) -> dict[str, Any]:
    """Project to JSON Graph Format (v2-style: nodes as an id→object map)."""
    return {
        "graph": {
            "directed": True,
            "nodes": {
                n.id: {"label": n.types[0] if n.types else "",
                       "metadata": {"types": list(n.types), **dict(n.attributes)}}
                for n in _nodes(graph)
            },
            "edges": [
                {"id": e.id, "source": e.source, "target": e.target, "relation": e.type,
                 "metadata": dict(e.attributes)}
                for e in _edges(graph)
            ],
        }
    }


# --- GraphML (XML) ------------------------------------------------------------
def to_graphml(graph: Graph) -> str:
    """Emit GraphML XML (string attributes; one ``<key>`` per attribute, id-sorted)."""
    node_attrs = sorted({k for n in graph.nodes() for k in n.attributes} | {"types"})
    edge_attrs = sorted({k for e in graph.edges() for k in e.attributes} | {"type"})
    keys, kid = [], {}
    for attr in node_attrs:
        kid[("node", attr)] = f"nd_{attr}"
        keys.append(f'  <key id="nd_{attr}" for="node" attr.name="{_x(attr)}" attr.type="string"/>')
    for attr in edge_attrs:
        kid[("edge", attr)] = f"ed_{attr}"
        keys.append(f'  <key id="ed_{attr}" for="edge" attr.name="{_x(attr)}" attr.type="string"/>')

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">', *keys,
             '  <graph edgedefault="directed">']
    for n in _nodes(graph):
        lines.append(f'    <node id="{_x(n.id)}">')
        lines.append(f'      <data key="nd_types">{_x(",".join(n.types))}</data>')
        for k in sorted(n.attributes):
            lines.append(f'      <data key="{kid[("node", k)]}">{_x(str(n.attributes[k]))}</data>')
        lines.append("    </node>")
    for e in _edges(graph):
        lines.append(f'    <edge id="{_x(e.id)}" source="{_x(e.source)}" target="{_x(e.target)}">')
        lines.append(f'      <data key="ed_type">{_x(e.type)}</data>')
        for k in sorted(e.attributes):
            lines.append(f'      <data key="{kid[("edge", k)]}">{_x(str(e.attributes[k]))}</data>')
        lines.append("    </edge>")
    lines += ["  </graph>", "</graphml>"]
    return "\n".join(lines)


# --- Cypher (parameterized, as data) -----------------------------------------
def to_cypher(graph: Graph) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(statement, params)`` pairs to load the graph into Neo4j safely.

    Relationship *types* cannot be parameterized in Cypher, so a generic ``:REL`` is
    used with a ``type`` property. Bind ``params`` via the driver — never interpolate.
    """
    statements: list[tuple[str, dict[str, Any]]] = []
    for n in _nodes(graph):
        statements.append((
            "MERGE (n {id: $id}) SET n += $props",
            {"id": n.id, "props": {"types": list(n.types), **dict(n.attributes)}},
        ))
    for e in _edges(graph):
        statements.append((
            "MATCH (a {id: $source}), (b {id: $target}) "
            "MERGE (a)-[r:REL {id: $id}]->(b) SET r += $props, r.type = $type",
            {"source": e.source, "target": e.target, "id": e.id, "type": e.type,
             "props": dict(e.attributes)},
        ))
    return statements


# --- RDF-star Turtle ----------------------------------------------------------
def to_turtle(graph: Graph, *, base: str = CREEL_NS) -> str:
    """Emit RDF-star Turtle; edge attributes annotate quoted triples ``<< s p o >>``.

    This is the lossless LPG↔RDF-star export (report R01). Caveat: parallel edges of
    the same ``(source, type, target)`` annotate the same quoted triple — distinguish
    them downstream by also reifying on the edge id if needed.
    """
    lines = [f"@prefix creel: <{base}> .",
             "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .", ""]
    for n in _nodes(graph):
        subject = f"creel:{_iri(n.id)}"
        for t in n.types:
            lines.append(f"{subject} rdf:type creel:{_iri(t)} .")
        for k in sorted(n.attributes):
            lines.append(f"{subject} creel:{_iri(k)} {_lit(n.attributes[k])} .")
    for e in _edges(graph):
        s, p, o = f"creel:{_iri(e.source)}", f"creel:{_iri(e.type)}", f"creel:{_iri(e.target)}"
        lines.append(f"{s} {p} {o} .")
        for k in sorted(e.attributes):
            lines.append(f"<< {s} {p} {o} >> creel:{_iri(k)} {_lit(e.attributes[k])} .")
    return "\n".join(lines) + "\n"


# --- helpers ------------------------------------------------------------------
def _x(text: str) -> str:
    """XML-escape."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _iri(text: str) -> str:
    """Make a safe IRI local name (replace anything outside [A-Za-z0-9_-])."""
    import re

    return re.sub(r"[^A-Za-z0-9_-]", "_", str(text)) or "x"


def _lit(value: Any) -> str:
    """Render a Turtle literal (numbers/bools bare; everything else a JSON string)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


__all__ = ["to_jgf", "to_graphml", "to_cypher", "to_turtle", "CREEL_NS"]
