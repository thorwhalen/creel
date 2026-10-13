# creel.sources

Sources — the heterogeneous inputs creel reads.

A [`Source`](#creel.sources.Source) is one unit of input with a stable `id`, a `kind` (so the
right extractor strategy can be routed to it — prose to an LLM, a table to a query
extractor), its `content`, and optionally its own `schema` (when a structured
source carries one, extraction can be made more robust).

A [`SourceBundle`](#creel.sources.SourceBundle) is an addressable collection of sources. [`coerce_sources()`](#creel.sources.coerce_sources)
makes the common cases simple: a bare string becomes one text source, a list of
sources becomes a bundle, etc. (progressive disclosure).

### Module Attributes

| [`TEXT`](#creel.sources.TEXT)   | Known source kinds.   |
|---------------------------------------------------------|-----------------------|

### Functions

| [`coerce_sources`](#creel.sources.coerce_sources)(sources)   | Normalise a flexible `sources` argument into a [`SourceBundle`](#creel.sources.SourceBundle).   |
|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|

### Classes

| [`Source`](#creel.sources.Source)(id, content[, kind, schema, metadata])   | One input unit: prose, a table, a JSON document, etc.                                                   |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [`SourceBundle`](#creel.sources.SourceBundle)([sources])                         | An addressable, iterable collection of [`Source`](#creel.sources.Source) objects. |

### *class* creel.sources.Source(id, content, kind='text', schema=None, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One input unit: prose, a table, a JSON document, etc.

### *class* creel.sources.SourceBundle(sources=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An addressable, iterable collection of [`Source`](#creel.sources.Source) objects.

#### get(source_id)

Return the source with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Source`](#creel.sources.Source)]

#### of_kind(kind)

Iterate over sources whose `kind` equals `kind`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Source`](#creel.sources.Source)]

#### texts()

Iterate over text (prose) sources.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Source`](#creel.sources.Source)]

### creel.sources.TEXT *= 'text'*

Known source kinds. Extra kinds are allowed; these are the ones built-in
strategies recognise for routing.

### creel.sources.coerce_sources(sources)

Normalise a flexible `sources` argument into a [`SourceBundle`](#creel.sources.SourceBundle).

Accepts a bare string (→ one `text` source with id `"source"`), a single
[`Source`](#creel.sources.Source), an existing [`SourceBundle`](#creel.sources.SourceBundle), an iterable of sources, or a
`{id: content_or_source}` mapping.

* **Return type:**
  [`SourceBundle`](#creel.sources.SourceBundle)
