# creel.annotate

Annotations — the standoff overlay for machine insight AND human coding (D-OP9 / A2).

A single [`Annotation`](#creel.annotate.Annotation) record serves both directions of authorship: an LLM/
analysis laying an insight over the graph (decision D15) and a human highlighting a
source passage and linking it to a node/edge/category (the manual-“coding” workflow).
They differ only by `motivation` + the provenance agent `kind` — never two
schemas. The overlay is standoff (kept separate from the graph; joined by target).

A [`Selection`](#creel.annotate.Selection) reifies a region of a source (id + selector) so several
annotations can share one highlighted span. Targets may be a graph element id, an
`(element_id, attribute)` pair (per-attribute, A1), or a [`Selection`](#creel.annotate.Selection).

### Classes

| [`Annotation`](#creel.annotate.Annotation)(id, target, body[, motivation, ...])   | A standoff annotation linking a `target` to a `body` with a `motivation`.      |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`Selection`](#creel.annotate.Selection)(id, source_id, selector)                | A reified, shareable selection of a source region (id + a grounding selector). |

### *class* creel.annotate.Annotation(id, target, body, motivation='commenting', provenance=None, confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A standoff annotation linking a `target` to a `body` with a `motivation`.

`target`: an element id (str), an `(element_id, attribute)` tuple, or a
[`Selection`](#creel.annotate.Selection) (a source span). `body`: a graph-element/category ref (str),
a free-text comment, or any structured insight. `provenance`/`confidence` reuse
the evidence vocabulary; `provenance.attributed_kind` distinguishes a
`software_agent` annotation (machine insight) from a `person` one (human coding).

#### target_element_id()

The graph element id this annotation targets, if any (else `None`).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### to_dict()

Serialise to a plain, JSON-ready dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.annotate.Selection(id, source_id, selector)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A reified, shareable selection of a source region (id + a grounding selector).

#### to_dict()

Serialise to a plain dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
