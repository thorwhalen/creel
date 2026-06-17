"""The extractor strategy contract: what an extractor is given, and what it returns.

Per decision D5 an :class:`Extractor` is a **callable strategy** — any
``(ExtractionContext) -> Extraction`` — dispatched per grammar element. A plain
function is a valid extractor; no inheritance required (composition over OOP). The
three built-in families (pattern, query, LLM) all satisfy this one Protocol.

An extractor bound to a node-type produces :class:`ExtractedNode` instances; one
bound to an edge-type produces :class:`ExtractedEdge` instances; a richer extractor
(e.g. an LLM reading prose) may return both. Each extracted element may carry an
:class:`~creel.evidence.Evidence` record for auditability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Sequence, runtime_checkable

from creel.evidence import Evidence
from creel.extract.cache import Cache, NullCache
from creel.sources import SourceBundle
from creel.spec.model import ElementType, GraphSpec


@dataclass(frozen=True)
class ExtractedNode:
    """A node instance produced by an extractor (id + type label + attributes)."""

    id: str
    type: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    evidence: Optional[Evidence] = None


@dataclass(frozen=True)
class ExtractedEdge:
    """An edge instance produced by an extractor (first-class, with own attributes)."""

    id: str
    type: str
    source: str
    target: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    evidence: Optional[Evidence] = None


@dataclass(frozen=True)
class Extraction:
    """The result of running one extractor: the nodes and/or edges it found."""

    nodes: Sequence[ExtractedNode] = ()
    edges: Sequence[ExtractedEdge] = ()
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))

    @property
    def is_empty(self) -> bool:
        """True if the extraction produced no nodes and no edges."""
        return not self.nodes and not self.edges


@dataclass(frozen=True)
class ExtractionContext:
    """Everything an extractor needs to do its job for one grammar element.

    ``element_id`` is the taxonomy id being extracted (a node-type or edge-type id);
    ``element_type`` is its typed schema (whose attribute ``description``s drive the
    schema-as-extractor default). ``services`` carries injected dependencies (an LLM
    client, an entity resolver, …) so the core never imports a provider SDK.
    """

    element_id: str
    element_type: ElementType
    sources: SourceBundle
    spec: GraphSpec
    cache: Cache = field(default_factory=NullCache)
    services: Mapping[str, Any] = field(default_factory=dict)
    config: Mapping[str, Any] = field(default_factory=dict)
    #: The cluster of element types this pass covers (D-OP8). Defaults to just
    #: ``(element_type,)``; a cluster extractor reads all of them and emits instances
    #: of each in a single LLM pass. ``element_id``/``element_type`` are the primary
    #: (first) of the cluster, so single-element extractors are unaffected.
    element_types: Sequence[ElementType] = ()

    def __post_init__(self) -> None:
        types = (
            tuple(self.element_types) if self.element_types else (self.element_type,)
        )
        object.__setattr__(self, "element_types", types)


@runtime_checkable
class Extractor(Protocol):
    """A strategy that extracts instances of one grammar element from sources.

    Any callable ``(ExtractionContext) -> Extraction`` satisfies this Protocol.
    """

    def __call__(self, ctx: ExtractionContext) -> Extraction:
        """Extract instances of ``ctx.element_type`` from ``ctx.sources``."""
        ...
