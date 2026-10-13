# creel.trace

Bidirectional source↔graph traceability (ADR D-OP9 — A1, A3, A4).

Three additive capabilities that make the extracted graph clickable both ways and
robust to re-ingestion, without changing the canonical graph:

- **A1 — per-attribute grounding.** Attach/read evidence keyed by `(element_id,
  attribute)` (the evidence sidecar already accepts arbitrary keys), so a single
  *property* — not just the node/edge — traces to its source span.
- **A3 — reverse-trace index.** [`TraceIndex`](#creel.trace.TraceIndex) is a rebuildable index over the
  evidence grounding selectors answering “which elements did this source span/cell/
  page produce?” (the inverse of element→source).
- **A4 — anchor robustness.** [`reanchor()`](#creel.trace.reanchor) re-locates a `TextQuoteSelector` after
  the source text changes or is re-OCR’d (quote = system of record; position = hint),
  falling back from exact+context to a bounded fuzzy match.

### Functions

| [`attribute_evidence`](#creel.trace.attribute_evidence)(graph, element_id, attribute)   | Return the per-attribute evidence for `(element_id, attribute)`, or the element-level evidence as a fallback, or `None`.   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| [`reanchor`](#creel.trace.reanchor)(selector, text, \*[, hint, fuzzy])        | Re-locate a `TextQuoteSelector` in (possibly changed) `text`.                                                              |
| [`set_attribute_evidence`](#creel.trace.set_attribute_evidence)(graph, element_id, ...)     | Attach an evidence record to a specific attribute value (key `(id, attribute)`).                                           |
| [`verify_anchor`](#creel.trace.verify_anchor)(selector, text)                      | True if the selector's `exact` quote still occurs verbatim in `text`.                                                      |

### Classes

| [`TraceIndex`](#creel.trace.TraceIndex)(graph)   | A rebuildable index from source locations to the elements grounded there.   |
|----------------------------------------------------------------------|-----------------------------------------------------------------------------|

### *class* creel.trace.TraceIndex(graph)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A rebuildable index from source locations to the elements grounded there.

Built from a graph’s evidence sidecar. Keys returned are the evidence keys, i.e.
an element id or an `(element_id, attribute)` pair (per-attribute grounding).

#### elements_at(source_id, offset)

Evidence keys whose text span contains `offset` (stabbing query).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### elements_in_cell(source_id, row, column)

Evidence keys grounded in table cell `(row, column)`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### elements_on_page(source_id, page)

Evidence keys grounded on `page`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### elements_overlapping(source_id, start, end)

Evidence keys whose text span overlaps `[start, end)` (range query).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.trace.attribute_evidence(graph, element_id, attribute)

Return the per-attribute evidence for `(element_id, attribute)`, or the
element-level evidence as a fallback, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Evidence`](creel.evidence.html.md#creel.evidence.Evidence)]

### creel.trace.reanchor(selector, text, , hint=None, fuzzy=True)

Re-locate a `TextQuoteSelector` in (possibly changed) `text`.

Strategy (Hypothes.is-style): exact match → disambiguate multiple hits by
prefix/suffix context (and `hint` position) → bounded fuzzy fallback. Returns the
`(start, end)` of the relocated quote, or `None` if it can’t be found. A caller
that resolves only via the fuzzy path should downgrade the element to needs-review.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)]]

### creel.trace.set_attribute_evidence(graph, element_id, attribute, evidence)

Attach an evidence record to a specific attribute value (key `(id, attribute)`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### creel.trace.verify_anchor(selector, text)

True if the selector’s `exact` quote still occurs verbatim in `text`.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
