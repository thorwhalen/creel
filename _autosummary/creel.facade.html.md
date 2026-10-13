# creel.facade

The facade: `extract(sources, graph_spec, extractors) -> graph`.

This is creel’s single public entry point and the embodiment of the whole package
(decisions D5/D7/D11). It:

1. normalises the flexible `sources` and `extractors` arguments;
2. equijoins the grammar with the extractor bindings into a runnable plan;
3. maps each resolved extractor over the sources (embarrassingly parallel in
   principle; run sequentially here for determinism and simplicity);
4. assembles the results into a Labeled Property Graph — nodes first, then the
   edges that reference them — attaching each element’s evidence to the separable
   audit sidecar;
5. returns the graph (the single source of truth), with `graph.evidence` and
   `graph.report` carrying the joinable audit/diagnostic layers.

Value-level constraint checking and faithfulness verification are the job of the
verifier subsystem (decision D6), not of the facade.

### Functions

| [`extract`](#creel.facade.extract)(sources, graph_spec[, extractors, ...])   | Read `sources`, populate the graph described by `graph_spec`, return it.   |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### creel.facade.extract(sources, graph_spec, extractors=None, , cache=None, services=None, on_missing_binding='schema_as_extractor', schema_as_extractor=None, resolve=None)

Read `sources`, populate the graph described by `graph_spec`, return it.

Args (beyond the 3rd, keyword-only):
: cache: a [`Cache`](creel.html.md#creel.Cache) for expensive extractor calls.
  services: injected dependencies (e.g. an LLM client under key `"llm"`).
  on_missing_binding: what to do for grammar elements with no extractor —
  <br/>
  > `"schema_as_extractor"` (use the `schema_as_extractor` factory if
  > available, else skip), `"skip"`, or `"error"`.
  <br/>
  schema_as_extractor: factory `(element_type, spec) -> Extractor` used for
  : unbound elements (provided by the LLM strategy layer; `None` here).
  <br/>
  resolve: an optional [`Resolver`](creel.resolve.html.md#creel.resolve.Resolver). If given, run entity
  : resolution (merge same-entity nodes + remap edges) as a post-extraction
    pass — required for messy multi-source corpora (decision #14).

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)
* **Returns:**
  A [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph) (the SSOT). `graph.evidence` maps
  element id → evidence record; `graph.report` holds run diagnostics.
