"""creel — a general, AI-powered source-to-graph extraction engine.

creel extracts a typed graph from a heterogeneous set of sources (prose, tables,
JSON, schema specs) and emits it as a clean, auditable Labeled Property Graph — the
single source of truth from which downstream persistence, query, annotation, and
rendering are projected.

Conceptually the package is one parameterised facade::

    extract(sources, graph_spec, extractors) -> graph

This ``v0.1`` exposes the **data layer**: the grammar (:mod:`creel.spec`) and the
graph model + canonical JSON (:mod:`creel.graph`). The ``extract`` facade and the
extractor/verifier strategy layers arrive in subsequent milestones — see
``misc/docs/design/ROADMAP.md``.
"""

from creel.graph import (
    CANONICAL_SCHEMA_URL,
    CANONICAL_VERSION,
    Edge,
    Graph,
    Node,
    from_canonical_dict,
    from_canonical_json,
    to_canonical_dict,
    to_canonical_json,
    validate_canonical,
)
from creel.spec import (
    AttrSchema,
    EdgeType,
    ElementType,
    EnumDef,
    GraphSpec,
    GraphValidationError,
    NodeType,
    ValidationIssue,
    effective_attributes,
    validate_graph,
)

__version__ = "0.0.2"

__all__ = [
    # grammar
    "AttrSchema",
    "EnumDef",
    "ElementType",
    "NodeType",
    "EdgeType",
    "GraphSpec",
    "effective_attributes",
    "validate_graph",
    "ValidationIssue",
    "GraphValidationError",
    # graph + canonical JSON
    "Graph",
    "Node",
    "Edge",
    "to_canonical_json",
    "from_canonical_json",
    "to_canonical_dict",
    "from_canonical_dict",
    "validate_canonical",
    "CANONICAL_SCHEMA_URL",
    "CANONICAL_VERSION",
    "__version__",
]
