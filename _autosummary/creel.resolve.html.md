# creel.resolve

Entity resolution — merge nodes that name the same real entity (decision #14 / D-OP8).

Messy multi-source documents (field-written, non-native English, OCR’d) name the
same entity in different ways — “Foundation Alpha” / “Alpha Fnd. (MFA)” /
“the Alpha foundation”. Per the changed decision #14 (report R14 §5), resolution is a
**required**, pluggable cascade — *blocking → matching → merging* — defaulting to
cheap deterministic strategies (exact id → normalize-before-merge → registry) with
hooks for embedding/LLM adjudication.

A [`Resolver`](#creel.resolve.Resolver) decides whether two nodes are the same entity. [`resolve_graph()`](#creel.resolve.resolve_graph)
applies one as a post-extraction pass: it blocks by node type, clusters by transitive
sameness (union-find), merges each cluster into one canonical node, and remaps every
edge — non-destructively returning a new graph with a `merges` report.

### Functions

| [`normalize_entity`](#creel.resolve.normalize_entity)(text)                        | Normalize an entity mention for matching: casefold, strip punctuation/legal/honorific.   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`resolve_graph`](#creel.resolve.resolve_graph)(graph, resolver, \*[, context]) | Return a new graph with same-entity nodes merged and edges remapped.                     |

### Classes

| [`CascadeResolver`](#creel.resolve.CascadeResolver)(resolvers)        | Try resolvers in order (cheapest first); two nodes match if ANY resolver matches.      |
|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`LLMResolver`](#creel.resolve.LLMResolver)(judge[, key])         | Adjudicate hard pairs with an injected judge `(name_a, name_b) -> bool`.               |
| [`NormalizeResolver`](#creel.resolve.NormalizeResolver)([key, aliases]) | Match by a normalized key attribute (+ an optional alias table).                       |
| [`RegistryResolver`](#creel.resolve.RegistryResolver)(registry[, key]) | Resolve mentions to canonical ids via an authoritative lookup table (an org registry). |
| [`Resolver`](#creel.resolve.Resolver)(\*args, \*\*kwargs)      | Decide whether two nodes denote the same real entity.                                  |

### *class* creel.resolve.CascadeResolver(resolvers)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Try resolvers in order (cheapest first); two nodes match if ANY resolver matches.

#### canonical_id(cluster)

Use the first resolver that can name a canonical id; else the smallest id.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.resolve.LLMResolver(judge, key='name')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Adjudicate hard pairs with an injected judge `(name_a, name_b) -> bool`.

The judge is injected (testable with a fake; an LLM in production via `creel[llm]`).
Reserve this for pairs the cheap resolvers leave ambiguous — it is the costly tail.

### *class* creel.resolve.NormalizeResolver(key='name', aliases=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Match by a normalized key attribute (+ an optional alias table). The cheap default.

#### canonical_id(cluster)

A stable id from the normalized key + type.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.resolve.RegistryResolver(registry, key='name')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Resolve mentions to canonical ids via an authoritative lookup table (an org registry).

#### canonical_id(cluster)

The registry’s canonical id for the cluster.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.resolve.Resolver(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Decide whether two nodes denote the same real entity.

#### same(a, b, , context=None)

Return `True` if `a` and `b` are the same entity.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### creel.resolve.normalize_entity(text)

Normalize an entity mention for matching: casefold, strip punctuation/legal/honorific.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.resolve.resolve_graph(graph, resolver, , context=None)

Return a new graph with same-entity nodes merged and edges remapped.

Blocking (by node type-tuple) → matching (`resolver.same`) → merging (union-find;
one canonical node per cluster, attributes first-wins) → edge remap. The original
graph is untouched; the result’s `report["merges"]` lists each merge.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)
