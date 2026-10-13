# creel.verify.kinds

The verifier-kind taxonomy — pick the comparison that matches the field’s nature.

These parallel the node/edge/attribute taxonomy (decision D9). The rule: use the
*cheapest verifier that is right* — `exact` only where exactness is correct,
`numeric_tolerance` for amounts/indicator values, `set_match` for unordered
collections, `schema_constraint` for no-gold property checks, `semantic_similarity`
or `llm_rubric` (see [`creel.verify.rubric`](creel.verify.rubric.html.md#module-creel.verify.rubric)) for free text, and `composite`
to weight several together.

Each kind is a callable verifier; each is registered so a binding can name it.
`graph_match` (whole-graph comparison) lives in [`creel.verify.graph_match`](creel.verify.graph_match.html.md#module-creel.verify.graph_match).

### Classes

| [`Composite`](#creel.verify.kinds.Composite)([components, threshold])               | Weighted combination of named sub-verifiers (promptfoo-style).               |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`ExactMatch`](#creel.verify.kinds.ExactMatch)()                                     | `score=1.0` iff `actual == expected`; else `0.0`.                            |
| [`NormalizedMatch`](#creel.verify.kinds.NormalizedMatch)([casefold, strip, collapse_ws])  | Equality after normalising strings (casefold / strip / collapse whitespace). |
| [`NumericTolerance`](#creel.verify.kinds.NumericTolerance)([abs_tol, rel_tol])             | Compare numbers within an absolute and/or relative tolerance.                |
| [`SchemaConstraint`](#creel.verify.kinds.SchemaConstraint)([spec, predicate, description]) | Property-based check with **no expected value** — validates `actual` itself. |
| [`SemanticSimilarity`](#creel.verify.kinds.SemanticSimilarity)([threshold])                  | Similarity of free text.                                                     |
| [`SetMatch`](#creel.verify.kinds.SetMatch)([key, threshold])                       | Set-based precision/recall/F1 over (canonicalised) collections.              |

### *class* creel.verify.kinds.Composite(components=<factory>, threshold=0.5)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Weighted combination of named sub-verifiers (promptfoo-style).

### *class* creel.verify.kinds.ExactMatch

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

`score=1.0` iff `actual == expected`; else `0.0`. The auditable default.

### *class* creel.verify.kinds.NormalizedMatch(casefold=True, strip=True, collapse_ws=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Equality after normalising strings (casefold / strip / collapse whitespace).

### *class* creel.verify.kinds.NumericTolerance(abs_tol=0.0, rel_tol=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Compare numbers within an absolute and/or relative tolerance.

For funding amounts and indicator values on edges — a brittle `==` would
spuriously fail on `1000000` vs `1000000.0` or rounding.

### *class* creel.verify.kinds.SchemaConstraint(spec=None, predicate=None, description='schema constraint')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Property-based check with **no expected value** — validates `actual` itself.

Pass either a [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec) (validates a graph against the
grammar) or a `predicate(actual) -> bool` with a `description`.

### *class* creel.verify.kinds.SemanticSimilarity(threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Similarity of free text. Uses an injected `embedder` if available, else a
deterministic lexical fallback (`difflib` ratio) — which is flagged, because
similarity is not equivalence.

### *class* creel.verify.kinds.SetMatch(key=None, threshold=1.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Set-based precision/recall/F1 over (canonicalised) collections.

`key` maps each item to a hashable canonical form before comparing (so dicts
or fuzzy items can be aligned). `score` is the F1.
