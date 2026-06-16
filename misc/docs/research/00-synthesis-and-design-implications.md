# 00 — Synthesis & Design Implications for creel

> This document is the bridge from the twelve research reports (`01-*.md` … `12-*.md`)
> and the vision brief (`starter -- source-to-graph-engine_core-description.md`) to
> implementation. It is **decisive**: it makes choices, records the alternatives it
> rejects (so they can be revisited), and sketches the concrete Python interfaces and
> package layout. It is intended to seed GitHub issues and the project's `CLAUDE.md`.
>
> Where a claim needs justification, it points to the owning report (e.g. `[R01]`,
> `[R08]`). The "Reading map" at the end gives one line per report.

---

## Executive summary

creel is a **general, AI-powered source-to-graph extraction engine**: a single
parameterized facade `extract(sources, graph_spec, extractors) -> graph` that reads
heterogeneous sources, conforms them to a caller-supplied grammar of typed node-types
and edge-types, and emits a clean, auditable, typed property graph as the single source
of truth. Persistence, query, annotation, and rendering are *downstream* — enabled by
the core, never implemented in it.

The twelve reports converge, with very little tension, on one coherent architecture:

1. **Internal model = Labeled Property Graph (LPG)** with first-class, identity-bearing,
   attribute-carrying edges. This is the *only* model where creel's defining requirement
   — funding amounts and indicator values living *on edges* — is native rather than a
   workaround `[R01][R03][R06][R09]`. RDF-star is an *export*, not the core, justified by
   the provably-lossless LPG↔RDF-star mapping `[R01]`.

2. **Grammar authored in LinkML**, used as the single source of truth, from which
   JSON Schema + Pydantic v2 (runtime validation) and all interop artifacts (JSON-LD
   `@context`, SHACL, GQL/Cypher DDL) are *generated* `[R02]`. LinkML is the only surveyed
   language that is human-writable, models edges as first-class typed objects, expresses
   every constraint creel names, and compiles to everything else. **LinkML is an authoring
   convenience and a generation engine, not a core runtime dependency** — see Dependency
   posture.

3. **Canonical output = creel-owned, versioned, property-graph node-link JSON**, a
   deliberate superset of JGF v2 / PG-JSON, with **stable string IDs on every node AND
   every edge**, deterministic sorted serialization (git-diffable), and three physically
   separated layers joined on demand: graph-definition, instance graph, and
   extraction/verification/provenance metadata `[R03][R06][R09]`.

4. **Extraction = one `Extractor` Protocol** (a callable strategy) dispatched per element
   across three families — LLM/NL-description (default, via constrained decoding), query
   (SQL via DuckDB for tables, Mongo-filter + JMESPath for JSON), and pattern/function
   (regex or any `source -> value`). The grammar enforces *shape only*; all value-level
   constraints (ranges) and faithfulness checks are pushed into a separate verification
   pass `[R04][R12]`.

5. **Auditability is structural, not bolted-on**: every element carries a separable
   "evidence record" (PROV-lite provenance + Web-Annotation-style grounding selector +
   method-tagged confidence + review status), stored in a sidecar keyed by element ID
   `[R07]`.

6. **Evaluation = one `Verifier` Protocol** mirroring the extractor pattern, with a kind
   taxonomy paralleling the node/edge taxonomy and an `llm_rubric` (G-Eval) default
   seeded from each element's own schema description `[R08]`.

7. **Tiny core, everything else an optional extra**: core depends on roughly
   `pydantic`, `jsonschema`, `networkx`, and a thin LLM-client seam — *no provider SDK
   pinned, no opinionated KG pipeline, and explicitly not Kùzu* (archived Oct 2025)
   `[R05][R06]`.

8. **uv-workspace monorepo**: `creel-core` (facade, Protocols, registry, join) separate
   from `creel-unhcr` (the ESA taxonomy + bindings as data), proving the layer-separation
   design by construction `[R12]`.

The first consumer, **UNHCR ESA**, ships as a bundled `unhcr-rbm` grammar that reuses the
COMPASS results taxonomy and the IATI indicator/transaction data model attribute-for-attribute
`[R11]`, so the bundled schema is faithful and interoperable out of the box.

---

## Cross-cutting design decisions

Each decision below states **the decision**, **the rationale**, and **the alternatives
rejected**. They are deliberately concrete so they can become issues and be revisited.

### D1 — Internal data model is a Labeled Property Graph with first-class typed edges

- **Decision.** The in-memory and conceptual model is an LPG: nodes and edges each have a
  stable identity, one or more type labels (a path in a recursively-subdivided taxonomy),
  and a typed attribute bag. Edges carry their own typed attributes and have their own
  identity, so parallel edges of the same type between the same endpoints (two different
  fundings) are distinguishable. `networkx.MultiDiGraph` is the default in-memory carrier.
- **Rationale.** creel's load-bearing requirement is *attributes on edges* (funding
  amounts on donor→project, indicator values on output→outcome). LPG is the only model
  where this is native, with distinct edge identity and queries that terminate in time
  proportional to graph size `[R01][R06]`. Every surveyed GraphRAG/KB downstream consumes
  an LPG shape `[R09]`.
- **Rejected.** *Plain RDF triples* (cannot attach attributes to a bare predicate without
  reification / n-ary intermediate node — verbose, poorly supported) `[R01][R03]`.
  *Hypergraph as the primary model* (genuinely n-ary but lacks mature standards, query
  language, tooling) — instead, treat an attributed edge and a reified relation-node as
  interchangeable renderings via a normalization toggle `[R01]`. *RDF-star as the core* —
  kept as an export only `[R01][R06]`.

### D2 — RDF-star and JSON-LD are losslessly-mappable export targets, not the source of truth

- **Decision.** Constrain the internal LPG to the RDF-star-losslessly-mappable subset
  (per Hartig/PREC). RDF-star, JSON-LD `@context`, SHACL, and Cypher/GQL DDL are all
  **generated export adapters**, never authoring surfaces. Reserve `rdf:reifies` /
  triple-term semantics for the export layer.
- **Rationale.** The LPG↔RDF-star transformation is provably lossless `[R01]`, so creel
  gets RDF interoperability as an export rather than paying for it as a structural tax.
  Closed-world "validate this extracted graph" is the right posture for an auditable
  engine; OWL's open-world entailment is the wrong posture `[R02]`.
- **Rejected.** Authoring in SHACL/OWL/PG-Schema (no mainstream Python tooling for
  PG-Schema; OWL is a reasoner not a validator) `[R02]`. Making JSON-LD the canonical
  form (context indirection hurts git-diffability) `[R03]`.

### D3 — Grammar authored in LinkML; validation layer generated from it

- **Decision.** The graph *grammar* (node-classes, edge-classes via
  `represents_relationship: true`, enums, numeric ranges, cardinality, `is_a` + `mixins`
  inheritance) is authored as a LinkML schema and treated as the single source of truth.
  From it, creel **generates** the instance-validation layer (JSON Schema + Pydantic v2)
  and all interop artifacts. There is never a second source of truth.
- **Rationale.** LinkML is the only surveyed language that is human-writable, models edges
  as first-class typed objects, expresses every constraint creel names, *and* compiles to
  JSON Schema, Pydantic, SHACL, OWL, SQL, GraphQL, and JSON-LD `[R02]`. It is the canonical
  precedent for creel's "single source of truth + multi-target codegen" `[R05]`. SPIRES/OntoGPT
  — the closest structural blueprint to creel — drives its whole extraction from a LinkML
  schema `[R04][R05]`.
- **Rejected.** *Authoring directly in JSON Schema or Pydantic* (no native graph/edge/taxonomy
  notion; you model those by convention) `[R02]`. *PG-Schema as the authoring surface*
  (best conceptual reference for the output model, but no mainstream Python tooling —
  keep as an export/reference target) `[R02]`.
- **Caveat / open question.** LinkML's edge model is reification-by-convention (role-slots),
  not a native LPG primitive; cross-edge participation constraints are weaker than
  PG-Schema's. Acceptable for "produce + validate a JSON graph"; revisit if in-database
  graph-integrity enforcement is ever needed `[R02]`. Also: whether LinkML is a *build-time*
  generation dependency or a runtime-optional extra is decided in Dependency posture (it is
  build/dev-time + optional, never required to *run* a pre-generated grammar).

### D4 — Canonical JSON: creel-owned, versioned, stable IDs on nodes AND edges, three separable layers

- **Decision.** Define creel's own canonical JSON with an explicit `$schema` URL and a
  `version` field, shaped as a deliberate superset of JGF v2 / PG-JSON: nodes as an
  id→object map, edges as objects each with a **required stable string `id`**,
  `source`/`target`, `relation`/`type`, and an `attributes` bag. Serialize with sorted
  keys and id-sorted element arrays for one-line git diffs. Physically separate three
  layers, joined on demand by element id:
  1. **graph-definition** — taxonomy + typed-attribute grammar (the generated JSON Schema);
  2. **instance graph** — nodes/edges with values (the canonical emit);
  3. **extraction/verification/provenance metadata** — the evidence sidecar (D8).
- **Rationale.** No off-the-shelf format satisfies all four hard constraints (edge
  attributes, typed schema with enums/ranges, standard provenance, git-diffability)
  simultaneously `[R03]`. Stable edge IDs are non-negotiable for parallel edges,
  provenance anchoring, deterministic diffs, and every downstream incremental-update /
  entity-resolution system `[R03][R09]`. The PG-JSON data model (multi-label, list-valued
  properties, first-class edges) is an almost exact structural match and already has
  converters to Neo4j/Neptune/PGX `[R06]`.
- **Rejected.** *Adopting JGF/NetworkX node-link verbatim* (no schema layer, no required
  edge IDs, no provenance) `[R03]`. *XML formats (GraphML/GEXF)* (typed-attribute schemas
  but verbose, weak git-diff targets, no enum/range) `[R03]`. *DOT as data interchange*
  (presentation language, lossy for typed data) `[R03]`.

### D5 — One `Extractor` Protocol; three strategy families; route by source type

- **Decision.** A single `runtime_checkable` `Extractor` Protocol — a callable
  `extract(ctx: ExtractionContext) -> Extraction`. Three built-in families implement it:
  - **LLM / NL-description** (default): compile the element schema to JSON Schema, run
    constrained-decoding structured output (default adapter targets Anthropic Claude
    Structured Outputs); read the schema's `description` fields as the LLM instruction so
    "schema-as-extractor" is literally true.
  - **Query**: parameterized SQL via DuckDB for tables; a Mongo-style filter document +
    JMESPath projection for JSON. Query-specs are **pure data**, validated against a schema,
    serialized alongside the extracted element — never raw engine strings.
  - **Pattern / function**: stdlib `re` or any `Callable[[Source], Value]`.
  Dispatch routes by source type *before* strategy selection; prefer query/pattern over
  LLM whenever structure allows.
- **Rationale.** The 2024–2026 SOTA has converged on schema-guided extraction +
  constrained decoding + chunk/map/reduce + grounding `[R04]`. Exploiting a structured
  source's own schema (text-to-SQL, Mongo projection) is cheaper, faster, and more
  auditable than asking an LLM to transcribe values `[R04][R06]`. Strategy-as-callable-Protocol
  is the most Pythonic strategy pattern (structural subtyping, composition over inheritance)
  `[R12]`. Pure-data query-specs are sandboxable and injection-safe `[R06]`.
- **Rejected.** *LangChain `LLMGraphTransformer` as the engine* (all properties string-typed
  and global, not per-edge-type) `[R04]`. *Letting extractors carry arbitrary engine strings*
  (injection surface, couples to a runtime) `[R06]`. *ABC class hierarchies for strategies*
  (reserve classes for stateful controllers only) `[R12]`.

### D6 — The grammar enforces shape only; value-level constraints live in verification

- **Decision.** Treat constrained decoding / structured outputs as enforcing **shape**
  (types, enums, required fields, string formats) only. Enforce numeric ranges,
  `multipleOf`, and string length **post-decode** with Pydantic/Instructor validators and
  auto-retry, as a first-class, separately-pluggable verification step.
- **Rationale.** Cross-verified across XGrammar-class backends and Anthropic Structured
  Outputs: grammars explicitly do NOT enforce numeric ranges or string length `[R04]`.
  Funding amounts and indicator values on edges are range-constrained and central to the
  UNHCR case — trusting the grammar for them would be a silent correctness bug `[R04]`.
- **Rejected.** *Assuming JSON Schema `minimum`/`maximum` are honored by the decoder*
  (they are not) `[R04]`.

### D7 — Physically separate graph-definition from extraction/verification metadata (ECS join)

- **Decision.** Two stores keyed by the same element id: `GraphSpec` (definition / SSOT)
  and `ExtractorBindings` (extraction + verification metadata). A pure
  `join(spec, bindings) -> ResolvedPlan` equijoin produces the resolved extraction plan at
  run time. When an element has *no* binding, fall back to schema-as-extractor: synthesize
  an NL description from the attribute schema. Edges are first-class entities in all layers
  (own attribute schema, own binding, own verifier) — never modeled as a property of nodes.
- **Rationale.** This is creel's most consequential, most posture-specific decision; the
  Entity-Component-System / data-oriented model (entities as ids, components stored
  separately, joined by equijoin) is the precise formalization `[R12]`. It delivers reuse
  without duplication (author the UNHCR taxonomy once; a new source set ships only a new
  binding table), progressive disclosure (bindings are additive overrides), and a lean
  canonical output (heavy metadata is a sidecar) `[R12]`. The nanopublication pattern
  independently validates physical-separation-with-join-by-id `[R07]`.
- **Rejected.** *One fat object per element* (couples grammar to extraction, blocks reuse,
  bloats canonical output) `[R12]`.

### D8 — Provenance: a separable evidence record per element (provenance + grounding + confidence)

- **Decision.** Attach to every node, edge, AND attribute value a small JSON evidence
  record in a sidecar keyed by stable element id, with three blocks:
  - **provenance** — PROV-lite + PAV as plain JSON keys: `derived_from`, `generated_by`
    (strategy + extractor id), `attributed_to` (model id+version or human id),
    `generated_at`, `version`.
  - **grounding** — one or more Web-Annotation-style selectors with a `type` discriminator:
    `TextQuoteSelector` (exact + prefix + suffix) primary for prose, `TextPositionSelector`
    secondary, fragment/cell selectors for tables, JSONPath/Mongo predicate for JSON.
  - **confidence** — method-tagged (`deterministic` | `logprob` | `verbalized` |
    `self_consistency`) + score + a `verified` faithfulness flag + `review_status`
    (`auto` | `needs_review` | `confirmed` | `rejected` | `corrected`).
- **Rationale.** Auditability decomposes into three orthogonal questions — where from
  (provenance), where exactly (grounding), how sure (confidence) — each mapping to a mature
  standard `[R07]`. Use only the lightweight cores of PROV-O/PAV and the Web Annotation
  Model as plain JSON (progressive disclosure), with optional PROV-O/JSON-LD export.
  Deterministic strategies get `confidence=1.0 method=deterministic`; LLM strategies default
  to verbalized confidence, escalate to self-consistency for high-stakes elements `[R07]`.
  A cheap deterministic *faithfulness gate* (does the value actually occur in the resolved
  span?) turns the anchor into a verifier `[R07]`.
- **Rejected.** *Full RDF/OWL provenance stack imposed on the JSON* (too heavy; export only)
  `[R07]`. *Bare confidence scores compared across methods* (record the method; never compare
  incommensurable scores) `[R07]`. *Destructive human-review overwrites* (record review as
  new provenance) `[R07]`.

### D9 — One `Verifier` Protocol; kind taxonomy parallels node/edge taxonomy; `llm_rubric` default

- **Decision.** A single `Verifier` Protocol —
  `verify(actual, expected, *, context) -> {score in [0,1], passed, reason, details}` — the
  evaluation-time dual of `Extractor`. Ship a verifier-kind taxonomy: `exact`/`normalized`,
  `numeric_tolerance` (amounts/indicators), `set_match` + `graph_match` (decomposable partial
  credit, not all-or-nothing triples), `schema_constraint` (property-based, no gold value),
  `semantic_similarity` (embedding/NLI), `llm_rubric` (G-Eval), and `composite` (weighted
  sub-verifiers). Verifier-spec is physically separate from graph-spec, keyed by taxonomy
  path with a default-resolution chain (element-specific → type-default → global default =
  `llm_rubric` seeded from the element's description). Run cheap deterministic verifiers
  first; fall through to semantic/LLM only on failure or for free-text.
- **Rationale.** The entire eval ecosystem (Inspect, DeepEval, OpenAI Graders, promptfoo,
  Ragas) has converged on this exact shape — a named comparison returning a `[0,1]` score
  + reason `[R08]`. Schema-description-as-verifier is the natural dual of
  schema-as-extractor. Bias mitigation is baked in by construction: **judge model ≠
  extractor model**, randomized rubric option order, mandatory stored `reason` `[R08]`.
- **Rejected.** *Whole-triple all-or-nothing F1 only* (too strict; use decomposable partial
  credit) `[R08]`. *Comparing without canonicalization first* (inflates FP/FN) `[R08]`.
  *Reporting raw judge-human agreement* (report chance-corrected Cohen's κ) `[R08]`.

### D10 — Dependency posture: tiny core, commodity bought behind seams

- **Decision.** Core depends on only `pydantic` (v2), `jsonschema`, `networkx`, and a thin
  LLM-client abstraction with **no provider SDK pinned**. Everything else is an optional
  extra behind the `Extractor`/`Verifier`/storage/`Renderer` seams. `dataclasses`
  internally (hot paths), Pydantic v2 only at the LLM/IO boundary and for untrusted input.
- **Rationale.** No single library is creel; opinionated pipelines own the graph model and
  hide extraction logic — the opposite of creel's auditable, pluggable design `[R05]`. Buy
  primitives behind seams; never adopt a pipeline as the spine `[R05]`. Structured output is
  now a *provider capability*, so it belongs behind an adapter, not married as a dependency
  `[R04][R05]`.
- **Rejected (hard constraints).** *Depending on Kùzu in core* (repo archived Oct 2025)
  `[R05][R06]`. *igraph as a core dep* (GPL) `[R05]`. *Coupling core to GraphRAG/LlamaIndex/
  Graphiti* (they own the graph model) `[R05]`. *Pinning a provider SDK in core* `[R05]`.
  See the full extras table in **Dependency posture** below.

### D11 — Orchestration is thin hand-composed callables; frameworks are downstream adapters

- **Decision.** Implement extraction as a `map` of resolved `Extractor` callables over
  elements (embarrassingly-parallel fan-out) plus a graph-assembly join. Cache expensive LLM
  calls on a deterministic key `hash(prompt, model, params, element_id, source_fingerprint)`
  with a persistent exact-match cache injected via context behind a `Cache` Protocol (no-op
  default). Leave a clean seam so Hamilton (lineage/caching) or Prefect (scheduling) can wrap
  creel downstream without invading core.
- **Rationale.** Extraction over a graph_spec is mostly fan-out + join, not a deep DAG; thin
  composition beats adopting a micro- or macro-orchestrator in core `[R12]`. Exact-match
  deterministic caching reinforces reproducibility/auditability; semantic caches are
  anti-auditability `[R12]`.
- **Rejected.** *Hamilton/Prefect in core* (couples the engine before the dependency-graph
  shape is known) `[R12]`. *GPTCache-style semantic caching in core* (approximate hits break
  reproducibility) `[R12]`.

### D12 — Plugin discovery: decorator registry now, entry points for third parties, pluggy deferred

- **Decision.** A decorator/dict registry for in-tree built-in strategies; `importlib.metadata`
  entry points (groups `creel.extractors`, `creel.verifiers`, `creel.renderers`) for
  third-party packages, lazily `.load()`-ed. Defer pluggy until a single extension point
  genuinely needs N cooperating implementations.
- **Rationale.** creel's extractor binding is fundamentally 1:1 (one chosen strategy per
  element), which makes pluggy's 1:N hook loop premature; registry + entry points is the
  right fit `[R12]`. Pluggy could later pay off only for *verification*, where multiple
  verifiers may weigh in on one element `[R12]`.
- **Rejected.** *pluggy in core now* (premature complexity) `[R12]`.

### D13 — Monorepo: uv workspace, core separate from the UNHCR consumer

- **Decision.** Lay out the repo as a uv-workspace monorepo with `src/` layout:
  `creel-core` (facade, Protocols, registry, join, dataclasses, canonical JSON,
  generated-validation glue) separate from `creel-unhcr` (the ESA/COMPASS taxonomy + IATI
  bindings as data + a thin package). Optionally split the default LLM strategy into its
  own member. Graduate downstream examples (persistence, render) into their own consumer
  packages as they mature.
- **Rationale.** A uv workspace gives one repo / one lockfile / one venv with editable
  internal deps, ideal for co-locating core and the UNHCR consumer while keeping them
  separately versioned `[R12]`. Keeping consumer-specific taxonomies out of core *proves*
  the layer-separation design by construction `[R12]`. (The starter's packaging strategy
  asks for exactly this: monorepo now, graduate consumers later.)
- **Rejected.** *One flat package forever* (current state — fine for a spike, but does not
  demonstrate the core/consumer separation that is creel's whole thesis). *Polyrepo from
  day one* (premature; loses the single-lockfile editable-dev ergonomics) `[R12]`.

### D14 — Bundle `unhcr-rbm` as the first grammar: reuse COMPASS + IATI verbatim

- **Decision.** Ship a bundled `unhcr-rbm` grammar in `creel-unhcr` whose node/edge spine is
  the COMPASS results taxonomy (4 impact / 16 outcome / 5 enabling areas; impact/outcome/output
  levels; donors, projects, cross-cutting areas) and whose indicator-bearing and funding-bearing
  **edges** adopt the IATI Activity Standard data model attribute-for-attribute: `measured-by`
  carries `(measure, ascending, baseline{value,year}, target{value,date}, actual{value,period},
  dimensions[])`; `funds` carries IATI transaction shape (amount, currency, commitment vs
  disbursement, value_date). Cross-cutting areas are a dual-idiom node + a scored `addresses`
  edge carrying both the OECD-DAC `0/1/2` marker and a categorical AGD/protection tag. Make
  `target` optional and level-aware (impact indicators have no target by design).
- **Rationale.** These are the de facto/de jure standards the UNHCR ESA documents are written
  against; reuse guarantees a faithful, auditable schema and free interoperability with the
  IATI/OECD donor-data ecosystem `[R11]`. The three synthetic test docs (prose donor agreement,
  results matrix table, indicator table) exercise all three extractor families against one
  shared spec and catch schema-join regressions early `[R11]`.
- **Rejected.** *Hand-rolling a bespoke UNHCR schema* (loses interoperability and faithfulness)
  `[R11]`. *Requiring a target on every indicator* (would reject valid COMPASS impact data)
  `[R11]`.
- **Caveat.** Re-verify the exact wording/numbering of the 16 outcome and 5 enabling areas
  against the current official GRF codelist before production (the UNHCR site blocks automated
  fetch) `[R11]`.

### D15 — Rendering: a three-layer annotated-graph contract + one Renderer Protocol; no renderers in core

- **Decision.** Core ships (a) a three-layer "annotated graph" contract — graph layer
  (keys near-isomorphic to Cytoscape.js `data` objects), a standoff annotation overlay keyed
  by element id (W3C Web Annotation shape: Body + Target + role/provenance), and optional
  selector→style presentation hints; (b) a `creel.view` projection family (`to_dot`,
  `to_mermaid`, `to_node_edge_records`, `to_table`, `to_sections`); and (c) a single
  `GraphRenderer` Protocol. **All concrete renderers live in consumer packages**, never in
  core. DOT and Mermaid are the zero-config "schema-as-renderer" defaults; Cytoscape.js is the
  reference interactive view; Sigma.js is the large-graph escape hatch.
- **Rationale.** Every mainstream renderer consumes a node/edge list + opaque attribute bag;
  the contract is near-invariant `[R10]`. Standoff annotation (target by stable element id, not
  positional selector) attaches insight without mutating the SSOT, exactly parallel to creel's
  definition/extraction split `[R10]`. Media generators want a *flattened view*, not the graph,
  hence the projection layer `[R10]`.
- **Rejected.** *Shipping renderers in core* (keeps core an extraction engine; renderers are DI
  plugins) `[R10]`. *Positional/offset annotation selectors over the graph* (graph elements have
  stable IDs; target by ID to dodge standoff fragility) `[R10]`.

---

## Recommended architecture

### Layers / modules (in `creel-core`)

```
creel/
  facade.py          # extract() — the single public entry point
  spec/              # the grammar layer (graph-definition / SSOT)
    model.py         #   GraphSpec, NodeType, EdgeType, AttrSchema (dataclasses)
    linkml.py        #   optional: load LinkML -> GraphSpec; generate JSON Schema/Pydantic
    validate.py      #   jsonschema/Pydantic validation of instance graphs
  bindings.py        # ExtractorBindings + Verifier bindings (metadata layer)
  join.py            # pure equijoin: join(spec, bindings) -> ResolvedPlan
  extract/
    protocol.py      #   Extractor Protocol, ExtractionContext, Extraction
    llm.py           #   NLExtractor (constrained decoding; schema-as-extractor default)
    query.py         #   QueryExtractor (DuckDB SQL; Mongo-filter + JMESPath)
    pattern.py       #   PatternExtractor (regex / Callable)
    registry.py      #   decorator registry + entry-point loader
    cache.py         #   Cache Protocol (no-op default), deterministic key
  verify/
    protocol.py      #   Verifier Protocol, VerdictScore
    kinds.py         #   exact/normalized/numeric_tolerance/set_match/graph_match/...
    rubric.py        #   llm_rubric (G-Eval), judge!=extractor, randomized order
  evidence.py        # provenance + grounding selectors + confidence (sidecar records)
  graph/
    model.py         #   in-memory LPG (networkx.MultiDiGraph wrapper), stable IDs
    canonical.py     #   to/from creel canonical JSON ($schema, version, sorted)
  view/              # projections for renderers (NOT renderers themselves)
    projections.py   #   to_dot, to_mermaid, to_node_edge_records, to_table, to_sections
  render.py          # GraphRenderer Protocol + annotated-graph contract (no concrete renderers)
  export/            # optional adapters (lazy-imported): networkx pivot, jgf, cytoscape,
                     # graphml, gexf, rdf_star/jsonld, neo4j_cypher, llamaindex, graphrag_parquet
```

### Key Python interfaces (sketches)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Any, Iterable, Mapping, Sequence


# ---- The facade -----------------------------------------------------------

def extract(
    sources: "SourceBundle",
    graph_spec: "GraphSpec",
    extractors: "ExtractorBindings | None" = None,
    *,
    verifiers: "VerifierBindings | None" = None,
    cache: "Cache | None" = None,
    on_missing_binding: str = "schema_as_extractor",  # default progressive-disclosure path
) -> "Graph":
    """Read `sources`, populate the graph described by `graph_spec` using the
    chosen `extractors` (per element), and return a typed LPG (the SSOT).

    Args beyond the 3rd are keyword-only. `extractors`/`verifiers` are physically
    separate metadata layers, equijoined to `graph_spec` by element id at run time.
    """


# ---- Grammar (graph-definition / SSOT) ------------------------------------

@dataclass(frozen=True)
class AttrSchema:
    name: str
    range: str                              # "string"|"integer"|"decimal"|<enum>|<class>
    required: bool = False
    multivalued: bool = False
    enum: Sequence[str] | None = None       # constrained value-set
    minimum: float | None = None            # range constraints (enforced in verify, not decode)
    maximum: float | None = None
    pattern: str | None = None
    description: str | None = None          # doubles as the schema-as-extractor instruction


@dataclass(frozen=True)
class ElementType:
    """A node-type or edge-type; a path in a recursively-subdivided taxonomy."""
    id: str                                 # dotted taxonomy path, e.g. "result.outcome"
    is_a: str | None = None                 # single-inheritance parent
    mixins: Sequence[str] = ()              # multiple-inheritance
    attributes: Mapping[str, AttrSchema] = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeType(ElementType):
    represents_relationship: bool = True
    # subject/object roles refer to node-type ids; edges are FIRST-CLASS (own id, own attrs)


# ---- Extraction strategy (the core contract) ------------------------------

@dataclass(frozen=True)
class ExtractionContext:
    element_id: str                         # address in the taxonomy
    element_type: ElementType               # typed attributes for this node/edge type
    sources: "SourceBundle"
    cache: "Cache"
    services: Mapping[str, Any] = field(default_factory=dict)  # injected llm client, resolver...


@dataclass(frozen=True)
class Extraction:
    value: Any                              # node(s)/edge(s)/attribute value(s)
    provenance: "Provenance"                # source span(s) -> auditability
    confidence: "Confidence | None" = None


@runtime_checkable
class Extractor(Protocol):
    def extract(self, ctx: ExtractionContext) -> Extraction: ...


# ---- Verification (the evaluation-time dual) ------------------------------

class VerdictScore(Protocol):               # TypedDict in practice
    score: float                            # normalized [0, 1]; 1.0 == fully correct
    passed: bool                            # score >= threshold
    reason: str                             # auditable explanation (mandatory for LLM judges)
    details: dict                           # per-component scores, matched pairs


@runtime_checkable
class Verifier(Protocol):
    def verify(self, actual: Any, expected: Any, *, context: ExtractionContext) -> VerdictScore: ...


# ---- Caching (deterministic, exact-match, pluggable) ----------------------

@runtime_checkable
class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any) -> None: ...


# ---- Downstream rendering (no concrete renderers in core) -----------------

@runtime_checkable
class GraphRenderer(Protocol):
    name: str
    output_media_type: str
    consumes_annotations: bool
    def render(self, graph: "AnnotatedGraph", *, options: dict | None = None) -> "RenderArtifact": ...
```

### Data flow

```
sources ──┐
graph_spec (LinkML → GraphSpec) ──► join(spec, bindings) ──► ResolvedPlan
extractors (ExtractorBindings) ──┘                                │
                                                                  ▼
                              per element: dispatch Extractor (LLM | query | pattern)
                                                                  │
                                                  ┌───────────────┼───────────────┐
                                                  ▼               ▼               ▼
                                          shape-valid value   provenance      confidence
                                                  │           (grounding)     (method-tagged)
                                                  ▼
                                   verify pass: range/constraint (Pydantic) +
                                   faithfulness gate (value-in-span) + Verifier kinds
                                                  │
                                                  ▼
                          assemble LPG (stable IDs on nodes & edges)  ── SSOT
                                                  │
                  ┌───────────────────────────────┼───────────────────────────────┐
                  ▼                                ▼                                ▼
        canonical JSON ($schema, version,   evidence sidecar              export adapters
        sorted, git-diffable)               (keyed by element id)         (rdf-star, cypher,
                                                                           llamaindex, ...)
```

---

## Dependency posture

**Core (`creel-core`) — minimal, permissive, no pipeline, no provider SDK.**

| Dependency | Role | Why core |
|---|---|---|
| `pydantic` (v2) | typed attributes, runtime validation at IO boundary, JSON-Schema export | universal typed-attribute backbone; drives constrained-decoding providers `[R05][R12]` |
| `jsonschema` | validate canonical graph + grammar-derived instance schema | most universally-tooled, diffable JSON validation layer `[R03][R05]` |
| `networkx` | in-memory LPG carrier (MultiDiGraph), edge attribute dicts | first-class typed edges for free; pivot to GraphML/GEXF/GML writers `[R03][R05]` |
| thin LLM-client seam | abstract the LLM call; **no provider SDK pinned** | structured output is a provider capability behind an adapter `[R04][R05]` |

`dataclasses` (stdlib) for internal records / hot paths; Pydantic only at edges `[R12]`.

**Optional extras (each behind a Protocol/storage seam, lazily imported).**

| Extra | Brings | Purpose |
|---|---|---|
| `creel[llm]` | `instructor` (+ optional `anthropic`/`openai`) | default LLM-extraction adapter; retry-on-validation `[R04][R05]` |
| `creel[constrained]` | `outlines` | self-hosted hard-guarantee constrained decoding `[R05]` |
| `creel[query]` | `duckdb`, `jmespath` | SQL over tables; JSON projection `[R06]` |
| `creel[ingest]` | `docling` and/or `markitdown` | document parsing `[R05]` |
| `creel[semantic]` | `linkml`, `rdflib`, `pyshacl` | LinkML authoring/generation + RDF/SHACL export `[R02][R05]` |
| `creel[graphdb]` | `neo4j` driver, `pyoxigraph` (RDF-star), `rustworkx` (perf) | persistence/export targets `[R05][R06]` |
| `creel[er]` | `splink` | entity resolution (MIT, DuckDB-embeddable) `[R05]` |
| `creel[eval]` | `deepeval` (or `inspect`) | verifier backend + CI gating `[R05][R08]` |
| `creel[pipelines]` | `graphrag` / `llama-index` | interop adapters only, never the spine `[R05][R09]` |
| `creel[render]` | per-target (cytoscape/pptx/quarto…) — ideally their own consumer packages | rendering `[R10]` |

**Hard "do not" constraints.** Do not depend on **Kùzu** in core (repo archived Oct 2025)
`[R05][R06]`; do not take **igraph** as a core dep (GPL) `[R05]`; do not couple core to any
opinionated KG pipeline (GraphRAG/LlamaIndex/Graphiti own the graph model and hide extraction)
`[R05]`; do not pin a provider SDK in core `[R05]`.

---

## The evaluation / verifier subsystem (distilled from R08)

The verifier subsystem is the evaluation-time mirror of the extractor subsystem and reuses
the same postures (strategy pattern, physical separation, progressive disclosure, auditability).

- **One protocol.** `verify(actual, expected, *, context) -> {score∈[0,1], passed, reason,
  details}`, structurally compatible with Inspect `Score` and DeepEval `BaseMetric` so either
  can be a pluggable backend.
- **Kind taxonomy parallel to the node/edge/attribute taxonomy:**
  - `exact` / `normalized` — auditable default for enums and IDs (lowercase/trim/unit-normalize).
  - `numeric_tolerance` (abs/rel) — for funding amounts and indicator values on edges.
  - `set_match` + `graph_match` — set-based P/R/F1 over **canonicalized** nodes/edges with
    **decomposable partial credit** (credit head/relation/tail separately; optional GED/fuzzy
    alignment for hard cases). Canonicalize before comparing.
  - `schema_constraint` — property-based invariants over the produced graph (types, enums,
    ranges, required edges); runs with **no gold value** (e.g. "every `funding_amount` is a
    positive number with a currency"; "every project links to ≥1 objective").
  - `semantic_similarity` — embedding or NLI/bidirectional-entailment for free-text fields,
    with explicit threshold (similarity ≠ equivalence — flagged).
  - `llm_rubric` (G-Eval) — the robust default fallback (below).
  - `composite` — weighted combination of sub-verifiers with named sub-metrics (promptfoo shape).
- **`llm_rubric` is first-class and the default fallback.** Specified purely in natural
  language, seeded automatically from each element's own schema `description`
  (schema-description-as-verifier). Executed via G-Eval (auto-generate CoT eval steps from the
  criterion, form-fill a normalized score with the gold answer in context). **Bias mitigation by
  construction:** (a) judge model ≠ extractor model; (b) randomize rubric option order / average
  over permutations; (c) mandatory stored `reason`.
- **Physical separation + default-resolution chain.** Verifier-spec is keyed by taxonomy path,
  joined to graph-spec on demand: element-specific → type-default → global default
  (`llm_rubric` from description). The same corpus can be re-scored under strict vs lenient
  policies with the SSOT preserved.
- **Corpus layout.** A corpus item = `{sources, expected_graph, verifier_overrides?}`. Because
  verifiers attach by taxonomy path, most items need zero per-item config. Scoring rolls
  per-element scores up to per-type and per-graph P/R/F1 and retains LLM-judge reasons for audit.
- **Operational rules.** Run cheap deterministic verifiers first; fall through to
  semantic/LLM only on failure or for free-text. The deterministic **faithfulness gate** (does
  the value occur within the resolved span?) is wired in as a verifier — a failed check
  downgrades confidence and flags `needs_review`. When validating creel's own judges against
  human labels, report **chance-corrected Cohen's κ**, not raw agreement.

---

## Open questions & deferred decisions

These are deliberately left open and should be revisited with the user before or during
implementation.

1. **LinkML as runtime vs build-time only.** The plan treats LinkML as an authoring +
   generation tool (build/dev-time) with `creel[semantic]` optional at runtime. Confirm the
   core never *requires* LinkML to run a pre-generated grammar — and decide whether creel
   commits generated artifacts (JSON Schema / Pydantic) to the repo or regenerates them.

2. **n-ary indicator readings: edge vs reified node.** An indicator reading is arguably 4-ary
   (output, outcome, value, period/source). D1 makes attributed-edge ↔ reified-relation-node a
   normalization toggle. Decide the *default* rendering for `unhcr-rbm` (`measured-by` edge vs
   a `Reading` node) and whether the toggle is per-spec or per-element `[R01]`.

3. **Repo restructure timing.** The repo is currently a single flat `creel/` package (v0.0.2,
   zero deps). Decide *when* to convert to the uv-workspace `creel-core` + `creel-unhcr` split
   (now, or after a single-package spike) `[R12][D13]`.

4. **Working name.** The vision brief lists candidate names (*Prism*, *Loom*, *Lattice*); the
   package is currently `creel`. Confirm the final name before publishing artifacts/`$schema`
   URLs.

5. **`$schema` URL / hosting.** The canonical JSON references a creel-owned `$schema` URL and
   the JSON-LD `@context` references a creel namespace. Decide the hosting domain and schema
   versioning discipline (SchemaVer ADDITION/REVISION/MODEL) `[R03]`.

6. **Default LLM provider + model in the default adapter.** D5 defaults to Anthropic Claude
   Structured Outputs; the verifier requires judge ≠ extractor. Decide the default judge model
   and confirm provider-agnosticism via Instructor `[R04][R08]`.

7. **Confidence escalation policy.** Per-type thresholds for routing to self-consistency voting
   and to human review (`needs_review`) are policy, not code. Decide defaults and whether they
   live in the grammar, the bindings, or a separate policy file `[R07]`.

8. **Entity resolution / grounding resolver.** Grounding to canonical IDs (lookup table /
   embedding index / annotator) is named as a strategy but its default implementation and the
   dedup cascade (Jaccard → embedding → LLM-adjudication) are unspecified for the UNHCR case
   `[R04][R09]`.

9. **Temporal modeling depth.** Optional `valid_from`/`valid_to` + ingestion timestamps on
   edges and invalidate-don't-delete semantics are flagged for the UNHCR multi-cycle reality.
   Decide whether v1 ships the temporal affordance or defers it `[R09][R11]`.

10. **GRF codelist verification.** Re-verify the 16 outcome / 5 enabling area wording and codes
    against the current official GRF codelist before the `unhcr-rbm` grammar is used in
    production `[R11]`.

---

## Reading map

| Report | One-line pointer to the decisions it justifies |
|---|---|
| `01-knowledge-graph-models.md` | LPG-as-core with first-class typed edges; lossless RDF-star export; SKOS+PG-Schema taxonomy; n-ary toggle → **D1, D2, D7** |
| `02-graph-schema-languages.md` | LinkML as grammar SSOT generating JSON Schema/Pydantic/SHACL/JSON-LD; edges via `represents_relationship` → **D3** |
| `03-graph-serialization-formats.md` | creel-owned versioned property-graph JSON; stable edge IDs; three separable layers; PROV-O field names; git-diffability → **D4, D8** |
| `04-llm-knowledge-extraction.md` | schema-guided constrained-decoding extraction; grammar=shape-only, ranges in verify; SPIRES field-decomposition; route by source type → **D5, D6** |
| `05-oss-tooling-landscape.md` | tiny core (pydantic/jsonschema/networkx + LLM seam); Instructor default; everything else extras; not Kùzu, not pipelines → **D10** |
| `06-graph-databases-query.md` | PG-JSON IR; emitters behind one interface; pure-data query-specs (DuckDB SQL, Mongo+JMESPath); generate Cypher with params → **D4, D5, D10** |
| `07-provenance-auditability.md` | separable evidence record (PROV-lite + Web-Annotation selector + method-tagged confidence + review state); faithfulness gate → **D8** |
| `08-extraction-evaluation-verifiers.md` | one Verifier protocol; kind taxonomy; `llm_rubric`/G-Eval default; judge≠extractor; chance-corrected κ → **D9** |
| `09-graphrag-knowledge-bases.md` | emit LPG JSON with stable IDs + provenance per element; optional `text_for_embedding`; thin downstream adapters → **D4, D8, D10** |
| `10-graph-rendering-media.md` | three-layer annotated-graph contract; standoff annotation by element id; `creel.view` projections; renderers out of core → **D15** |
| `11-rbm-logframe-domain.md` | bundle `unhcr-rbm` reusing COMPASS taxonomy + IATI indicator/transaction model + DAC markers; optional level-aware target → **D14** |
| `12-pluggable-extraction-architecture.md` | Protocol-typed callable strategies; ECS two-table join; registry+entry points (pluggy deferred); thin orchestration; uv-workspace monorepo → **D5, D7, D11, D12, D13** |
