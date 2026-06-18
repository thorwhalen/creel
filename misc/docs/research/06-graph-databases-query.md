# 06 — Graph databases & query languages

> **TL;DR.** Creel's canonical output is a *typed property graph with first-class, attribute-bearing edges*. The graph-DB ecosystem now has, for the first time, an ISO standard for exactly this model — **GQL (ISO/IEC 39075:2024)** [1][2] — descended from Cypher, and a de-facto interchange spec — the **Property Graph Exchange Format (PG / PG-JSON)** [3] — whose data model (nodes *and* edges with multiple labels and list-valued properties) is a near-exact match for creel's needs. Creel should therefore (a) keep its **internal IR vendor-neutral and PG-JSON-shaped**, with thin emitters to Cypher/openCypher (Neo4j, Memgraph, embedded engines), Gremlin/GraphSON (TinkerPop), and RDF-star/SPARQL (Oxigraph) — *never* coupling the core to any one engine; and (b) for the query-based **extractor strategy**, adopt a **small, declarative, sandboxed query-spec** dispatched per source-type — SQL (via DuckDB) for tables, a MongoDB-style filter document plus **JMESPath** for JSON — rather than letting extractors emit raw engine strings. The single most consequential fact this quarter: **Kùzu, the leading embedded property-graph engine, was abandoned by its sponsor in October 2025** [4][5]; do not build a hard dependency on it.

## Background / landscape

There are two largely separate worlds of "graph data," and creel sits astride both.

**Labeled Property Graphs (LPG).** Nodes and edges each carry one or more *labels* (types) and a set of *properties* (typed key/value attributes). Crucially, **edges are first-class** and carry their own properties — funding amounts, indicator values, weights. This is creel's native model: the first-consumer use case puts indicator values and funding amounts *on edges* between objectives, projects, outputs and outcomes. The LPG world's languages are **Cypher** (Neo4j, openCypher), **Gremlin** (Apache TinkerPop), **GSQL** (TigerGraph), **PGQL** (Oracle), and now the unifying ISO standard **GQL** [1][2][6].

**RDF / triple stores.** Data is a set of `(subject, predicate, object)` triples; the W3C query language is **SPARQL**. Vanilla RDF cannot natively attach attributes to an edge (a predicate); you must *reify* the statement. **RDF-star / SPARQL-star** (heading toward RDF 1.2 / SPARQL 1.2) fixes this by letting a triple be the subject/object of another triple, emulating edge properties [7][8]. RDF buys you global IRIs, formal semantics, and reasoning (OWL/SHACL) — valuable if creel graphs ever feed a shared knowledge base — at the cost of a clumsier fit for attribute-on-edge modeling.

The watershed event is **GQL, published 12 April 2024** — the first new ISO database-language standard since SQL in 1987, produced by the same committee (ISO/IEC JTC 1/SC 32/WG3) [1][2]. GQL standardizes the LPG model and a Cypher-descended syntax (it draws on Cypher/openCypher, PGQL and GSQL), and is paired with **SQL/PGQ**, a read-only graph-pattern extension to SQL SELECT [1][6]. Practically, GQL legitimizes "property graph with typed, attributed edges" as the *standard* target — exactly creel's output — and gives creel a stable conceptual vocabulary independent of any vendor.

## Comparative analysis

### Graph databases as downstream persistence targets

| Engine | Model | Query language | Edge attributes | Schema / constraints | Deploy | Python client | License (core) |
|---|---|---|---|---|---|---|---|
| **Neo4j** | LPG | Cypher (→GQL) | Yes (native) | Schema-optional; uniqueness, node-key, existence, type constraints [9] | Server (Bolt) | `neo4j` (official, Bolt) | GPLv3 (Community) / commercial |
| **Memgraph** | LPG (Neo4j-compatible) | Cypher/openCypher | Yes | Indexes, constraints; Neo4j-compatible | Server (Bolt), in-mem first | `neo4j`/`gqlalchemy` | BSL → Apache-2.0 after delay [10] |
| **TigerGraph** | LPG | GSQL (→GQL) | Yes | Strongly-typed, **schema-first** | Server, MPP | `pyTigerGraph` | Commercial / free cloud tier |
| **Kùzu** *(abandoned)* | LPG | Cypher (GQL-inspired) | Yes | **Schema-required**, strongly typed | **Embedded (in-process)** | `kuzu` (pip) | MIT — **sponsor abandoned Oct 2025** [4][5] |
| **TinkerPop/Gremlin** | LPG | Gremlin (traversal) | Yes | Engine-dependent (often schema-less) | Library + many backends | `gremlinpython` | Apache-2.0 |
| **Oxigraph** | RDF (+RDF-star) | SPARQL 1.1 | via RDF-star/reification | RDF/SHACL (external) | **Embedded** + server | `pyoxigraph`, `oxrdflib` | MIT/Apache-2.0 [11] |
| **Apache Jena (TDB2)** | RDF | SPARQL | via reification/RDF-star | SHACL, OWL reasoning | JVM library/Fuseki server | via HTTP/`SPARQLWrapper` | Apache-2.0 |
| **GraphDB (Ontotext)** | RDF (+RDF-star) | SPARQL-star | Yes (RDF-star) | OWL/SHACL reasoning | Server | HTTP/`SPARQLWrapper` | Commercial / free tier |
| **Blazegraph** | RDF | SPARQL | reification | — | Server | HTTP | GPLv2 — *effectively dormant*; basis of AWS Neptune [12] |

Notes that survived a second-source check: **Kùzu's MIT license means the code lives on** — Kineviz forked it as *bighorn*, and *LadybugDB* is an object-storage-oriented successor — but the original project is archived and unsupported [4][5]. **Blazegraph** is essentially unmaintained; its lineage continues commercially inside Amazon Neptune [12]. **Memgraph** is source-available under BSL (not OSI-open) until its time-delayed Apache-2.0 conversion, so "open source" needs an asterisk for production [10].

### Interchange / bulk-import formats

| Format | Shape | Edge props | Multi-label | Notes |
|---|---|---|---|---|
| **PG-JSON / PG-JSONL** [3] | JSON object `{nodes,edges}` / NDJSON stream | Yes | Yes | ISO-adjacent community spec v1.0 (2024); list-valued props; converters to Neo4j/Neptune/PGX via `pgraphs` |
| **Neo4j `LOAD CSV` / `neo4j-admin import`** | separate node/edge CSVs | Yes | Yes | Fastest bulk path; pair with uniqueness/node-key constraints for idempotency [9][13] |
| **GraphSON** (TinkerPop 2.x/3.x) | JSON | Yes | single label | Native to Gremlin ecosystem |
| **RDF (Turtle/N-Quads/JSON-LD)** | triples/quads | via RDF-star | n/a | For the RDF target; Oxigraph reads all of these [11] |

The standout is **PG-JSON**: its data model is explicitly "nodes and edges, each with multiple unique *labels* and properties mapping keys to *non-empty lists of values*, edge identifiers optional" [3] — which lines up almost one-to-one with creel's taxonomized node/edge *types* and *typed attributes*. A companion converter (`pgraphs`) targets Neo4j, Oracle PGX and Neptune [3].

### Query languages over STRUCTURED sources (for the extractor strategy)

| Language | Domain | Spec status | Python | Power | Safety posture |
|---|---|---|---|---|---|
| **SQL** (via **DuckDB**) | tables / DataFrames / CSV / Parquet | ISO; DuckDB in-process | `duckdb` (zero-config, queries pandas/Arrow directly) [14] | High (joins, windows, CTEs) | Parameterize; restrict to read-only |
| **Mongo-style query documents** | JSON / lists-of-JSON | de-facto (MongoDB) | `mongoquery`, `jsonschema`-adjacent | Medium (filter/match, operators) | Pure-data → inherently sandboxable |
| **JMESPath** | JSON | **complete formal grammar + compliance tests** [15] | `jmespath` | Medium (project/filter/transform) | Pure, side-effect-free |
| **JSONPath** | JSON | RFC 9535 (2024); historically divergent dialects | `jsonpath-ng` | Low–medium (select/filter) | Pure |

For JSON, the literature is consistent: **JMESPath has a precise specification and a cross-language compliance suite**, so semantics are identical across implementations, whereas classic **JSONPath** suffered dialect drift (now partly cured by RFC 9535) [15]. JMESPath is the recommended default for declarative JSON extraction in Python.

## Deep dive 1 — GQL, Cypher, and the case for a Cypher-shaped IR

GQL inherits Cypher's `MATCH (a)-[r:TYPE {p:1}]->(b)` pattern syntax but renames a few constructs: **`INSERT`** replaces Cypher's `CREATE` for adding nodes/edges, and **`FOR`** replaces `UNWIND` [1][2]. GQL adds a real type system and *graph types* (schema), formal semantics, and cross-vendor portability; it deliberately omits procedural branching/looping [6]. SQL/PGQ lets the same pattern syntax run inside a relational `SELECT`, which matters because many of creel's *sources* are tables.

The strategic implication: creel's emitters should target **the Cypher/GQL pattern family as the primary downstream**, because (a) it's now an ISO standard, (b) Neo4j, Memgraph and the embedded engines all speak it, and (c) it natively expresses attributed edges. But creel must **not generate Cypher strings as its internal representation** — that couples the core to one dialect and invites Cypher injection. Generate Cypher *at the edge*, from a structured IR, using **parameters** for all values (the universal anti-injection guidance for Cypher/openCypher) [16][17]. Parameters can't stand in for labels or property *keys* [16], so type/label names must come from creel's validated `graph_spec`, never from raw source text.

## Deep dive 2 — RDF as a secondary target

If creel graphs ever need to merge into a shared knowledge base or support OWL/SHACL reasoning (plausible for multi-agency results data), an RDF emitter is worth having. The clean modern path is **RDF-star**: represent each creel edge as a triple, then attach edge attributes as triples *about that triple* (`<< :proj :funds :objA >> :amount 5000000`) [7][8]. **Oxigraph** is the most attractive RDF target for an embeddable, Python-first stack: a Rust core with `pyoxigraph` offering in-memory and on-disk SPARQL-1.1 stores, plus `oxrdflib` as a drop-in fast backend for the ubiquitous `rdflib` [11]. **Apache Jena** and **GraphDB** are heavier (JVM / commercial) but bring mature reasoning. Treat RDF as *one strategy implementation behind the same emitter interface*, not as the core model — the LPG↔RDF mapping is lossy and best deferred until a concrete reasoning requirement appears.

## Deep dive 3 — the query-based extractor strategy

Creel's extractor strategies include "query forms over structured sources (SQL-like for tables, Mongo-like for JSON)." The danger is letting an extractor carry an arbitrary engine string (a `SELECT … FROM duckdb` or `db.collection.find(...)`) — that's an injection surface and couples extraction to a runtime. Instead, define a **small, closed, declarative query-spec** per source-type, validated against a schema before execution:

- **Tables → SQL via DuckDB.** DuckDB runs in-process, queries pandas/Arrow/CSV/Parquet directly with zero setup, and returns Arrow/pandas [14]. Either accept a *parameterized* SQL template (values bound, never concatenated) or a higher-level structured filter that creel compiles to parameterized SQL. Run read-only.
- **JSON / lists-of-JSON → Mongo-style filter + JMESPath.** A **Mongo-style query document** (`{"status": {"$in": [...]}, "amount": {"$gte": 1000}}`) is pure data — trivially serializable, auditable, and sandboxable — for *selecting* records; **JMESPath** then *projects/transforms* the matched value into the target attribute [15]. Both are side-effect-free, which aligns with creel's auditability posture.
- **Pattern / functional → regex or `source -> value`.** Already in scope; keep these as the escape hatch.

Every query-spec is **data, not code**: it serializes into the same JSON graph spec alongside the element it extracts, so each extracted value is *traceable to its source and reproducible* — directly serving creel's "auditability over opaqueness" principle.

## Design implications for creel

1. **Make PG-JSON the shape of the internal IR.** Adopt the PG data model — nodes and edges each with *multiple labels* (creel's taxonomy paths) and *typed, possibly list-valued properties*, edges first-class with their own attributes [3]. It maps cleanly to creel's `graph_spec` and already has converters to Neo4j/Neptune/PGX, so the core never imports a DB driver.
2. **Emitters behind a strategy interface, one per target dialect.** `to_cypher` (Neo4j/Memgraph/GQL), `to_gremlin`/`to_graphson` (TinkerPop), `to_rdf_star` (Oxigraph), `to_neo4j_csv` (bulk). The core depends on none of them; each is an optional extra. This is the persistence layer kept "enabled, not implemented in core."
3. **Generate queries, never store them; parameterize everything.** Cypher/SQL are produced at emit time from the structured IR with bound parameters; labels and property keys come only from the validated `graph_spec`, closing the injection hole [16][17].
4. **Keep the "graph definition" and "extraction metadata" layers physically separate, join on demand** — which the query-spec design reinforces: extractor query-specs are data attached to spec elements, not embedded engine code.
5. **Treat embedded LPG engines as pluggable, not foundational.** Kùzu was the obvious in-process default but is now abandoned [4][5]. If an embedded store is needed, keep it behind the emitter interface so a switch to bighorn/LadybugDB, Memgraph, or DuckDB-PGQ is a one-file change.
6. **Default the extractor query-spec to pure-data forms** (Mongo-style filters + JMESPath for JSON; structured filters compiled to parameterized SQL for tables), with raw-SQL/regex as opt-in advanced escape hatches — classic progressive disclosure.

## Recommendation

**Anchor creel's canonical output to the PG-JSON property-graph model (vendor-neutral IR), and ship downstream persistence as a set of pluggable emitters behind a single strategy interface — with Cypher/GQL as the primary target and RDF-star/Oxigraph as the optional semantic-web target. For the query-based extractor, do not let extractors carry engine strings: define a small, closed, declarative query-spec per source-type — parameterized SQL (compiled, run read-only via DuckDB) for tables, and a Mongo-style filter document plus JMESPath for JSON — validated against a schema and serialized as data alongside each extracted element.** Rationale: PG-JSON's model is an almost exact structural match for creel's typed-attributed-edge graph and is now backed by an ISO-standard data model (GQL) [1][3]; the emitter pattern keeps the core driver-free and future-proof against ecosystem churn (vividly demonstrated by the Kùzu abandonment [4][5]); and a pure-data query-spec makes every extraction auditable, reproducible, and injection-safe [15][16] — the core values creel is built around.

## References

[1] [Graph Query Language — Wikipedia](https://en.wikipedia.org/wiki/Graph_Query_Language) (ISO/IEC 39075:2024; published 12 Apr 2024; SC32/WG3; INSERT/FOR vs Cypher; SQL/PGQ).

[2] [Creating the GQL Database Language Standard — Neo4j](https://neo4j.com/blog/cypher-and-gql/gql-database-language-standard/) (GQL fuses openCypher, GSQL, PGQL with SQL; first ISO query-language standard since SQL 1987).

[3] [Property Graph Exchange Format (PG) specification v1.0.0 (2024), DOI 10.5281/zenodo.13859531](https://pg-format.github.io/specification/) and [pg-format/pgraphs converter](https://github.com/pg-format/pgraphs) (PG-JSON/PG-JSONL; multi-label, list-valued props, first-class edges; Neo4j/Neptune/PGX conversion).

[4] [KuzuDB graph database abandoned, community mulls options — The Register, 14 Oct 2025](https://www.theregister.com/2025/10/14/kuzudb_abandoned/) (Kùzu Inc abandons project; archived; MIT license).

[5] [KuzuDB and LadybugDB — Mass Programming Resistance, Nov 2025](https://mpr.crossjam.net/wp/mpr/2025/11/kuzudb-and-ladybugdb/) (Kineviz "bighorn" fork; LadybugDB object-storage successor).

[6] [GQL: A New ISO Standard for Querying Graph Databases — The New Stack](https://thenewstack.io/gql-a-new-iso-standard-for-querying-graph-databases/) (GQL semantics, typed graphs, relation to SQL/PGQ).

[7] [What Is RDF-star — Ontotext Fundamentals](https://www.ontotext.com/knowledgehub/fundamentals/what-is-rdf-star/) (embedded triples `<< >>` emulate edge properties; reification).

[8] [RDF-star and SPARQL-star — GraphDB 11.2 documentation](https://graphdb.ontotext.com/documentation/11.2/rdf-sparql-star.html) (edge properties bridging RDF and property graphs; RDF 1.2 / SPARQL 1.2 status).

[9] [System Properties Comparison: Memgraph vs Neo4j vs TigerGraph — DB-Engines](https://db-engines.com/en/system/Memgraph%3BNeo4j%3BTigerGraph) (data models, schema/constraint and workload comparison).

[10] [Memgraph vs Neo4j — PuppyGraph](https://www.puppygraph.com/blog/memgraph-vs-neo4j) (Memgraph BSL→Apache-2.0; Neo4j-compatible Cypher; OLTP vs analytics).

[11] [pyoxigraph — PyPI](https://pypi.org/project/pyoxigraph/) and [oxigraph/oxigraph — GitHub](https://github.com/oxigraph/oxigraph) and [oxrdflib](https://github.com/oxigraph/oxrdflib) (embedded in-memory + on-disk SPARQL 1.1; rdflib drop-in; Turtle/TriG/N-Quads/JSON-LD I/O; MIT/Apache-2.0).

[12] [Apache Jena-TDB vs Blazegraph vs GraphDB vs Neo4j — DB-Engines](https://db-engines.com/en/system/Apache+Jena+-+TDB%3BBlazegraph%3BGraphDB%3BMariaDB%3BNeo4j) (Blazegraph → AWS Neptune lineage; RDF store characteristics).

[13] [Using LOAD CSV for Import — Neo4j GraphAcademy](https://neo4j.com/graphacademy/training-importing-data-40/02-import-40-using-load-csv-import/) (CSV bulk import; uniqueness constraints for idempotent loads).

[14] [DuckDB — An in-process SQL OLAP database](https://duckdb.org/) and [DuckDB Python Quickstart — MotherDuck](https://motherduck.com/learn/duckdb-python-quickstart-part1/) (zero-config in-process SQL over pandas/Arrow/CSV/Parquet).

[15] [JMESPath in Python: A Practical Guide](https://iproyal.com/blog/jmespath-python/) and [JSONata, JSONPath, and JMESPath — comparison](https://medium.com/@khileshsahu2007/jsonata-jsonpath-and-jmespath-exploring-capabilities-and-limitations-bf491348022d) (JMESPath complete spec + compliance tests vs JSONPath dialect drift).

[16] [Parameters — Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/syntax/parameters/) (parameterized queries; parameters cannot be labels or property keys; plan caching).

[17] [Examples of openCypher parameterized queries — Amazon Neptune](https://docs.aws.amazon.com/neptune/latest/userguide/opencypher-parameterized-queries.html) (parameterization as the injection defense for openCypher).
