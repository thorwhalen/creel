# creel.spec.model

The grammar layer: a typed description of *what* graph creel should extract.

A [`GraphSpec`](#creel.spec.model.GraphSpec) is creel’s **graph-definition** layer and single source of
truth for structure (decision D1/D3/D7). It declares a taxonomy of node-types and
edge-types, each carrying typed attribute schemas. Edges are **first-class**: they
have their own identity and their own typed attributes (funding amounts, indicator
values), and they declare which node-types they connect.

The model is deliberately small, immutable (frozen dataclasses), and free of any
extraction concern — *how* to populate the graph lives in a physically separate
bindings layer joined on demand (see [`creel.bindings`](creel.bindings.html.md#module-creel.bindings)).

### Example

```pycon
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
```

### Module Attributes

| [`PRIMITIVE_RANGES`](#creel.spec.model.PRIMITIVE_RANGES)   | Primitive attribute ranges creel understands out of the box.   |
|---------------------------------------------------------------------|----------------------------------------------------------------|

### Functions

| [`effective_attributes`](#creel.spec.model.effective_attributes)(spec, type_id)   | Resolve the full attribute set for a type, including inherited attributes.   |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------|

### Classes

| [`AttrSchema`](#creel.spec.model.AttrSchema)(name[, range, required, ...])          | Typed schema for a single attribute (a "leaf" value) of a node or edge.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`EdgeType`](#creel.spec.model.EdgeType)(id[, description, is_a, mixins, ...])    | An edge-type (a.k.a.                                                      |
| [`ElementType`](#creel.spec.model.ElementType)(id[, description, is_a, mixins, ...]) | Base for a node-type or edge-type — a position in a recursive taxonomy.   |
| [`EnumDef`](#creel.spec.model.EnumDef)(name, permissible_values[, description])  | A named, reusable set of permissible values (a constrained value-set).    |
| [`GraphSpec`](#creel.spec.model.GraphSpec)([node_types, edge_types, enums, ...])   | A complete graph grammar: node-types, edge-types, and reusable enums.     |
| [`NodeType`](#creel.spec.model.NodeType)(id[, description, is_a, mixins, ...])    | A node-type (a.k.a.                                                       |

### *class* creel.spec.model.AttrSchema(name, range='string', required=False, multivalued=False, enum=None, minimum=None, maximum=None, pattern=None, description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Typed schema for a single attribute (a “leaf” value) of a node or edge.

These follow ordinary schema semantics: a value may be a freeform string or
number (or lists thereof via `multivalued`), or constrained to an `enum`,
bounded by `minimum`/`maximum`, or matched against a `pattern`.

The `description` is load-bearing: it doubles as the default natural-language
instruction for the *schema-as-extractor* and *schema-as-verifier* defaults, so
a usable extraction/verification can often be derived from the grammar alone.

#### NOTE
`minimum`/`maximum` are *value-level* constraints. Per decision D6
they are enforced in the verification pass, not by an LLM decoder’s grammar.

### *class* creel.spec.model.EdgeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False, subject_type=None, object_type=None)

Bases: [`ElementType`](#creel.spec.model.ElementType)

An edge-type (a.k.a. link type): first-class, with its own typed attributes.

`subject_type` and `object_type` name the node-types this edge connects
(its endpoints). Edges have their own identity, so two `funds` edges between
the same donor and project (two distinct fundings) are distinguishable.

### *class* creel.spec.model.ElementType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Base for a node-type or edge-type — a position in a recursive taxonomy.

The taxonomy is expressed by `is_a` (single-inheritance parent) plus
`mixins` (multiple inheritance). An element’s *effective* attributes are its
own plus all inherited ones (see [`effective_attributes()`](#creel.spec.model.effective_attributes)). `id` is an
opaque identifier and may be a dotted path (e.g. `"result.outcome"`) by
convention, but the real hierarchy is the `is_a`/`mixins` graph.

#### attribute(name)

Return this type’s *own* attribute schema named `name` (no inheritance).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`AttrSchema`](#creel.spec.model.AttrSchema)]

#### *property* parents *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

All direct supertype ids (`is_a` then `mixins`).

### *class* creel.spec.model.EnumDef(name, permissible_values, description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A named, reusable set of permissible values (a constrained value-set).

### *class* creel.spec.model.GraphSpec(node_types=(), edge_types=(), enums=(), id=None, version='0.1.0', description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A complete graph grammar: node-types, edge-types, and reusable enums.

This is the graph-definition layer (SSOT). It knows nothing about extraction.

#### edge_type(type_id)

Return the edge-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`EdgeType`](#creel.spec.model.EdgeType)]

#### element_type(type_id)

Return the node- or edge-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ElementType`](#creel.spec.model.ElementType)]

#### enum(name)

Return the named enum, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`EnumDef`](#creel.spec.model.EnumDef)]

#### is_subtype(type_id, ancestor_id)

True if `type_id` equals or descends from `ancestor_id` (is_a + mixins).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### iter_element_types()

Yield every node-type then every edge-type.

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`ElementType`](#creel.spec.model.ElementType)]

#### node_type(type_id)

Return the node-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`NodeType`](#creel.spec.model.NodeType)]

#### with_(\*\*changes)

Return a copy of this spec with the given top-level fields replaced.

* **Return type:**
  [`GraphSpec`](#creel.spec.model.GraphSpec)

### *class* creel.spec.model.NodeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`ElementType`](#creel.spec.model.ElementType)

A node-type (a.k.a. point type). Carries typed attributes and a taxonomy.

### creel.spec.model.PRIMITIVE_RANGES *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= frozenset({'boolean', 'date', 'datetime', 'decimal', 'float', 'integer', 'string'})*

Primitive attribute ranges creel understands out of the box. Anything else is
treated as a reference to a named [`EnumDef`](#creel.spec.model.EnumDef) or (later) a node-type id.

### creel.spec.model.effective_attributes(spec, type_id)

Resolve the full attribute set for a type, including inherited attributes.

Walks `is_a` then `mixins` (depth-first), with a subtype’s own attributes
overriding inherited ones of the same name. Returns an insertion-ordered dict
keyed by attribute name. Unknown `type_id` yields an empty dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`AttrSchema`](#creel.spec.model.AttrSchema)]
