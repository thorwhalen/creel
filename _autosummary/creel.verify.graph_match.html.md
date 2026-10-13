# creel.verify.graph_match

`graph_match` — compare a whole extracted graph to an expected one.

Per decision D9 this is **decomposable partial credit**, not all-or-nothing: it
scores nodes and edges with set-based precision/recall/F1 (after canonicalisation)
*and* scores the attributes of matched elements with per-attribute sub-verifiers
(`numeric_tolerance` for amounts, `normalized` for strings, …). The overall
score is a weighted blend, and `details` carries a full breakdown for audit.

Nodes are matched by id (creel’s ids are deterministic, so a correct extraction and
the expected graph share them). Edges are matched by their canonical key
`(type, source, target)` with greedy best-attribute alignment for parallel edges.

### Classes

| [`GraphMatch`](#creel.verify.graph_match.GraphMatch)([spec, attribute_verifiers, ...])   | Score an `actual` `Graph` against an `expected` one (partial credit).   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|

### *class* creel.verify.graph_match.GraphMatch(spec=None, attribute_verifiers=<factory>, node_weight=1.0, edge_weight=1.0, attr_weight=1.0, threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Score an `actual` `Graph` against an `expected` one (partial credit).
