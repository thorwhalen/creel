# creel.evaluation

The evaluation runner — score an extraction corpus with pluggable verifiers.

A corpus case is `{sources, spec, bindings, expected_graph, verifier_overrides?}`
(decision D9). The runner extracts the actual graph and scores it against the
expected one — by default with [`GraphMatch`](creel.verify.graph_match.html.md#creel.verify.graph_match.GraphMatch)
(decomposable partial credit), or with a caller-supplied verifier. Per-attribute
verifiers attach by `(type, attribute)` so most cases need zero per-item config.

This is deliberately thin (decision D11): a function over cases, not a framework.
Roll-ups (per-graph node/edge/attribute scores) come straight from the verdict
`details`; a richer per-type breakdown can be layered on without changing the
contract.

### Functions

| [`evaluate_case`](#creel.evaluation.evaluate_case)(case)    | Extract `case.sources` and score the result against `case.expected_graph`.   |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`evaluate_corpus`](#creel.evaluation.evaluate_corpus)(cases) | Evaluate every case and aggregate the results.                               |

### Classes

| [`CaseResult`](#creel.evaluation.CaseResult)(name, verdict, actual_graph)        | The outcome of evaluating one case: the verdict + the produced graph.   |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`CorpusCase`](#creel.evaluation.CorpusCase)(name, sources, spec, bindings, ...) | One evaluation item: inputs + how to extract + the expected graph.      |
| [`CorpusResult`](#creel.evaluation.CorpusResult)(cases)                            | Aggregate outcome over a corpus.                                        |

### *class* creel.evaluation.CaseResult(name, verdict, actual_graph)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The outcome of evaluating one case: the verdict + the produced graph.

#### *property* passed *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the case met its verifier’s threshold.

#### *property* score *: [float](https://docs.python.org/3/builtins/functions.html#float)*

The case’s normalised score in `[0, 1]`.

### *class* creel.evaluation.CorpusCase(name, sources, spec, bindings, expected_graph, verifier=None, attribute_verifiers=<factory>, services=<factory>, on_missing_binding='skip')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One evaluation item: inputs + how to extract + the expected graph.

### *class* creel.evaluation.CorpusResult(cases)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Aggregate outcome over a corpus.

#### *property* mean_score *: [float](https://docs.python.org/3/builtins/functions.html#float)*

Mean case score (`1.0` for an empty corpus).

#### *property* pass_rate *: [float](https://docs.python.org/3/builtins/functions.html#float)*

Fraction of cases that passed.

#### summary()

A compact, JSON-ready summary (mean score, pass rate, per-case scores).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.evaluation.evaluate_case(case)

Extract `case.sources` and score the result against `case.expected_graph`.

* **Return type:**
  [`CaseResult`](#creel.evaluation.CaseResult)

### creel.evaluation.evaluate_corpus(cases)

Evaluate every case and aggregate the results.

* **Return type:**
  [`CorpusResult`](#creel.evaluation.CorpusResult)
