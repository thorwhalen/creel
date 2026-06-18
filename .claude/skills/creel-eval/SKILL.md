---
name: creel-eval
description: Use when building or extending creel's evaluation/verification subsystem, or when writing tests for extraction. Covers the Verifier Protocol, the verifier-kind taxonomy (exact/normalized/numeric_tolerance/set_match/graph_match/schema_constraint/semantic_similarity/llm_rubric/composite), how an LLM-instruction (G-Eval) verifier is specified and run, the test-corpus layout ({sources, expected_graph, verifier_overrides?}), per-element→per-type→per-graph score roll-up, and the rule that comparisons are pluggable verifiers — NOT hardcoded equality. Trigger on work in creel/verify/, the eval runner, the RBM corpus, or any extraction test.
---

# creel evaluation & verifiers

The core idea the user emphasized: a **hardcoded `expected == actual` check is
usually wrong**. Instead, comparison is a pluggable **`Verifier`**, and many
verifiers are **fully defined by natural-language instructions to an LLM** that
judges robustly. The verifier subsystem is the evaluation-time mirror of the
extractor subsystem and reuses the same postures (strategy pattern, physical
separation, progressive disclosure, auditability). Authoritative design:
synthesis §"The evaluation/verifier subsystem" + report `08-extraction-evaluation-verifiers.md`. (Decision D9.)

## The Protocol (keep stable)

```python
@runtime_checkable
class Verifier(Protocol):
    def verify(self, actual, expected, *, context) -> VerdictScore: ...
# VerdictScore: {score: float in [0,1], passed: bool, reason: str, details: dict}
```

Structurally compatible with Inspect `Score` / DeepEval `BaseMetric` so either can
back a verifier via the `[eval]` extra. `reason` is **mandatory** for LLM judges
(auditability).

## Verifier-kind taxonomy (parallels the node/edge/attribute taxonomy)

| Kind | Use for | Notes |
|---|---|---|
| `exact` / `normalized` | enums, IDs, codes | normalize: lowercase/trim/unit before compare |
| `numeric_tolerance` | funding amounts, indicator values | abs and/or rel tolerance |
| `set_match` | unordered collections of nodes/edges | P/R/F1 over **canonicalized** items |
| `graph_match` | whole-graph comparison | **decomposable partial credit** (credit head/relation/tail separately), optional GED / fuzzy alignment; canonicalize first |
| `schema_constraint` | property checks with **no gold value** | e.g. "every funding_amount is a positive number with a currency"; "every project links ≥1 objective" |
| `semantic_similarity` | free-text fields | embedding or NLI/bidirectional-entailment; explicit threshold; similarity ≠ equivalence (flag it) |
| `llm_rubric` (G-Eval) | prose, objective statements, the default fallback | NL criterion → auto CoT steps → form-filled normalized score |
| `composite` | combine the above | weighted sub-verifiers with named sub-metrics |

**Default fallback = `llm_rubric` seeded from the element's own schema
`description`** (schema-description-as-verifier — the dual of schema-as-extractor).

## Bias mitigation is by construction (do not skip)

- **Judge model ≠ extractor model** (self-preference bias).
- Randomize rubric option order / average over permutations (position bias).
- Always store the judge's `reason`.
- When validating creel's own judges against human labels, report **chance-
  corrected Cohen's κ**, not raw agreement.

## Physical separation + default-resolution chain

Verifier-spec is keyed by taxonomy path and joined to graph-spec on demand:
element-specific → type-default → global default (`llm_rubric` from description).
The same corpus can be re-scored under strict vs lenient policies with the SSOT
preserved. Run **cheap deterministic verifiers first**; fall through to
semantic/LLM only on failure or for free-text.

## Test-corpus layout (this is how creel's tests are built)

A corpus item:

```
tests/data/<corpus>/<case>/
  sources/               # the input docs (prose .md/.txt, tables .csv, .json)
  expected_graph.json    # canonical-JSON expected output
  verifiers.yaml         # OPTIONAL per-element verifier overrides (by taxonomy path)
```

Because verifiers attach by taxonomy path, **most cases need zero per-item
config** — the defaults do the right thing. The eval runner:
1. runs `extract(sources, grammar, bindings)`;
2. for each expected element, resolves its verifier and scores actual vs expected;
3. rolls per-element scores up to per-type and per-graph **P/R/F1**;
4. retains LLM-judge reasons; applies the faithfulness gate (value-in-span).

## Writing an extraction test — the rule

Do **not** write `assert result == expected`. Instead pick the verifier that
matches the field's nature:
- an enum/code → `exact`/`normalized`;
- a funding amount → `numeric_tolerance`;
- a set of extracted projects → `set_match` with canonicalization;
- the whole graph → `graph_match` (partial credit);
- a free-text objective statement → `llm_rubric` (or `semantic_similarity` when an
  embedding suffices and you want determinism).

When adding a new verifier kind: implement the Protocol, register it, add a
self-test with a known-good and known-bad pair, and document the kind in this
table. The `rbm` corpus (EPIC 7) is the integration test that exercises all
three extractor families against one shared grammar — keep it green.
