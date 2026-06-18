---
name: creel-projections
description: Project/transform a creel graph into everything downstream — persist, query, view, export, annotate are all projections of the one graph, never engine features. Use after you have a Graph and want to clean it up or get it OUT. Covers entity resolution (merge duplicate/same-entity nodes via Normalize/Registry/LLM/Cascade resolvers, the resolve= facade arg, or resolve_graph); the reify/unreify toggle (attributed edge ⇄ relation node when it goes n-ary, losslessly); view projections (to_node_edge_records/to_table/to_dot/to_mermaid/to_cytoscape); export adapters (to_jgf/to_graphml/to_cypher/to_turtle — GraphML, JGF, parameterized Cypher for Neo4j, RDF-star Turtle); the annotate/render contract; and trace (per-attribute grounding, TraceIndex reverse lookup, reanchor to source span). Triggers on "merge duplicate nodes", "entity resolution", "reify edge to node", "view as Mermaid/DOT/Cytoscape", "export to GraphML/Cypher/RDF/Turtle", "annotate a graph", "trace a value to its source span", "downstream rendering".
metadata:
  audience: users
---

# creel-projections — everything downstream is a projection of the one graph

The graph is the **single source of truth**. Persistence, query, RAG, rendering,
annotation, export — none of these are engine features. Each is a deterministic
**projection** of the same canonical LPG. You produce the graph once (skill
**creel-extract**, against a grammar from **creel-grammar**); then transform it
(resolve, reify) or get it out (view, export, annotate, trace) without ever
re-running extraction. All projections are dependency-free and id-sorted, so output
is stable and git-diffable.

A `Graph` for the examples below:

```python
from creel.graph.model import Graph

g = Graph()
g.add_node("d:1", types=("donor",), attributes={"name": "Gov X"})
g.add_node("p:1", types=("project",), attributes={"title": "Water"})
g.add_edge("f:1", source="d:1", target="p:1", type="funds", attributes={"amount": 100})
```

## resolve — merge nodes that name the same real entity

Messy multi-source corpora name one entity many ways ("Foundation Alpha" /
"Alpha Fnd. (MFA)" / "the Alpha foundation"). Resolution is a pluggable cascade —
*blocking → matching → merging* — that returns a **new** graph (original untouched)
with same-entity nodes merged, edges remapped, and evidence carried onto the
canonical node. `report["merges"]` lists each merge.

```python
from creel.resolve import NormalizeResolver, resolve_graph

merged = resolve_graph(g, NormalizeResolver(key="name"))   # cheap default
merged.report["merges"]   # [{"canonical": ..., "merged": [...]}, ...]
```

Resolvers (all are `Resolver` Protocols — callables, not class trees):

- **`NormalizeResolver(key="name", aliases={...})`** — match on a normalized key
  (casefold, strip punctuation/legal-forms/honorifics; `normalize_entity` is exposed).
  Optional `aliases` table for known synonyms. The cheap, deterministic default.
- **`RegistryResolver(registry, key="name")`** — resolve mentions to authoritative
  canonical ids via a lookup table (e.g. an org registry); the canonical id wins.
- **`LLMResolver(judge, key="name")`** — adjudicate the hard, ambiguous tail with an
  injected judge `(name_a, name_b) -> bool` (a fake in tests; an LLM in production —
  see **creel-ai**). Reserve it; it is the costly path.
- **`CascadeResolver([...])`** — try resolvers cheapest-first; nodes match if **any**
  resolver matches. The recommended production shape.

```python
from creel.resolve import CascadeResolver, NormalizeResolver, LLMResolver
cascade = CascadeResolver([NormalizeResolver(key="name"), LLMResolver(judge=judge)])
```

Run it inside the facade instead of as a separate pass — pass `resolve=`:

```python
g = extract(sources, spec, bindings, resolve=NormalizeResolver(key="name"))
```

## reify / unreify — toggle an attributed edge ⇄ a relation node

An attributed edge and a reified relation-node are two renderings of one fact (D1).
Keep the simpler edge until a relation goes genuinely **n-ary** (e.g. a reading that
needs shared `Period`/`Source`/disaggregation nodes, or that will be merged across
periods — resolution then dedups the node). The pair is **lossless** — a round-trip
reproduces the original (evidence rides along, including per-attribute records).

```python
from creel.reify import reify, unreify

reified  = reify(g, "funds", node_type="funding")    # edge -> node + two connector edges
original = unreify(reified, "funds", node_type="funding")   # back, byte-identical
```

Per-edge-type: other edges are untouched. `node_type`/connector names must be fresh
(it raises otherwise, so `unreify` can tell reified structure from real data).

**Time series:** carry a measurement over time as **parallel period-keyed edges**
(one edge per period), and `reify` an edge into a node only when it goes n-ary
(needs its own `Period`/`Source`/disaggregation nodes). For timestamps, use the
reserved keys in `creel.temporal` — `valid_from`/`valid_to`/`observed_at`/
`recorded_at` (exposed as `RESERVED`; `is_temporal_attribute(name)` tests
membership). They are a **convention, not enforced** by the grammar.

## view — projections for tables, DataFrames, and zero-config visualisation

`creel.view` projects to the shapes downstream tools want. These are **not**
renderers (concrete PNG/HTML renderers live in consumer packages).

```python
from creel.view import (
    to_node_edge_records, to_table, to_dot, to_mermaid, to_cytoscape,
)

to_node_edge_records(g)   # {"nodes": [{"id","types",**attrs}], "edges": [{"id","type","source","target",**attrs}]}
to_table(g, "donor")      # rows for one node-type OR edge-type → DataFrame/CSV
to_dot(g, label_attr="name")       # Graphviz DOT string
to_mermaid(g, label_attr="name")   # Mermaid flowchart (ids aliased n0/n1 so colons are safe)
to_cytoscape(g)           # Cytoscape.js {"elements": {...}} — the reference interactive view
```

`to_embedding_records(g)` emits one `{"id","kind","type","text"}` per element for
graph+vector **RAG** indexing.

## export — interchange formats for downstream tools and DBs

`creel.export` emits the graph into the wider ecosystem with zero coupling.

```python
from creel.export import to_jgf, to_graphml, to_cypher, to_turtle

to_jgf(g)       # JSON Graph Format dict (de-facto JSON interchange)
to_graphml(g)   # GraphML XML string (Gephi / yEd / NetworkX)
to_turtle(g)    # RDF-star Turtle; edge attributes annotate quoted triples << s p o >>
```

`to_cypher(g)` returns **parameterized** `(statement, params)` pairs — values live in
`params`, never interpolated (injection-safe). Bind them with a Neo4j driver:

```python
for statement, params in to_cypher(g):
    session.run(statement, **params)
```

## annotate / render — the machine + human overlay, and the renderer seam

A standoff **`Annotation`** overlay (kept separate from the graph, joined by target)
serves both an LLM laying an insight and a human "coding" a passage — one schema;
they differ only by `motivation` and provenance `attributed_kind`
(`software_agent` vs `person`).

```python
from creel.annotate import Annotation, Selection, IDENTIFYING, TAGGING
from creel.evidence import TextQuoteSelector

machine = Annotation("a1", target="d:1", body="major bilateral donor", motivation=IDENTIFYING)
sel = Selection("s1", "donor_agreement", TextQuoteSelector(exact="Government X"))
human = Annotation("a2", target=sel, body="d:1", motivation=TAGGING)   # span -> node
attr  = Annotation("a3", target=("f:1", "amount"), body="verified")    # per-attribute target
```

`AnnotatedGraph(graph, annotations=..., presentation=...)` is the three-layer render
**contract**; a `GraphRenderer` is a `runtime_checkable` Protocol
(`render(graph: AnnotatedGraph, *, options=None) -> RenderArtifact`). creel ships the contract;
concrete renderers are consumer-package work — build them on the `view` projections.

## trace — source ↔ graph, both ways

Three additive capabilities that make the graph clickable both directions without
changing it (the canonical graph never moves):

```python
from creel.trace import (
    set_attribute_evidence, attribute_evidence, TraceIndex, reanchor, verify_anchor,
)

# A1 — per-attribute grounding: a single value, not just the node, traces to its span
set_attribute_evidence(g, "d:1", "org_code", ev)
attribute_evidence(g, "d:1", "org_code")          # falls back to element-level evidence

# A3 — reverse index: which elements did this source span / cell / page produce?
idx = TraceIndex(g)
idx.elements_at("doc", 15)                  # evidence keys whose span contains offset 15
idx.elements_in_cell("tbl", 2, "amount")    # keys grounded in a table cell
idx.elements_on_page("doc", 3)

# A4 — reanchor a quote after the source is edited / re-OCR'd (exact → context → fuzzy)
span = reanchor(selector, new_text)         # (start, end) or None; verify_anchor() for a quick check
```

## Verify before you project — and the sibling skills

Confirm correctness with **creel-evaluation**'s pluggable verifiers (never `==`)
before persisting or rendering a graph. Other handoffs:

- **creel-extract** — produce the `Graph` (the `extract()` facade and its `resolve=` arg).
- **creel-grammar** — the node/edge types and `AttrSchema` you are projecting.
- **creel-ai** — the LLM judge behind `LLMResolver`, and LLM extraction generally.
- **creel-evaluation** — verify the graph (`numeric_tolerance`/`graph_match`/`llm_rubric`).
