"""Canonical JSON for creel graphs — the deterministic, versioned on-disk truth.

Per decision D4 the canonical form is creel-owned and versioned (``$schema`` +
``version``), shapes nodes as an id→object map and edges as objects each with a
**required stable id**, and serialises with sorted keys + id-sorted arrays so that
diffs are one line and round-trips are byte-identical. That determinism is a tested
invariant (``to → from → to`` reproduces the exact bytes).

Public surface
--------------
- :func:`to_canonical_dict` / :func:`to_canonical_json`
- :func:`from_canonical_dict` / :func:`from_canonical_json`
- :data:`CANONICAL_SCHEMA_URL`, :data:`CANONICAL_VERSION`, :data:`CANONICAL_GRAPH_SCHEMA`
- :func:`validate_canonical`
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

import jsonschema

from creel.graph.model import Graph
from creel.spec.model import GraphSpec

#: The creel-owned ``$schema`` identifier for the canonical graph format. This is a
#: stable placeholder URL (decision D-OP4); it need not resolve to host the schema.
CANONICAL_SCHEMA_URL: str = "https://creel.dev/schema/graph/v1"

#: Canonical-format version (SchemaVer-style: bump on additive/breaking changes).
CANONICAL_VERSION: str = "1.0"

#: JSON Schema (Draft 2020-12) describing a valid canonical graph document.
CANONICAL_GRAPH_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": CANONICAL_SCHEMA_URL,
    "title": "creel canonical property graph",
    "type": "object",
    "required": ["$schema", "version", "nodes", "edges"],
    "properties": {
        "$schema": {"type": "string"},
        "version": {"type": "string"},
        "directed": {"type": "boolean"},
        "spec": {"type": ["object", "null"]},
        "nodes": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["types", "attributes"],
                "properties": {
                    "types": {"type": "array", "items": {"type": "string"}},
                    "attributes": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "source", "target", "type", "attributes"],
                "properties": {
                    "id": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "attributes": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def _str_keyed(attrs: Mapping[Any, Any]) -> dict[str, Any]:
    """Coerce attribute keys to ``str`` so ``sort_keys=True`` can't crash on mixed
    int/str keys (JSON object keys are strings anyway)."""
    return {str(k): v for k, v in attrs.items()}


def to_canonical_dict(
    graph: Graph, *, spec: Optional[GraphSpec] = None
) -> dict[str, Any]:
    """Build the canonical dict for ``graph`` (edges id-sorted; ready to serialise).

    If ``spec`` is given, a lightweight ``{"id", "version"}`` reference is recorded
    so a reader knows which grammar the instance claims to conform to.
    """
    nodes = {
        node.id: {"types": list(node.types), "attributes": _str_keyed(node.attributes)}
        for node in graph.nodes()
    }
    edges = [
        {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "attributes": _str_keyed(edge.attributes),
        }
        for edge in sorted(graph.edges(), key=lambda e: e.id)
    ]
    doc: dict[str, Any] = {
        "$schema": CANONICAL_SCHEMA_URL,
        "version": CANONICAL_VERSION,
        "directed": True,
        "nodes": nodes,
        "edges": edges,
    }
    if spec is not None:
        doc["spec"] = {"id": spec.id, "version": spec.version}
    return doc


def to_canonical_json(
    graph: Graph, *, spec: Optional[GraphSpec] = None, indent: int = 2
) -> str:
    """Serialise ``graph`` to canonical JSON text — deterministic and git-diffable.

    Keys are sorted and edge arrays are id-sorted, so the same graph always yields
    byte-identical output regardless of insertion order.
    """
    return json.dumps(
        to_canonical_dict(graph, spec=spec),
        sort_keys=True,
        ensure_ascii=False,
        indent=indent,
        allow_nan=False,  # NaN/Infinity are not valid JSON — fail loud, keep output portable
    )


def from_canonical_dict(data: Mapping[str, Any], *, validate: bool = True) -> Graph:
    """Rebuild a :class:`Graph` from a canonical dict.

    With ``validate=True`` (default) the document is checked against
    :data:`CANONICAL_GRAPH_SCHEMA` before loading, so malformed input fails fast
    with a clear error rather than a confusing ``KeyError`` mid-build.
    """
    if validate:
        validate_canonical(data)
    graph = Graph()
    for node_id, node in data["nodes"].items():
        graph.add_node(
            node_id,
            types=tuple(node.get("types", ())),
            attributes=node.get("attributes", {}),
        )
    for edge in data["edges"]:
        graph.add_edge(
            edge["id"],
            source=edge["source"],
            target=edge["target"],
            type=edge["type"],
            attributes=edge.get("attributes", {}),
        )
    return graph


def from_canonical_json(text: str, *, validate: bool = True) -> Graph:
    """Parse canonical JSON ``text`` into a :class:`Graph` (see :func:`from_canonical_dict`)."""
    return from_canonical_dict(json.loads(text), validate=validate)


def validate_canonical(data: Mapping[str, Any]) -> None:
    """Validate a canonical document against the format schema.

    Raises ``jsonschema.ValidationError`` if ``data`` is not a well-formed canonical
    graph document.
    """
    jsonschema.validate(instance=data, schema=CANONICAL_GRAPH_SCHEMA)
