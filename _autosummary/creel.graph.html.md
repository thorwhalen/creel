# creel.graph

creel graph layer: the in-memory LPG and its canonical JSON serialisation.

Re-exports the graph model ([`creel.graph.model`](creel.graph.model.html.md#module-creel.graph.model)) and the canonical JSON
codec ([`creel.graph.canonical`](creel.graph.canonical.html.md#module-creel.graph.canonical)).

### Functions

| [`from_canonical_dict`](#creel.graph.from_canonical_dict)(data, \*[, validate])    | Rebuild a [`Graph`](#creel.graph.Graph) from a canonical dict.                                                                                 |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`from_canonical_json`](#creel.graph.from_canonical_json)(text, \*[, validate])    | Parse canonical JSON `text` into a [`Graph`](#creel.graph.Graph) (see [`from_canonical_dict()`](#creel.graph.from_canonical_dict)). |
| [`to_canonical_dict`](#creel.graph.to_canonical_dict)(graph, \*[, spec])         | Build the canonical dict for `graph` (edges id-sorted; ready to serialise).                                                                                             |
| [`to_canonical_json`](#creel.graph.to_canonical_json)(graph, \*[, spec, indent]) | Serialise `graph` to canonical JSON text — deterministic and git-diffable.                                                                                              |
| [`validate_canonical`](#creel.graph.validate_canonical)(data)                     | Validate a canonical document against the format schema.                                                                                                                |

### Classes

| [`Edge`](#creel.graph.Edge)(id, source, target, type[, attributes])   | An immutable view of a graph edge: a first-class, identity-bearing relation.   |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`Graph`](#creel.graph.Graph)()                                        | A labeled property (multi-)graph with stable ids on nodes and edges.           |
| [`Node`](#creel.graph.Node)(id, types[, attributes])                  | An immutable view of a graph node: its id, type label(s), and attributes.      |

### *class* creel.graph.Edge(id, source, target, type, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph edge: a first-class, identity-bearing relation.

### *class* creel.graph.Graph

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A labeled property (multi-)graph with stable ids on nodes and edges.

Edge ids are unique across the whole graph (not merely per node pair); this is
what makes the canonical JSON edge-by-id map and per-element provenance possible
(decision D4/D8).

#### add_edge(edge_id, , source, target, type, attributes=None)

Add a typed edge with an explicit, globally-unique id.

Raises `ValueError` if `edge_id` already exists (edge identity is
sacred) or if an endpoint is missing.

* **Return type:**
  [`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)

#### add_node(node_id, , types=(), attributes=None)

Add (or merge into) a node. Re-adding an id merges types/attributes.

Merging makes extraction idempotent: the same entity surfaced by two
extractors lands on one node rather than duplicating.

* **Return type:**
  [`Node`](creel.graph.model.html.md#creel.graph.model.Node)

#### edge(edge_id)

Return the [`Edge`](#creel.graph.Edge) view, or raise `KeyError`.

* **Return type:**
  [`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)

#### edges()

Iterate over all edges.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### edges_between(source, target)

Iterate over all (parallel) edges from `source` to `target`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### edges_of_type(type_id)

Iterate over edges of relation type `type_id`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### evidence *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

element id -> evidence record (D8). Populated by
the facade; deliberately NOT part of the canonical JSON (joined on demand).

* **Type:**
  Separable audit sidecar

#### has_edge(edge_id)

True if an edge with this id exists.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### has_node(node_id)

True if a node with this id exists.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### node(node_id)

Return the [`Node`](#creel.graph.Node) view, or raise `KeyError`.

* **Return type:**
  [`Node`](creel.graph.model.html.md#creel.graph.model.Node)

#### nodes()

Iterate over all nodes.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](creel.graph.model.html.md#creel.graph.model.Node)]

#### nodes_of_type(type_id)

Iterate over nodes carrying `type_id` as one of their labels.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](creel.graph.model.html.md#creel.graph.model.Node)]

#### *property* number_of_edges *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Count of edges.

#### *property* number_of_nodes *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Count of nodes.

#### report *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

Free-form run report (e.g. skipped edges, unbound elements) attached by
the facade; also excluded from canonical JSON.

#### to_networkx()

Return a copy of the underlying `networkx.MultiDiGraph`.

* **Return type:**
  `MultiDiGraph`

### *class* creel.graph.Node(id, types, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph node: its id, type label(s), and attributes.

### creel.graph.from_canonical_dict(data, , validate=True)

Rebuild a [`Graph`](#creel.graph.Graph) from a canonical dict.

With `validate=True` (default) the document is checked against
`CANONICAL_GRAPH_SCHEMA` before loading, so malformed input fails fast
with a clear error rather than a confusing `KeyError` mid-build.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.graph.from_canonical_json(text, , validate=True)

Parse canonical JSON `text` into a [`Graph`](#creel.graph.Graph) (see [`from_canonical_dict()`](#creel.graph.from_canonical_dict)).

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.graph.to_canonical_dict(graph, , spec=None)

Build the canonical dict for `graph` (edges id-sorted; ready to serialise).

If `spec` is given, a lightweight `{"id", "version"}` reference is recorded
so a reader knows which grammar the instance claims to conform to.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.graph.to_canonical_json(graph, , spec=None, indent=2)

Serialise `graph` to canonical JSON text — deterministic and git-diffable.

Keys are sorted and edge arrays are id-sorted, so the same graph always yields
byte-identical output regardless of insertion order.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.graph.validate_canonical(data)

Validate a canonical document against the format schema.

Raises `jsonschema.ValidationError` if `data` is not a well-formed canonical
graph document.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Modules

| [`canonical`](creel.graph.canonical.html.md#module-creel.graph.canonical)   | Canonical JSON for creel graphs — the deterministic, versioned on-disk truth.   |
|-------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`model`](creel.graph.model.html.md#module-creel.graph.model)           | The in-memory Labeled Property Graph (LPG) — creel's runtime source of truth.   |
