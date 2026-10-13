# creel.view

Projections of the graph into views — “one model, many views” (decision D15).

These are *not* renderers; they are deterministic, dependency-free projections of the
canonical graph into the shapes downstream consumers and tools want: flat records
and per-type tables (for DataFrames/reports), DOT and Mermaid (zero-config
visualisation), and Cytoscape.js elements (the reference interactive view). Concrete
renderers (PNG/PPTX/HTML) live in consumer packages on top of these.

All projections are deterministic (nodes/edges id-sorted) so output is stable and
git-diffable.

### Functions

| [`to_cytoscape`](#creel.view.to_cytoscape)(graph)                 | Project to Cytoscape.js `elements` (the reference interactive-view shape).      |
|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`to_dot`](#creel.view.to_dot)(graph, \*[, label_attr])     | Render the graph as Graphviz DOT (a directed multigraph).                       |
| [`to_embedding_records`](#creel.view.to_embedding_records)(graph)         | RAG-readiness: one `{"id","kind","type","text"}` record per element (EPIC 8.1). |
| [`to_mermaid`](#creel.view.to_mermaid)(graph, \*[, label_attr]) | Render the graph as a Mermaid `flowchart` (ids aliased to be Mermaid-safe).     |
| [`to_node_edge_records`](#creel.view.to_node_edge_records)(graph)         | Flatten the graph to `{"nodes": [...], "edges": [...]}` of plain records.       |
| [`to_table`](#creel.view.to_table)(graph, type_id)            | Rows for a single node-type *or* edge-type — one record per element.            |

### creel.view.to_cytoscape(graph)

Project to Cytoscape.js `elements` (the reference interactive-view shape).

Node `data` is near-isomorphic to the canonical node object, which is why
Cytoscape is the natural default interactive view (decision D15).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.view.to_dot(graph, , label_attr=None)

Render the graph as Graphviz DOT (a directed multigraph).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.view.to_embedding_records(graph)

RAG-readiness: one `{"id","kind","type","text"}` record per element (EPIC 8.1).

`text` is a compact natural-language rendering of the element (type + attributes;
for edges, the relation and its endpoints) suitable for embedding into a vector
index, so the extracted graph flows into graph+vector RAG without coupling.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### creel.view.to_mermaid(graph, , label_attr=None)

Render the graph as a Mermaid `flowchart` (ids aliased to be Mermaid-safe).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.view.to_node_edge_records(graph)

Flatten the graph to `{"nodes": [...], "edges": [...]}` of plain records.

Each node record is `{"id", "types", **attributes}`; each edge record is
`{"id", "type", "source", "target", **attributes}`. Ideal input for a
DataFrame, a table renderer, or a CSV export.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]]

### creel.view.to_table(graph, type_id)

Rows for a single node-type *or* edge-type — one record per element.

Returns node rows if `type_id` is a node-type present in the graph, else edge
rows for that edge-type (else an empty list).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
