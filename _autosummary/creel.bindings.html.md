# creel.bindings

The extraction-metadata layer: which strategy populates each grammar element.

Per decision D7 this is physically separate from the grammar (`GraphSpec`)
and joined to it on demand ([`creel.join.join()`](creel.join.html.md#creel.join.join)). A binding pairs a taxonomy
element id with either a registered strategy name + pure-data config, or a direct
extractor callable. Keeping this separate means the same grammar can be paired with
different extraction strategies for different source sets — reuse by join, not by
duplication.

Resolution is by a default chain (element-specific → type-default → global
default); unresolved elements fall back to schema-as-extractor at join time.

### Functions

| [`coerce_bindings`](#creel.bindings.coerce_bindings)(extractors)   | Normalise the facade's `extractors` argument into [`ExtractorBindings`](#creel.bindings.ExtractorBindings).   |
|--------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|

### Classes

| [`ExtractorBinding`](#creel.bindings.ExtractorBinding)(element_id[, strategy, ...])   | Bind one grammar element (or a cluster) to a strategy or a direct callable.                                 |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| [`ExtractorBindings`](#creel.bindings.ExtractorBindings)([bindings])                   | A collection of [`ExtractorBinding`](#creel.bindings.ExtractorBinding), looked up by element id. |

### *class* creel.bindings.ExtractorBinding(element_id, strategy=None, config=<factory>, extractor=None, elements=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Bind one grammar element (or a cluster) to a strategy or a direct callable.

When `elements` is set, this is a **cluster binding** (D-OP8): the extractor is
invoked **once** for the whole set of element ids (one pass over several coupled
types), rather than once per element. `element_id` is then just a label.

#### build()

Instantiate the bound extractor (direct callable wins over a named strategy).

Raises a binding-level [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError) (naming the element and strategy)
for a malformed config or missing required params, instead of leaking a
`dict`-internals or `__init__` traceback to the caller.

* **Return type:**
  [`Extractor`](creel.html.md#creel.Extractor)

### *class* creel.bindings.ExtractorBindings(bindings=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A collection of [`ExtractorBinding`](#creel.bindings.ExtractorBinding), looked up by element id.

#### DEFAULT *= '\*'*

element id used for the catch-all / global default binding.

#### for_element(element_id)

Return the binding for `element_id`, else the global default, else `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ExtractorBinding`](#creel.bindings.ExtractorBinding)]

#### *classmethod* from_mapping(mapping)

Build bindings from `{element_id: spec}` where `spec` is flexible.

`spec` may be an [`ExtractorBinding`](#creel.bindings.ExtractorBinding), a `(strategy, config)` tuple,
a `{"strategy": ..., "config": ...}` dict, or a bare extractor callable.

* **Return type:**
  [`ExtractorBindings`](#creel.bindings.ExtractorBindings)

### creel.bindings.coerce_bindings(extractors)

Normalise the facade’s `extractors` argument into [`ExtractorBindings`](#creel.bindings.ExtractorBindings).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ExtractorBindings`](#creel.bindings.ExtractorBindings)]
