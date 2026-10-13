# creel.export

Export adapters — interchange formats for the canonical graph (EPIC 3.4 / 8.4).

Deterministic, **dependency-free** emitters that let the extracted graph flow into the
wider ecosystem without coupling the core to any DB/library (decision D2/D10):

- [`to_jgf()`](#creel.export.to_jgf) — JSON Graph Format (the de-facto JSON interchange).
- [`to_graphml()`](#creel.export.to_graphml) — GraphML (XML; Gephi/yEd/NetworkX).
- [`to_cypher()`](#creel.export.to_cypher) — **parameterized** Cypher statements as *data* (never string
  interpolation — injection-safe; bind the params with a Neo4j driver).
- [`to_turtle()`](#creel.export.to_turtle) — RDF-star Turtle; attributes-on-edges become annotations on
  quoted triples (`<< s p o >>`), the lossless LPG↔RDF-star mapping (report R01).

All outputs are id-sorted → stable and git-diffable.

### Functions

| [`to_jgf`](#creel.export.to_jgf)(graph)                | Project to JSON Graph Format (v2-style: nodes as an id→object map).          |
|-------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`to_graphml`](#creel.export.to_graphml)(graph)            | Emit GraphML XML (string attributes; one `<key>` per attribute, id-sorted).  |
| [`to_cypher`](#creel.export.to_cypher)(graph)             | Return `(statement, params)` pairs to load the graph into Neo4j safely.      |
| [`to_turtle`](#creel.export.to_turtle)(graph, \*[, base]) | Emit RDF-star Turtle; edge attributes annotate quoted triples `<< s p o >>`. |

### creel.export.to_cypher(graph)

Return `(statement, params)` pairs to load the graph into Neo4j safely.

Relationship *types* cannot be parameterized in Cypher, so a generic `:REL` is
used with a `type` property. Bind `params` via the driver — never interpolate.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]]

### creel.export.to_graphml(graph)

Emit GraphML XML (string attributes; one `<key>` per attribute, id-sorted).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.export.to_jgf(graph)

Project to JSON Graph Format (v2-style: nodes as an id→object map).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.export.to_turtle(graph, , base='https://creel.dev/ns/')

Emit RDF-star Turtle; edge attributes annotate quoted triples `<< s p o >>`.

This is the lossless LPG↔RDF-star export (report R01). Caveat: parallel edges of
the same `(source, type, target)` annotate the same quoted triple — distinguish
them downstream by also reifying on the edge id if needed.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
