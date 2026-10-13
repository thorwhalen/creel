# creel.verify.protocol

The verifier contract — the evaluation-time dual of the extractor contract.

The user-emphasized principle (decision D9): comparing an *actual* extraction to an
*expected* one is **not** a hardcoded equality check, but a pluggable
[`Verifier`](#creel.verify.protocol.Verifier) — and many verifiers are fully defined by natural-language
instructions to an LLM (see [`creel.verify.rubric`](creel.verify.rubric.html.md#module-creel.verify.rubric)).

A [`Verifier`](#creel.verify.protocol.Verifier) is any callable `(actual, expected, *, context) -> Verdict`,
mirroring the callable [`Extractor`](creel.html.md#creel.Extractor). Every verdict is
a normalised `score` in `[0, 1]` plus a boolean `passed`, an auditable
`reason` (mandatory for LLM judges), and structured `details` (per-component
scores, matched pairs) — the exact shape the whole eval ecosystem converged on.

### Functions

| [`passed_at`](#creel.verify.protocol.passed_at)(score, threshold)   | Helper: `True` iff `score >= threshold` (used uniformly by all kinds).   |
|--------------------------------------------------------------------------------|--------------------------------------------------------------------------|

### Classes

| [`Verdict`](#creel.verify.protocol.Verdict)(score, passed[, reason, details])      | The result of a verification: a normalised score plus an audit trail.       |
|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`VerificationContext`](#creel.verify.protocol.VerificationContext)([element_type, spec, ...]) | Optional context a verifier may consult (element schema, services, config). |
| [`Verifier`](#creel.verify.protocol.Verifier)(\*args, \*\*kwargs)                   | A strategy that scores an `actual` value against an `expected` one.         |

### *class* creel.verify.protocol.Verdict(score, passed, reason='', details=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The result of a verification: a normalised score plus an audit trail.

#### to_dict()

Serialise to a plain dict (reasons retained for audit).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.verify.protocol.VerificationContext(element_type=None, spec=None, services=<factory>, config=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Optional context a verifier may consult (element schema, services, config).

`services` carries injected dependencies such as an LLM `"judge"` (which
must differ from the extractor model — D9) or an `"embedder"` for semantic
similarity. `element_type`/`spec` let a verifier read the schema (e.g. to
seed an `llm_rubric` from a `description`).

### *class* creel.verify.protocol.Verifier(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A strategy that scores an `actual` value against an `expected` one.

### creel.verify.protocol.passed_at(score, threshold)

Helper: `True` iff `score >= threshold` (used uniformly by all kinds).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
