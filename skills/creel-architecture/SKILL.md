---
name: creel-architecture
description: Use when working anywhere inside the creel package internals — the source-to-graph extraction engine. Covers the architecture map (layers/modules), the 15 design decisions D1–D15, the key Protocol interfaces, the canonical JSON contract, the two-layer (grammar vs bindings) join, and where each choice is justified in the research. Trigger when adding/changing core modules, wiring the extract() facade, the graph model, the spec/grammar layer, or canonical JSON; or when a design question needs the authoritative answer.
metadata:
  audience: developers
---

# creel architecture

creel = `extract(sources, graph_spec, extractors) -> graph`. A typed **Labeled
Property Graph** (LPG) is the single source of truth; everything downstream is a
projection. Authoritative design: `misc/docs/research/00-synthesis-and-design-implications.md`
(decisions D1–D15). Roadmap: `misc/docs/design/ROADMAP.md`. Decision log:
`misc/docs/design/DECISIONS.md` — which now includes **D-OP7** (ingestion layer,
report R13), **D-OP8** (extraction granularity = hybrid class-cluster passes,
report R14), **D-OP9** (bidirectional traceability + human annotation/coding as a
first-class contract; 5 additive extensions A1–A5, report R15), and the 2026-06-17
resolutions of the open questions (notably **#14 entity resolution = full cascade**,
required because the real consumer corpus is very messy).

## Module map (single-package spike; uv-workspace split at v0.4 — D-OP3)

```
creel/
  facade.py          # extract() — the only public entry point
  ingest/            # INGESTION layer: files -> Source(s) (D-OP7, R13) [planned]
                     #   route-by-format + quality-gate; Docling default; markdown +
                     #   provenance sidecar (page/cell/char-span/bbox). See creel-ingestion.
  spec/              # GRAMMAR layer = graph-definition / SSOT (D1,D3,D7)
    model.py         #   GraphSpec, NodeType, EdgeType, AttrSchema (frozen dataclasses)
    validate.py      #   validate an instance graph against a GraphSpec
    linkml.py        #   [semantic] LinkML <-> GraphSpec; generate JSON Schema/Pydantic
  bindings.py        # EXTRACTION/VERIFICATION metadata layer (keyed by taxonomy path)
  join.py            # pure equijoin join(spec, bindings) -> ResolvedPlan (D7)
  graph/
    model.py         #   Graph: networkx.MultiDiGraph wrapper, stable IDs on nodes+edges (D1)
    canonical.py     #   to/from creel canonical JSON ($schema, version, sorted) (D4)
  extract/
    protocol.py      #   Extractor Protocol, ExtractionContext, Extraction (D5)
    pattern.py       #   regex / Callable  (the trivial default; brings the facade up)
    query.py         #   [query] DuckDB SQL (tables) + Mongo-filter/JMESPath (json)
    llm.py           #   [llm] schema-as-extractor via constrained structured output
    registry.py      #   decorator registry + entry points (creel.extractors) (D12)
    cache.py         #   Cache Protocol (no-op default), deterministic key (D11)
  verify/            # the EVALUATION-time dual (see creel-eval skill) (D9)
    protocol.py kinds.py rubric.py
  evidence.py        # provenance + grounding selectors + confidence (sidecar) (D8)
  view/projections.py# to_dot/to_mermaid/to_table/... (NOT renderers) (D15)
  render.py          # GraphRenderer Protocol + AnnotatedGraph contract (no concrete renderers)
  export/            # [lazy] networkx, cytoscape, dot, mermaid, rdf_star, neo4j_cypher (D2)
```

## The core contracts (keep these stable; see synthesis §"Key Python interfaces")

- **`extract(sources, graph_spec, extractors=None, *, verifiers=None, cache=None,
  on_missing_binding="schema_as_extractor") -> Graph`** — keyword-only past arg 3.
- **`Extractor` Protocol**: `extract(ctx: ExtractionContext) -> Extraction`.
- **`Verifier` Protocol**: `verify(actual, expected, *, context) -> {score∈[0,1],
  passed, reason, details}`.
- **`Cache` / `GraphRenderer`** Protocols. All `runtime_checkable`; callables, not
  inheritance trees.

## Non-negotiables (= the load-bearing decisions)

- Edges are **first-class** with their own id + attrs (D1). Parallel edges between
  the same endpoints must stay distinguishable — test it.
- Grammar and bindings are **physically separate**, joined by id (D7). Never fuse
  "what the graph is" with "how to extract it" into one object.
- Grammar enforces **shape**; ranges/faithfulness are a **verify** pass (D6).
- Canonical JSON is **deterministic** (sorted keys, id-sorted arrays, stable
  edge ids) — round-trip byte-identity is a tested invariant (D4).
- Core stays tiny; new mechanisms enter via Protocol seams + registry/entry
  points, never by adding a pipeline framework to the spine (D10, D11, D12).

## When the synthesis doesn't answer a question

Make the smallest defensible choice consistent with the load-bearing decisions,
implement it, and append a `D-OP*` entry to `misc/docs/design/DECISIONS.md`
(decision + rationale + rejected alternatives). Don't leave design choices
implicit in code.
