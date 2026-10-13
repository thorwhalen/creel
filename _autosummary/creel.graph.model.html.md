# creel.graph.model

The in-memory Labeled Property Graph (LPG) — creel’s runtime source of truth.

Per decision D1 the model is an LPG: nodes and edges each have a \*\*stable string
id\*\*, one or more type labels, and a typed attribute bag. Edges are first-class —
they carry their own identity and attributes, so parallel edges of the same type
between the same endpoints (two distinct fundings) stay distinguishable.

[`Graph`](#creel.graph.model.Graph) is a thin, ergonomic wrapper over `networkx.MultiDiGraph`: the
MultiDiGraph gives us multi-edges and per-edge attribute dicts for free, while the
wrapper enforces creel’s invariants (globally-unique edge ids, typed accessors).

### Example

```pycon
>>> g = Graph()
>>> _ = g.add_node("d:gov-x", types=("donor",), attributes={"name": "Government X"})
>>> _ = g.add_node("p:water", types=("project",), attributes={"title": "Water Access"})
>>> _ = g.add_edge("f:1", source="d:gov-x", target="p:water", type="funds",
...                 attributes={"amount": 1_000_000, "currency": "USD"})
>>> _ = g.add_edge("f:2", source="d:gov-x", target="p:water", type="funds",
...                 attributes={"amount": 500_000, "currency": "USD"})
>>> sorted(e.id for e in g.edges_between("d:gov-x", "p:water"))   # parallel edges kept
['f:1', 'f:2']
```

### Classes

| [`Edge`](#creel.graph.model.Edge)(id, source, target, type[, attributes])   | An immutable view of a graph edge: a first-class, identity-bearing relation.   |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`Graph`](#creel.graph.model.Graph)()                                        | A labeled property (multi-)graph with stable ids on nodes and edges.           |
| [`Node`](#creel.graph.model.Node)(id, types[, attributes])                  | An immutable view of a graph node: its id, type label(s), and attributes.      |

### *class* creel.graph.model.Edge(id, source, target, type, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph edge: a first-class, identity-bearing relation.

### *class* creel.graph.model.Graph

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
  [`Edge`](#creel.graph.model.Edge)

#### add_node(node_id, , types=(), attributes=None)

Add (or merge into) a node. Re-adding an id merges types/attributes.

Merging makes extraction idempotent: the same entity surfaced by two
extractors lands on one node rather than duplicating.

* **Return type:**
  [`Node`](#creel.graph.model.Node)

#### edge(edge_id)

Return the [`Edge`](#creel.graph.model.Edge) view, or raise `KeyError`.

* **Return type:**
  [`Edge`](#creel.graph.model.Edge)

#### edges()

Iterate over all edges.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](#creel.graph.model.Edge)]

#### edges_between(source, target)

Iterate over all (parallel) edges from `source` to `target`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](#creel.graph.model.Edge)]

#### edges_of_type(type_id)

Iterate over edges of relation type `type_id`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](#creel.graph.model.Edge)]

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

Return the [`Node`](#creel.graph.model.Node) view, or raise `KeyError`.

* **Return type:**
  [`Node`](#creel.graph.model.Node)

#### nodes()

Iterate over all nodes.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](#creel.graph.model.Node)]

#### nodes_of_type(type_id)

Iterate over nodes carrying `type_id` as one of their labels.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](#creel.graph.model.Node)]

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

### *class* creel.graph.model.Node(id, types, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph node: its id, type label(s), and attributes.
