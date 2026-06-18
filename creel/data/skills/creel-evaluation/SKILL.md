---
name: creel-evaluation
description: >-
  Evaluate / verify a creel extraction — the answer to "is this extraction
  correct?" is a pluggable Verifier, NOT a hardcoded == . Use when you need to
  score extraction quality, compare an actual graph to an expected_graph, build a
  test corpus, or pick the right comparison per attribute. Covers the verifier-kind
  taxonomy (exact, normalized, numeric_tolerance, set_match, schema_constraint,
  semantic_similarity, composite), graph_match (decomposable partial credit with a
  structured mismatch report), and llm_rubric (a verifier defined by a
  natural-language criterion, graded by an injected LLM judge). Keywords: pluggable
  Verifier not equality, graph_match partial credit, numeric_tolerance, semantic
  similarity, natural-language LLM rubric verifier, score extraction quality.
metadata:
  audience: users
---

# Evaluating a creel extraction

**The principle:** "Is this extraction correct?" is answered by a **pluggable
`Verifier` — never a hardcoded `==`.** Comparison is a *strategy you choose per
attribute*, because correctness means different things for different fields:
`1000000` vs `1000000.0` is a pass, two phrasings of the same outcome statement is
a pass, but a wrong currency code is a fail. Some verifiers are defined purely by a
**natural-language instruction** to an LLM judge (`llm_rubric`).

A `Verifier` is any callable `(actual, expected, *, context) -> Verdict`. A
`Verdict` (frozen dataclass) carries `score` (clamped to `[0,1]`), `passed`,
`reason` (mandatory for LLM judges, for audit), and structured `details`.

Prerequisites: produce the graph with **creel-extract**; the grammar and bindings
you're testing come from **creel-grammar** / **creel-bindings**; for a real LLM
judge or embedder see **creel-ai**.

## Pick the cheapest verifier that is *right*

| Field nature | Verifier kind | Notes |
|---|---|---|
| Identity / enum / code | `ExactMatch` (`"exact"`) | `1.0` iff `actual == expected`. The auditable default. |
| String, surface variation | `NormalizedMatch` (`"normalized"`) | equality after casefold / strip / collapse whitespace. |
| Amounts, indicator values | `NumericTolerance` (`"numeric_tolerance"`) | `abs_tol` / `rel_tol`; absorbs int-vs-float and rounding. |
| Unordered collection | `SetMatch` (`"set_match"`) | precision/recall/**F1**; `key=` canonicalises items; `details` lists `missing`/`extra`. |
| No gold value (validate `actual` itself) | `SchemaConstraint` (`"schema_constraint"`) | pass a `GraphSpec` (conforms-to-grammar) or a `predicate(actual)->bool`. |
| Free prose, no judge | `SemanticSimilarity` (`"semantic_similarity"`) | injected `embedder` → cosine; else a `difflib` lexical fallback (flagged — *not* semantic). |
| Free prose, nuanced | `LLMRubric` (`"llm_rubric"`) | graded by a natural-language criterion + injected judge (below). |
| Several weighted together | `Composite` (`"composite"`) | `components=((name, verifier, weight), ...)`; score = weighted mean of sub-scores. |
| A whole graph | `GraphMatch` (`"graph_match"`) | decomposable partial credit over nodes/edges/attributes (below). |

Rule of thumb: `exact` only where exactness is genuinely right; `numeric_tolerance`
for amounts; `normalized`/`semantic_similarity`/`llm_rubric` for prose;
`set_match`/`graph_match` for collections and graphs. Each kind is registered, so a
binding can name it as a string and build it via `creel.verify.registry`.

## graph_match: partial credit + a structured mismatch report

`GraphMatch` is the default whole-graph verifier and the heart of corpus
evaluation. It is **decomposable partial credit, not all-or-nothing**:

- **Nodes** matched by id (creel ids are deterministic) → precision/recall/**F1**.
- **Edges** matched by canonical key `(type, source, target)` → P/R/F1, with greedy
  best-attribute alignment for parallel edges.
- **Attributes** of matched elements scored by **per-attribute sub-verifiers**.
- Overall `score` is a weighted blend (`node_weight`/`edge_weight`/`attr_weight`) of
  only the components that actually measured something — an empty extraction scores
  `0`, not a vacuous `0.667`.

`verdict.details` carries the full breakdown: `details["nodes"]` (P/R/F1 plus the
`missing`/`extra` id lists), `details["edges"]` (P/R/F1 plus
`matched`/`expected_total`/`actual_total` counts), and
`details["attributes"]["mismatches"]` — a list of
`{kind, id, attr, expected, actual, reason}` for every attribute that failed its
sub-verifier. That is your debugging report: it tells you *which* edge's *which*
attribute disagreed and *why*.

**Per-attribute verifier overrides** are the key dial. By default `GraphMatch`
picks `NumericTolerance` for numeric-ranged attributes and `NormalizedMatch`
otherwise. Override per `(type, attr)` (or just `attr`) via `attribute_verifiers`:

```python
GraphMatch(spec=spec, attribute_verifiers={
    ("funds", "amount"): NumericTolerance(rel_tol=0.001),  # amounts: tolerance
    ("addresses", "marker"): ExactMatch(),                 # code: exact
    ("outcome", "statement"): NormalizedMatch(),           # prose: normalized
})
```

## llm_rubric: a verifier defined by a sentence

`LLMRubric(criterion=...)` grades by a **natural-language criterion** (G-Eval
shape). The judge is **injected** via `context.services["judge"]` — so the core
pins no provider, the judge can differ from the extractor model (bias mitigation,
D9), and tests stay deterministic with a fake judge. A judge is any callable
`(prompt: str) -> {"score": float, "reason": str}` (a JSON string also works). Set
`reference_free=True` to grade against the criterion alone (no gold value). It
**raises** if no judge is in `context.services`. (`schema_description_verifier`
builds the default rubric seeded from an element's schema `description` — the dual
of schema-as-extractor.) For a real judge, see **creel-ai**.

## Name a verifier by string; register your own

Every kind is registered, so you can build one **by name** instead of importing the
class — handy when the choice travels as data (a corpus case, a binding, config):

```python
from creel import build_verifier, available_verifiers
available_verifiers()                                  # the registered kind names
v = build_verifier("numeric_tolerance", abs_tol=1.0)   # == NumericTolerance(abs_tol=1.0)
```

When no built-in kind is *right*, register your own — a `Verifier` is just a callable
`(actual, expected, *, context) -> Verdict`, and `register_verifier` makes it
name-addressable (the dual of `register_extractor` in **creel-bindings**):

```python
from creel import register_verifier
from creel.verify.protocol import Verdict

@register_verifier("startswith")           # factory: (**config) -> Verifier
def make_startswith(*, n=3):
    def verify(actual, expected, *, context=None):
        ok = str(actual)[:n] == str(expected)[:n]
        return Verdict(score=1.0 if ok else 0.0, passed=ok, reason=f"first {n} chars")
    return verify
```

Now `"startswith"` works wherever a kind string does — including a `GraphMatch`
`attribute_verifiers` entry built via `build_verifier("startswith", n=4)`. (The
built-in `predicate` kind is the registered form of `SchemaConstraint(predicate=...)`.)

## Building a test corpus case

A corpus case bundles inputs + how to extract + the expected output. **Build sample
docs and their expected graphs *as you implement*** — the expected graph is your
gold standard, and the verifier (not `==`) decides closeness.

```python
from creel.evaluation import CorpusCase, evaluate_case, evaluate_corpus

case = CorpusCase(
    name="rbm",
    sources=sources,               # from creel-extract / creel.ingest
    spec=spec,                     # the grammar under test (creel-grammar)
    bindings=bindings,             # extractor strategies (creel-bindings)
    expected_graph=expected_graph, # your gold graph
    attribute_verifiers={          # per-(type,attr) overrides
        ("funds", "amount"): NumericTolerance(),
        ("output", "statement"): NormalizedMatch(),
    },
    # services={"judge": my_judge},  # needed only if a verifier uses llm_rubric
    # verifier=...,                  # override the default GraphMatch entirely
)

result = evaluate_case(case)        # -> CaseResult
print(result.score, result.passed)
print(result.verdict.details["attributes"]["mismatches"])  # what disagreed

corpus = evaluate_corpus([case])   # -> CorpusResult
print(corpus.summary())            # mean_score, pass_rate, per-case scores
```

`evaluate_case` extracts the actual graph, then scores it with `case.verifier` or a
default `GraphMatch(spec, attribute_verifiers)`, building a `VerificationContext`
that carries `spec` and `services`. The same comparison is a `Verifier`, so swap in
`set_match`, `llm_rubric`, or a `Composite` without changing the runner.

## Runnable example (deterministic — no network)

```python
from creel.graph.model import Graph
from creel.verify.graph_match import GraphMatch
from creel.verify.kinds import NumericTolerance
from creel.verify.protocol import VerificationContext
from creel.verify.rubric import LLMRubric

def make_graph(amount):
    g = Graph()
    g.add_node("d:gov-x", types=("donor",), attributes={"name": "Government X"})
    g.add_node("p:water", types=("project",), attributes={"title": "Water Access"})
    g.add_edge("f:1", source="d:gov-x", target="p:water", type="funds",
               attributes={"amount": amount, "currency": "USD"})
    return g

expected = make_graph(1_000_000)
actual = make_graph(1_000_000.4)  # float, slightly off — == would fail

# numeric_tolerance override lets the tiny amount difference pass
verifier = GraphMatch(attribute_verifiers={("funds", "amount"): NumericTolerance(abs_tol=1.0)})
verdict = verifier(actual, expected)
print(verdict.score, verdict.passed)            # 1.0 True
print(verdict.details["attributes"]["mismatches"])  # []

# llm_rubric with a FAKE injected judge (deterministic)
fake_judge = lambda prompt: {"score": 1.0, "reason": "semantically equivalent"}
ctx = VerificationContext(services={"judge": fake_judge})
rubric = LLMRubric(criterion="Both name the same donor.")
v = rubric("Government X", "Govt of X", context=ctx)
print(v.score, v.passed, v.reason)              # 1.0 True semantically equivalent
```

## Gotchas

- A verifier needing a judge/embedder **raises** if `context.services` lacks it —
  pass `services=` on the `CorpusCase` (or `VerificationContext`).
- `SemanticSimilarity` without an injected embedder silently uses a `difflib`
  fallback that is lexical, not semantic — `details["method"]` flags it.
- `GraphMatch` matches nodes by id: a correct extraction shares ids with the
  expected graph because creel ids are deterministic. Mismatched ids show up as
  `details["nodes"]["missing"]`/`["extra"]`, not as attribute mismatches.
- Don't reach for `ExactMatch` on prose or floats; that's the brittleness this
  whole subsystem exists to avoid.
