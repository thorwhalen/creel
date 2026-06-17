# creel — Decision Log

> Single place to find *what was decided and why*, and to revisit choices later.
> **Design decisions D1–D15** live in the research synthesis
> ([`../research/00-synthesis-and-design-implications.md`](../research/00-synthesis-and-design-implications.md)) —
> each records the decision, its rationale, and the alternatives rejected. This
> file indexes them and adds **operational decisions (D-OP\*)** made while
> building, plus the **open questions** that still need the user.

Per the user's instruction: choices are made autonomously to keep momentum;
everything is recorded here so it can be challenged and changed.

## Design decisions (full text in the synthesis)

| ID | Decision (one line) |
|---|---|
| D1 | Internal model = Labeled Property Graph with first-class typed edges (`networkx.MultiDiGraph` carrier) |
| D2 | RDF-star / JSON-LD / SHACL / Cypher are *generated export targets*, not the source of truth |
| D3 | Grammar authored in **LinkML**; validation layer (JSON Schema + Pydantic) generated from it |
| D4 | Canonical JSON: creel-owned, versioned, stable IDs on nodes **and** edges, three separable layers, git-diffable |
| D5 | One `Extractor` Protocol; three strategy families (LLM/NL · query · pattern/function); route by source type |
| D6 | Grammar enforces **shape**; value-level constraints (ranges) enforced in a **verify** pass |
| D7 | Physically separate graph-definition from extraction/verification metadata; join by element id (ECS pattern) |
| D8 | Per-element **evidence record**: provenance (PROV-lite) + grounding (Web-Annotation selectors) + method-tagged confidence |
| D9 | One `Verifier` Protocol; kind taxonomy + `llm_rubric` (G-Eval) default seeded from schema `description` |
| D10 | Tiny core (`pydantic`, `jsonschema`, `networkx`, thin LLM seam); everything else optional extras |
| D11 | Orchestration = thin hand-composed callables (map + join); frameworks are downstream adapters |
| D12 | Plugin discovery: decorator registry + `importlib.metadata` entry points; pluggy deferred |
| D13 | Monorepo: uv workspace, `creel-core` separate from `creel-unhcr` |
| D14 | Bundle `unhcr-rbm` as first grammar: reuse COMPASS taxonomy + IATI indicator/transaction model verbatim |
| D15 | Rendering: three-layer annotated-graph contract + one `Renderer` Protocol; no renderers in core |

## Operational decisions (made during build)

### D-OP1 — Defer CI activation; keep `.github/workflows/ci.yml` untracked until v0.5
- **Decision.** The wads CI calls a reusable workflow whose publish job
  auto-bumps the version and publishes to PyPI on push to `main`. During heavy
  iterative development we do **not** want a PyPI release per merge, so the CI
  file is intentionally left untracked (not pushed) until the package is
  releasable. Tests are run **locally** (`pytest`) instead; planning/doc PRs carry
  `[skip ci]`.
- **Revisit.** At milestone **v0.5**, commit `.github/workflows/ci.yml`, confirm
  the publish/version-sync behaviour (see the user's `wads-ci-fix` notes), and cut
  the first intentional release.

### D-OP2 — Project name is `creel` (working name resolved)
- **Decision.** The vision brief left the name `TBD` (candidates *Prism*, *Loom*,
  *Lattice*). The repo is already `creel` (renamed from `bale`); a *creel* is the
  frame that holds bobbins/spools feeding a loom — apt for "one graph, many
  renders". We proceed with `creel` and use it in `$schema`/namespace URLs.
- **Revisit.** Open Q4 — confirm before the first public release.

### D-OP3 — Start single-package; split to uv-workspace at v0.4
- **Decision.** D13 calls for a `creel-core` + `creel-unhcr` uv-workspace
  monorepo. To keep early iteration fast we **spike as one flat `creel/` package**
  with the synthesis module tree, and perform the workspace split at v0.4 once the
  layer boundaries are proven by working code. (Open Q3.)

### D-OP4 — Canonical `$schema` / namespace hosting deferred; use a stable placeholder
- **Decision.** Canonical JSON references a creel-owned `$schema` URL. Until a
  hosting domain is chosen we use `https://creel.dev/schema/graph/v1` (or the
  GitHub Pages URL `https://thorwhalen.github.io/creel/schema/...`) as a stable
  placeholder and version with SchemaVer. Not resolved to a live URL yet.
- **Revisit.** Open Q5.

### D-OP5 — Default LLM is Anthropic Claude; judge ≠ extractor
- **Decision.** The default LLM-extraction adapter targets Anthropic Claude
  structured outputs (via Instructor, provider-agnostic). The verifier's
  `llm_rubric` must use a **different** model from the extractor to mitigate
  self-preference bias; default judge is a second Claude model unless configured
  otherwise. No provider SDK is pinned in core. (Open Q6.)

### D-OP6 — Concrete extractor result shape & callable `Extractor` (refines synthesis sketch)
- **Decision.** The synthesis sketched `Extractor.extract(ctx)` returning an
  `Extraction(value, provenance, confidence)`. The implementation refines this for
  workability: (a) `Extractor` is **any callable** `(ExtractionContext) -> Extraction`
  (a plain function qualifies — truest realisation of "strategy as callable, not a
  class hierarchy"); (b) `Extraction` carries concrete `nodes: tuple[ExtractedNode]`
  and `edges: tuple[ExtractedEdge]` rather than an opaque `value`, so the facade can
  assemble the LPG (nodes-before-edges) directly; (c) per-element evidence rides on
  each `ExtractedNode`/`ExtractedEdge` and is collected by the facade into a
  separable `graph.evidence` sidecar (and `graph.report` for diagnostics), which the
  canonical JSON deliberately ignores — preserving D7/D8 separation.
- **Rationale.** A concrete result shape makes the facade and tests simple and the
  data flow explicit; callable extractors keep the seam maximally open. The sidecars
  keep evidence "logically woven, physically separable" without coupling the graph
  model to the evidence types (they are plain dicts on `Graph`).
- **Rejected.** Opaque `Extraction.value` (forces every caller to know the shape);
  an `Extractor` ABC (heavier than a Protocol/callable); storing evidence inside
  node/edge attributes (would pollute the canonical graph and break separation).

### D-OP7 — Document ingestion strategy (from research round 2, report R13)
- **Decision.** creel gains an **ingestion layer** (`creel.ingest`) that turns raw
  files into `Source`s. Default = **local, structure-preserving,
  permissively-licensed** extraction (Docling/MIT primary; trafilatura HTML;
  openpyxl XLSX; python-docx DOCX), emitting **Markdown for the LLM + a structured
  sidecar carrying page/cell/char-span/bbox provenance**. **Route by format** with a
  **quality-gate escalation ladder**: cheap local → quality check → OCR/VLM →
  multimodal model (Claude native PDF + Citations) behind a provider-agnostic
  `Ingestor`/grounding interface. **Grounding is mandatory in the data model**
  (every produced unit carries a locator), optional in the backend (coarsest
  available locator if a backend can't supply coordinates). **License discipline:**
  no AGPL/GPL (PyMuPDF4LLM, Marker) in the default set.
- **Rationale.** R13: no single best parser; structured table parsing beats prose
  flattening for typed-graph extraction; grounding is the cheap audit layer.
  Reinforces D8 (auditability) and D10 (tiny core; heavy backends are extras).
- **Rejected.** Single-parser hammer; markitdown as the default (no OCR, no
  provenance); flattening tables to prose; PyMuPDF4LLM in core (AGPL).

### D-OP8 — Extraction granularity = hybrid class-cluster passes (from R14)
- **Decision.** The LLM extractor defaults to **hybrid class-cluster passes**:
  group tightly-coupled node+edge+attribute types into **one** pass; split
  weakly-coupled classes into their own (parallel) passes; **class-by-class**
  (SPIRES-style) for large/deep schemas. Mechanics: put the **document first as a
  cacheable prefix** (enable provider prompt caching), vary only the trailing class
  instruction, fire passes in a burst, optionally batch; **validate-retry**
  (Instructor) always; **ground reference/enum fields to stable IDs early**;
  gleanings/self-consistency only for high-value/low-confidence fields; a
  **consolidation/entity-resolution stage is REQUIRED** whenever we chunk or split.
  This requires extending the **binding model so one binding can cover a *cluster*
  of elements** (invoked once), not strictly one element per invocation.
- **Rationale.** R14: "lost in the middle" + structured-output schema-complexity
  degradation favor focused passes; **prompt caching neutralizes the multi-pass
  cost** (≈"1× document + N× tiny deltas"); SPIRES/GraphRAG/LangExtract precedent.
- **Rejected.** One giant holistic prompt as the default for non-trivial schemas;
  the naive "N passes = N× document cost" assumption; reflection loops for bulk
  low-stakes fields.
- **Implementation note.** Build the cluster-pass binding model **with** the LLM
  extractor (EPIC 4.4). The deterministic pattern/function extractors keep the
  cheap per-element model.

### D-OP9 — Bidirectional traceability & human annotation/coding as a first-class contract (from report R15)
- **Decision.** Record bidirectional source↔graph traceability and human
  annotation/"coding" as a **committed forward-compatibility requirement** that the
  evidence/annotation layers must honor. The current model (D7/D8) is well-positioned
  and needs **no schema fork** — only five **additive** extensions, all reserved now
  and built with EPIC 8 / the LLM extractor (not before):
  - **A1 — Per-attribute grounding.** Allow evidence to key on an optional finer id
    `(element_id, attribute_path)` (JSONPath-style) in addition to `element_id`, so a
    single *property* (not just the node/edge) traces to its source span. D8 always
    promised "node, edge, **and value**"; this closes the gap. Don't mandate it
    everywhere — only where an extractor can actually attribute a value.
  - **A2 — One `Annotation` contract for output *and* human input.** A standoff
    record `Annotation{ id, target (element_id | (element_id, attr) | source span),
    body (node/edge/category ref | insight | comment), motivation, provenance,
    confidence }`. Machine insight (D15) and manual coding are the **same object**,
    differing only by `motivation` + `attributed_to.kind`. Reify the **Selection**
    (id + selector + source_id) so several codings can share one highlighted span.
  - **A3 — Derived reverse-trace index (span → elements).** A *rebuildable cache*
    (interval tree over text spans; parallel structures for cell/page/bbox) exposing
    `elements_at(source_id, offset)` and `elements_overlapping(...)`. Not canonical
    state — rebuilt from the sidecar.
  - **A4 — Anchor robustness for re-ingestion.** Policy: every text grounding emits
    **both** a `TextQuoteSelector` (exact + ~32-char prefix/suffix) and a
    `TextPositionSelector`, plus a `cited_text` snapshot. **Quote = system of record;
    position = disposable hint recomputed on every re-ingest.** Add an ordered
    re-anchoring resolver (structural/position fast-path → verify quote → **bounded**
    diff-match-patch fuzzy search near the position → whole-doc quote search), and
    downgrade `review_status` to `needs_review` on fuzzy-only resolution. Most robust
    anchor = a structural id (block/cell/JSONPath/page) **`refinedBy`** a quote — which
    needs the small schema additions `RangeSelector` + CSS/XPath selectors + `refinedBy`.
  - **A5 — Machine/manual/corrected provenance, *derived* not hardcoded.** Add an
    agent `kind` (`software_agent | person`) to `attributed_to`; record corrections
    **non-destructively** as a new record with `wasRevisionOf → superseded_id`; keep a
    parallel `coded_by` for human tools. The three-way state becomes a query, not an
    `entry_kind` enum.
- **Rationale.** R15: the W3C Web Annotation multi-selector + `refinedBy` model and
  Hypothes.is fuzzy anchoring are the proven recipe; char-offsets must be treated as a
  disposable cache (PDF draw-order ≠ reading order; re-OCR shifts offsets); value-level
  provenance needs a finer addressable id (the non-RDF analogue of RDF-star reification).
  Everything aligns with existing D7/D8 separability — no migration.
- **Reserved, explicitly NOT built now.** Front-end linked-view UI; RDF-star/PROV-O/
  JSON-LD export; per-annotator layers / IAA / adjudication; REFI-QDA round-trip;
  active-learning retraining; editable graph-spec UI. (R15 §"Explicitly NOT yet".)
- **Tracking.** Seeds **EPIC 8** (annotated-graph contract); see `misc/docs/research/15-traceability-annotation.md`.

## Resolutions — 2026-06-17 (open questions Q1/Q2/Q7/Q8/Q9 after research round 2)

User accepted my leans on #11/#12/#13/#15; **#14 changed** because the real source
corpus is confirmed *very messy* (multi-source, field-written, non-native English,
OCR'd). Recorded here; GitHub issues updated accordingly.

- **#11 (LinkML, Q1) — RESOLVED (lean).** LinkML is an **optional, build-time
  authoring front-end**; the Python `GraphSpec` (plus a forthcoming JSON/YAML
  serialization) is the runtime SSOT. Refines D3 (LinkML is a generation
  convenience, not the spine). Commit only interface-contract artifacts.
- **#12 (indicator readings, Q2) — RESOLVED & closed (2026-06-17).** Default to a
  `measured_by` **attributed edge** for `unhcr-rbm`; a time-series is carried as
  **parallel `measured_by` edges** (creel's LPG supports them natively). The
  per-edge-type **`reify()` ⇄ `unreify()` toggle is BUILT** (`creel/reify.py`,
  lossless round-trip tested) and the **temporal vocabulary is reserved**
  (`creel/temporal.py`: `valid_from`/`valid_to`/`observed_at`/`recorded_at`) — so
  promotion to a `Reading` node is a non-breaking switch. **Reify when (a) v1 needs
  AGD/location-disaggregated readings** (a disaggregated reading is genuinely n-ary),
  **or (b) extraction merges across reporting periods** into one evolving graph
  (then the node-based `resolve_graph` dedups readings for free — readings-as-edges
  would need bespoke edge-dedup). **Update (2026-06-17): trigger (a) fired** — v1
  needs AGD-disaggregation, so `unhcr-rbm` now models a native **`reading` node**
  (sex/age_group/location enums) with `measures`/`assesses` edges; `funds` stays an
  edge. The generic `reify()` toggle remains for graphs first extracted as edges.
- **#13 (confidence escalation, Q7) — RESOLVED (lean).** A **separate
  `ExtractionPolicy`** object resolved by chain (element→type→global). Defaults:
  validate-retry always; self-consistency on high-value/low-confidence fields
  (amounts, indicator values); `needs_review` thresholds. Built with the LLM
  extractor.
- **#14 (entity resolution, Q8) — CHANGED.** Because docs are very messy,
  exact-ID/registry resolution alone is insufficient. New decision: a **pluggable
  `Resolver`** with the **full cascade** — registry/exact-ID (where codes exist) →
  **normalize-before-merge** → embedding **blocking + similarity** → **LLM
  adjudication** for hard clusters; **ER/consolidation is a REQUIRED stage**, not
  optional (R14 §5: blocking→matching→merging). **Ground-to-IDs early** during
  extraction to shrink the ER burden. `[er]` extra (Splink) + LLM adjudication via
  `[llm]`. **No longer deferrable** — needed for v1's real corpus.
- **#15 (temporal, Q9) — RESOLVED (lean).** Defer; **reserve** the
  `valid_from`/`valid_to`/`observed_at` names + convention. Revisit if extraction
  **merges across reporting periods** (then it becomes load-bearing; decide with #12).

## Open questions for the user (from the synthesis §"Open questions")

These are recorded in GitHub as `question`-labelled issues and summarized here:

1. **LinkML runtime vs build-time** + whether to commit generated artifacts.
2. **n-ary indicator readings**: default to a `measured-by` edge vs a `Reading`
   node; toggle per-spec or per-element.
3. **Repo restructure timing** (covered by D-OP3 — split at v0.4).
4. **Working name** (covered by D-OP2 — proceeding with `creel`).
5. **`$schema` URL / hosting** + versioning discipline (covered by D-OP4).
6. **Default judge model** + provider-agnosticism confirmation (covered by D-OP5).
7. **Confidence escalation policy**: thresholds for self-consistency / human
   review — grammar vs bindings vs separate policy file.
8. **Entity resolution / grounding resolver**: default impl + dedup cascade.
9. **Temporal modeling depth**: ship `valid_from`/`valid_to` in v1 or defer.
10. **GRF codelist verification**: re-verify the 16 outcome / 5 enabling-area
    wording/codes before `unhcr-rbm` production use.

Items 1, 2, 7, 8, 9 are genuinely open; 3, 4, 5, 6 have provisional answers above;
10 is a data-verification chore before production.
