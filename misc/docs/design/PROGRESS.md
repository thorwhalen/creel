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
| #21 | graph_match + runner + UNHCR | `GraphMatch` partial credit + eval runner + end-to-end `unhcr-rbm` corpus (EPICs 6.4–6.7, 7.1–7.4) |
| #23 | research round 2 | reports R13/R14 + D-OP7/D-OP8 + EPIC 10/11 + ingestion skill + evidence selectors |
| #26 | traceability research | report R15 + ADR D-OP9 (A1–A5 reserved for EPIC 8) |
| #27 | query extractor | `table_map` / `sql` (DuckDB) / `json_query` (JMESPath) + shared transforms; UNHCR rewired (EPIC 4.3) |
| #28 | ingestion layer | `ingest()` route-by-format; stdlib loaders + optional backends; UNHCR loads via ingest (EPIC 10) |
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
- A faithful **UNHCR RBM corpus** (3 synthetic docs → 12 nodes / 11 edges) scored
  at 1.0 by the verifiers; the integration test that guards schema-join regressions.
- **All three extractor families** now real: pattern/function, **query**
  (`table_map`/`sql`/`json_query`), and **LLM** (schema-as-extractor via an injected
  client, validate-retry, faithfulness gate). The UNHCR corpus loads via the
  **ingestion layer** and its tables extract via declarative `table_map` specs.
- **Cluster-pass** extraction (one binding → a set of coupled types, one LLM pass)
  and a required **entity-resolution** cascade (normalize/registry/LLM, with a
  non-destructive `resolve_graph` merge pass) — both wired through the facade.
- **103 tests green** locally (`PYTHONPATH=. python -m pytest`).

## Remaining (by milestone)

**v0.2 — nearly complete; remaining**
- `creel.extract.llm.ExtractionPolicy` (EPIC 11.4): validate-retry always +
  self-consistency / `needs_review` thresholds (the *policy* home; mechanics exist).
- Optional: a default real LLM/embedder client wired behind `[llm]`/`[er]` (the seams
  + a thin Anthropic adapter exist; production hardening is a follow-up).

**v0.1 carry-over**
- `creel.spec.linkml` — LinkML ⇄ GraphSpec + generate JSON Schema/Pydantic
  (EPIC 2.4, `[semantic]` extra; Open Q1).
- Export adapters beyond the canonical/networkx basics: rdf-star, cypher params,
  cytoscape/dot/mermaid (EPIC 3.4 / 8.4).

**v0.4 — downstream contracts & package split**
- RAG-readiness affordances; `render.py` `GraphRenderer` + `AnnotatedGraph`
  contract; `view/` projections (EPIC 8).
- uv-workspace split `creel-core` + `creel-unhcr`; graduate the corpus grammar
  (D-OP3, EPIC 7.5).

**v0.5 — hardening**
- README polish + `examples/`; **activate wads CI** and cut the first intentional
  release (D-OP1, EPIC 9).

**Open design questions:** #11/#13/#14/#15 resolved & closed (see DECISIONS.md
"Resolutions 2026-06-17"); **#12 stays open** pending one fact — AGD-disaggregated
vs aggregate indicator values in v1 (decides edge-vs-reified-`Reading` node, with
#15 temporal). GRF codelist re-verification before production (Open Q10).

## How to run the tests

```bash
cd <repo> && PYTHONPATH="$PWD" python -m pytest -q          # 65 tests
PYTHONPATH="$PWD" python -m pytest --doctest-modules creel/spec/model.py creel/graph/model.py
python -m ruff check creel/
# regenerate the UNHCR expected graph after an intentional change:
PYTHONPATH="$PWD" python -c "import sys; sys.path.insert(0,'tests/data/unhcr'); import corpus; corpus.regenerate_expected()"
```
