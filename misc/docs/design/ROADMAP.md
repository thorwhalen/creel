# creel — Implementation Roadmap

> Translates the research synthesis
> ([`../research/00-synthesis-and-design-implications.md`](../research/00-synthesis-and-design-implications.md),
> decisions **D1–D15**) into an ordered, milestone-based build plan. Each epic
> maps to a GitHub issue labelled `epic`; each task becomes a child issue. The
> decision log is [`DECISIONS.md`](DECISIONS.md).

## Guiding shape

```
extract(sources, graph_spec, extractors) -> graph        # the facade (the whole point)
        │            │            │            └─ typed LPG, SSOT, canonical JSON
        │            │            └─ ExtractorBindings (metadata layer, joined by element id)
        │            └─ GraphSpec (grammar: node/edge types, typed attrs, taxonomy)
        └─ SourceBundle (prose / tables / json, each maybe schema-carrying)
```

Build **inside-out**: the data model and canonical JSON first (everything is
defined in terms of them), then the join + facade skeleton with a trivial
extractor, then real extractor strategies, then the verifier/eval harness and the
UNHCR corpus, then downstream *contracts* (not implementations).

## Milestones

| Milestone | Theme | Exit criteria |
|---|---|---|
| **v0.1 — Spine** | Grammar + LPG + canonical JSON + validation | `GraphSpec`/`Graph` round-trip through canonical JSON deterministically; instance validation against grammar; `extract()` facade exists end-to-end with the pattern extractor; tests green locally |
| **v0.2 — Extractors** | Strategy layer + bindings/join + evidence | pattern + query (DuckDB/JMESPath) + LLM (schema-as-extractor) strategies; `join(spec, bindings)`; per-element evidence (provenance + grounding + confidence); facade wires them; tests with real sample sources |
| **v0.3 — Evaluation** | Verifier protocol + kinds + corpus runner + UNHCR | `Verifier` protocol; deterministic kinds + `llm_rubric`; corpus runner with roll-up P/R/F1; `unhcr-rbm` grammar + 3 synthetic docs + expected graph + verifier overrides; eval runs green |
| **v0.4 — Downstream contracts** | Export adapters + annotated-graph + renderer/RAG seams | canonical→{networkx, cytoscape, dot/mermaid, rdf-star} export; `AnnotatedGraph` contract + `GraphRenderer`/`view` projections; RAG-readiness affordances; consumer-package split (`creel-unhcr`) |
| **v0.5 — Hardening** | Docs, CI activation, release | README/usage docs; activate wads CI; first intentional PyPI release; monorepo graduation as needed |

---

## EPIC 1 — Project structure & dev ergonomics  `infra`
*Establish the package skeleton the rest of the work slots into. (D13)*

- **1.1** Decide & document the **layout**: start single-package `creel/` with the
  module tree from the synthesis (`spec/`, `extract/`, `verify/`, `graph/`,
  `view/`, `export/`, `bindings.py`, `join.py`, `facade.py`, `evidence.py`,
  `render.py`); record the *when* of the uv-workspace split as a deferred decision
  (Open Q3). **Decision: spike as one package; split at v0.4.**
- **1.2** Add module docstrings to every module (global CLAUDE.md rule); set up
  `creel/__init__.py` facade exports.
- **1.3** Dev tooling: `pytest` config (already in pyproject), `ruff`, a
  `tests/` tree mirroring the package, a `tests/data/` corpus area.
- **1.4** Core dependency wiring in `pyproject.toml`: core = `pydantic`,
  `jsonschema`, `networkx`; optional extras `[llm] [query] [semantic] [graphdb]
  [eval] [render] [ingest]` (D10).
- **1.5** Defer **CI activation** (`.github/workflows/ci.yml` untracked) until
  v0.5; create a tracking note. (Decision log D-OP1.)

## EPIC 2 — Grammar / spec layer (graph-definition SSOT)  `schema` `core`
*The "what we extract" half. (D1, D3, D7)*

- **2.1** `spec/model.py`: frozen dataclasses `AttrSchema`, `ElementType`,
  `NodeType`, `EdgeType`, `GraphSpec`. Recursive taxonomy via `is_a` + `mixins`;
  edges first-class with own attrs + subject/object node-type roles.
- **2.2** Constraint vocabulary on `AttrSchema`: `range` (string/int/decimal/
  bool/date/enum/class), `required`, `multivalued`, `enum`, `minimum`/`maximum`,
  `pattern`, `description` (doubles as the schema-as-extractor instruction).
- **2.3** `spec/validate.py`: validate an instance graph against a `GraphSpec`
  (types known, required attrs present, enums/ranges respected, edge endpoints
  type-correct). Pydantic/jsonschema under the hood.
- **2.4** `spec/linkml.py` *(extra `[semantic]`)*: load a LinkML schema →
  `GraphSpec`; generate JSON Schema + Pydantic from a `GraphSpec`. Edges via
  `represents_relationship: true`. Build-time/optional, never required to run a
  pre-generated grammar (Open Q1).
- **2.5** Tests: construct a small grammar in code; round-trip; validate a
  conforming and a non-conforming instance.

## EPIC 3 — Graph model & canonical JSON  `core` `schema`
*The LPG carrier and the on-disk truth. (D1, D2, D4)*

- **3.1** `graph/model.py`: `Graph` wrapping `networkx.MultiDiGraph`; stable
  string IDs on nodes AND edges; multi-label nodes; attribute bags; helpers to
  add/get typed nodes/edges and to iterate by type.
- **3.2** `graph/canonical.py`: `to_canonical_json` / `from_canonical_json` with
  explicit `$schema` + `version`, nodes as id→object map, edges as objects with
  required `id`, `source`, `target`, `type`, `attributes`; **sorted keys +
  id-sorted arrays** for one-line git diffs. JSON Schema for the canonical format
  itself, in `spec/` or `schemas/`.
- **3.3** Determinism test: serialize → parse → serialize is byte-identical;
  parallel edges preserved & distinguishable.
- **3.4** `export/` adapters *(lazy)*: `to_networkx`/`from_networkx`,
  `to_cytoscape`, `to_dot`, `to_mermaid`; stubs for `rdf_star`, `neo4j_cypher`
  (params, not string interpolation). (D2, D15, partially v0.4.)

## EPIC 4 — Extraction strategy layer  `extraction` `core`
*The "how we extract" half. (D5, D6, D11, D12)*

- **4.1** `extract/protocol.py`: `Extractor` Protocol (`runtime_checkable`),
  `ExtractionContext` (element id+type, sources, cache, injected services),
  `Extraction` (value + provenance + confidence).
- **4.2** `extract/pattern.py`: regex / `Callable[[Source], Value]` extractor
  (the trivial, deterministic default used to bring the facade up).
- **4.3** `extract/query.py` *(extra `[query]`)*: DuckDB SQL over tables;
  Mongo-style filter + JMESPath over JSON. **Query-specs are pure data**,
  validated, serialized alongside results — never raw engine strings.
- **4.4** `extract/llm.py` *(extra `[llm]`)*: schema→JSON-Schema→constrained
  structured output; `description` fields become the instruction
  (schema-as-extractor). Thin LLM-client seam; default adapter targets Anthropic
  Claude structured outputs via Instructor; **no provider SDK pinned in core**.
- **4.5** `extract/registry.py`: decorator/dict registry for built-ins +
  `importlib.metadata` entry points (`creel.extractors`) for third parties.
- **4.6** `extract/cache.py`: `Cache` Protocol (no-op default) + deterministic
  key `hash(prompt, model, params, element_id, source_fingerprint)`.
- **4.7** Range/constraint enforcement is a **post-decode verify step**, not the
  decoder's job (D6) — wire into the facade's verify pass.
- **4.8** *(D-OP8, R14)* The LLM extractor uses **hybrid class-cluster passes**
  (group coupled types; split weakly-coupled; class-by-class for big schemas),
  document-first **prompt caching**, validate-retry always, ground-to-IDs early.
  Requires the **cluster-pass binding model** (a binding can cover a *set* of
  elements, invoked once) — see EPIC 11.

## EPIC 5 — Bindings, join & the facade  `core`
*Wire the two layers together. (D7, D11)*

- **5.1** `bindings.py`: `ExtractorBindings` + `VerifierBindings` keyed by
  taxonomy path; resolution chain element-specific → type-default → global
  default (= schema-as-extractor / `llm_rubric`).
- **5.2** `join.py`: pure equijoin `join(spec, bindings) -> ResolvedPlan`;
  schema-as-extractor fallback synthesizes an NL description from the attr schema
  when no binding exists.
- **5.3** `facade.py`: `extract(sources, graph_spec, extractors=None, *,
  verifiers=None, cache=None, on_missing_binding="schema_as_extractor") -> Graph`.
  Map resolved extractors over elements (parallelizable), assemble LPG, run verify
  pass, attach evidence, return SSOT. Keyword-only beyond 3rd arg.
- **5.4** `evidence.py`: per-element evidence record — provenance (PROV-lite/PAV
  JSON), grounding (Web-Annotation selectors: TextQuote/TextPosition/cell/JSONPath),
  confidence (method-tagged) + review status; sidecar keyed by element id. (D8)
- **5.5** End-to-end facade test: tiny grammar + tiny sources + pattern/query
  extractors → expected graph + evidence.

## EPIC 6 — Evaluation / verifier subsystem  `evaluation` `core`
*The evaluation-time dual of extraction. (D9) — user-emphasized.*

- **6.1** `verify/protocol.py`: `Verifier` Protocol
  `verify(actual, expected, *, context) -> {score∈[0,1], passed, reason, details}`.
- **6.2** `verify/kinds.py`: `exact`, `normalized`, `numeric_tolerance`,
  `set_match`, `graph_match` (decomposable partial credit + canonicalization),
  `schema_constraint` (no-gold property checks), `semantic_similarity`,
  `composite` (weighted).
- **6.3** `verify/rubric.py`: `llm_rubric` (G-Eval) — NL-instruction verifier
  seeded from each element's `description`; judge model ≠ extractor model;
  randomized option order; mandatory stored `reason`.
- **6.4** Corpus model: item = `{sources, expected_graph, verifier_overrides?}`;
  verifiers attach by taxonomy path (most items need zero per-item config).
- **6.5** `eval` runner: score per-element → roll up to per-type & per-graph
  P/R/F1; retain judge reasons; cheap-deterministic-first, fall through to
  semantic/LLM. Optional `[eval]` backend (DeepEval/Inspect) behind the protocol.
- **6.6** A **faithfulness gate** verifier (value occurs within resolved span) that
  downgrades confidence + flags `needs_review`.
- **6.7** Tests: each verifier kind; a known-good and known-bad extraction scored.

## EPIC 7 — UNHCR RBM first consumer  `domain-unhcr` `evaluation`
*Prove the engine on the real first use case. (D14)*

- **7.1** `unhcr-rbm` grammar: COMPASS results taxonomy spine (impact/outcome/
  output; donors, projects, cross-cutting areas); IATI-shaped `funds` and
  `measured-by` edges; DAC-marker `addresses` edge; level-aware optional `target`.
- **7.2** Three synthetic-but-realistic test docs (prose donor agreement excerpt,
  project results matrix table, indicator table) — seeded from report 11.
- **7.3** Expected graph + per-element verifier overrides (numeric_tolerance on
  amounts/indicator values; llm_rubric on prose objective statements).
- **7.4** End-to-end eval: extract from the 3 docs with all 3 strategy families →
  score against expected → report. Catches schema-join regressions.
- **7.5** *(v0.4)* Graduate to `creel-unhcr` package member.

## EPIC 8 — Downstream contracts (enabled, not implemented)  `downstream`
*Enable §6 of the vision without building consumers. (D8, D9 RAG-readiness, D15, D-OP9)*

- **8.1** RAG-readiness affordances on canonical output: stable IDs, typed edges,
  per-element provenance, optional `text_for_embedding` projection.
- **8.2** `render.py`: `GraphRenderer` Protocol + `AnnotatedGraph` three-layer
  contract (graph ≈ Cytoscape `data`; standoff annotation overlay keyed by element
  id; optional selector→style hints).
- **8.5** *(D-OP9, R15)* **Per-attribute grounding** — evidence keyed by optional
  `(element_id, attribute_path)`, not just element id (A1).
- **8.6** *(D-OP9)* **`Annotation` contract** — one standoff record for machine
  insight *and* human coding (`target`/`body`/`motivation`/`provenance`); reified
  `Selection`; bidirectional (human highlights passage → links to node/edge/category) (A2).
- **8.7** *(D-OP9)* **Reverse-trace index** (span → elements): rebuildable interval
  index; `elements_at` / `elements_overlapping` (A3).
- **8.8** *(D-OP9)* **Anchor robustness**: always emit quote+position+`cited_text`;
  quote = system-of-record; ordered re-anchoring resolver (bounded diff-match-patch);
  `RangeSelector`/CSS/XPath + `refinedBy`; `needs_review` on fuzzy-only (A4).
- **8.9** *(D-OP9)* **Provenance kind + `wasRevisionOf`**: derive
  machine/manual/corrected; non-destructive corrections; `coded_by` for humans (A5).
- **8.3** `view/projections.py`: `to_dot`, `to_mermaid`, `to_node_edge_records`,
  `to_table`, `to_sections` — flattened views renderers/media want.
- **8.4** Export adapters maturity (rdf-star, cypher params, llamaindex/graphrag
  parquet) behind `[graphdb]`/`[pipelines]` extras.

## EPIC 9 — Docs, examples & release  `infra` `documentation`
- **9.1** README: essential-in-a-few-lines → paragraphs → details; easy example
  first (schema-as-extractor on a tiny doc), advanced after.
- **9.2** `examples/` worked notebooks/scripts: minimal, query, UNHCR.
- **9.3** Activate wads CI; first intentional release; epythet docs.

## EPIC 10 — Document ingestion layer  `extraction` `provenance`
*Files → Sources. (D-OP7, report R13)*

- **10.1** `ingest/protocol.py`: `Ingestor` Protocol (file → `Source`(s) with
  Markdown content + a structured provenance sidecar); `LoaderRegistry` route-by-
  format.
- **10.2** Local default backends `[ingest]`: Docling (PDF/DOCX/XLSX/HTML/image +
  page/bbox provenance), trafilatura (HTML), openpyxl (XLSX, merged-cell aware),
  python-docx (DOCX); Markdown/text pass-through.
- **10.3** Quality-gate escalation ladder: cheap local → quality check (empty/
  garbled text, table-detect failure) → `[ocr]` (pytesseract) / VLM → multimodal
  model (`[anthropic]` Claude native PDF + Citations grounding provider).
- **10.4** Grounding selectors wired through to evidence: `PageSelector`,
  `BoundingBoxSelector`, `CellSelector`, `TextPositionSelector`. Grounding mandatory
  in the data model, coarsest-available in weak backends.
- **10.5** Tests: per-format ingestion + provenance fidelity on small fixtures.

## EPIC 11 — Extraction granularity & entity resolution  `extraction` `core`
*The LLM-era extraction shape. (D-OP8, #14, report R14)*

- **11.1** **Cluster-pass binding model**: a binding may cover a *set* of grammar
  elements and be invoked **once**; the facade groups elements into passes.
- **11.2** Granularity planner: hybrid class-cluster default (group coupled,
  split weakly-coupled, class-by-class for big schemas); document-first prompt
  caching; parallel independent passes; gleanings for recall.
- **11.3** `Resolver` Protocol + cascade (registry/exact → normalize-before-merge →
  embedding blocking/similarity → LLM adjudication); consolidation stage; `[er]`
  extra (Splink). Required whenever we chunk/split.
- **11.4** `ExtractionPolicy` (#13): validate-retry always; self-consistency on
  high-value/low-confidence fields; `needs_review` thresholds; resolution chain.
- **11.5** Tests: cluster-pass invocation; ER cascade on messy variant names.

---

## Critical path (suggested order)

`EPIC1 → EPIC2 → EPIC3 → EPIC5(skeleton w/ pattern extractor) → EPIC4 → EPIC6 → EPIC7`
(**all done through here as of v0.3**) `→ EPIC10 (ingestion) → EPIC4.4+EPIC11 (LLM
extractor, granularity, ER) → EPIC8 → EPIC9`

The facade came up **early** (after a trivial pattern extractor) so every later
strategy and verifier plugs into a working end-to-end pipe. Round-2 research (R13
ingestion, R14 granularity) reorders the *remaining* work: **ingestion (EPIC 10)
and the granularity/ER-aware LLM extractor (EPIC 4.4 + EPIC 11)** now precede the
downstream contracts, because the real (messy, multi-format) corpus needs them.
