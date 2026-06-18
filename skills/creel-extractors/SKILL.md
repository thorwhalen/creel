---
name: creel-extractors
description: Use when adding, changing, or wiring an extraction strategy in creel — the pluggable mechanisms that detect and pull a graph element's value(s) from sources. Covers the Extractor Protocol, the three strategy families (LLM/NL-description, query over structured sources, pattern/function), the registry + entry points, the schema-as-extractor default, the bindings→join→facade flow, and how every extraction attaches an evidence record (provenance + grounding + confidence). Trigger on work in creel/extract/, bindings.py, join.py, facade.py, or evidence.py.
metadata:
  audience: developers
---

# creel extractors

An **Extractor** is a strategy that, given an `ExtractionContext` (which element
of the grammar to find, the sources, injected services, a cache), returns an
`Extraction` (the value(s) + provenance + confidence). Extractors are
**callables behind a Protocol**, dispatched per grammar element. (Decisions D5,
D6, D7, D8, D11, D12.)

## The Protocol (keep stable)

```python
@runtime_checkable
class Extractor(Protocol):
    def extract(self, ctx: ExtractionContext) -> Extraction: ...
```

`ExtractionContext` carries `element_id` (taxonomy path), `element_type` (its typed
attrs), `sources`, `cache`, and injected `services` (e.g. an llm client, an entity
resolver). `Extraction` carries `value`, `provenance`, and optional `confidence`.

## The three strategy families

1. **pattern / function** (`extract/pattern.py`) — stdlib `re` or any
   `Callable[[Source], Value]`. Deterministic; `confidence=1.0
   method=deterministic`. This is the trivial default that brings the facade up
   before LLMs exist; prefer it whenever structure allows.
2. **query** (`extract/query.py`, extra `[query]`) — DuckDB SQL for tables;
   Mongo-style filter document + JMESPath projection for JSON / lists-of-JSON.
   **Query-specs are PURE DATA** (validated against a schema, serialized alongside
   the result) — never raw engine strings interpolated from input (injection-safe,
   sandboxable, auditable).
3. **LLM / NL-description** (`extract/llm.py`, extra `[llm]`) — compile the
   element's attribute schema to JSON Schema, run constrained/structured output;
   the schema's `description` fields are the instruction (**schema-as-extractor**).
   Thin LLM-client seam; default adapter targets Anthropic Claude structured
   outputs via Instructor. **No provider SDK pinned in core.** Remember D6: the
   decoder guarantees *shape only* — enforce numeric ranges in the verify pass.

**Route by source type before choosing a strategy.** A table → query; a regex-able
field → pattern; prose → LLM.

## Adding a new extractor

1. Implement the `Extractor` Protocol (a function or a small callable class).
2. Register it: decorator into the in-tree registry (`@register_extractor("name")`),
   or, for a third-party package, expose it under the `creel.extractors`
   entry-point group (lazily `.load()`-ed). (D12)
3. Make it produce a real **evidence record** (next section). An extractor that
   can't say *where* a value came from is incomplete.
4. Add a corpus test: a small source + the element + expected value, scored by a
   `Verifier` (see `creel-eval`), not bare `assert ==`.

## Bindings → join → facade (the two-layer flow, D7)

- `bindings.py` — `ExtractorBindings` map a taxonomy path to a chosen extractor +
  its config. Resolution chain: element-specific → type-default → **global default
  = schema-as-extractor**.
- `join.py` — `join(spec, bindings) -> ResolvedPlan` is a pure equijoin by element
  id. Missing binding ⇒ synthesize an NL description from the attr schema.
- `facade.py` — `extract(...)` maps the resolved extractors over elements
  (embarrassingly parallel), assembles the LPG with stable ids, runs the verify
  pass (ranges + faithfulness gate), attaches evidence, returns the SSOT.

Never let the extractor layer reach into the grammar definition or mutate it; they
meet only through the join.

## Evidence (D8) — required on every extraction

Attach a small record (sidecar, keyed by element id), three blocks:
- **provenance** — `derived_from` (source id/span), `generated_by` (strategy +
  extractor id), `attributed_to` (model id+version or human id), `generated_at`,
  `version`.
- **grounding** — Web-Annotation-style selector(s): `TextQuoteSelector`
  (exact+prefix+suffix) for prose, `TextPositionSelector`, cell selector for
  tables, JSONPath/Mongo predicate for JSON.
- **confidence** — `{method: deterministic|logprob|verbalized|self_consistency,
  score, verified, review_status}`. Never compare scores across methods; record
  the method.

A cheap deterministic **faithfulness gate** (does the value actually occur in the
resolved span?) doubles as a verifier and downgrades confidence + flags
`needs_review` on failure.

## Caching (D11)

Wrap expensive LLM calls with the `Cache` Protocol (no-op default) keyed on
`hash(prompt, model, params, element_id, source_fingerprint)`. Exact-match only —
semantic caches break reproducibility/auditability. (This is creel-side
memoisation; it is *separate* from provider-side **prompt caching** — see below.)

## Extraction granularity — the LLM extractor (D-OP8, report R14)

How many LLM passes to split extraction into is a separation-of-concerns problem.
The default is **hybrid class-cluster passes**, NOT one giant prompt:

- **Group** tightly-coupled node+edge+attribute types into one pass (co-dependent
  attributes, shared coreference, small schema).
- **Split** weakly-coupled classes into their own **parallel** passes; go
  **class-by-class** (SPIRES-style) for large/deep schemas (structured-output
  accuracy degrades with schema size; "lost in the middle" hurts long single prompts).
- **Cost:** put the **document first as a cacheable prefix**, enable provider
  **prompt caching** (Anthropic ~90% off cache reads), vary only the trailing class
  instruction, fire passes in a burst, optionally use the Batch API (50% off). This
  makes "many narrow passes ≈ one big pass" in cost — the historical objection to
  decomposition is gone.
- **Accuracy ladder:** validate-retry (Instructor) **always**; **ground reference/
  enum fields to stable IDs early** (fixes precision *and* cross-pass identity);
  gleanings / self-consistency only for **high-value/low-confidence** fields; skip
  reflection loops for bulk low-stakes fields.
- **Binding-model implication:** a binding may cover a **cluster** of grammar
  elements and be invoked **once** (not once-per-element). Implement this cluster
  model when building `extract/llm.py`; the deterministic pattern/function family
  keeps the cheap per-element model.

## Consolidation / entity resolution is REQUIRED when you chunk or split (D-OP8/#14)

Messy multi-source docs (field-written, non-native English, OCR'd) guarantee
duplicate/variant entities. A **`Resolver`** runs the cascade **blocking →
matching → merging**: registry/exact-ID (where codes exist) → **normalize-before-
merge** → embedding similarity → **LLM adjudication** for hard clusters. Ground to
canonical IDs during extraction to shrink the burden. `[er]` extra (Splink) + LLM
adjudication via `[llm]`. This is a first-class stage, not an afterthought.

## Sources come from the ingestion layer (D-OP7)

Extractors consume `Source`s produced by `creel.ingest` (files → Markdown for the
LLM + a structured sidecar with page/cell/char-span/bbox provenance). Route by
format; prefer structured table parsing over prose flattening. See the
**`creel-ingestion`** skill.
