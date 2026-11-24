# creel.export.to_lacing

creel → lacing: carry a creel annotation into lacing’s envelope, source link intact.

A [`creel.annotate.Annotation`](creel.annotate.html.md#creel.annotate.Annotation) knows where a fact came from: its `target` can be
a [`Selection`](creel.annotate.html.md#creel.annotate.Selection) (a source region plus a grounding selector) and its
`provenance` says whether a model or a person made it. lacing’s
`lacing.Annotation` is what decks, videos and reports render, but lacing has no
source selector of its own (its `Reference` is media, node or annotation). This
adapter is the bridge thorwhalen/loomun#35 and its ADR-0012 call for: one function
that maps the envelope and the provenance, and keeps the whole creel record in the
body, so a rendered fact can always drill back to its source.

```pycon
>>> from creel.annotate import Annotation, Selection
>>> from creel.evidence import Provenance, TextQuoteSelector, SOFTWARE_AGENT
>>> sel = Selection("s1", "report.pdf", TextQuoteSelector(exact="revenue grew 12%"))
>>> note = Annotation(
...     "a1", sel, "fact:revenue-growth", motivation="identifying",
...     provenance=Provenance("report.pdf", "llm:extract", attributed_to="model-x",
...                           attributed_kind=SOFTWARE_AGENT),
... )
>>> ann = to_lacing_annotation(note)
>>> source_selection(ann)["source"]
'report.pdf'
```

Needs lacing: `pip install creel[lacing]`. Nothing here is imported until called.

### Module Attributes

| [`CREEL_BODY_SCHEMA_URI`](#creel.export.to_lacing.CREEL_BODY_SCHEMA_URI)   | The lacing `body_schema_uri` under which a creel annotation travels.       |
|--------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`DEFAULT_TIER`](#creel.export.to_lacing.DEFAULT_TIER)            | Default lacing tier for exported creel annotations.                        |
| [`CREEL_ID_NAMESPACE`](#creel.export.to_lacing.CREEL_ID_NAMESPACE)      | The `uuid5` namespace that turns a creel annotation id into a lacing UUID. |
| [`ACTIVITY_BY_KIND`](#creel.export.to_lacing.ACTIVITY_BY_KIND)        | a model's output is inferred, a person's coding is authored.               |
| [`SOURCE_PATH_PREFIX`](#creel.export.to_lacing.SOURCE_PATH_PREFIX)      | The path prefix of the `NodeRef` built for each kind of creel target.      |

### Functions

| [`lacing_id`](#creel.export.to_lacing.lacing_id)(creel_id, \*[, namespace])              | The lacing UUID for a creel annotation id: stable across exports.                                         |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`node_path`](#creel.export.to_lacing.node_path)(target)                                 | The `NodeRef.scene_path` that stands for a creel `target`.                                                |
| [`register_creel_body_schema`](#creel.export.to_lacing.register_creel_body_schema)()                      | Register [`CREEL_BODY_SCHEMA_URI`](#creel.export.to_lacing.CREEL_BODY_SCHEMA_URI) with lacing (idempotent). |
| [`source_selection`](#creel.export.to_lacing.source_selection)(lacing_annotation)               | The source region a lacing annotation made by this adapter points at, if any.                             |
| [`to_lacing_annotation`](#creel.export.to_lacing.to_lacing_annotation)(annotation, \*[, tier, ...]) | A `lacing.Annotation` carrying *annotation*, source link intact.                                          |

### creel.export.to_lacing.ACTIVITY_BY_KIND *= {'person': 'create', 'software_agent': 'infer'}*

a model’s output is
inferred, a person’s coding is authored. Unknown kinds read as imported, and a
software agent whose confidence method is deterministic derived, not inferred.

* **Type:**
  `Provenance.activity` by creel `attributed_kind`

### creel.export.to_lacing.CREEL_BODY_SCHEMA_URI *= 'annot://schema/creel-annotation/v1'*

The lacing `body_schema_uri` under which a creel annotation travels. The body is
[`creel.annotate.Annotation.to_dict()`](creel.annotate.html.md#creel.annotate.Annotation.to_dict), unchanged.

### creel.export.to_lacing.CREEL_ID_NAMESPACE *= UUID('9d6c3f0e-5b6a-5c1e-9a4e-6372656c0001')*

The `uuid5` namespace that turns a creel annotation id into a lacing UUID.
Fixed, so exporting the same annotation twice gives the same lacing id.

### creel.export.to_lacing.DEFAULT_TIER *= 'creel'*

Default lacing tier for exported creel annotations.

### creel.export.to_lacing.SOURCE_PATH_PREFIX *= 'creel/source'*

The path prefix of the `NodeRef` built for each kind of creel target.

### creel.export.to_lacing.lacing_id(creel_id, , namespace=UUID('9d6c3f0e-5b6a-5c1e-9a4e-6372656c0001'))

The lacing UUID for a creel annotation id: stable across exports.

```pycon
>>> lacing_id("a1") == lacing_id("a1") != lacing_id("a2")
True
```

* **Return type:**
  [`UUID`](https://docs.python.org/3/library/uuid.html#uuid.UUID)

### creel.export.to_lacing.node_path(target)

The `NodeRef.scene_path` that stands for a creel `target`.

A source selection points at its source, a graph element at the element, and an
`(element_id, attribute)` pair at that attribute of the element. The precise
region (the selector) is in the body: see [`source_selection()`](#creel.export.to_lacing.source_selection).

A `/` or `%` inside an id is percent-escaped, so `("a", "b")` and
`"a/b"` never share a path.

```pycon
>>> node_path("n1"), node_path(("n1", "name")), node_path("a/b")
('creel/element/n1', 'creel/element/n1/name', 'creel/element/a%2Fb')
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.export.to_lacing.register_creel_body_schema()

Register [`CREEL_BODY_SCHEMA_URI`](#creel.export.to_lacing.CREEL_BODY_SCHEMA_URI) with lacing (idempotent).

Called by [`to_lacing_annotation()`](#creel.export.to_lacing.to_lacing_annotation), so lacing can validate the body.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### creel.export.to_lacing.source_selection(lacing_annotation)

The source region a lacing annotation made by this adapter points at, if any.

The drill-in: `{"id", "source", "selector"}` as
[`creel.annotate.Selection.to_dict()`](creel.annotate.html.md#creel.annotate.Selection.to_dict) wrote it, or `None` when the creel
target was a graph element rather than a source region.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### creel.export.to_lacing.to_lacing_annotation(annotation, , tier='creel', reference=None, attributed_to=None, generated_by=None, namespace=UUID('9d6c3f0e-5b6a-5c1e-9a4e-6372656c0001'))

A `lacing.Annotation` carrying *annotation*, source link intact.

* **Parameters:**
  * **annotation** ([`Annotation`](creel.annotate.html.md#creel.annotate.Annotation)) – The creel annotation.
  * **tier** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The lacing tier it goes in.
  * **reference** ([`Union`](https://docs.python.org/3/library/typing.html#typing.Union)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Annotation`](creel.annotate.html.md#creel.annotate.Annotation)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – What it annotates in lacing: a lacing `Reference`, or a function
    of the creel annotation that returns one. Default: a `NodeRef` at
    [`node_path()`](#creel.export.to_lacing.node_path), a point at time 0 (a document region has no time).
  * **attributed_to** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Who is responsible, when the creel provenance does not say.
    Required in that case: lacing records a responsible party on everything.
  * **generated_by** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – lacing’s `was_generated_by`. Default:
    `adapter:creel@<creel version>`, as lacing’s own loaders stamp what they
    import; the creel extractor id stays in the body’s provenance.
  * **namespace** ([`UUID`](https://docs.python.org/3/library/uuid.html#uuid.UUID)) – The `uuid5` namespace of the lacing ids. creel ids are chosen
    per corpus, and lacing ids are unique across a whole store, so give each
    corpus its own namespace (`uuid.uuid5(CREEL_ID_NAMESPACE, corpus)`)
    when several share one lacing store.

The lacing id is [`lacing_id()`](#creel.export.to_lacing.lacing_id) of the creel id in *namespace*, so
re-exporting is idempotent. `was_derived_from` holds the lacing id of the record a creel
revision supersedes (`was_revision_of`). The body is the full creel record.
