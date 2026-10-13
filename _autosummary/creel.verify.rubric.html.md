# creel.verify.rubric

`llm_rubric` — a verifier defined purely by natural-language instructions.

This is the capability the user emphasised: a verifier that is \*fully specified by
instructions to an LLM\*, which judges robustly where a hardcoded comparison cannot
(decision D9). It follows the G-Eval shape — a criterion (optionally expanded into
chain-of-thought eval steps) form-filled into a normalised `[0, 1]` score with a
mandatory `reason`.

The judge model is **injected** via `context.services["judge"]` so the core never
pins a provider SDK, the call is testable with a fake judge, and the \*\*judge can be
held distinct from the extractor model\*\* (self-preference-bias mitigation). The
default rubric is \*seeded from the element’s own schema 

```
``
```

description\`\`\* — the dual
of schema-as-extractor (schema-as-verifier).

A judge is any callable `(prompt: str) -> {"score": float, "reason": str}` (a raw
JSON string with those keys is also accepted).

### Functions

| [`schema_description_verifier`](#creel.verify.rubric.schema_description_verifier)(element_type, \*)   | Build the default `llm_rubric` for an element, seeded from its `description`.   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|

### Classes

| [`LLMRubric`](#creel.verify.rubric.LLMRubric)(criterion[, threshold, ...])   | Grade `actual` (optionally against `expected`) by a natural-language criterion.   |
|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|

### *class* creel.verify.rubric.LLMRubric(criterion, threshold=0.5, reference_free=False, instructions=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Grade `actual` (optionally against `expected`) by a natural-language criterion.

Set `reference_free=True` to grade `actual` against the criterion alone (no
gold value). `threshold` sets the pass bar.

### creel.verify.rubric.schema_description_verifier(element_type, , threshold=0.5)

Build the default `llm_rubric` for an element, seeded from its `description`.

This is the schema-as-verifier default: the same `description` that drives the
schema-as-extractor also becomes the grading criterion.

* **Return type:**
  [`LLMRubric`](#creel.verify.rubric.LLMRubric)
