# creel.verify

creel evaluation layer: pluggable verifiers (not hardcoded equality).

Re-exports the verifier contract ([`creel.verify.protocol`](creel.verify.protocol.html.md#module-creel.verify.protocol)), the kind taxonomy
([`creel.verify.kinds`](creel.verify.kinds.html.md#module-creel.verify.kinds)), the natural-language `llm_rubric` ([`creel.verify.rubric`](creel.verify.rubric.html.md#module-creel.verify.rubric)),
and the registry. Importing this package registers the built-in verifier kinds.

### Functions

| [`schema_description_verifier`](#creel.verify.schema_description_verifier)(element_type, \*)   | Build the default `llm_rubric` for an element, seeded from its `description`.   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`available_verifiers`](#creel.verify.available_verifiers)()                           | Return the sorted names of all registered verifiers (incl.                      |
| [`build_verifier`](#creel.verify.build_verifier)(name, \*\*config)                | Instantiate the named verifier with its `config`.                               |
| [`register_verifier`](#creel.verify.register_verifier)(name)                         | Decorator registering a verifier *factory* under `name`.                        |

### Classes

| [`Verdict`](#creel.verify.Verdict)(score, passed[, reason, details])        | The result of a verification: a normalised score plus an audit trail.           |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`VerificationContext`](#creel.verify.VerificationContext)([element_type, spec, ...])   | Optional context a verifier may consult (element schema, services, config).     |
| [`Verifier`](#creel.verify.Verifier)(\*args, \*\*kwargs)                     | A strategy that scores an `actual` value against an `expected` one.             |
| [`ExactMatch`](#creel.verify.ExactMatch)()                                     | `score=1.0` iff `actual == expected`; else `0.0`.                               |
| [`NormalizedMatch`](#creel.verify.NormalizedMatch)([casefold, strip, collapse_ws])  | Equality after normalising strings (casefold / strip / collapse whitespace).    |
| [`NumericTolerance`](#creel.verify.NumericTolerance)([abs_tol, rel_tol])             | Compare numbers within an absolute and/or relative tolerance.                   |
| [`SetMatch`](#creel.verify.SetMatch)([key, threshold])                       | Set-based precision/recall/F1 over (canonicalised) collections.                 |
| [`SchemaConstraint`](#creel.verify.SchemaConstraint)([spec, predicate, description]) | Property-based check with **no expected value** — validates `actual` itself.    |
| [`SemanticSimilarity`](#creel.verify.SemanticSimilarity)([threshold])                  | Similarity of free text.                                                        |
| [`Composite`](#creel.verify.Composite)([components, threshold])               | Weighted combination of named sub-verifiers (promptfoo-style).                  |
| [`GraphMatch`](#creel.verify.GraphMatch)([spec, attribute_verifiers, ...])     | Score an `actual` `Graph` against an `expected` one (partial credit).           |
| [`LLMRubric`](#creel.verify.LLMRubric)(criterion[, threshold, ...])           | Grade `actual` (optionally against `expected`) by a natural-language criterion. |

### *class* creel.verify.Composite(components=<factory>, threshold=0.5)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Weighted combination of named sub-verifiers (promptfoo-style).

### *class* creel.verify.ExactMatch

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

`score=1.0` iff `actual == expected`; else `0.0`. The auditable default.

### *class* creel.verify.GraphMatch(spec=None, attribute_verifiers=<factory>, node_weight=1.0, edge_weight=1.0, attr_weight=1.0, threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Score an `actual` `Graph` against an `expected` one (partial credit).

### *class* creel.verify.LLMRubric(criterion, threshold=0.5, reference_free=False, instructions=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Grade `actual` (optionally against `expected`) by a natural-language criterion.

Set `reference_free=True` to grade `actual` against the criterion alone (no
gold value). `threshold` sets the pass bar.

### *class* creel.verify.NormalizedMatch(casefold=True, strip=True, collapse_ws=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Equality after normalising strings (casefold / strip / collapse whitespace).

### *class* creel.verify.NumericTolerance(abs_tol=0.0, rel_tol=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Compare numbers within an absolute and/or relative tolerance.

For funding amounts and indicator values on edges — a brittle `==` would
spuriously fail on `1000000` vs `1000000.0` or rounding.

### *class* creel.verify.SchemaConstraint(spec=None, predicate=None, description='schema constraint')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Property-based check with **no expected value** — validates `actual` itself.

Pass either a [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec) (validates a graph against the
grammar) or a `predicate(actual) -> bool` with a `description`.

### *class* creel.verify.SemanticSimilarity(threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Similarity of free text. Uses an injected `embedder` if available, else a
deterministic lexical fallback (`difflib` ratio) — which is flagged, because
similarity is not equivalence.

### *class* creel.verify.SetMatch(key=None, threshold=1.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Set-based precision/recall/F1 over (canonicalised) collections.

`key` maps each item to a hashable canonical form before comparing (so dicts
or fuzzy items can be aligned). `score` is the F1.

### *class* creel.verify.Verdict(score, passed, reason='', details=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The result of a verification: a normalised score plus an audit trail.

#### to_dict()

Serialise to a plain dict (reasons retained for audit).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.verify.VerificationContext(element_type=None, spec=None, services=<factory>, config=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Optional context a verifier may consult (element schema, services, config).

`services` carries injected dependencies such as an LLM `"judge"` (which
must differ from the extractor model — D9) or an `"embedder"` for semantic
similarity. `element_type`/`spec` let a verifier read the schema (e.g. to
seed an `llm_rubric` from a `description`).

### *class* creel.verify.Verifier(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A strategy that scores an `actual` value against an `expected` one.

### creel.verify.available_verifiers()

Return the sorted names of all registered verifiers (incl. entry points).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### creel.verify.build_verifier(name, \*\*config)

Instantiate the named verifier with its `config`.

* **Return type:**
  [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)

### creel.verify.register_verifier(name)

Decorator registering a verifier *factory* under `name`.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]]

### creel.verify.schema_description_verifier(element_type, , threshold=0.5)

Build the default `llm_rubric` for an element, seeded from its `description`.

This is the schema-as-verifier default: the same `description` that drives the
schema-as-extractor also becomes the grading criterion.

* **Return type:**
  [`LLMRubric`](creel.verify.rubric.html.md#creel.verify.rubric.LLMRubric)

### Modules

| [`graph_match`](creel.verify.graph_match.html.md#module-creel.verify.graph_match)   | `graph_match` — compare a whole extracted graph to an expected one.                |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`kinds`](creel.verify.kinds.html.md#module-creel.verify.kinds)               | The verifier-kind taxonomy — pick the comparison that matches the field's nature.  |
| [`protocol`](creel.verify.protocol.html.md#module-creel.verify.protocol)         | The verifier contract — the evaluation-time dual of the extractor contract.        |
| [`registry`](creel.verify.registry.html.md#module-creel.verify.registry)         | Verifier discovery: a decorator registry + entry points (group `creel.verifiers`). |
| [`rubric`](creel.verify.rubric.html.md#module-creel.verify.rubric)             | `llm_rubric` — a verifier defined purely by natural-language instructions.         |
