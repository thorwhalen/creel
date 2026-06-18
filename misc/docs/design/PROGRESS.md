# creel — Progress Log

> What has been built, in what PR, and what remains. Pairs with
> [`ROADMAP.md`](ROADMAP.md) (the plan) and [`DECISIONS.md`](DECISIONS.md) (the
> why). Updated as milestones land.

## Done — milestones v0.1 → v0.3 (engine works end-to-end)

| PR | Title | Delivered |
|----|-------|-----------|
| #1  | Foundation research + synthesis | 12 cited reports + decisive synthesis (D1–D15) |
| #17 | Planning | ROADMAP, DECISIONS, `.claude/` config + 3 dev skills; GitHub epics/milestones/project/discussion |
| #18 | v0.1 data layer | `creel.spec` grammar + `creel.graph` LPG + deterministic canonical JSON (EPICs 2,3) |
| #19 | facade + extractors | `extract()` + pattern/function strategies + bindings/join + evidence (EPICs 4*,5) |
| #20 | verifier subsystem | `Verifier` protocol + kind taxonomy + `llm_rubric` (G-Eval) (EPIC 6.1–6.3) |
| #21 | graph_match + runner + RBM | `GraphMatch` partial credit + eval runner + end-to-end `rbm` corpus (EPICs 6.4–6.7, 7.1–7.4) |
| #23 | research round 2 | reports R13/R14 + D-OP7/D-OP8 + EPIC 10/11 + ingestion skill + evidence selectors |
| #26 | traceability research | report R15 + ADR D-OP9 (A1–A5 reserved for EPIC 8) |
| #27 | query extractor | `table_map` / `sql` (DuckDB) / `json_query` (JMESPath) + shared transforms; RBM corpus rewired (EPIC 4.3) |
| #28 | ingestion layer | `ingest()` route-by-format; stdlib loaders + optional backends; RBM corpus loads via ingest (EPIC 10) |
| #29 | LLM extractor | schema-as-extractor via injected client; validate-retry; faithfulness gate; facade fallback (EPIC 4.4) |
| #30 | cluster-pass | one binding covers a set of elements, invoked once; `ClusterLLMExtractor` (EPIC 11.1/11.2) |
| #31 | entity resolution | Normalize/Registry/LLM/Cascade resolvers + `resolve_graph` merge pass + facade `resolve=` (EPIC 11.3, #14) |

**Capabilities now real:**
- Declare a typed grammar (node/edge taxonomy, typed attributes, enums, ranges,
  inheritance); **edges are first-class with attributes** (funding amounts,
  indicator values live on edges).
- `extract(sources, graph_spec, extractors) -> graph` runs end-to-end with the
  deterministic **pattern/function** extractor family; every element carries a
  separable **evidence** record (provenance + grounding selector + confidence).
- Emit **deterministic, git-diffable canonical JSON** (byte-identical round-trip).
- **Verifier-based evaluation** (not hardcoded equality): exact / normalized /
  numeric_tolerance / set_match / **graph_match** (decomposable partial credit) /
  schema_constraint / semantic_similarity / **llm_rubric** (NL-defined, injected
  judge) / composite — plus a thin corpus **eval runner**.
- A faithful **RBM corpus** (4 synthetic docs → 17 nodes incl. 5 disaggregated
  reading nodes (e.g. by sex, age, location) / 19 edges) scored at 1.0 by the
  verifiers; the integration test that guards schema-join regressions across the
  whole engine.
- **All three extractor families** now real: pattern/function, **query**
  (`table_map`/`sql`/`json_query`), and **LLM** (schema-as-extractor via an injected
  client, validate-retry, faithfulness gate). The RBM corpus loads via the
  **ingestion layer** and its tables extract via declarative `table_map` specs.
- **Cluster-pass** extraction (one binding → a set of coupled types, one LLM pass)
  and a required **entity-resolution** cascade (normalize/registry/LLM, with a
  non-destructive `resolve_graph` merge pass) — both wired through the facade.

## v0.2 → v0.3 complete (2026-06-17) — PRs #27–#38

| PR | Delivered |
|----|-----------|
| #27 | Query extractor (`table_map`/`sql`/`json_query`) + shared transforms; RBM corpus tables rewired |
| #28 | Ingestion layer (`ingest()` route-by-format; stdlib + optional backends); RBM corpus loads via it |
| #29 | LLM extractor (schema-as-extractor, validate-retry, faithfulness gate, facade fallback) |
| #30 | Cluster-pass binding model + `ClusterLLMExtractor` (D-OP8) |
| #31 | Entity-resolution cascade + `resolve_graph` merge pass (#14) |
| #33 | `reify()`⇄`unreify()` edge↔node toggle + reserved temporal vocab (#12) |
| #34/#37 | **Disaggregated reading nodes** in `rbm` (e.g. by sex, age, location) |
| #35 | `creel.view` projections — records/table/DOT/Mermaid/Cytoscape (D15) |
| #36 | **Real-AI via `aix`** (`aix_client`/`aix_judge`/`aix_embedder`/`aix_entity_judge`) + 3 gated live tests |
| #38 | `ExtractionPolicy` — self-consistency + `needs_review` thresholds (EPIC 11.4 → **EPIC 11 done**) |

**The engine is feature-complete for its core mission:**
`ingest(files) → extract(sources, grammar, extractors) → graph → verify / resolve / reify / view`.
**125 tests green** (`PYTHONPATH=. python -m pytest`), plus **3 gated live-LLM tests**
that pass against a real model via `aix` (run when an API key is present).
**Completed epics: 2*, 3*, 4, 5, 6, 7*, 10, 11** (\* = all but one deferred sub-item).

## Released — v0.4 / v0.5 complete (2026-06-17) — PRs #40–#45

| PR | Delivered |
|----|-----------|
| #40 | Export adapters: JGF / GraphML / parameterized Cypher / RDF-star Turtle (EPIC 3.4/8.4) |
| #41 | Render contract (`AnnotatedGraph`/`GraphRenderer`) + `Annotation` overlay (machine + human coding) + RAG-readiness; A5 provenance kind/`wasRevisionOf` |
| #42 | Traceability A1/A3/A4: per-attribute grounding, `TraceIndex` reverse index, `reanchor` |
| #43 | LinkML bridge + JSON-Schema/Pydantic codegen (EPIC 2.4) |
| #44 | README for the full engine + `examples/quickstart.py` + bump to 0.1.0 (EPIC 9.1/9.2) |
| #45 | **Activated wads CI + first release** — published to PyPI + docs to GitHub Pages (EPIC 9.3) |

**🎉 Released to PyPI** (`pip install creel`; CI auto-bumped to **0.1.1**) with docs on
GitHub Pages. CI is live (tests on push/PR; publish-on-push-to-main). **Closed epics:
1, 2, 3, 4, 5, 6, 8, 9, 11.**

## Remaining

**Deferred — `creel-core` / consumer-package workspace split (EPIC 7.5, D-OP3).**
Intentionally NOT done: it restructures the just-published `creel` package (a
breaking packaging change), and the layer separation it would prove is *already*
true by construction (core has zero consumer imports; the RBM grammar lives only
in `tests/`). Real consumer grammars live in separate downstream repos, so
there's nothing public to ship as a dedicated consumer package yet. **Recommend
doing this as a deliberate 0.2.0 decision**, not a rushed post-release churn.

**Consumer-package work (out of core, by design):** concrete renderers (PNG/PPTX/
HTML on top of the `view`/`render` contracts).

**Production chore:** results-framework codelist re-verification before the `rbm`
grammar is used on real data (Open Q10).

**Open items:** all design questions resolved & closed (#11–#15; DECISIONS.md
"Resolutions").

## How to run the tests

```bash
cd <repo> && PYTHONPATH="$PWD" python -m pytest -q -m "not llm"   # 144 offline tests
# CI installs the package, so `import creel` works there without PYTHONPATH.
PYTHONPATH="$PWD" python -m pytest --doctest-modules creel/spec/model.py creel/graph/model.py
python -m ruff check creel/
# regenerate the RBM expected graph after an intentional change:
PYTHONPATH="$PWD" python -c "import sys; sys.path.insert(0,'tests/data/rbm'); import corpus; corpus.regenerate_expected()"
```
