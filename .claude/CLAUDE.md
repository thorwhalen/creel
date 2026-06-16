# creel — project instructions for Claude

**creel** is a general, AI-powered **source-to-graph extraction engine**. Its
core is one parameterized facade:

```python
extract(sources, graph_spec, extractors) -> graph   # a typed LPG; the single source of truth
```

It reads heterogeneous sources (prose, tables, JSON, schema specs), conforms them
to a caller-supplied **grammar** of typed node-types and edge-types, and emits a
clean, auditable, typed **property graph** as canonical JSON. Persistence, query,
annotation, and rendering are *downstream* — **enabled** by the core, never
implemented in it.

## Read these first (the project's source of truth)

- **Vision** — `misc/docs/starter -- source-to-graph-engine_core-description.md`
- **Design SSOT** — `misc/docs/research/00-synthesis-and-design-implications.md`
  (decisions **D1–D15**, module layout, the `Protocol` interfaces, dependency
  posture, the verifier subsystem). *When a design question arises, this doc
  decides it; if it doesn't, make a choice and record it in the decision log.*
- **Roadmap** — `misc/docs/design/ROADMAP.md` (epics → tasks → milestones; mirrors
  the GitHub issues).
- **Decision log** — `misc/docs/design/DECISIONS.md` (D1–D15 index + operational
  D-OP\* decisions + open questions).
- **Deep research** — `misc/docs/research/01..12-*.md` (each design choice cites
  the report that justifies it, e.g. `[R08]`).

Skills: `creel-architecture` (the map), `creel-extractors` (strategy layer),
`creel-eval` (the verifier/evaluation subsystem). Invoke the matching one when
working in that area.

## The load-bearing ideas (do not violate without recording a decision)

1. **Attributes live on edges.** Funding amounts and indicator values sit on
   edges, which have their own identity. The model is an **LPG**
   (`networkx.MultiDiGraph`), never bare RDF triples. (D1)
2. **Two physically separate layers, joined by element id.** The *graph
   definition* (grammar) and the *extraction/verification metadata* (bindings) are
   separate stores joined on demand (`join(spec, bindings)`), so the same grammar
   pairs with many extraction strategies and vice-versa. (D7)
3. **Strategy pattern everywhere.** Extractors, verifiers, renderers, caches,
   storage are `runtime_checkable` `Protocol`s — callables, not class hierarchies.
   New mechanisms plug in without touching old ones (open-closed). (D5, D9, D12)
4. **Schema-as-extractor / schema-as-verifier defaults.** An element's attribute
   `description` doubles as the default LLM extraction instruction *and* the
   default `llm_rubric` verification criterion. Simple things stay simple. (D5, D9)
5. **Grammar enforces shape; verification enforces values.** Constrained decoding
   guarantees types/enums/required fields only. Numeric ranges and faithfulness
   are checked in a separate **verify** pass — never trusted to the decoder. (D6)
6. **Auditability is structural.** Every node, edge, and attribute value carries a
   separable **evidence record**: provenance + a grounding selector back to the
   exact source span + method-tagged confidence + review status. (D8)
7. **Tiny core, commodity behind seams.** Core deps ≈ `pydantic`, `jsonschema`,
   `networkx`, and a thin LLM-client seam — **no provider SDK pinned, no
   opinionated KG pipeline as the spine**. Everything else is an optional extra.
   (D10, D11)
8. **Canonical JSON is the on-disk truth.** Versioned (`$schema` + `version`),
   stable string IDs on nodes *and* edges, sorted keys + id-sorted arrays so diffs
   are one line. Deterministic round-trip is a tested invariant. (D4)

## How we work here

- **Build inside-out**, facade early. Order: structure → grammar/spec → graph +
  canonical JSON → facade skeleton with the trivial *pattern* extractor → real
  extractor strategies → verifier/eval harness → UNHCR corpus → downstream
  contracts. (See `ROADMAP.md` critical path.)
- **Tests are first-class and verifier-based.** A test corpus item is
  `{sources, expected_graph, verifier_overrides?}`. The comparison of actual vs
  expected is a pluggable **`Verifier`**, *not* hardcoded equality — `exact` only
  where exactness is right; `numeric_tolerance` for amounts; `set_match`/
  `graph_match` with partial credit for graphs; `semantic_similarity` /
  `llm_rubric` for prose. Build sample docs + expected outputs as you implement.
  See the `creel-eval` skill.
- **CI is deferred (D-OP1).** `.github/workflows/ci.yml` is intentionally
  **untracked** until milestone v0.5 to avoid the wads publish-on-push auto-release
  during development. **Run `pytest` locally**; put `[skip ci]` on doc/planning
  commits. Do not commit/activate the CI file without flagging it.
- **PR and merge per logical unit.** Branch from `main`, open a PR (labelled),
  squash-merge, return to `main`. Public repo → never put local paths, secrets, or
  hostnames in commits/PRs/issues/committed files.
- **Coding principles** (global CLAUDE.md applies): functional over OOP; small
  focused helpers (`_underscore` for module-private, inner for single-use);
  keyword-only args beyond the 3rd; sensible defaults + informative errors; every
  module gets a top-level docstring. Use `dataclasses` for records, Pydantic only
  at the LLM/IO boundary.
- **Record decisions.** When you choose something the synthesis didn't dictate,
  append a `D-OP*` entry to `misc/docs/design/DECISIONS.md` rather than leaving it
  implicit. Link work to its GitHub issue.

## Status

Greenfield. Foundation research + synthesis merged (PR #1). Planning artifacts and
this config are next. Implementation begins at EPIC 2 (grammar/spec layer). The
empty `creel/__init__.py` is the only code so far.
