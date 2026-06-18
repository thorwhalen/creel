---
name: creel-ai
description: >-
  Use a real LLM with creel — wire an injected LLM client, run AI-powered graph
  extraction, and judge/resolve with a model. Use when the user wants
  schema-as-extractor extraction, to inject an LLM client (services={'llm':
  aix_client()} or anthropic_client()), the ('llm', {}) binding, an LLM judge for
  llm_rubric verification, LLM entity resolution, self-consistency policy, or to
  test LLM code with a fake client. Triggers on "use a real LLM with creel",
  "extract with an LLM / GPT / Claude", "schema-as-extractor", "inject an LLM
  client", "aix_client / anthropic_client", "services={'llm':...}", "the
  ('llm',{}) binding", "LLM as a judge", "LLM entity resolution", "self-consistency
  voting", "ExtractionPolicy", "AI-powered graph extraction", "fake LLM client for
  tests". The LLM is a swappable strategy — no provider SDK lives in creel's core.
metadata:
  audience: users
---

# creel-ai — real LLMs as a swappable strategy

creel is **AI-first** but the LLM is a **strategy you inject**, not a dependency baked
into the core. Core pins no provider SDK; you install a provider extra and pass a
client through `services={"llm": ...}`. The extractor is fully testable with a fake.

## 1. Install a provider, wire a client, bind `("llm", {})`

```python
pip install creel[aix]        # default provider client (uses aix's configured model)
# creel[llm] is an alias for creel[aix] (the default provider)
# or: pip install creel[anthropic]   # a thin direct-SDK Anthropic client
```

```python
from creel import GraphSpec, NodeType, AttrSchema, extract
from creel.extract.llm import aix_client            # or: anthropic_client

spec = GraphSpec(node_types=(
    NodeType("donor", description="An entity that provides funding.",
             attributes=(AttrSchema("name", required=True,
                                    description="The donor's official name."),)),
))
g = extract(
    "Donor: Foundation Alpha (ref 301). Donor: Agency Beta (ref 918).",
    spec,
    {"donor": ("llm", {})},                # bind the donor element to the LLM strategy
    services={"llm": aix_client()},        # inject the client (the swappable seam)
    on_missing_binding="skip",
)
```

`("llm", {})` selects the `LLMExtractor` (one element type per call). To pull
several **coupled** types out of one LLM pass (e.g. donors *and* their funding
edges, keeping them consistent), use the `cluster_llm` strategy with a cluster
binding instead — see **creel-bindings**. (See **creel-bindings** for the strategy
slot, **creel-extract** for the facade `services=` arg.) Unbound elements with
`on_missing_binding="schema_as_extractor"` (the default) route to the *same* LLM
strategy automatically — but still need `services={"llm": ...}`.

## 2. The injected-client contract

An LLM client is any object with **one method** — no base class to subclass:

```python
def complete_json(self, *, prompt, schema, system=None) -> Mapping:
    "Return a parsed JSON object for `prompt`, shaped like `schema`."
```

`aix_client()` and `anthropic_client()` are factories that build this for you. To use
any other provider (or a stub), implement that one method. `aix_judge()`,
`aix_embedder()`, `aix_entity_judge()` (extra `[aix]`) build the judge/embedder/
entity-judge callables described below.

## 3. Schema-as-extractor — descriptions ARE the prompt

There is **no separate prompt to write**. The element's `description` and each
attribute's `description` are compiled into the extraction instruction
(`build_instruction`), and the attribute types/enums/required flags become the output
JSON schema (`compile_output_schema`). So **good grammar descriptions are good
prompts** — invest in them. (Authoring: **creel-grammar**.)

```python
AttrSchema("name", required=True, description="The donor's official name.")
#                                              ^ becomes the LLM's instruction for this field
```

## 4. Validate-retry + the faithfulness gate

Two guards run automatically (decisions D6/D8):

- **validate-retry** — the decoder guarantees *shape* (types, enums, required); after
  decode, value-level constraints (e.g. numeric ranges, regex `pattern`) are
  re-checked and the model is **re-asked with the specific problems** up to
  `max_retries` times. Ranges are deliberately *not* in the decoder schema.
- **faithfulness gate** — each extracted value is grounded: if it occurs verbatim in
  the source it is `verified=True` with a quote/position selector; otherwise it is
  flagged `needs_review`. Hallucinated values get caught here, not silently kept.

On the returned graph these live in the evidence sidecar, keyed by element id:
`g.evidence[node.id].confidence.verified`, `.confidence.review_status`,
`g.evidence[node.id].grounding`.

## 5. ExtractionPolicy — self-consistency + review thresholds

`ExtractionPolicy` turns confidence into *action*; it only bites for the LLM strategy.

```python
from creel import ExtractionPolicy

policy = ExtractionPolicy(
    self_consistency_samples=3,   # draw N samples, keep the modal result;
                                  # confidence becomes the agreement fraction
    review_below=0.5,             # flag needs_review below this score
    max_retries=2,                # validate-retry attempts
)
g = extract(src, spec, {"donor": ("llm", {})},
            services={"llm": client, "policy": policy})   # global policy for the run
```

Inject the policy one of two ways: globally via `services={"policy": policy}` (above),
or per-binding via the strategy config — `("llm", {"policy": policy})` — which wins
for that element. (There is no `config=` argument on `extract()`.) Per-element /
per-type overrides inside one policy resolve most-specific-first:
`ExtractionPolicy(overrides={"donor": ExtractionPolicy(self_consistency_samples=5)})`.

## 6. An LLM as a judge (verification)

`llm_rubric` grades prose against a natural-language criterion. The judge is injected
under `services["judge"]` and **should be a different model from the extractor** (D9,
self-preference bias). The default criterion is seeded from the element's
`description` (schema-as-verifier). See **creel-evaluation**.

```python
from creel.extract.llm import aix_judge
from creel.verify.rubric import LLMRubric
from creel.verify.protocol import VerificationContext

ctx = VerificationContext(services={"judge": aix_judge()})
verdict = LLMRubric(criterion="Both describe the same outcome.")(actual, expected, context=ctx)
# verdict.score (0..1), verdict.passed, verdict.reason
```

## 7. An LLM as an entity-resolution adjudicator

`LLMResolver` settles hard "same entity?" pairs with an injected judge
`(name_a, name_b) -> bool`. Use it as the **costly tail** of a `CascadeResolver`
(cheap deterministic resolvers first). Pass the resolver via `extract(..., resolve=)`.

```python
from creel.extract.llm import aix_entity_judge
from creel.resolve import LLMResolver, CascadeResolver, NormalizeResolver

resolver = CascadeResolver([NormalizeResolver(key="name"),
                            LLMResolver(judge=aix_entity_judge(), key="name")])
g = extract(sources, spec, bindings, services={"llm": client}, resolve=resolver)
```

## 8. Testing: fake by default, gate real-LLM tests

Inject a fake client so tests are deterministic and offline — this is the whole point
of the seam. Real-LLM tests are marked `@pytest.mark.llm` and skipped without a key.

```python
class FakeLLM:
    "Routes by the element id mentioned in the prompt (mirrors tests/test_extract_llm.py)."
    def __init__(self, by_element):
        self.by_element = by_element
    def complete_json(self, *, prompt, schema, system=None):
        for element_id, items in self.by_element.items():
            if f"every {element_id} (" in prompt:
                return {"items": items}
        return {"items": []}

fake = FakeLLM({"donor": [{"name": "Foundation Alpha"}]})
g = extract("Donor: Foundation Alpha.", spec, {"donor": ("llm", {})},
            services={"llm": fake}, on_missing_binding="skip")
```

Run offline tests with `pytest -m "not llm"`; run live ones occasionally with a key.

## Gotchas

- **No client injected** → `LLMExtractor` raises a clear `ValueError` naming
  `services['llm']`. Install an extra and pass a factory, or inject any
  `complete_json(...)` object.
- **The judge must differ from the extractor model** (D9) — don't reuse the same
  `aix_*` default model for both if you can avoid it.
- Numeric ranges are **not** enforced by the decoder — they're a validate-retry /
  verify-pass concern. Don't expect `minimum`/`maximum` to gate decoding.
