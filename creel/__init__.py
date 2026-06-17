"""creel — a general, AI-powered source-to-graph extraction engine.

creel extracts a typed graph from a heterogeneous set of sources (prose, tables,
JSON, schema specs) and emits it as a clean, auditable Labeled Property Graph — the
single source of truth from which downstream persistence, query, annotation, and
rendering are projected.

Conceptually the package is one parameterised facade::

    extract(sources, graph_spec, extractors) -> graph

This ``v0.1`` exposes the grammar (:mod:`creel.spec`), the graph model + canonical
JSON (:mod:`creel.graph`), and the ``extract`` facade with the deterministic
pattern/function extractor family (:mod:`creel.extract`). The query and LLM
strategies and the verifier subsystem arrive in subsequent milestones — see
``misc/docs/design/ROADMAP.md``.
"""

from creel.bindings import ExtractorBinding, ExtractorBindings
from creel.evidence import (
    Confidence,
    Evidence,
    Provenance,
    TextPositionSelector,
    TextQuoteSelector,
)
from creel.extract import (
    Cache,
    DictCache,
    ExtractedEdge,
    ExtractedNode,
    Extraction,
    ExtractionContext,
    Extractor,
    NullCache,
    RegexEdgeExtractor,
    RegexNodeExtractor,
    available_extractors,
    register_extractor,
)
from creel.evaluation import (
    CaseResult,
    CorpusCase,
    CorpusResult,
    evaluate_case,
    evaluate_corpus,
)
from creel.export import to_cypher, to_graphml, to_jgf, to_turtle
from creel.facade import extract
from creel.ingest import ingest, ingest_paths
from creel.policy import ExtractionPolicy
from creel.reify import reify, unreify
from creel.resolve import (
    CascadeResolver,
    LLMResolver,
    NormalizeResolver,
    RegistryResolver,
    Resolver,
    normalize_entity,
    resolve_graph,
)
from creel.sources import Source, SourceBundle, coerce_sources
from creel.annotate import Annotation, Selection
from creel.render import AnnotatedGraph, GraphRenderer, RenderArtifact
from creel.trace import (
    TraceIndex,
    attribute_evidence,
    reanchor,
    set_attribute_evidence,
    verify_anchor,
)
from creel.view import (
    to_cytoscape,
    to_dot,
    to_embedding_records,
    to_mermaid,
    to_node_edge_records,
    to_table,
)
from creel.verify import (
    Composite,
    ExactMatch,
    GraphMatch,
    LLMRubric,
    NormalizedMatch,
    NumericTolerance,
    SchemaConstraint,
    SemanticSimilarity,
    SetMatch,
    Verdict,
    VerificationContext,
    Verifier,
    available_verifiers,
    build_verifier,
    register_verifier,
    schema_description_verifier,
)
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

__version__ = "0.1.0"

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
    # facade + sources + ingestion
    "extract",
    "ingest",
    "ingest_paths",
    "Source",
    "SourceBundle",
    "coerce_sources",
    # extraction strategies
    "Extractor",
    "ExtractionContext",
    "Extraction",
    "ExtractedNode",
    "ExtractedEdge",
    "RegexNodeExtractor",
    "RegexEdgeExtractor",
    "register_extractor",
    "available_extractors",
    "Cache",
    "NullCache",
    "DictCache",
    # bindings + policy
    "ExtractorBinding",
    "ExtractorBindings",
    "ExtractionPolicy",
    # entity resolution
    "Resolver",
    "NormalizeResolver",
    "RegistryResolver",
    "LLMResolver",
    "CascadeResolver",
    "resolve_graph",
    "normalize_entity",
    # reification toggle (D1 / #12)
    "reify",
    "unreify",
    # projections / views (D15)
    "to_node_edge_records",
    "to_table",
    "to_dot",
    "to_mermaid",
    "to_cytoscape",
    "to_embedding_records",
    # annotation overlay + render contract (D15 / D-OP9)
    "Annotation",
    "Selection",
    "AnnotatedGraph",
    "GraphRenderer",
    "RenderArtifact",
    # traceability (D-OP9 A1/A3/A4)
    "TraceIndex",
    "reanchor",
    "verify_anchor",
    "set_attribute_evidence",
    "attribute_evidence",
    # export adapters (D2 / EPIC 3.4, 8.4)
    "to_jgf",
    "to_graphml",
    "to_cypher",
    "to_turtle",
    # evidence / auditability
    "Evidence",
    "Provenance",
    "Confidence",
    "TextQuoteSelector",
    "TextPositionSelector",
    # evaluation / verifiers
    "Verifier",
    "Verdict",
    "VerificationContext",
    "ExactMatch",
    "NormalizedMatch",
    "NumericTolerance",
    "SetMatch",
    "SchemaConstraint",
    "SemanticSimilarity",
    "Composite",
    "GraphMatch",
    "LLMRubric",
    "schema_description_verifier",
    "build_verifier",
    "register_verifier",
    "available_verifiers",
    # evaluation runner
    "CorpusCase",
    "CaseResult",
    "CorpusResult",
    "evaluate_case",
    "evaluate_corpus",
    "__version__",
]
