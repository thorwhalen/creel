# 05 — Open-source tooling landscape & build-vs-buy

> **TL;DR.** The Python ecosystem already solves most of creel's *sub-problems* well, but **no single library is creel** — none combines a first-class, recursively-taxonomic node/edge *grammar with typed edge attributes*, a *pluggable per-element extraction strategy* layer (LLM / query / regex), and *physical separation* of graph-definition from extraction-metadata. The closest architectural kin is **OntoGPT/SPIRES** (schema-as-extractor, BSD-3) and **LinkML** (single-source-of-truth schema → JSON/Pydantic/RDF/SQL), which should be the *intellectual* templates for creel even if not hard dependencies. For the strategy seams: lean on **Pydantic v2** as the universal typed-attribute backbone, **Instructor** (MIT) as the *default* LLM-extraction strategy adapter (provider-agnostic, retry/validate), **jsonschema** + Pydantic for validation, and keep everything else (GraphRAG, LlamaIndex, dedupe/Splink, DeepEval, docling) as *optional extras* plugged in behind the strategy interface. Critically, creel core should depend on **almost nothing heavy**: Pydantic, jsonschema, NetworkX, and a thin LLM-client abstraction. Buy the commodity (structured output, parsing, eval); build the differentiator (the grammar + strategy + audit-trail facade).

---

## Background / landscape

Creel's core facade is `extract(sources, graph_spec, extractors) -> graph`, with three pillars that map onto distinct, mature OSS concerns:

1. **graph_spec** is fundamentally a *schema-modeling* problem (node/edge types, taxonomies, typed/constrained attributes). This is the domain of Pydantic, LinkML, jsonschema, and SHACL.
2. **extractors** are *strategies* — an LLM agent reading an NL description (default), a query over structured sources, or a regex/function. This is the domain of structured-LLM-output libraries (Instructor, Outlines, BAML, Anthropic SDK) plus plain query/regex tooling.
3. **graph** is a *graph data structure / KG* problem — represented in memory (NetworkX/rustworkx), persisted (Kùzu/Neo4j/Memgraph/Oxigraph), and optionally resolved (entity resolution) and evaluated (eval frameworks).

The market has bifurcated into (a) **library primitives** you compose yourself, and (b) **opinionated end-to-end pipelines** (GraphRAG, LlamaIndex PropertyGraphIndex, Graphiti) that bake in their *own* graph model and extraction loop. Creel's design posture — single source of truth, strategy pattern, auditability, progressive disclosure — is fundamentally incompatible with adopting an opinionated pipeline *as the core*: those pipelines own the graph model and hide the extraction logic, which is exactly the thing creel exposes and makes pluggable. So the build-vs-buy line falls naturally: **buy primitives behind strategy seams; do not buy a pipeline as the spine.**

A second structural observation: 2025 collapsed much of the "structured output" value. Anthropic shipped **Structured Outputs / strict tool use** (constrained decoding, guaranteed JSON-schema compliance) in public beta on 2025-11-14 [1], following OpenAI's earlier strict mode. This commoditizes a layer that libraries like Instructor and Outlines used to differentiate on — meaning creel should treat "guaranteed-schema LLM output" as a *provider capability behind an adapter*, not a dependency to marry.

---

## Comparative analysis

### (a) Structured LLM output

| Tool | License | Approach | Maturity / recency | Fit for creel |
|---|---|---|---|---|
| **Instructor** [2] | MIT | Function-calling + Pydantic `response_model`, post-gen validation, auto-retry, multi-provider | Very mature: ~13k★, 3M+ downloads/mo, v1.15+ (2026) | **Best default LLM-strategy adapter.** Provider-agnostic, Pydantic-native, retry-on-validation = aligns with auditability |
| **Outlines** [3] | Apache-2.0 (OSS) + commercial | Constrained decoding (regex/CFG/JSON-schema), 100% compliance | Mature: ~13.5k★, active | Strong for *self-hosted* models needing hard guarantees; heavier seam (needs logit access) |
| **Guidance** | MIT | Constrained generation + control flow (if/else during gen) | Mature, active | Niche: branching generation; more than creel needs by default |
| **LMQL** | Apache-2.0 | Query-language for LLMs | Maturing/slowing | Skip — DSL lock-in, smaller community |
| **BAML** [4] | Apache-2.0 | Separate DSL + codegen; "Schema-Aligned Parsing" recovers partial/garbled output; multi-language | Growing fast | Compelling robustness, but the DSL is a *parallel* SSOT to creel's grammar — architectural friction |
| **Pydantic-AI** [5] | MIT | Agent framework (tools, DI, validated results), Pydantic-native | Newer (GA'd late 2025), maturing | Good if creel wants an agent loop; overlaps creel's own orchestration |
| **Anthropic SDK structured outputs** [1] | MIT (SDK) | Native constrained decoding; `.parse()` with Pydantic | Beta since 2025-11; production-grade SDK | Use as a *capability* behind the LLM adapter, not a hard dep |

### (b) Document → KG pipelines

| Tool | License | What it owns | Recency | Fit |
|---|---|---|---|---|
| **OntoGPT / SPIRES** [6][7] | BSD-3 | **Schema-as-extractor**: LinkML schema + text → JSON/YAML/RDF/OWL, recursive prompt interrogation, ontology grounding | Active, v1.1.x (2026), ~900★ | **Closest conceptual match to creel.** Study it; possibly wrap it as one extractor strategy |
| **Microsoft GraphRAG** [8] | MIT | Full pipeline: entity/relation extraction → Leiden communities → summaries → query | Active; "demo, not supported product" | Owns its graph model; *expensive* (graph extraction ≈75% of indexing cost [8]). Optional extra, not core |
| **LlamaIndex PropertyGraphIndex** [9] | MIT | `SchemaLLMPathExtractor` (allowed node/edge/relation types), modular extractors/retrievers | Mature, active | Good reference for schema-guided extraction; pluggable as a strategy but drags in LlamaIndex |
| **iText2KG** [10] | (permissive) | Incremental, schema-aware KG construction; entity/relation dedup; async core (2025) | Active, on PyPI | Interesting for *incremental* updates; smaller community |
| **Graphiti** [11] | Apache-2.0 | **Bi-temporal** KG memory for agents; validity intervals (t_valid/t_invalid) *on edges* | Active, popular | Temporal edge attributes are *exactly* creel's "values live on edges" pattern — strong reference for the edge model |
| **REBEL** | (model: open) | End-to-end relation-extraction transformer (triplets) | Stable, older | A *non-LLM* extractor strategy option (cheap, deterministic-ish) |
| **LangChain** | MIT | `LLMGraphTransformer`, glue | Mature, sprawling | Avoid as core; cherry-pick if at all |

### (c) Graph data structures & DBs

| Tool | License | Type | Recency / health | Fit |
|---|---|---|---|---|
| **NetworkX** [12] | BSD-3 | Pure-Python in-memory graph | Ubiquitous, active | **Core in-memory representation** — universal, zero-friction, attribute dicts on nodes *and* edges |
| **rustworkx** [12] | Apache-2.0 | Rust-backed, NetworkX-like | Active (Qiskit team) | Optional perf extra for large graphs (3–100× faster [12]) |
| **igraph** | GPL-2.0 | C-backed | Mature | GPL license = avoid as a *core* dep for a permissive package |
| **Neo4j Python driver** | Apache-2.0 | Client to Neo4j server | Mature | Optional persistence backend; server is a heavy external dep |
| **Kùzu** [13] | MIT | Embedded property graph, Cypher | **⚠ Repo archived Oct 2025 (Apple acqui-hire)** [13] | Was ideal (embedded, MIT); **now a maintenance risk** — do not bet core on it |
| **Memgraph** | BSL 1.1 / partly | In-memory graph DB server | Active | Source-available license caveats; optional only |
| **RDFLib** [14] | BSD-3 | RDF triples in Python | Active, v7.4 (2025), v8 coming | Use only if/when an RDF/semantic output is required |
| **Oxigraph** | Apache-2.0/MIT | Fast Rust RDF store + SPARQL | Active | Optional RDF persistence; pairs with RDFLib |

### (d) Schema / validation

| Tool | License | Role | Fit |
|---|---|---|---|
| **Pydantic v2** | MIT | Typed models, constraints (enums/ranges), JSON-schema export, fast Rust core | **Core backbone** for typed attributes on nodes *and* edges |
| **jsonschema** | MIT | Validate arbitrary JSON against Draft 2020-12 | **Core** for validating the canonical JSON graph spec + freeform/constrained attrs |
| **LinkML** [15] | CC0/BSD | YAML schema → JSON/Pydantic/RDF/SQL/SHACL; SSOT modeling | Strong *conceptual* template; optional dep for users wanting semantic interop |
| **pyshacl** [16] | Apache-2.0 | SHACL validation of RDF graphs | Optional, only in the RDF path |

### (e) Entity resolution

| Tool | License | Approach | Fit |
|---|---|---|---|
| **Splink** [17] | MIT | Probabilistic linkage, SQL backends (DuckDB/Spark), scales to 10s of millions | **Best optional ER extra** — fast, MIT, embeddable via DuckDB |
| **dedupe** | MIT | Active-learning ER | Optional; needs labeling loop |
| **RecordLinkage** | BSD-3 | Prototyping toolkit | Optional, smaller-scale |

### (f) Evaluation

| Tool | License | Strength | Fit |
|---|---|---|---|
| **DeepEval** [18] | Apache-2.0 | "Pytest for LLMs"; metrics, CI gating | **Best fit for creel's per-element verification tests** |
| **Inspect (AISI)** | MIT | Rigorous eval framework | Good for deeper audits |
| **Ragas** | Apache-2.0 | RAG-centric metrics | Only if creel adds RAG downstream |
| **promptfoo** | MIT | YAML-defined matrix evals + red-team, CLI | Good for prompt-strategy regression across providers |
| **OpenAI Evals / LangSmith** | MIT / proprietary-SaaS | — | Skip core; LangSmith is hosted |

### (g) Document parsing / ingest

| Tool | License | Strength | Fit |
|---|---|---|---|
| **docling** [19] | MIT | Layout (DocLayNet) + tables (TableFormer), local, strong structural fidelity | **Best default OSS ingest extra** |
| **markitdown** [19] | MIT | Many formats → Markdown, tiny | Good *lightweight* default for text-first docs |
| **unstructured** [19] | Apache-2.0 (+ paid) | Broad ETL, connectors, chunking | Heavyweight optional |
| **LlamaParse** | proprietary SaaS | Agentic OCR, fast | Optional paid backend, not core |

---

## Deep section: where creel is genuinely different (and what to reuse)

**1. Typed attributes on edges as first-class.** Most graph builders treat edges as labeled relations; attributes (funding amounts, indicator values) are an afterthought. Two systems get this right and are worth studying: **Graphiti** [11], whose edges carry explicit validity intervals (`t_valid`/`t_invalid`) — a direct precedent for "values live *on* edges" — and **NetworkX/rustworkx** [12], whose edge model is just an attribute dict, making arbitrary typed edge attributes trivial. *Reuse:* NetworkX as the in-memory carrier; *do not* reuse Graphiti's pipeline, only its temporal-edge idea.

**2. Schema-as-extractor (progressive disclosure).** Creel's "schema is the default extractor" is *exactly* SPIRES [6][7]: a LinkML schema is compiled into prompts and a typed object is recursively extracted, grounded to ontologies, emitted as JSON/RDF. This validates creel's central bet. *Reuse:* either depend on OntoGPT as one strategy, or (cleaner) replicate the pattern with Pydantic-derived JSON-schema → prompt, keeping the dependency surface small and the audit trail in creel's hands.

**3. Single source of truth + multi-target codegen.** **LinkML** [15] is the canonical example: one YAML schema generates Pydantic, JSON-Schema, RDF, SQL, SHACL. Creel's "graph definition layer physically separated from extraction metadata, joined on demand" is a LinkML-flavored idea. *Reuse:* adopt LinkML's *philosophy*; offer LinkML import/export as an optional bridge for semantic-web users, but keep the *native* SSOT a plain JSON/Pydantic graph spec so the dependency floor stays low.

**4. The strategy seam, concretely.** Define a single `Extractor` protocol — `detect/extract/verify(element_spec, source) -> typed_value + provenance`. Each external tool plugs in as one implementation:
- *LLM strategy* → wraps **Instructor** [2] (default) or the **Anthropic SDK** [1] structured-output capability; returns Pydantic-validated value + the raw response for the audit log.
- *Query strategy* → SQL-like over tables (DuckDB/pandas), Mongo-like over JSON (jsonpath/`pymongo`-style filters) — no heavy dep needed.
- *Pattern strategy* → stdlib `re` or any `Callable[[Source], Value]`.
- *Verification* → reuse **DeepEval** [18] assertions / **jsonschema** constraint checks, run as the `verify` step, emitting pass/fail into provenance for **auditability**.

This keeps the *facade* stable while every "buy" decision becomes a swappable adapter — the open-closed design creel's CLAUDE-level principles demand.

---

## Design implications for creel

- **Pydantic v2 is the typed-attribute backbone, everywhere.** Node-type, edge-type, and attribute specs (enums, ranges, freeform) should compile to Pydantic models; export JSON-Schema for the canonical spec and for any constrained-decoding provider. This single choice unifies validation, IDE support, and LLM-output shaping. (Don't reinvent constraint types.)
- **Default LLM extractor = Instructor; structured-output is a provider capability, not a hard dep.** Wrap Instructor [2] behind the `Extractor` protocol so Anthropic strict mode [1], OpenAI, or self-hosted Outlines [3] are interchangeable. Retry-on-validation maps directly to creel's "verifiable element" requirement.
- **Graph carrier = NetworkX in core; everything else is an extra.** Edge attribute dicts give creel first-class typed edges for free [12]. Offer rustworkx as a perf extra and Neo4j/Oxigraph as persistence extras *behind a storage interface* — never as a core import. **Explicitly do not depend on Kùzu in core** given its Oct-2025 archival [13].
- **Treat GraphRAG / LlamaIndex / Graphiti as optional pipeline *extras*, never the spine.** They own a graph model and hide extraction logic — the opposite of creel's auditable, strategy-pluggable design. Borrow ideas (SPIRES schema-as-prompt, Graphiti temporal edges, LlamaIndex `SchemaLLMPathExtractor`), not the frameworks. Note GraphRAG's ~75% indexing-cost in the LLM extraction step [8] — a strong argument for creel's cheaper query/regex strategies where applicable.
- **Entity resolution and evaluation are first-class but optional seams.** Splink [17] (MIT, DuckDB-embeddable) for node-merge; DeepEval [18] for the `verify` step and CI gating. Both fit creel's auditability story (provenance + test verdicts on every element).
- **Offer LinkML/SPIRES interop as a bridge, not a base.** Let semantic-web users import a LinkML schema as a `graph_spec` and emit RDF/SHACL [15][16], without forcing the RDF stack on the median user (progressive disclosure).

## Recommendation

**Build the differentiator (the grammar + strategy + audit facade) on a deliberately tiny core, and buy every commodity behind a strategy/storage seam.**

Concretely, the **minimal creel core** depends on only: **`pydantic` (typed attrs + JSON-schema), `jsonschema` (validate canonical spec), `networkx` (in-memory graph with typed node/edge attrs)**, and a *thin* LLM-client abstraction (no provider SDK pinned). The default LLM-extraction strategy adapter wraps **Instructor** — but as an **optional extra** (`creel[llm]`), so the pure-schema + query + regex paths run with zero LLM dependency, honoring progressive disclosure and keeping the core installable and auditable.

Recommended **optional extras**, each isolated behind the `Extractor`/storage protocols:
- `creel[llm]` → instructor (+ optional anthropic/openai)
- `creel[constrained]` → outlines (self-hosted hard-guarantee path)
- `creel[ingest]` → docling and/or markitdown
- `creel[graphdb]` → neo4j driver and/or oxigraph (RDF), rustworkx (perf)
- `creel[er]` → splink
- `creel[eval]` → deepeval
- `creel[semantic]` → linkml, rdflib, pyshacl
- `creel[pipelines]` → graphrag / llama-index (interop adapters only)

Rationale: this keeps creel's *identity* — the parameterized facade with a pluggable, auditable strategy layer over a typed node/edge grammar — fully owned by creel, while delegating commoditized, fast-moving, sometimes-license-encumbered components (constrained decoding, parsing, ER, eval, persistence) to best-in-class libraries that can be swapped without touching the spine. The single most consequential adversarially-verified caveat: **do not couple core to any opinionated KG pipeline or to Kùzu** [13] — both would compromise creel's auditability and longevity.

---

## References

1. [Anthropic — Structured outputs (Claude API docs / public beta announcement, 2025-11-14)](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
2. [Instructor — Structured LLM outputs (GitHub, jxnl/instructor)](https://github.com/jxnl/instructor)
3. [Outlines — Structured generation (dottxt-ai/outlines, GitHub)](https://github.com/dottxt-ai/outlines)
4. [BAML — Schema-Aligned Parsing for structured LLM output (comparison writeup)](https://www.glukhov.org/post/2025/12/baml-vs-instruct-for-structured-output-llm-in-python/)
5. [Pydantic-AI — Agent framework, the Pydantic way (GitHub)](https://github.com/pydantic/pydantic-ai)
6. [SPIRES — Structured Prompt Interrogation and Recursive Extraction of Semantics (Bioinformatics, 2024)](https://academic.oup.com/bioinformatics/article/40/3/btae104/7612230)
7. [OntoGPT — LLM ontological extraction incl. SPIRES (GitHub, monarch-initiative/ontogpt)](https://github.com/monarch-initiative/ontogpt)
8. [Microsoft GraphRAG — modular graph-based RAG (GitHub) + cost analysis](https://github.com/microsoft/graphrag)
9. [LlamaIndex — Property Graph Index & SchemaLLMPathExtractor](https://www.llamaindex.ai/blog/introducing-the-property-graph-index-a-powerful-new-way-to-build-knowledge-graphs-with-llms)
10. [iText2KG — Incremental Knowledge Graph Construction with LLMs (arXiv 2409.03284 / GitHub AuvaLab/itext2kg)](https://arxiv.org/abs/2409.03284)
11. [Graphiti — Temporal knowledge graphs for agents (Zep; bi-temporal edges)](https://blog.getzep.com/graphiti-knowledge-graphs-for-agents/)
12. [rustworkx — A High-Performance Graph Library for Python (JOSS) incl. NetworkX comparison](https://arxiv.org/pdf/2110.15221)
13. [Kùzu — embedded property graph DB; repo archival / Apple acqui-hire analysis](https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/)
14. [RDFLib — Python RDF library (rdflib.dev)](https://rdflib.dev/)
15. [LinkML — An Open Data Modeling Framework (GigaScience 2025 / linkml.io)](https://linkml.io/)
16. [pySHACL — SHACL validator for Python (GitHub, RDFLib/pySHACL)](https://github.com/RDFLib/pySHACL)
17. [Splink — probabilistic record linkage / entity resolution (GitHub, moj-analytical-services/splink)](https://github.com/moj-analytical-services/splink)
18. [DeepEval — the LLM evaluation framework ("Pytest for LLMs")](https://deepeval.com/blog/deepeval-alternatives-compared)
19. [Docling vs LlamaParse vs Unstructured vs MarkItDown — document parser comparison (2025/2026)](https://blazedocs.io/blog/best-pdf-parser-for-rag)
