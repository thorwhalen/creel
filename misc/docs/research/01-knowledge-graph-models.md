# 01 — Models for representing knowledge as graphs

> **TL;DR.** For a system like creel — which must extract a *typed* graph whose **nodes and edges both carry typed attributes**, organized in **recursively-subdivided subtype taxonomies**, from heterogeneous documents — the **Labeled Property Graph (LPG)** is the natural *internal* model: edges are first-class and carry properties natively, which is exactly where creel puts funding amounts and indicator values. The RDF triple model is *interoperability-superior* (global IRIs, standard schema/ontology layers, reasoning) but represents edge attributes only indirectly, via reification / n-ary intermediate nodes / RDF-star. The good news, well-established in the literature, is that **RDF-star ↔ LPG transformations are provably lossless** [6][9][12], and **PG-Schema** [7][8] now gives LPGs a real typing-and-inheritance layer comparable to RDFS/OWL subclassing. The recommendation: adopt an **LPG-with-typed-attributes core** (first-class edges, typed properties, an explicit subtype taxonomy on both node-types and edge-types) designed from day one to round-trip losslessly to **RDF-star** and to **JSON**, borrowing PG-Schema's type/constraint vocabulary and SKOS for the taxonomy spine.

## Background / landscape

A "knowledge graph" can be built on several distinct data models, and the choice constrains *what is cheap to say* and *what requires a workaround*. The four families that matter for creel are:

1. **RDF triple model** (W3C). All knowledge is atomic `subject–predicate–object` (S-P-O) triples; nodes and predicates are global IRIs; meaning is layered on via **RDFS** (classes, subclasses, domains/ranges), **OWL** (logic-based ontologies, reasoning), and **SKOS** (lightweight taxonomies/thesauri). RDF optimizes for *interoperability and semantic reasoning* [1][3].
2. **Labeled Property Graph (LPG)** (Neo4j-style; now standardized by **ISO/IEC 39075 GQL**, 2024 [5]). A graph of nodes and **directed, typed, first-class relationships**, where *both* nodes and relationships carry arbitrary key–value **properties** [1][3]. LPG optimizes for *real-time performance, modeling simplicity, and analytics* [1].
3. **Hypergraphs / n-ary models.** Edges (hyperedges) connect an arbitrary number of nodes, representing n-ary facts directly rather than decomposing them into binary relations [10]. Useful when a single "fact" inherently involves >2 participants.
4. **Typed/attributed graphs + graph-grammar theory** (formal CS). A *type graph* plus an *attribution* mechanism gives a rigorous, category-theoretic foundation for what a "typed attributed graph" *is* and how rule-based transformations on it behave [13][14]. This is the formal backbone under creel's "grammar of node-types and edge-types."

The central tension for creel is **attributes-on-edges**. Creel deliberately puts funding amounts (donor→project) and indicator values (output→outcome) *on the edge*. This is native in LPG, awkward in classic RDF, and first-class in hypergraph/n-ary thinking. Everything below is organized around that axis.

## Comparative analysis

### Core models at a glance

| Dimension | RDF (triples) | RDF-star / RDF 1.2 | LPG (GQL/Neo4j) | Hypergraph / n-ary | Typed attributed graph (theory) |
|---|---|---|---|---|---|
| Atomic unit | S-P-O triple | Triple + *triple terms* (triples as terms) [2] | Node / first-class edge | Hyperedge over N nodes | Typed node/edge over a *type graph* [13] |
| Node identity | Global IRI | Global IRI | Local node id | Local node id | Node mapped to type-node |
| **Edge attributes** | **Indirect** (reify / n-ary node) | **Native-ish** via triple terms / `<< >>` [2][4] | **Native** key–value on edge [1][3] | Native on hyperedge | Native (attributed edges) [13] |
| Edge identity (distinct parallel edges) | Hard ("can't identify unique relationships of same type" [3]) | Improved via triple terms | Native (each edge has id) | Native | Native |
| Subtype hierarchy | `rdfs:subClassOf`, `rdfs:subPropertyOf`; OWL | Same as RDF | PG-Schema inheritance (incl. multi-inheritance) [7][8] | Varies | `subClassOf`/inheritance in type graph [14] |
| Schema/typing layer | RDFS/OWL/SHACL | RDFS/OWL/SHACL | PG-Schema [7][8]; GQL DDL (limited in v1) [5][7] | Ad hoc | Type graph + constraints [13] |
| Standard query | SPARQL | SPARQL-star | Cypher / **GQL (ISO 2024)** [5] | system-specific | — |
| Optimized for | Interoperability, reasoning [1] | Above + edge metadata | Performance, simplicity, analytics [1] | n-ary fidelity, retrieval [10] | Formal correctness/confluence [13] |
| Termination guarantee on query | SPARQL not guaranteed to terminate [3] | same | Cypher/GQL: time ∝ graph size [3] | — | — |

### How each expresses node types, edge types, edge attributes, subtypes

**RDF + RDFS/OWL.** Node *types* are `rdf:type` assertions to classes; *edge types* are predicates (IRIs); *subtype hierarchies* use `rdfs:subClassOf` (node taxonomies) and `rdfs:subPropertyOf` (edge taxonomies), with OWL adding logical axioms. **Edge attributes are the weak point**: a plain predicate is a bare binary link with nowhere to hang a value. RDF "must introduce more triples, with new nodes, to model the properties of each relationship … analogous to using join tables in a relational database" [3]. There are four ways out:

- **Standard RDF reification** (`rdf:Statement`/`rdf:subject`/`rdf:predicate`/`rdf:object`): 4 extra triples per fact; widely judged verbose and "not widely used, understood or implemented" [11][2-status]. *Not* recommended for n-ary relations because it is designed to talk *about a statement*, not to characterize the relation instance itself [12].
- **N-ary intermediate node** (W3C Working Group Note): introduce a node representing the *relation instance* and hang all participants + attributes off it (e.g., a `Diagnosis` node carrying probability HIGH/MEDIUM/LOW; a purchase carrying purpose + amount) [12]. This is the canonical, recommended RDF pattern for attributed relations.
- **RDF-star / RDF 1.2 triple terms.** A triple may be used as a term inside another triple; `<<:a :p :b>> :startDate "2020-02-11"` annotates the *edge* directly [4][2]. RDF 1.2 formalizes this as **reification over triple terms**: "a reifying triple is a triple where the predicate is `rdf:reifies` and the object is a triple term" [2]. Crucially, an embedded triple term is **not automatically asserted** — enabling statements about unasserted statements (beliefs, provenance) [2]. RDF-star/SPARQL-star are the most widely supported extensions and are folded into RDF 1.2 [4].
- **Singleton property pattern.** Mint a unique sub-property IRI per edge so attributes attach to it; has adherents but is not OWL-DL-compatible and is criticized as fragile [9-blog].

**LPG (GQL / Neo4j).** Node types are **labels**; edge types are **relationship types**; **both nodes and edges carry properties natively** — "relationships always have a direction, a type, a start node, and an end node, and they can have properties, just like nodes" [3]. Each edge has its own identity, so *parallel edges of the same type* (two different fundings between the same donor and project) are trivially distinguishable — something RDF struggles with [3]. Historically LPG lacked a schema/subtyping story; that gap is now filled by **PG-Schema** [7][8], which adds flexible type definitions, **multi-inheritance**, and constraints/keys (PG-Keys). The first GQL standard (ISO/IEC 39075:2024) has only limited schema/DDL support, with a richer DDL expected in v2 [5][7].

**Hypergraphs / n-ary.** A hyperedge represents an n-ary fact in one object, "preserving multi-entity co-occurrence contexts" and avoiding the information loss of binary decomposition [10]. Attributes live on the hyperedge. Subtyping is not standardized. Hypergraphs are conceptually attractive for genuinely n-ary facts (e.g., an *indicator reading* = (output, outcome, indicator, value, period, source)) but lack the mature standards, query languages, and tooling of LPG/RDF; in practice most KG systems emulate them with intermediate/event nodes [10][12].

**Typed attributed graphs (graph-grammar theory).** Formally, a typed attributed graph is a graph **typed over a type graph** (the schema) plus an **attribution** of nodes/edges with values from a data algebra; the category of such graphs is an *adhesive HLR category*, which yields strong results (Local Church-Rosser, parallelism, confluence / Critical Pair Lemma) for *rule-based transformation* [13]. Type-graph **inheritance** lets subtypes specialize supertypes [14]. This is exactly the abstraction creel's "graph_spec grammar" instantiates: node-types and edge-types are the type graph; typed attributes are the attribution; recursively-subdivided taxonomies are inheritance edges in the type graph.

### Ontologies vs schemas vs taxonomies (OWL / RDFS / SKOS / PG-Schema)

These are different *layers*, not competitors:

| Artifact | Standard | Role | Subtype mechanism |
|---|---|---|---|
| **Taxonomy / thesaurus** | **SKOS** | Lightweight controlled vocabulary; concepts in a `ConceptScheme` | `skos:broader`/`skos:narrower` (hierarchical), `skos:related` (associative); `skos:broaderTransitive` for query expansion [15] |
| **Schema** | RDFS / SHACL / PG-Schema | Classes, properties, domain/range, constraints/keys | `rdfs:subClassOf`/`subPropertyOf`; PG-Schema inheritance + keys [7][8][15] |
| **Ontology** | OWL | Logic-based model with reasoning, consistency checking | `owl:subClassOf` + axioms (disjointness, cardinality, equivalence) |

A taxonomy is an "is-a" tree; an ontology adds properties, constraints, and reasoning; a **knowledge graph = ontology/schema + the actual instances** [15]. SKOS is deliberately *less rigorous* — `broader`/`narrower` instead of strict `subClassOf` — which makes it ideal for the **navigational taxonomy spine** of node/edge subtypes that humans curate, while a stricter schema (PG-Schema / RDFS) governs **validation**. SKOS and OWL are routinely combined [15].

## Deep section: the "attributes-on-edges" decision for creel

Creel's hardest modeling requirement is that **values live on edges**: `(:Donor)-[:FUNDS {amount, currency, period}]->(:Project)`, `(:Output)-[:MEASURED_BY {value, unit, baseline, target}]->(:Indicator)`. The model families rank as follows for this requirement:

1. **LPG — first-class.** Zero ceremony, plus distinct edge identity for parallel fundings, plus GQL/Cypher queries that terminate in time proportional to graph size [3]. Direct, auditable, and fast.
2. **RDF-star / RDF 1.2 — first-class-ish.** `<<...>>` lets you annotate the edge directly, and the lossless RDF-star→LPG mapping means the two are *information-equivalent* [4][6][9]. The subtlety: an annotated edge is reified — semantics differ from a plain asserted triple, and a triple term is not auto-asserted [2].
3. **Hypergraph / n-ary intermediate node — explicit but heavier.** Promote the *funding* or *reading* to its own node carrying the attributes [12]. This is what RDF *forces*; it is more verbose but maximally explicit and is the most faithful model when a "fact" is genuinely >2-ary (an indicator reading with value + period + source is arguably 4-ary). Creel can treat this as a **normalization choice**: an attributed edge and a reified relation-node are two renderings of the same fact.
4. **Classic RDF reification — avoid.** Verbose, poorly supported, semantically aimed at "statements about statements" rather than relation attributes [12][11].

### Lossless round-tripping is real (the key enabler)

The literature establishes concrete, *reversible* mappings:

- Hartig's **RDF-star ↔ property-graph** transformation is **lossless**: the resulting property graph "contains all information present in the original RDF* data" [6][9]. (Conversely, RDF-star→*simple* property graphs can be lossy — so design matters [9].)
- **PREC / PREC-0**: the property-graph→RDF description is **reversible** — nodes, edges, labels, and properties are all reconstructable; "no information is lost" because a blank node identifies every element [9].
- The **"DAG bridge"** work models RDF, RDF-star, and property graphs uniformly as directed (acyclic) graphs, giving a common substrate for translation [6].

This means creel can **pick LPG as the internal SSOT and still guarantee a faithful RDF-star export** (and back) — satisfying both the "property-graph-friendly" and "losslessly mappable to RDF" goals without compromise.

## Design implications for creel

- **Make the internal model an LPG with typed attributes, edges as first-class typed objects.** This matches creel's requirement that funding amounts and indicator values live *on edges*, gives every edge an identity (parallel fundings distinguishable), and keeps queries fast and terminating [1][3][5].
- **Separate the two layers physically, as already planned — and map them to graph-grammar concepts.** Creel's "graph definition layer" = the **type graph** (node-types, edge-types, their attribute schemas, and the subtype taxonomy); the "extraction/verification metadata" = annotations *over* that type graph. Typed-attributed-graph theory [13][14] is the formal justification for this split and for treating extraction as rule-based transformation into a typed target.
- **Express subtype taxonomies with two cooperating mechanisms.** Use a **SKOS-style spine** (`broader`/`narrower`) for the human-navigable, recursively-subdivided taxonomy of node/edge subtypes (donors→bilateral/multilateral; objectives→…), and a **PG-Schema/RDFS-style `subClassOf` with multi-inheritance + keys/constraints** [7][8][15] for validation. SKOS for browsing, PG-Schema for enforcing.
- **Model genuinely n-ary facts (indicator readings) as promotable.** Treat an attributed edge and a reified relation-node as interchangeable renderings of one fact, so a 4-ary indicator reading (output, outcome, value, period/source) can normalize to an intermediate node when needed [10][12] without changing the source-of-truth semantics. Expose this as a normalization toggle, not two incompatible models.
- **Bake lossless RDF-star and JSON export into the core data model from day one**, not as an afterthought. Constrain the internal LPG so it stays in the *RDF-star-losslessly-mappable* subset (per Hartig/PREC) [6][9], and reserve `rdf:reifies`/triple-term semantics for the export layer. JSON is the canonical serialization; RDF-star is the interoperability serialization.
- **Carry extraction/verification metadata as edge/element annotations, leveraging non-asserted triple terms for auditability.** RDF 1.2's notion that a triple term is *not automatically asserted* [2] is a perfect fit for creel's auditability posture: "this element was *proposed* by extractor X from source Y with confidence Z" is a statement *about* an unasserted candidate, cleanly separable from the asserted graph.

## Recommendation

**Adopt a Labeled-Property-Graph core with first-class typed edges and a two-layer (type-graph + annotation) design, engineered to round-trip losslessly to RDF-star and JSON.** Concretely: node-types and edge-types form an explicit **type graph** with typed attribute schemas and a **subtype taxonomy** (SKOS-style `broader`/`narrower` for navigation, PG-Schema-style `subClassOf` + multi-inheritance + keys for validation [7][8][15]); **attributes live natively on edges**; and the canonical JSON graph spec is constrained to the subset that maps **losslessly to RDF-star** [6][9] so creel is simultaneously property-graph-friendly *and* RDF-interoperable.

Rationale: LPG is the only model where creel's defining requirement — typed attributes *on edges*, with distinct edge identity and terminating queries — is **native rather than a workaround** [1][3][5]. RDF's interoperability and reasoning strengths are not lost, because the RDF-star↔LPG transformation is provably information-preserving [6][9][12], so creel gets RDF's reach as an *export*, not as a structural tax on the internal model. PG-Schema supplies the typing/inheritance rigor LPG historically lacked [7][8], and graph-grammar theory supplies the formal backbone for creel's "grammar of node/edge types" and its strategy-pattern, rule-based extraction [13][14]. The single clearest call: **internal LPG, external RDF-star, JSON canonical — losslessness as a hard design constraint.**

## References

1. Memgraph. [LPG vs. RDF](https://memgraph.com/docs/data-modeling/graph-data-model/lpg-vs-rdf). Accessed 2026-06-16.
2. W3C. [RDF 1.2 Concepts and Abstract Syntax — Candidate Recommendation Snapshot, 07 April 2026](https://www.w3.org/TR/rdf12-concepts/). (Triple terms; `rdf:reifies`; non-asserted triple terms.)
3. Neo4j. [RDF triple stores vs. labeled property graphs: What's the difference?](https://neo4j.com/blog/knowledge-graph/rdf-vs-property-graphs-knowledge-graphs/). Accessed 2026-06-16.
4. Ontotext. [What Is RDF-star (RDF*)?](https://www.ontotext.com/knowledgehub/fundamentals/what-is-rdf-star/). Accessed 2026-06-16.
5. ISO/IEC. [ISO/IEC 39075:2024 — Database languages — GQL](https://www.iso.org/obp/ui/en/#!iso:std:76120:en); see also TigerGraph, [The Rise of GQL: A New ISO Standard](https://www.tigergraph.com/blog/the-rise-of-gql-a-new-iso-standard-in-graph-query-language/).
6. Lassila E. et al. [Bridging graph data models: RDF, RDF-star, and property graphs as directed (acyclic) graphs](https://arxiv.org/pdf/2304.13097). arXiv 2304.13097.
7. Angles R. et al. [PG-Schema: Schemas for Property Graphs](https://arxiv.org/pdf/2211.10962). arXiv 2211.10962. (Multi-inheritance, PG-Keys, constraints.)
8. JTC1/SC32. [ISO/IEC 39075 Database Language GQL — overview](https://jtc1info.org/wp-content/uploads/2024/04/2024-Article-39075-Database-Language-GQL.docx.pdf).
9. Bonifati A. et al. [PREC: semantic translation of property graphs](https://arxiv.org/pdf/2110.12996) (reversible PG↔RDF); Hartig O. [Reconciliation of RDF* and Property Graphs](https://arxiv.org/pdf/1409.3288) (lossless RDF*↔PG).
10. NeurIPS / arXiv. [HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation](https://arxiv.org/pdf/2602.14470) and [Hypergraph-Based Knowledge Representations overview](https://www.emergentmind.com/topics/hypergraph-based-knowledge-representations).
11. Apache Jena. [Support of RDF-star](https://jena.apache.org/documentation/rdf-star/) (RDF-star ↔ reification translation; reification verbosity).
12. W3C. [Defining N-ary Relations on the Semantic Web (Working Group Note)](https://www.w3.org/TR/swbp-n-aryRelations/). (Intermediate relation-instance pattern; why standard reification is not recommended.)
13. Ehrig H. et al. [Fundamental Theory for Typed Attributed Graphs and Graph Transformation based on Adhesive HLR Categories](https://link.springer.com/chapter/10.1007/978-3-540-30203-2_13). (Type graph + attribution; confluence.)
14. de Lara J. et al. [A Typed Attributed Graph Grammar with Inheritance for the Abstract Syntax of UML Class and Sequence Diagrams](https://www.sciencedirect.com/science/article/pii/S1571066108002636). (Inheritance in type graphs.)
15. W3C. [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/); Wang J. [Ontology, Taxonomy, and Graph standards: OWL, RDF, RDFS, SKOS](https://medium.com/@jaywang.recsys/ontology-taxonomy-and-graph-standards-owl-rdf-rdfs-skos-052db21a6027). (Concept/ConceptScheme; broader/narrower; ontology = schema + instances.)
