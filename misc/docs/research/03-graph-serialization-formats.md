# 03 — Graph serialization & JSON interchange formats

> **TL;DR.** No off-the-shelf graph serialization format cleanly meets creel's
> hard requirements — first-class **typed attributes on edges**, **recursive
> node/edge-type taxonomies**, **per-element extraction/verification metadata**,
> and **git-diffable provenance**. The closest JSON candidates are the **JSON
> Graph Format (JGF v2)** and **NetworkX node-link**, both of which model the
> property-graph shape (typed nodes/edges with arbitrary attribute bags) but
> punt on schema, typing, and provenance. RDF/JSON-LD models provenance and
> schema beautifully but is hostile to edge attributes (needs reification or
> RDF-star) and is a poor git-diff target. **Recommendation:** define creel's
> own **explicit, versioned canonical JSON** — a property-graph node-link
> document that is a *deliberate superset of JGF v2 conventions* (so JGF/NetworkX
> export is near-lossless) — and ship a thin **adapter set** (strategy pattern)
> that downcasts to JGF, NetworkX, Cytoscape.js, GraphML, GEXF, DOT, GraphSON,
> JSON-LD/PROV, and Neo4j/APOC JSON. Keep the canonical shape under your own
> `$schema` so you control evolution.

## Background / landscape

Graph serialization formats cluster into four lineages, each shaped by the
community that produced it:

1. **Property-graph / node-link JSON** (JGF, NetworkX node-link, Cytoscape.js,
   APOC/Neo4j JSON, GraphSON). These treat a graph as *nodes + edges*, each
   carrying an arbitrary key/value **attribute bag**. They natively support
   **attributes on edges** — creel's central requirement — because the edge is a
   first-class object, not a predicate. They differ on identifier conventions,
   typing rigor, and tooling.
2. **XML graph-drawing formats** (GraphML, GEXF). Born from the graph-drawing /
   network-science community. Strong on **typed attribute declarations** (GraphML
   `<key>` blocks declare attribute name + type + default), good tooling (Gephi,
   yEd, igraph, NetworkX), but XML — verbose and a weaker git-diff target than
   JSON [1][2].
3. **Layout/description languages** (DOT/Graphviz). A *rendering* language, not a
   data-interchange format. Attributes exist but are presentation-oriented and
   weakly typed; round-tripping rich data through DOT is lossy [3].
4. **RDF / linked-data** (Turtle, N-Triples, JSON-LD, PROV-JSONLD). A *semantic*
   triple model: subject–predicate–object. Superb for global identifiers
   (IRIs), shared schema/ontology references, and **provenance** (W3C PROV-O),
   but its rigid triple shape cannot natively hang attributes on a relationship —
   you must **reify** the edge into a node or adopt **RDF-star** [4][5].

Creel's data model is squarely a **property graph with a schema**: typed node-
and edge-types organized in recursively-subdivided taxonomies, typed attributes
(freeform / enum / range) on both nodes *and* edges, plus a physically separate
extraction/verification metadata layer joined on demand. That model maps most
naturally onto lineage (1), borrows the *typed-attribute declaration* idea from
(2), and the *provenance vocabulary* from (4).

## Comparative analysis

| Format | Encoding | Typed nodes/edges | **Attrs on edges** | Schema refs | Multigraph / parallel edges | Directedness | ID convention | Provenance | Git diff/readability | Tooling/ecosystem |
|---|---|---|---|---|---|---|---|---|---|---|
| **JGF v2** | JSON | edge `relation`; node via key; types via `metadata` | **Yes** (`metadata` on edge) | `$schema` (JSON-Schema) | Yes (edges are an array; no required unique edge id) | per-graph `directed` (default true), per-edge override | nodes = map keys; edges have no required id | none built-in (use `metadata`) | Good (JSON, but edge array order churns) | Moderate (gravis, jgf py/npm) [6][7] |
| **NetworkX node-link** | JSON | via arbitrary node/edge attrs | **Yes** (edge dict attrs) | none | Yes (`multigraph:true`, edge `key`) | `directed` bool | `id` per node; edge `source`/`target`(+`key`) | none | Good | **Excellent** (NetworkX hub → GraphML/GEXF/GML/…) [8] |
| **Cytoscape.js** | JSON | `data` bag; compound nodes via `parent` | **Yes** (`data` on edge) | none | Yes (each edge has `data.id`) | `directed`-ish via render; data-level neutral | every element needs `data.id` | none | Good (verbose; position/style noise) | Strong for **viz**; Cytoscape desktop import [9] |
| **GraphSON 3.0** | JSON | vertex/edge **labels**; rich `g:*` typed values | **Yes** (edge properties) | none (TinkerPop schema external) | Yes (edge ids) | edges directed (out/in V) | typed ids (`g:Int64` etc.) | none | Poor (deeply nested, type-tagged) | Strong in **Gremlin/TinkerPop** world [10] |
| **GraphML** | XML | `<key>` declares attr name+**type**+default | **Yes** (`<data>` on `<edge>`) | XSD; `<key>` typing | Yes (optional edge `id`) | `edgedefault` + per-edge `directed` | node/edge `id` | none | Fair (XML verbose, but stable order) | **Excellent** (Gephi, yEd, igraph, NetworkX) [1][2] |
| **GEXF** | XML | `<attributes>` declares typed columns; **dynamic/spells** | **Yes** | typed `<attribute>` decls | Yes | `defaultedgetype` | node/edge `id` | weak (dynamic time, not source) | Fair (XML) | Strong (Gephi-native) [11][12] |
| **DOT** | text | weak (presentation attrs) | **Yes** but presentation-y | none | Yes (parallel edges allowed) | `digraph`/`graph`, `->`/`--` | identifiers, weak typing | none | Good (terse) but **lossy for data** | Ubiquitous for **render** only [3] |
| **RDF Turtle / N-Triples** | text | `rdf:type` / classes | **No** natively (reify or RDF-star) | **Yes** (ontologies/IRIs) | n/a (triple-level) | predicates are directed | **IRIs** (global) | **Excellent** (PROV-O) | Turtle fair; N-Triples poor (1 triple/line, no nesting) | Strong **semantic-web** stack [4][5] |
| **JSON-LD** | JSON | `@type`, `@context` | **No** natively (edges = predicates) | **Excellent** (`@context` → ontology) | n/a | predicate direction | **`@id`** (IRIs) | **Excellent** (PROV-JSONLD) | Fair (context indirection hurts diff) | Growing (web/KG) [13][14] |
| **Neo4j / APOC JSON** | JSON(L) | `labels`, rel `label` | **Yes** (`properties`) | none | Yes (rel ids) | rel `start`/`end` | numeric/internal ids | none | Poor (JSON-Lines, internal ids) | Strong in **Neo4j** [15][16] |

Key reading of the table for creel: **every property-graph JSON format supports
attributes on edges**; the RDF family does *not* without reification or RDF-star.
Only **GraphML/GEXF** ship *declarative typed-attribute schemas*; only the **RDF
family** ships *standard provenance and schema-reference vocabularies*. No single
format gives creel all three of {edge attributes, typed schema, provenance} at
once — which is the core finding driving the recommendation below.

## Deep section A — Attributes on edges: the dividing line

Creel deliberately puts funding amounts, indicator values, etc. **on edges**.
This single requirement eliminates plain RDF as a *canonical* form. In RDF a
relationship is a predicate inside an immutable subject–predicate–object triple;
you cannot attach `amount: 4.2M` to the predicate. The two escape hatches both
hurt:

- **Reification** turns each edge into an `rdf:Statement` node with
  `rdf:subject/predicate/object` triples, then hangs attributes off that node.
  This multiplies triple count and query/diff complexity [4].
- **RDF-star** lets a triple be the subject of another triple
  (`<< :proj :fundedBy :donor >> :amount 4.2e6 .`), elegantly approximating the
  property-graph model [4][5]. But RDF-star is still stabilizing (RDF 1.2 era),
  tooling is uneven, and N-Triples/Turtle remain awkward git-diff targets.

By contrast, the property-graph JSON formats make the edge a first-class object
with its own attribute bag — exactly creel's model. **This is decisive: creel's
canonical form must be property-graph-shaped, and RDF/JSON-LD becomes an
*export target*, not the source of truth.**

## Deep section B — Schema & typed attributes

Creel needs a *grammar*: node/edge-types in recursive taxonomies, each attribute
freeform or constrained (enum, range). Two patterns exist in the wild:

- **Declared-attribute schemas (GraphML/GEXF):** GraphML's `<key id="…"
  attr.name="…" attr.type="double" for="edge">` declares typed columns once and
  references them per element; GEXF's `<attributes>` does likewise and adds
  *dynamic* attributes with time `spells` [1][2][11]. This is close to creel's
  "typed attribute" idea but lives *inline with the data* and lacks enums/ranges.
- **Ontology references (RDF/JSON-LD):** `@context`/IRIs point at external
  ontologies; strongest for shared semantics and reuse, weakest for diffability
  [13][14].

JGF and NetworkX node-link have **no schema layer at all** — types live as
convention inside the `metadata`/attribute bag, validated only by an external
JSON-Schema you supply [6][8]. This matches creel's posture of **physical
separation**: the *graph definition* (taxonomy + typed-attribute grammar) is a
separate artifact, joined to instance data on demand. JSON-Schema (via `$schema`)
is the natural vehicle — it expresses enums (`"enum": [...]`) and ranges
(`minimum`/`maximum`) directly, and is the most diffable, most universally
tooled validation layer for JSON.

## Deep section C — Provenance & auditability

Creel's "auditability over opaqueness" mandate (every element verifiable +
traceable to source) has a ready-made standard: **W3C PROV-O** — `prov:Entity`,
`prov:Activity`, `prov:wasGeneratedBy`, `prov:wasDerivedFrom`, `prov:used` [17].
PROV-JSONLD serializes this cleanly [18]. None of the property-graph JSON formats
have a provenance concept; they'd carry it inside the generic attribute bag.

The pragmatic move: creel models provenance **natively as typed per-element
metadata** (which extractor/strategy produced this element, source span/locator,
confidence, verification status, timestamp), using **PROV-O field *names* as the
controlled vocabulary** (`wasDerivedFrom`, `wasGeneratedBy`) so that the JSON-LD/
PROV export is a mechanical mapping rather than a reinterpretation. This keeps
the canonical form plain JSON (diffable) while making the semantic-web export
faithful.

## Deep section D — Git-diffability (the underrated axis)

Because creel emits *the* single source of truth and prizes auditability, the
canonical file will live in git and be reviewed in diffs. This favors:

- **JSON over XML over triples.** N-Triples is one triple per line (no nesting,
  enormous and order-sensitive); Turtle is better but still not reviewer-friendly
  for instance data. XML (GraphML/GEXF) is verbose. JSON wins.
- **Stable, deterministic ordering.** JGF and node-link put edges in an *array*;
  array reordering produces noisy diffs. Creel should give every node *and edge*
  a **stable string id** and serialize with **sorted keys + sorted element
  arrays by id**, so a one-attribute change is a one-line diff.
- **Avoid presentation noise.** Cytoscape's `position`/`style` and GraphSON's
  per-value type tags bloat diffs; keep them out of canonical, add on export.
- **Avoid indirection.** JSON-LD `@context` resolution and Neo4j internal numeric
  ids make diffs hard to read in isolation — another reason these are exports.

## Design implications for creel

1. **Canonical = property-graph node-link JSON, owned and versioned by creel.**
   Don't adopt JGF/NetworkX verbatim — both lack schema, typing, stable edge ids,
   and provenance. Define creel's own document with an explicit `"version"` field
   *and* a `"$schema"` URL you control. Treat it as a **deliberate superset of
   JGF v2 conventions** (`nodes` as id→object map, `edges` as objects with
   `source`/`target`/`relation`, graph-level `directed`) so JGF/NetworkX export
   is a near-lossless downcast [6][8].
2. **Give every edge a stable `id` and support parallel edges.** JGF doesn't
   require edge ids; creel must, both for multigraph/parallel-edge support and
   for deterministic, low-noise git diffs and stable provenance anchoring.
3. **Physically separate three layers, join on demand** (matches creel's stated
   posture): (a) **graph-definition** = the taxonomy of node/edge-types + typed-
   attribute grammar (enums/ranges) expressed as JSON-Schema; (b) **instance
   graph** = nodes/edges with attribute values; (c) **extraction/verification
   metadata** = per-element strategy + source locator + confidence + status.
   Keep (c) addressable by element `id` so it can be detached (lean export) or
   joined (full audit).
4. **Adopt PROV-O field names for provenance** in the metadata layer
   (`wasDerivedFrom`, `wasGeneratedBy`, `used`) even though the canonical file is
   plain JSON — this makes the JSON-LD/PROV-JSONLD export mechanical and standards-
   aligned [17][18].
5. **Validate with JSON-Schema, version with SchemaVer-style semantics.** Use
   *ADDITION* (backward-compatible) / *REVISION* / *MODEL* (breaking) discipline
   so old graphs keep validating as the grammar grows [19][20]. Enums and ranges
   map directly to JSON-Schema `enum` / `minimum`/`maximum`.
6. **Adapters are strategy objects, not a monolith.** A `to_jgf`, `to_networkx`,
   `to_cytoscape`, `to_graphml`, `to_gexf`, `to_dot`, `to_graphson`, `to_jsonld`,
   `to_neo4j_json` registry — each declaring what it *drops* (e.g. DOT drops typed
   data; RDF/JSON-LD reifies edge attributes or uses RDF-star; Cytoscape adds
   layout). NetworkX should be the **pivot adapter**: once you can round-trip to a
   NetworkX MultiDiGraph, you inherit its writers for GraphML/GEXF/GML for free [8].

## Recommendation

**Define an explicit, versioned, creel-owned canonical JSON — a property-graph
node-link document shaped as a deliberate superset of JGF v2 — and treat every
other format as an export adapter.** Concretely:

```json
{
  "$schema": "https://creel.dev/schema/graph/v1.json",
  "version": "1.0",
  "graph": {
    "directed": true,
    "spec_ref": "esa-strategic-frame@1.2",
    "nodes": {
      "obj:protection": {
        "type": "objective",
        "attributes": { "title": "Protection", "priority": "high" }
      },
      "donor:eu": { "type": "donor", "attributes": { "name": "EU" } }
    },
    "edges": [
      {
        "id": "e:fund:001",
        "source": "donor:eu",
        "target": "obj:protection",
        "relation": "funds",
        "type": "funding",
        "attributes": { "amount_usd": 4200000, "year": 2025 }
      }
    ]
  }
}
```

with the **graph-definition** (taxonomy + typed-attribute grammar as JSON-Schema)
and the **extraction/verification metadata** (keyed by node/edge `id`, using
PROV-O field names) living in *separate* documents joined on demand.

**Rationale.** This is the only option that satisfies all four hard constraints
simultaneously: edge attributes (property-graph shape), typed schema (JSON-Schema
with enums/ranges), provenance (PROV-O-named metadata layer), and git-diffability
(plain JSON, stable ids, sorted serialization). Owning the schema avoids being
boxed in by JGF's gaps (no schema, no edge ids, no provenance) while staying
*one mechanical downcast away* from JGF and NetworkX — and from there, via the
NetworkX pivot, the entire GraphML/GEXF/DOT ecosystem. RDF/JSON-LD and Neo4j
remain first-class **export targets** for downstream graph-DB / graph-RAG /
linked-data consumers, but never the source of truth.

## References

[1] [GraphML — Wikipedia](https://en.wikipedia.org/wiki/GraphML)
[2] [GraphML Format — Gephi Desktop Documentation](https://docs.gephi.org/desktop/User_Manual/Import/GraphML_Format/)
[3] [DOT Language — Graphviz](https://graphviz.org/doc/info/lang.html)
[4] [RDF-star and SPARQL-star — W3C Community Group Report](https://w3c.github.io/rdf-star/cg-spec/2021-04-13.html)
[5] [Property graph vs RDF — PuppyGraph](https://www.puppygraph.com/blog/property-graph-vs-rdf)
[6] [JSON Graph Specification (README) — jsongraph/json-graph-specification](https://github.com/jsongraph/json-graph-specification/blob/master/README.md)
[7] [JSON Graph Format Specification Website](https://jsongraphformat.info/)
[8] [node_link_data / node_link_graph — NetworkX (stable) documentation](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.json_graph.node_link_data.html)
[9] [Cytoscape.js — Notation / JSON format](https://js.cytoscape.org/)
[10] [IO Reference: GraphSON — Apache TinkerPop](https://tinkerpop.apache.org/docs/current/dev/io/)
[11] [GEXF File Format — Gephi Desktop Documentation](https://docs.gephi.org/desktop/User_Manual/Import/GEXF_File_Format/)
[12] [GEXF 1.2draft Primer — GEXF Working Group](http://gexf.net/1.2draft/gexf-12draft-primer.pdf)
[13] [JSON-LD 1.1 — W3C Recommendation](https://www.w3.org/TR/json-ld11/)
[14] [JSON-LD — JSON for Linked Data (Fluree)](https://flur.ee/json-ld/)
[15] [apoc.import.json — APOC Core Documentation, Neo4j](https://neo4j.com/docs/apoc/current/overview/apoc.import/apoc.import.json/)
[16] [apoc.export.json.graph — APOC Core Documentation, Neo4j](https://neo4j.com/docs/apoc/current/overview/apoc.export/apoc.export.json.graph/)
[17] [PROV-O: The PROV Ontology — W3C Recommendation](https://www.w3.org/TR/prov-o/)
[18] [The PROV-JSONLD Serialization — openprovenance.org](https://openprovenance.org/prov-jsonld/2020-03-23/)
[19] [Introducing SchemaVer for semantic versioning of schemas — Snowplow](https://snowplow.io/blog/introducing-schemaver-for-semantic-versioning-of-schemas)
[20] [Introducing versioning in JSON schema validation — KrakenD](https://www.krakend.io/blog/changes-in-json-schema/)
