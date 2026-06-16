# Creel — Deep Research Prompts

This document records the research agenda that informs the design and
implementation of **creel**, a general AI-powered *source-to-graph extraction
engine* (see [`../starter -- source-to-graph-engine_core-description.md`](../starter%20--%20source-to-graph-engine_core-description.md)).

Each subject below was researched by a dedicated agent that performed
multi-source web research, adversarially sanity-checked claims, and wrote a
cited report (Vancouver-style `[n]` references) into `misc/docs/research/`. A
final synthesis report (`00-synthesis-and-design-implications.md`) distills the
cross-cutting design implications for creel.

The subjects were chosen to cover the full arc of the package's mission:
**(what)** representing knowledge as a typed graph, **(how)** extracting that
graph from heterogeneous sources, **(with what)** the existing open-source
landscape we should build on, **(persist/query)** graph databases and query
languages, **(trust)** provenance/auditability, **(evaluate)** verification and
LLM-as-judge evaluation, **(consume)** downstream RAG and rendering, **(domain)**
the first UNHCR results-based-management use case, and **(architecture)** the
pluggable strategy-based software design.

---

## Subject index

| # | Slug | Title | Why it matters to creel |
|---|------|-------|-------------------------|
| 01 | `knowledge-graph-models` | Models for representing knowledge as graphs | Defines creel's core data model (the *what*) |
| 02 | `graph-schema-languages` | Graph schema & grammar specification languages | Creel's two schemas: grammar spec + instance |
| 03 | `graph-serialization-formats` | Graph serialization & JSON interchange formats | Choosing creel's canonical JSON graph emit format |
| 04 | `llm-knowledge-extraction` | LLM-based information & knowledge-graph extraction | The extraction engine's methods (the *how*) |
| 05 | `oss-tooling-landscape` | Open-source tooling landscape & build-vs-buy | What creel should reuse vs build |
| 06 | `graph-databases-query` | Graph databases & query languages | Downstream persistence/query; query-based extractors |
| 07 | `provenance-auditability` | Provenance, grounding, confidence & auditability | The "auditability over opaqueness" posture |
| 08 | `extraction-evaluation-verifiers` | Evaluation, verifiers & LLM-as-judge | Creel's evaluation system (user-emphasized) |
| 09 | `graphrag-knowledge-bases` | GraphRAG & graph knowledge bases | Downstream consumer §6.1 |
| 10 | `graph-rendering-media` | Graph rendering, annotation & media generation | Downstream consumer §6.2 ("one model, many views") |
| 11 | `rbm-logframe-domain` | Results-based management & logframe domain (UNHCR) | First use case's domain ontology + test data |
| 12 | `pluggable-extraction-architecture` | Pluggable strategy-based extraction architecture | The package's software design posture |

---

## 01 — Models for representing knowledge as graphs

**Prompt.** Survey the principal models for representing knowledge as graphs and
compare them for a system that must extract a *typed* graph (nodes and edges that
each carry typed attributes, organized into recursively-subdivided taxonomies of
subtypes) from heterogeneous documents. Cover at minimum: the **Labeled Property
Graph (LPG)** model; the **RDF triple / RDF-star** model; **RDF vs LPG**
trade-offs; **hypergraphs** and **n-ary relations** (reification, RDF-star,
intermediate nodes); **typed/attributed graphs** and graph-grammar theory; and
**ontologies vs schemas vs taxonomies** (OWL, SKOS). For each model explain how
node types, edge types, edge attributes, and subtype hierarchies are expressed,
and how well attributes-on-edges are supported (critical for creel, which puts
funding amounts and indicator values *on edges*). Conclude with a recommendation
for an internal model that is property-graph-friendly yet losslessly mappable to
RDF and to JSON. Use Vancouver references.

## 02 — Graph schema & grammar specification languages

**Prompt.** Creel needs two schemas: (1) a schema for **specifying the grammar**
(the node-type and edge-type taxonomy plus typed-attribute definitions and
constraints) and (2) a schema for **describing extracted graph instances**.
Survey and compare the languages/standards available to express such schemas:
**JSON Schema**, **Pydantic** (v2), **LinkML**, **SHACL** and **ShEx**, **OWL**,
**GraphQL SDL**, **PG-Schema / PG-Keys** (the property-graph schema proposal),
**Neo4j schema constraints**, **Cypher's `CREATE CONSTRAINT`**, **Dublin
Core/SKOS** for taxonomies, and **JSON-LD `@context`**. For each: how it
expresses node vs edge types, attribute typing, enumerations/value sets,
cardinality, ranges, and subtype/inheritance; whether it can describe *edges as
first-class typed objects with their own attributes*; tooling and Python support;
and whether it round-trips to validation code. Pay special attention to
**LinkML** (which targets exactly this "schema for data + generates Pydantic/JSON
Schema/SHACL" space) and to representing **constrained value sets / enumerations
/ numeric ranges**. Recommend a layered approach for creel that keeps the
*grammar definition* separable from *extraction metadata*. Vancouver references.

## 03 — Graph serialization & JSON interchange formats

**Prompt.** Creel emits, canonically, "a JSON graph specification." Survey the
established JSON and non-JSON graph serialization/interchange formats and assess
each as creel's canonical emit format: **JSON Graph Format (JGF)**,
**NetworkX node-link JSON**, **Cytoscape.js JSON**, **TinkerPop GraphSON**,
**JSON-LD**, **GraphML (XML)**, **GEXF**, **DOT/Graphviz**, **RDF
Turtle/N-Triples**, and **Neo4j's import JSON / APOC formats**. Compare on:
support for typed nodes/edges, **attributes on edges**, schema references,
multi-graph/parallel edges, directedness, identifier conventions, provenance
fields, human-readability/diffability (important for auditability and git),
ecosystem/tooling, and ease of conversion to the others. Recommend a canonical
internal JSON shape for creel (with an explicit, versioned schema) plus an
adapter set to export to the others. Vancouver references.

## 04 — LLM-based information & knowledge-graph extraction

**Prompt.** Survey the state of the art (through 2025/early 2026) in extracting
**structured, typed graphs** from documents using LLMs. Cover: **schema-guided /
ontology-guided extraction**; **structured output** mechanisms (function/tool
calling, JSON mode, constrained decoding / grammars, Pydantic-validated output);
classical building blocks (**NER**, **relation extraction**, **OpenIE**,
**coreference / entity resolution / entity linking**); **document-to-KG**
pipelines (LangChain `LLMGraphTransformer`, LlamaIndex `KnowledgeGraphIndex` /
`PropertyGraphIndex`, **Microsoft GraphRAG** extraction, **REBEL**, **iText2KG**,
**SPIRES/OntoGPT**); strategies for **long documents** (chunking, map-reduce,
windowing) and **multi-document consolidation/deduplication**; handling
**tables and semi-structured/JSON sources** (when a source carries its own
schema, how to exploit it); **hallucination/faithfulness** mitigation and
**source grounding**; and **prompt/skill design** for extraction instructions.
Identify concrete, reusable techniques creel should adopt for its
NL-description, query-based, and pattern/functional extractor strategies. Note
where Anthropic Claude tool-use / structured output fits. Vancouver references.

## 05 — Open-source tooling landscape & build-vs-buy

**Prompt.** Produce a practical, opinionated **landscape of open-source Python
tooling** relevant to building creel, grouped by concern, with build-vs-buy
guidance for each: (a) **structured LLM output** — Instructor, Outlines,
Guidance, LMQL, BAML, Pydantic-AI, the Anthropic SDK's tool use; (b)
**document→KG construction** — LangChain, LlamaIndex, Microsoft GraphRAG,
iText2KG, OntoGPT/SPIRES, Graphiti, REBEL; (c) **graph data structures & DBs in
Python** — NetworkX, rustworkx, igraph, Neo4j driver, Kùzu, Memgraph, RDFLib,
Oxigraph, NetworkX-backed stores; (d) **schema/validation** — Pydantic, LinkML,
jsonschema, pyshacl; (e) **entity resolution** — dedupe, Splink, RecordLinkage;
(f) **evaluation** — DeepEval, Ragas, promptfoo, Inspect, OpenAI Evals,
LangSmith; (g) **document parsing/ingest** — unstructured, docling, markitdown,
LlamaParse. For each tool note maturity, license, last-active status, fit, and
the integration seam by which creel could plug it in via the strategy pattern.
End with a recommended **minimal dependency set** for creel's core vs optional
extras. Vancouver references.

## 06 — Graph databases & query languages

**Prompt.** Survey graph databases and graph query languages as **downstream
persistence/query targets** for a typed property graph, and as inspiration for
creel's **query-based extractor strategy**. Cover: **Cypher** and the new ISO
**GQL** standard; **Neo4j**; **Kùzu** (embedded), **Memgraph**, **TigerGraph**;
**RDF/SPARQL** stores (Oxigraph, GraphDB, Blazegraph), **Apache Jena**;
**Gremlin/Apache TinkerPop**; and embedded/lightweight options. Compare data
models, schema/constraint support, attributes-on-edges, bulk-import formats,
Python clients, and licensing. Separately, survey **query languages over
structured sources** that creel's query-based extractors should emulate: **SQL**
for tables and **MongoDB-style query documents** / JMESPath / JSONPath for JSON
and lists-of-JSON. Recommend (a) a clean intermediate representation that maps to
several graph DBs without coupling the core to one, and (b) a small, safe
query-spec abstraction for the extractor strategy. Vancouver references.

## 07 — Provenance, grounding, confidence & auditability

**Prompt.** Creel insists on **auditability over opaqueness**: every extracted
element should carry the means to be verified and traced to its source. Survey
the methods and standards for this. Cover: **provenance data models** (**W3C
PROV-O / PROV-DM**, **PAV**, **nanopublications**); **standoff annotation** and
**text-anchoring / selector** schemes (W3C Web Annotation Data Model,
character-offset spans, quote/prefix/suffix selectors) for pinning an extracted
value to exact source locations; **source grounding & citation** techniques for
LLM extraction (span attribution, "cite your evidence" prompting, retrieval
attribution); **confidence/uncertainty** estimation for LLM outputs (token
logprobs, self-consistency/voting, verbalized confidence, calibration); and
**human-in-the-loop review** workflows for correcting extractions. Recommend a
concrete, lightweight provenance+confidence record that creel should attach to
every node, edge, and attribute value, kept *physically separable* from the
graph definition but joinable on demand. Vancouver references.

## 08 — Evaluation, verifiers & LLM-as-judge

**Prompt.** This is central to creel. We want an **evaluation system** for
extraction where the comparison between *actual* output and *expected* output is
**not** generally a hardcoded equality check, but a pluggable **verifier** — and
where some verifiers can be **fully defined by natural-language instructions to
an LLM** that judges robustly. Research and synthesize: (1) **metrics for KG/IE
extraction** — precision/recall/F1 on entities and relations/triples, slot-filling
metrics, **graph similarity / graph edit distance**, set-based matching with
fuzzy entity alignment, canonicalization before comparison; (2) **semantic
equivalence** checking (embedding similarity, NLI/entailment, normalization);
(3) **LLM-as-judge** methodology — pairwise vs pointwise, rubric/criteria-based
grading, reference-free vs reference-based, **G-Eval**, known **biases**
(position, verbosity, self-preference) and mitigations, reliability/agreement
with humans; (4) **verifier abstractions** in eval frameworks (DeepEval metrics,
Ragas, OpenAI Evals graders, Inspect scorers, **OpenAI/“model graders” and
rubric graders**, guardrails-style validators) and how they're composed;
(5) **assertion/property-based testing** ideas for non-deterministic output. Then
**design, concretely, creel's verifier abstraction**: a common `Verifier`
interface, a taxonomy of verifier kinds (exact/normalized equality, set/graph
matching, schema/constraint, numeric-tolerance, semantic-similarity,
LLM-instruction/rubric, composite/weighted), how an LLM-instruction verifier is
specified and executed, and how the test corpus (sources + expected) is
organized so verifiers attach to fields/elements. Vancouver references.

## 09 — GraphRAG & graph knowledge bases

**Prompt.** Survey **graph-based retrieval-augmented generation** and graph
knowledge bases as the downstream consumer of creel's extracted graph (core
description §6.1). Cover: **Microsoft GraphRAG** (entity/relation extraction →
community detection (Leiden) → community summaries → global vs local search);
**LlamaIndex PropertyGraphIndex**, **Neo4j GraphRAG**, **Graphiti** (temporal),
**LightRAG**, **HippoRAG**; **hybrid graph+vector** retrieval; **knowledge-base
construction & maintenance** (incremental updates, temporal/versioned graphs,
conflict resolution); and what properties an extracted graph needs to feed these
well (stable IDs, typed edges, provenance, embeddings-ready text). Recommend the
shape of creel's output and optional "RAG-readiness" affordances that make the
graph flow naturally into these systems without coupling the core to any.
Vancouver references.

## 10 — Graph rendering, annotation & media generation

**Prompt.** Creel's second downstream family (core description §6.2) is
**annotation + rendering** into analysis media under a "one model, many views"
principle. Survey: **declarative graph visualization** (Graphviz/DOT, Mermaid,
Cytoscape.js, D3, vis.js, yFiles, Sigma, **netwulf**, pyvis); **annotation
layers** over graphs (how to attach insights/comments/captions as a separable
overlay; standoff annotation again); and **automated media generation from
structured data** — tables, **PowerPoint generation** (python-pptx), **report
generation** (Quarto, Jinja+Markdown→PDF, Pandoc), data-narrative/auto-insight
generation, and **narrated video** (slide+TTS pipelines). For each, note the
input shape it expects and how a typed graph + annotation overlay would map onto
it. Recommend a renderer-plugin interface for creel's consumer packages and the
minimal "annotated graph" contract renderers consume. Vancouver references.

## 11 — Results-based management & logframe domain (UNHCR first use case)

**Prompt.** Creel's first concrete consumer is **UNHCR ESA Bureau use case #3**:
extracting, from project and donor documents, a graph of **donors, objectives,
cross-cutting areas, projects, outputs, outcomes, and indicators**, with
**funding amounts** and **indicator values** on edges. Research the domain so we
can model it faithfully and build realistic test data. Cover: **Results-Based
Management (RBM)** and the **logical framework (logframe)**; the **results chain**
(inputs→activities→outputs→outcomes→impact) and **Theory of Change**; **SMART
indicators**, baselines/targets/means-of-verification; **UNHCR's results
framework** and **COMPASS** terminology (impact/outcome/output statements,
objectives, enabling areas) where publicly documented; the **IATI** standard and
**OECD-DAC** markers for donor/funding data; and how cross-cutting areas (e.g.
gender, environment, protection, AGD) are typically represented. Produce a
candidate **node/edge taxonomy** (with typical attributes and edge types like
*funds*, *delivers*, *contributes-to*, *advances*, *addresses*, *measured-by*)
and 2–3 short **synthetic but realistic example documents** (a donor agreement
excerpt, a project results matrix, an indicator table) that can seed creel's test
corpus. Vancouver references; cite public UNHCR/IATI/OECD sources.

## 12 — Pluggable strategy-based extraction architecture

**Prompt.** Translate creel's design posture (core description §3, §5) into
concrete **software architecture** options, in Python. Cover: the **strategy
pattern** and **plugin registries** for swappable extraction mechanisms
(NL-description, query-based, pattern/functional) and later renderers; the
**facade** for `extract(sources, graph_spec, extractors) → graph`; **dependency
injection** and **functions-as-parameters** over inheritance; mechanisms for
**physically separating** the *graph definition* layer from the
*extraction/verification metadata* layer and **joining them on demand** (think
data-oriented design, "schema join", entity-component patterns); **registry/entry-
point plugin discovery** (Python `entry_points`, `pluggy`, simple decorator
registries) with **open-closed** extensibility; **typed dataclasses / Pydantic**
for the records; **pipeline/DAG orchestration** (when is a full framework like
Prefect/Hamilton/Haystack warranted vs a thin composition of callables);
**caching** of expensive LLM calls; and a **monorepo** layout that keeps core vs
consumer packages separate but co-located (uv/Hatch workspaces, `src` layout).
Recommend a concrete module/layer decomposition and the key Python interfaces
(Protocols/ABCs) for creel's core. Vancouver references.

---

*Generated as the research agenda for creel. Results are the sibling `NN-*.md`
report files; cross-cutting conclusions are in
`00-synthesis-and-design-implications.md`.*
