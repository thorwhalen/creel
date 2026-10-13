# creel.policy

ExtractionPolicy — the operational policy layer for LLM extraction (decision #13).

This turns a recorded confidence into *action*: how hard to try (validate-retry), when
to spend more for reliability (self-consistency voting on high-value/low-confidence
fields), and when to flag an element for human review (`needs_review`). It is kept
**separate** from the grammar and the bindings (the same separation-of-concerns as
verifiers), and resolved by a chain: per-element → per-type → global default.

The deterministic extractor families ignore it (they are always
`deterministic, score=1.0`); it only bites for the probabilistic LLM extractor.

### Classes

| [`ExtractionPolicy`](#creel.policy.ExtractionPolicy)([max_retries, ...])   | How the LLM extractor should try, escalate, and flag for review.   |
|-----------------------------------------------------------------------------------------|--------------------------------------------------------------------|

### *class* creel.policy.ExtractionPolicy(max_retries=2, self_consistency_samples=1, review_below=0.5, overrides=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How the LLM extractor should try, escalate, and flag for review.

* **Parameters:**
  * **max_retries** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – validate-retry attempts for shape/constraint failures.
  * **self_consistency_samples** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – if >1, draw N samples and keep the modal result;
    confidence becomes the agreement fraction (`self_consistency` method).
  * **review_below** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – any element whose confidence score is below this is marked
    `needs_review` (human-in-the-loop gate).
  * **overrides** ([`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`ExtractionPolicy`](#creel.policy.ExtractionPolicy)]) – per element-id or per type-id policies (most specific wins).

#### for_element(element_id, type_id=None)

Resolve the effective policy for an element (element-id → type-id → self).

* **Return type:**
  [`ExtractionPolicy`](#creel.policy.ExtractionPolicy)
