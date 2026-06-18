# 02 — Graph schema & grammar specification languages

> **TL;DR.** Creel needs two schemas — a *grammar* schema (node/edge taxonomies + typed attributes + constraints) and an *instance* schema (extracted graphs) — and these should be **physically separated** from extraction/verification metadata. Of the surveyed languages, **LinkML is the strongest fit for the grammar layer**: it is a single, human-writable YAML *schema-for-data* that natively expresses classes (node *and* edge types), typed slots, enums/value-sets (static *and* ontology-backed dynamic), numeric ranges, cardinality, and multiple inheritance + mixins — and it **compiles down to JSON Schema, Pydantic v2, SHACL, OWL, SQL DDL, GraphQL and JSON-LD `@context`** [1][2][3]. Crucially, LinkML models **edges as first-class typed classes** via `represents_relationship: true` with `subject`/`predicate`/`object` slots, so funding amounts and indicator values can live *on* edges [4]. The instance layer should be plain **JSON validated by LinkML-generated JSON Schema + Pydantic v2**, with a generated **JSON-LD `@context`** for downstream RDF/graph-DB/graph-RAG interop. Reserve **PG-Schema/Neo4j constraints, SHACL/ShEx, and OWL as *export targets*, not authoring surfaces** — they are downstream consumers of the canonical LinkML grammar, not the source of truth. Keep extraction strategies in a **separate document joined by element ID**, never inline in the grammar.

## Background / landscape

The candidate languages fall into four families, each born of a different community with different priorities. Conflating them is the central design trap.

1. **Data-validation / code-generation schemas** — *JSON Schema* and *Pydantic v2*. These validate tree-shaped JSON/Python objects. They have excellent tooling and runtime validation but no native notion of "graph", "edge", or "taxonomy of types"; you model those by convention.
2. **Schema-for-data modeling frameworks** — *LinkML*. A meta-layer that authors a domain model once and **generates** the validators above (and the semantic ones below). This is the "write once, target many" layer [1][2].
3. **Graph-shape / graph-schema languages** — *SHACL*, *ShEx*, *PG-Schema/PG-Keys*, *Neo4j constraints*. These validate or constrain *graphs* (RDF triples or labeled property graphs) directly. SHACL and ShEx are W3C-community RDF validators; PG-Schema is the academic/ISO-GQL formalism for **labeled property graphs (LPGs)**, the data model creel's output most resembles [5][6][7].
4. **Semantic vocabularies / ontologies** — *OWL*, *RDFS*, *SKOS*, *Dublin Core*, *JSON-LD `@context`*. These describe *meaning* and *taxonomy* for the open world of linked data. OWL is an inference logic; SKOS is the lightweight standard for **controlled vocabularies and taxonomies** (`skos:broader`/`narrower`/`related`) [8][9]; JSON-LD `@context` maps plain-JSON keys to IRIs so a JSON graph becomes RDF on demand [10].

The key conceptual axis for creel is the **open-world vs. closed-world** split. OWL/RDFS reason under the *open-world assumption* (absence of a fact ≠ falsehood; classes describe entailments, not validation gates). JSON Schema, Pydantic, PG-Schema and SHACL operate under a *closed-world, "validate this document"* posture — which is exactly what an extraction engine needs for auditability ("did we extract a valid graph?"). This alone argues against OWL as the authoring surface and for a validation-oriented core [6].

A second axis is **edge-as-property vs. edge-as-object**. Creel explicitly requires edges to carry typed attributes (funding amounts on a *funds* edge; values on an *indicator* edge). RDF/SHACL/OWL treat a predicate as a binary relation with no native attributes — you must *reify* the statement into a node to attach data. LPG models (PG-Schema, Neo4j) and LinkML's relationship-classes give edges first-class status with their own property bags, which maps cleanly onto creel's requirement [4][5][7].

## Comparative analysis

| Language | Node types | Edge types | First-class edge attrs? | Attribute typing | Enums / value-sets | Numeric ranges | Cardinality | Inheritance / subtype | Python support | Round-trip to validation |
|---|---|---|---|---|---|---|---|---|---|---|
| **JSON Schema (2020-12)** | object schema (by convention) | none native | only via nested objects | rich (`type`, `format`) | `enum`, `const` [11] | `minimum`/`maximum`/`exclusive*` [12] | `minItems`/`maxItems`, `required` | `$ref`, `allOf` (no real subtyping) | many validators | *is* the validator |
| **Pydantic v2** | `BaseModel` | none native | only via nested models | Python types + `Annotated` | `Enum`, `Literal` [13] | `Field(ge=, le=, gt=, lt=)`, `conint`/`confloat` [13] | `min_length`/`max_length`, optionality | class inheritance | native (it *is* Python) | *is* the validator + JSON Schema export |
| **LinkML** | `class` | `class` w/ `represents_relationship` [4] | **yes** (slots on the relationship class) | `slot` `range` (types/classes/enums) | `enum` permissible_values + **dynamic `reachable_from`** [3] | `minimum_value`/`maximum_value` on slots | `multivalued`, `required`, `minimum/maximum_cardinality` | `is_a` + `mixins` (multi) [14] | generates Pydantic/dataclasses | **generates** JSON Schema, Pydantic, SHACL, OWL, SQL [1][2] |
| **SHACL** | `NodeShape` | `PropertyShape` (path) | no (reify to node) | `sh:datatype`, `sh:class` | `sh:in` | `sh:minInclusive`/`sh:maxInclusive` | `sh:minCount`/`sh:maxCount` | shape composition, `owl:imports` | `pyshacl` | validation engine |
| **ShEx** | shape | triple constraint | no (reify) | datatype/value sets | value sets | facet constraints | `{m,n}` cardinality | shape refs (limited) | `PyShEx` | validation engine |
| **OWL 2** | `owl:Class` | `owl:ObjectProperty` / `DataProperty` [15] | no (reify / n-ary pattern) | `rdfs:range` (datatype) | `owl:oneOf` | datatype facets | `owl:min/maxCardinality` [15] | `rdfs:subClassOf` (rich) | `owlanguages`/`rdflib` | reasoner (entailment, not validation) |
| **GraphQL SDL** | `type`/`interface` | field references (edges-by-convention) | only via explicit edge `type` | scalars + custom | `enum` | none native | `!` (non-null), lists | `interface`, `union` | `strawberry`/`graphene` | resolver-time, not data validation |
| **PG-Schema / PG-Keys** | PG-Type (node) | PG-Type (edge) [5] | **yes** (edges have label+props) | property types | (value constraints) | constraint expressions | participation constraints, PG-Keys | **multi-inheritance + abstract types** [5] | none mainstream (academic/GQL) | maps to GQL DDL |
| **Neo4j constraints** | node label | relationship type | **yes** (rel properties) | `IS :: TYPE` property-type constraint [16] | (app-enforced) | (app-enforced) | existence + node/rel key | labels (no inheritance) | `neo4j` driver | `CREATE CONSTRAINT` (DB-enforced) |
| **SKOS** | `skos:Concept` | semantic relations | n/a (taxonomy, not data) | n/a | concept schemes *are* value-sets | n/a | n/a | `broader`/`narrower` [8][9] | `rdflib` | not a validator |
| **JSON-LD `@context`** | term→IRI map | term→IRI map | n/a (serialization) | `@type` coercion | n/a | n/a | `@container` | n/a | `pyld` | not a validator (RDF bridge) [10] |

Reading the table for creel: only **LinkML, PG-Schema and Neo4j** treat edges as first-class typed objects with their own attributes, and only **LinkML** simultaneously (a) is human-authorable, (b) carries the full constraint vocabulary creel needs (enums, ranges, cardinality, inheritance), and (c) *generates* the rest of the column. That is the headline result.

## Deep dive: LinkML as the grammar layer

LinkML (now formally described in a Dec 2025 GigaScience paper [2] and a 2025 arXiv overview [1]) is a **schema-for-data** framework authored in YAML. Its metamodel is itself a LinkML schema, giving it clean self-description [2]. Four constructs matter for creel:

- **Classes** model both node-types *and* edge-types. A class is a named, inheritable bundle of slots.
- **Slots** are the typed attributes. A slot has a `range` (a primitive type, another class, or an enum), plus facets: `required`, `multivalued`, `minimum_value`/`maximum_value`, `pattern` (regex), `minimum_cardinality`/`maximum_cardinality`.
- **Enums** are value-sets. Static `permissible_values` cover the "constrained enum" case; each value can carry a `meaning:` CURIE binding it to an ontology term (e.g. a SKOS concept) [3]. **Dynamic enums** via `reachable_from` populate the value-set from an ontology subtree at compile/validation time, with `minus`/boolean composition for include/exclude [3]. For JSON Schema targets (which can't run live queries) dynamic enums **materialize** to static lists [3]. This directly serves creel's "freeform or constrained (enums, ranges)" attribute requirement.
- **Inheritance** is via `is_a` (single parent) plus `mixins` (multiple), enabling the *recursively subdivided taxonomies* of node/edge types creel calls for [14].

**Edges with attributes.** LinkML's `represents_relationship: true` declares a class to be a reified relationship — an ER association, an `rdf:Statement`, or *a property-graph edge connecting nodes* [4]. Such a class carries `subject`/`predicate`/`object` role-slots plus any number of ordinary typed slots. So creel's "funding amount on a *funds* edge" is just a `Funds` class with `subject: Donor`, `object: Project`, and a `funding_amount` slot (range `decimal`, `minimum_value: 0`). This is the single most important capability match in the survey.

**Generation / round-trip.** From one schema LinkML emits: **JSON Schema**, **Pydantic** (v2) classes, **SHACL** and **ShEx**, **OWL/RDF**, **SQL DDL & SQLAlchemy**, **GraphQL**, **JSON-LD `@context`**, ER/PlantUML diagrams, and more [1][2]. This means creel can *author once* and hand SHACL to an RDF consumer, Cypher-shaped DDL intent to a Neo4j consumer, and Pydantic to its own runtime — without a second source of truth. The official positioning is explicitly "a pragmatic middle ground… complements rather than replaces JSON Schema, Pydantic, SHACL" [2].

**Caveats (flagged honestly).** LinkML's edge model is reification-by-convention, not a native LPG primitive, so the *semantics* of an edge are encoded in slot roles, not enforced by a graph engine; cross-edge integrity (PG-Keys-style participation constraints) is weaker than PG-Schema's. And while LinkML *generates* SHACL, the generated SHACL covers structural shapes, not arbitrary SPARQL-target constraints. For creel's core (produce + validate a JSON graph), these are acceptable; they bite only if creel later needs in-database graph-integrity enforcement, which is downstream.

## Deep dive: the graph-shape languages (SHACL / ShEx / PG-Schema)

A Feb 2025 arXiv paper, *Common Foundations for SHACL, ShEx, and PG-Schema* [6], gives the authoritative cross-walk. Its conclusion is nuanced: the three languages do **not** share a pre-existing common foundation — the authors *construct* a uniform framework to compare them, and find "overlapping functionalities alongside distinctive features" reflecting the RDF vs. property-graph split [6]. Practically:

- **SHACL** (W3C Recommendation, 2017) is a *constraint language*: `NodeShape`s target nodes, `PropertyShape`s constrain a path, with `sh:datatype`, `sh:class`, `sh:in`, `sh:minCount`/`maxCount`, `sh:minInclusive`/`maxInclusive`. Single RDF syntax. Produces rich, detailed validation reports [17][18] — valuable for creel's **auditability** posture. Python: `pyshacl`.
- **ShEx** is a *grammar* for RDF (regular-bag-expression semantics), with a friendly compact syntax (ShExC) and a ShapeMap to bind nodes to shapes; its report vocabulary is essentially pass/fail [18]. Less suited to creel's "explain *why* this element failed verification" need than SHACL.
- **PG-Schema** (SIGMOD 2023; LDBC working group feeding ISO GQL) is the formalism that matches creel's *output* data model best: **PG-Types** for nodes and edges with **multi-inheritance and abstract types**, and **PG-Keys** for keys + participation constraints [5][7]. It is the right *mental model* for creel's grammar (typed nodes, typed edges, key/participation constraints), but it has no mainstream Python tooling and is aimed at GQL engines, so it is an export/conceptual target, not an authoring surface.

The takeaway: use **PG-Schema as the conceptual reference** for what creel's grammar must express, **SHACL as a generated export** for RDF consumers who want machine-checkable shapes with good reports, and skip ShEx unless a specific consumer demands it.

## Deep dive: typed attributes, enums, and numeric ranges

Creel's spec says attributes are "freeform or constrained: enums, ranges." Mapping each to the stack:

- **Freeform** → LinkML slot with a primitive `range` (`string`, `integer`, `float`, `date`) → JSON Schema `type` / Pydantic field.
- **Enum (closed value-set)** → LinkML `enum` with `permissible_values` → JSON Schema `enum` [11] / Pydantic `Enum` or `Literal` [13]. Each value optionally `meaning:`-bound to a SKOS/ontology IRI for taxonomy alignment [3][8].
- **Ontology-backed value-set (open/evolving)** → LinkML dynamic `reachable_from`, materialized to static `enum` for JSON Schema validators [3].
- **Numeric range** → LinkML `minimum_value`/`maximum_value` → JSON Schema `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum` [12] / Pydantic `Field(ge=, le=, gt=, lt=)` [13].
- **Pattern / functional constraint** → LinkML `pattern` (regex) → JSON Schema `pattern` / Pydantic. (Arbitrary `source->value` functions belong in the *extraction* layer, not the grammar.)

This is a clean, total mapping with no gaps — every constraint creel names has a first-class LinkML construct that round-trips to both JSON Schema and Pydantic.

## Design implications for creel

1. **Two LinkML schemas, both generated-from one metamodel.** Author the **grammar** as a LinkML schema (node-classes, edge-classes via `represents_relationship`, enums, ranges). Generate the **instance** validators (JSON Schema + Pydantic v2) from it. This satisfies "two schemas" while preserving a single source of truth and giving immediate, auditable runtime validation [1][2][4].
2. **Edges are LinkML relationship-classes, not slots.** Model `Funds`, `Measures`, `Contributes-To` as classes with `subject`/`object`/`predicate` plus typed payload slots (`funding_amount: {range: decimal, minimum_value: 0}`, `indicator_value`). This is the only surveyed approach that is both authorable and edge-first [4][5].
3. **Keep extraction/verification metadata in a *separate* document, joined by element ID.** Do **not** inline regex/SQL/Mongo/NL-prompt strategies into the LinkML grammar. Use LinkML `annotations` *only* as the join key/anchor; store the strategy spec (the StrategyPattern config) in a parallel JSON/YAML keyed by the same `class`/`slot` names. This honors the "physical separation, joined on demand" posture and keeps the grammar reusable across extractors.
4. **Make the canonical output a plain JSON graph + a generated JSON-LD `@context`.** Ship the JSON graph for ergonomics; ship the LinkML-generated `@context` so any consumer can lift it to RDF for graph-DB / knowledge-base / graph-RAG use without creel owning that code [10].
5. **Treat SHACL, PG-Schema/Cypher constraints, and OWL as *export targets*, never authoring surfaces.** Offer "export grammar as SHACL" (good validation reports for auditability [17]) and "export as Cypher `CREATE CONSTRAINT`/GQL DDL" (for the Neo4j/property-graph consumer [16]) as downstream adapters generated from the LinkML grammar — progressive disclosure for advanced users, invisible by default.
6. **Use SKOS semantics for the node/edge *taxonomy* dimension.** The recursively-subdivided type taxonomies are conceptually `skos:broader`/`narrower` trees; bind LinkML enum `meaning:` / class `class_uri:` to SKOS concepts so the taxonomy is portable and the first-consumer results framework (donors→objectives→outcomes→indicators) can be expressed as a concept scheme [8][9].

## Recommendation

**Adopt LinkML as creel's grammar-definition language and single source of truth; generate the instance-validation layer (JSON Schema + Pydantic v2) and all interop artifacts (JSON-LD `@context`, SHACL, GQL/Cypher DDL) from it; and keep extraction/verification strategies in a physically separate, ID-joined document.**

Rationale: creel's requirements — node *and* edge taxonomies, edges-with-attributes, freeform/enum/range typing, inheritance, auditability, and downstream graph-DB/graph-RAG interop — are satisfied *as a set* by exactly one surveyed language. LinkML is the only option that is human-writable, models edges as first-class typed objects (`represents_relationship`), expresses every constraint creel names, and **compiles to JSON Schema, Pydantic, SHACL, OWL, SQL, GraphQL and JSON-LD** so no second source of truth is ever needed [1][2][3][4]. JSON Schema and Pydantic remain in the stack — but as *generated outputs* (the immediate runtime validators), not as the authoring surface. SHACL/ShEx, PG-Schema and Neo4j constraints serve as conceptual reference (PG-Schema) and optional export adapters (SHACL, Cypher); OWL and SKOS provide the semantic/taxonomy bindings. This layering exactly realizes creel's "physical separation of the graph-definition layer from the extraction/verification metadata, joined on demand," with progressive disclosure (schema-as-default) and auditability (every element traceable through a generated, machine-checkable validator) built in.

## References

[1] Moxon S. et al. *LinkML: An Open Data Modeling Framework.* arXiv:2511.16935, 2025. [https://arxiv.org/pdf/2511.16935](https://arxiv.org/pdf/2511.16935)

[2] *LinkML: an open data modeling framework.* GigaScience, vol. 15, Dec 2025. [https://academic.oup.com/gigascience/article/doi/10.1093/gigascience/giaf152/8378082](https://academic.oup.com/gigascience/article/doi/10.1093/gigascience/giaf152/8378082)

[3] *Semantic Enumerations — LinkML documentation.* [https://linkml.io/linkml/schemas/enums.html](https://linkml.io/linkml/schemas/enums.html)

[4] *Slot: represents_relationship — LinkML Model.* [https://linkml.io/linkml-model/latest/docs/represents_relationship/](https://linkml.io/linkml-model/latest/docs/represents_relationship/)

[5] Angles R., Bonifati A., Dumbrava S., et al. *PG-Schema: Schemas for Property Graphs.* Proc. ACM Manag. Data (SIGMOD), 2023. arXiv:2211.10962. [https://arxiv.org/abs/2211.10962](https://arxiv.org/abs/2211.10962)

[6] Ahmetaj S. et al. *Common Foundations for SHACL, ShEx, and PG-Schema.* arXiv:2502.01295, 2025. [https://arxiv.org/abs/2502.01295](https://arxiv.org/abs/2502.01295)

[7] Angles R. et al. *PG-Keys: Keys for Property Graphs.* (LDBC Property Graph Schema Working Group). [https://www.semanticscholar.org/paper/PG-Keys:-Keys-for-Property-Graphs-Angles-Bonifati/a2e52a7e9c0862d2d841e5a788f1e975e736d7c5](https://www.semanticscholar.org/paper/PG-Keys:-Keys-for-Property-Graphs-Angles-Bonifati/a2e52a7e9c0862d2d841e5a788f1e975e736d7c5)

[8] *SKOS Simple Knowledge Organization System Reference (W3C Recommendation).* [https://www.w3.org/TR/skos-reference/](https://www.w3.org/TR/skos-reference/)

[9] *SKOS — ISKO Encyclopedia of Knowledge Organization.* [https://www.isko.org/cyclo/skos.htm](https://www.isko.org/cyclo/skos.htm)

[10] *JSON-LD 1.1 (W3C Recommendation).* [https://www.w3.org/TR/json-ld11/](https://www.w3.org/TR/json-ld11/)

[11] *enum (2020-12) — Learn JSON Schema.* [https://www.learnjsonschema.com/2020-12/validation/enum/](https://www.learnjsonschema.com/2020-12/validation/enum/)

[12] *JSON Schema — Numeric types (minimum/maximum).* [https://json-schema.org/understanding-json-schema/reference/numeric](https://json-schema.org/understanding-json-schema/reference/numeric)

[13] *Standard Library Types & Fields — Pydantic Docs.* [https://docs.pydantic.dev/latest/api/standard_library_types/](https://docs.pydantic.dev/latest/api/standard_library_types/)

[14] *LinkML FAQ: Modeling (is_a, mixins, relationships).* [https://linkml.io/linkml/faq/modeling.html](https://linkml.io/linkml/faq/modeling.html)

[15] *OWL 2 Web Ontology Language Structural Specification (W3C).* [https://www.w3.org/TR/owl2-syntax/](https://www.w3.org/TR/owl2-syntax/)

[16] *Create constraints — Neo4j Cypher Manual.* [https://neo4j.com/docs/cypher-manual/current/constraints/examples/](https://neo4j.com/docs/cypher-manual/current/constraints/examples/)

[17] *SHACL Generator — LinkML documentation.* [https://linkml.io/linkml/generators/shacl.html](https://linkml.io/linkml/generators/shacl.html)

[18] *SHACL–ShEx Comparison — W3C RDF Data Shapes Working Group.* [https://www.w3.org/2014/data-shapes/wiki/SHACL-ShEx-Comparison](https://www.w3.org/2014/data-shapes/wiki/SHACL-ShEx-Comparison)
