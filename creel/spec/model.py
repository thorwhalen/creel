"""The grammar layer: a typed description of *what* graph creel should extract.

A :class:`GraphSpec` is creel's **graph-definition** layer and single source of
truth for structure (decision D1/D3/D7). It declares a taxonomy of node-types and
edge-types, each carrying typed attribute schemas. Edges are **first-class**: they
have their own identity and their own typed attributes (funding amounts, indicator
values), and they declare which node-types they connect.

The model is deliberately small, immutable (frozen dataclasses), and free of any
extraction concern — *how* to populate the graph lives in a physically separate
bindings layer joined on demand (see :mod:`creel.bindings`).

Example
-------
>>> spec = GraphSpec(
...     node_types=(
...         NodeType("donor", attributes=(AttrSchema("name"),)),
...         NodeType("project", attributes=(AttrSchema("title"),)),
...     ),
...     edge_types=(
...         EdgeType(
...             "funds", subject_type="donor", object_type="project",
...             attributes=(AttrSchema("amount", range="decimal", minimum=0),),
...         ),
...     ),
... )
>>> spec.node_type("donor").id
'donor'
>>> [a.name for a in spec.edge_type("funds").attributes]
['amount']
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Optional, Sequence

#: Primitive attribute ranges creel understands out of the box. Anything else is
#: treated as a reference to a named :class:`EnumDef` or (later) a node-type id.
PRIMITIVE_RANGES: frozenset[str] = frozenset(
    {"string", "integer", "decimal", "float", "boolean", "date", "datetime"}
)


@dataclass(frozen=True)
class AttrSchema:
    """Typed schema for a single attribute (a "leaf" value) of a node or edge.

    These follow ordinary schema semantics: a value may be a freeform string or
    number (or lists thereof via ``multivalued``), or constrained to an ``enum``,
    bounded by ``minimum``/``maximum``, or matched against a ``pattern``.

    The ``description`` is load-bearing: it doubles as the default natural-language
    instruction for the *schema-as-extractor* and *schema-as-verifier* defaults, so
    a usable extraction/verification can often be derived from the grammar alone.

    Note: ``minimum``/``maximum`` are *value-level* constraints. Per decision D6
    they are enforced in the verification pass, not by an LLM decoder's grammar.
    """

    name: str
    range: str = "string"
    required: bool = False
    multivalued: bool = False
    enum: Optional[Sequence[str]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        # Normalise enum to a tuple so the dataclass stays comparable/immutable.
        if self.enum is not None and not isinstance(self.enum, tuple):
            object.__setattr__(self, "enum", tuple(self.enum))


@dataclass(frozen=True)
class EnumDef:
    """A named, reusable set of permissible values (a constrained value-set)."""

    name: str
    permissible_values: Sequence[str]
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.permissible_values, tuple):
            object.__setattr__(
                self, "permissible_values", tuple(self.permissible_values)
            )


@dataclass(frozen=True)
class ElementType:
    """Base for a node-type or edge-type — a position in a recursive taxonomy.

    The taxonomy is expressed by ``is_a`` (single-inheritance parent) plus
    ``mixins`` (multiple inheritance). An element's *effective* attributes are its
    own plus all inherited ones (see :func:`effective_attributes`). ``id`` is an
    opaque identifier and may be a dotted path (e.g. ``"result.outcome"``) by
    convention, but the real hierarchy is the ``is_a``/``mixins`` graph.
    """

    id: str
    description: Optional[str] = None
    is_a: Optional[str] = None
    mixins: Sequence[str] = ()
    attributes: Sequence[AttrSchema] = ()
    abstract: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mixins, tuple):
            object.__setattr__(self, "mixins", tuple(self.mixins))
        # Accept attributes given as a mapping {name: AttrSchema} for ergonomics.
        attrs = self.attributes
        if isinstance(attrs, Mapping):
            attrs = tuple(attrs.values())
        elif not isinstance(attrs, tuple):
            attrs = tuple(attrs)
        object.__setattr__(self, "attributes", attrs)

    def attribute(self, name: str) -> Optional[AttrSchema]:
        """Return this type's *own* attribute schema named ``name`` (no inheritance)."""
        for a in self.attributes:
            if a.name == name:
                return a
        return None

    @property
    def parents(self) -> tuple[str, ...]:
        """All direct supertype ids (``is_a`` then ``mixins``)."""
        return ((self.is_a,) if self.is_a else ()) + tuple(self.mixins)


@dataclass(frozen=True)
class NodeType(ElementType):
    """A node-type (a.k.a. point type). Carries typed attributes and a taxonomy."""


@dataclass(frozen=True)
class EdgeType(ElementType):
    """An edge-type (a.k.a. link type): first-class, with its own typed attributes.

    ``subject_type`` and ``object_type`` name the node-types this edge connects
    (its endpoints). Edges have their own identity, so two ``funds`` edges between
    the same donor and project (two distinct fundings) are distinguishable.
    """

    subject_type: Optional[str] = None
    object_type: Optional[str] = None


@dataclass(frozen=True)
class GraphSpec:
    """A complete graph grammar: node-types, edge-types, and reusable enums.

    This is the graph-definition layer (SSOT). It knows nothing about extraction.
    """

    node_types: Sequence[NodeType] = ()
    edge_types: Sequence[EdgeType] = ()
    enums: Sequence[EnumDef] = ()
    id: Optional[str] = None
    version: str = "0.1.0"
    description: Optional[str] = None

    def __post_init__(self) -> None:
        for fname in ("node_types", "edge_types", "enums"):
            val = getattr(self, fname)
            if not isinstance(val, tuple):
                object.__setattr__(self, fname, tuple(val))

    # -- lookups -----------------------------------------------------------
    def node_type(self, type_id: str) -> Optional[NodeType]:
        """Return the node-type with this id, or ``None``."""
        return _by_id(self.node_types, type_id)

    def edge_type(self, type_id: str) -> Optional[EdgeType]:
        """Return the edge-type with this id, or ``None``."""
        return _by_id(self.edge_types, type_id)

    def element_type(self, type_id: str) -> Optional[ElementType]:
        """Return the node- or edge-type with this id, or ``None``."""
        return self.node_type(type_id) or self.edge_type(type_id)

    def enum(self, name: str) -> Optional[EnumDef]:
        """Return the named enum, or ``None``."""
        return _by_id(self.enums, name, key="name")

    def is_subtype(self, type_id: str, ancestor_id: str) -> bool:
        """True if ``type_id`` equals or descends from ``ancestor_id`` (is_a + mixins)."""
        if type_id == ancestor_id:
            return True
        et = self.element_type(type_id)
        if et is None:
            return False
        return any(self.is_subtype(p, ancestor_id) for p in et.parents)

    def iter_element_types(self) -> Iterable[ElementType]:
        """Yield every node-type then every edge-type."""
        yield from self.node_types
        yield from self.edge_types

    def with_(self, **changes: Any) -> "GraphSpec":
        """Return a copy of this spec with the given top-level fields replaced."""
        return replace(self, **changes)


# --- inheritance resolution ----------------------------------------------------


def effective_attributes(
    spec: GraphSpec, type_id: str
) -> "dict[str, AttrSchema]":
    """Resolve the full attribute set for a type, including inherited attributes.

    Walks ``is_a`` then ``mixins`` (depth-first), with a subtype's own attributes
    overriding inherited ones of the same name. Returns an insertion-ordered dict
    keyed by attribute name. Unknown ``type_id`` yields an empty dict.
    """
    et = spec.element_type(type_id)
    if et is None:
        return {}
    resolved: dict[str, AttrSchema] = {}
    # Inherited first (so own attributes override), parents in is_a→mixins order.
    for parent_id in et.parents:
        for name, attr in effective_attributes(spec, parent_id).items():
            resolved[name] = attr
    for attr in et.attributes:
        resolved[attr.name] = attr
    return resolved


def _by_id(items: Sequence[Any], value: str, *, key: str = "id") -> Optional[Any]:
    """Return the first item whose ``key`` attribute equals ``value``, else ``None``."""
    for item in items:
        if getattr(item, key) == value:
            return item
    return None
