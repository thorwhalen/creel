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
