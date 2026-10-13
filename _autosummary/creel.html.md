# creel

creel — a general, AI-powered source-to-graph extraction engine.

creel extracts a typed graph from a heterogeneous set of sources (prose, tables,
JSON, schema specs) and emits it as a clean, auditable Labeled Property Graph — the
single source of truth from which downstream persistence, query, annotation, and
rendering are projected.

Conceptually the package is one parameterised facade:

```default
extract(sources, graph_spec, extractors) -> graph
```

It exposes the grammar ([`creel.spec`](creel.spec.html.md#module-creel.spec)), the graph model + canonical JSON
([`creel.graph`](creel.graph.html.md#module-creel.graph)), and the `extract` facade with all three extractor families:
deterministic pattern/function ([`creel.extract`](#creel.extract)), query
(`creel.extract.query` — `table_map`/`sql`/`json_query`), and
LLM/schema-as-extractor (`creel.extract.llm`). Around the facade sit the
pluggable verifier subsystem ([`creel.verify`](creel.verify.html.md#module-creel.verify)) and its corpus runner
([`creel.evaluation`](creel.evaluation.html.md#module-creel.evaluation)), file ingestion ([`creel.ingest`](#creel.ingest)), entity resolution
([`creel.resolve`](creel.resolve.html.md#module-creel.resolve)), the reify edge⇄node toggle ([`creel.reify`](#creel.reify)), and the
downstream view/export projections ([`creel.view`](creel.view.html.md#module-creel.view), [`creel.export`](creel.export.html.md#module-creel.export)). See
`misc/docs/design/ROADMAP.md` for the design history.

### Functions

| [`effective_attributes`](#creel.effective_attributes)(spec, type_id)               | Resolve the full attribute set for a type, including inherited attributes.                                                                                              |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`validate_graph`](#creel.validate_graph)(graph, spec, \*[, raise_on_error]) | Return the list of grammar-conformance issues for `graph` under `spec`.                                                                                                 |
| [`to_canonical_json`](#creel.to_canonical_json)(graph, \*[, spec, indent])      | Serialise `graph` to canonical JSON text — deterministic and git-diffable.                                                                                              |
| [`from_canonical_json`](#creel.from_canonical_json)(text, \*[, validate])         | Parse canonical JSON `text` into a [`Graph`](#creel.Graph) (see [`from_canonical_dict()`](#creel.from_canonical_dict)). |
| [`to_canonical_dict`](#creel.to_canonical_dict)(graph, \*[, spec])              | Build the canonical dict for `graph` (edges id-sorted; ready to serialise).                                                                                             |
| [`from_canonical_dict`](#creel.from_canonical_dict)(data, \*[, validate])         | Rebuild a [`Graph`](#creel.Graph) from a canonical dict.                                                                                 |
| [`validate_canonical`](#creel.validate_canonical)(data)                          | Validate a canonical document against the format schema.                                                                                                                |
| [`extract`](#creel.extract)(sources, graph_spec[, extractors, ...])   | Read `sources`, populate the graph described by `graph_spec`, return it.                                                                                                |
| [`ingest`](#creel.ingest)(path, \*[, source_id, loader])             | Load the file at `path` into a [`Source`](creel.sources.html.md#creel.sources.Source).                                                            |
| [`ingest_paths`](#creel.ingest_paths)(paths)                               | Load several files into one [`SourceBundle`](creel.sources.html.md#creel.sources.SourceBundle).                                                   |
| [`coerce_sources`](#creel.coerce_sources)(sources)                           | Normalise a flexible `sources` argument into a [`SourceBundle`](#creel.SourceBundle).                                                           |
| [`register_extractor`](#creel.register_extractor)(name)                          | Decorator registering an extractor *factory* under `name`.                                                                                                              |
| [`available_extractors`](#creel.available_extractors)()                            | Return the sorted names of all registered extractors (incl.                                                                                                             |
| [`resolve_graph`](#creel.resolve_graph)(graph, resolver, \*[, context])     | Return a new graph with same-entity nodes merged and edges remapped.                                                                                                    |
| [`normalize_entity`](#creel.normalize_entity)(text)                            | Normalize an entity mention for matching: casefold, strip punctuation/legal/honorific.                                                                                  |
| [`reify`](#creel.reify)(graph, edge_type, \*[, node_type, ...])     | Return a new graph with every `edge_type` edge promoted to a node.                                                                                                      |
| [`unreify`](#creel.unreify)(graph, edge_type, \*[, node_type, ...])   | Invert [`reify()`](#creel.reify): collapse well-formed relation-nodes back into edges.                                                   |
| [`to_node_edge_records`](#creel.to_node_edge_records)(graph)                       | Flatten the graph to `{"nodes": [...], "edges": [...]}` of plain records.                                                                                               |
| [`to_table`](#creel.to_table)(graph, type_id)                          | Rows for a single node-type *or* edge-type — one record per element.                                                                                                    |
| [`to_dot`](#creel.to_dot)(graph, \*[, label_attr])                   | Render the graph as Graphviz DOT (a directed multigraph).                                                                                                               |
| [`to_mermaid`](#creel.to_mermaid)(graph, \*[, label_attr])               | Render the graph as a Mermaid `flowchart` (ids aliased to be Mermaid-safe).                                                                                             |
| [`to_cytoscape`](#creel.to_cytoscape)(graph)                               | Project to Cytoscape.js `elements` (the reference interactive-view shape).                                                                                              |
| [`to_embedding_records`](#creel.to_embedding_records)(graph)                       | RAG-readiness: one `{"id","kind","type","text"}` record per element (EPIC 8.1).                                                                                         |
| [`reanchor`](#creel.reanchor)(selector, text, \*[, hint, fuzzy])       | Re-locate a `TextQuoteSelector` in (possibly changed) `text`.                                                                                                           |
| [`verify_anchor`](#creel.verify_anchor)(selector, text)                     | True if the selector's `exact` quote still occurs verbatim in `text`.                                                                                                   |
| [`set_attribute_evidence`](#creel.set_attribute_evidence)(graph, element_id, ...)    | Attach an evidence record to a specific attribute value (key `(id, attribute)`).                                                                                        |
| [`attribute_evidence`](#creel.attribute_evidence)(graph, element_id, attribute)  | Return the per-attribute evidence for `(element_id, attribute)`, or the element-level evidence as a fallback, or `None`.                                                |
| [`to_jgf`](#creel.to_jgf)(graph)                                     | Project to JSON Graph Format (v2-style: nodes as an id→object map).                                                                                                     |
| [`to_graphml`](#creel.to_graphml)(graph)                                 | Emit GraphML XML (string attributes; one `<key>` per attribute, id-sorted).                                                                                             |
| [`to_cypher`](#creel.to_cypher)(graph)                                  | Return `(statement, params)` pairs to load the graph into Neo4j safely.                                                                                                 |
| [`to_turtle`](#creel.to_turtle)(graph, \*[, base])                      | Emit RDF-star Turtle; edge attributes annotate quoted triples `<< s p o >>`.                                                                                            |
| [`schema_description_verifier`](#creel.schema_description_verifier)(element_type, \*)     | Build the default `llm_rubric` for an element, seeded from its `description`.                                                                                           |
| [`build_verifier`](#creel.build_verifier)(name, \*\*config)                  | Instantiate the named verifier with its `config`.                                                                                                                       |
| [`register_verifier`](#creel.register_verifier)(name)                           | Decorator registering a verifier *factory* under `name`.                                                                                                                |
| [`available_verifiers`](#creel.available_verifiers)()                             | Return the sorted names of all registered verifiers (incl.                                                                                                              |
| [`evaluate_case`](#creel.evaluate_case)(case)                               | Extract `case.sources` and score the result against `case.expected_graph`.                                                                                              |
| [`evaluate_corpus`](#creel.evaluate_corpus)(cases)                            | Evaluate every case and aggregate the results.                                                                                                                          |

### Classes

| [`AttrSchema`](#creel.AttrSchema)(name[, range, required, ...])          | Typed schema for a single attribute (a "leaf" value) of a node or edge.                                                                           |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`EnumDef`](#creel.EnumDef)(name, permissible_values[, description])  | A named, reusable set of permissible values (a constrained value-set).                                                                            |
| [`ElementType`](#creel.ElementType)(id[, description, is_a, mixins, ...]) | Base for a node-type or edge-type — a position in a recursive taxonomy.                                                                           |
| [`NodeType`](#creel.NodeType)(id[, description, is_a, mixins, ...])    | A node-type (a.k.a.                                                                                                                               |
| [`EdgeType`](#creel.EdgeType)(id[, description, is_a, mixins, ...])    | An edge-type (a.k.a.                                                                                                                              |
| [`GraphSpec`](#creel.GraphSpec)([node_types, edge_types, enums, ...])   | A complete graph grammar: node-types, edge-types, and reusable enums.                                                                             |
| [`ValidationIssue`](#creel.ValidationIssue)(element, element_id, code, ...)   | A single grammar-conformance problem found in an instance graph.                                                                                  |
| [`Graph`](#creel.Graph)()                                           | A labeled property (multi-)graph with stable ids on nodes and edges.                                                                              |
| [`Node`](#creel.Node)(id, types[, attributes])                     | An immutable view of a graph node: its id, type label(s), and attributes.                                                                         |
| [`Edge`](#creel.Edge)(id, source, target, type[, attributes])      | An immutable view of a graph edge: a first-class, identity-bearing relation.                                                                      |
| [`Source`](#creel.Source)(id, content[, kind, schema, metadata])     | One input unit: prose, a table, a JSON document, etc.                                                                                             |
| [`SourceBundle`](#creel.SourceBundle)([sources])                           | An addressable, iterable collection of [`Source`](#creel.Source) objects.                                           |
| [`Extractor`](#creel.Extractor)(\*args, \*\*kwargs)                     | A strategy that extracts instances of one grammar element from sources.                                                                           |
| [`ExtractionContext`](#creel.ExtractionContext)(element_id, element_type, ...)  | Everything an extractor needs to do its job for one grammar element.                                                                              |
| [`Extraction`](#creel.Extraction)([nodes, edges, notes])                 | The result of running one extractor: the nodes and/or edges it found.                                                                             |
| [`ExtractedNode`](#creel.ExtractedNode)(id, type[, attributes, evidence])   | A node instance produced by an extractor (id + type label + attributes).                                                                          |
| [`ExtractedEdge`](#creel.ExtractedEdge)(id, type, source, target[, ...])    | An edge instance produced by an extractor (first-class, with own attributes).                                                                     |
| [`RegexNodeExtractor`](#creel.RegexNodeExtractor)(pattern[, node_type, ...])     | Produce nodes from regex matches over text sources.                                                                                               |
| [`RegexEdgeExtractor`](#creel.RegexEdgeExtractor)(pattern, ...[, ...])           | Produce first-class edges from regex matches over text sources.                                                                                   |
| [`Cache`](#creel.Cache)(\*args, \*\*kwargs)                         | A minimal get/set cache.                                                                                                                          |
| [`NullCache`](#creel.NullCache)()                                       | The default cache: stores nothing, always misses.                                                                                                 |
| [`DictCache`](#creel.DictCache)()                                       | A simple in-memory cache backed by a dict (handy for tests and single runs).                                                                      |
| [`ExtractorBinding`](#creel.ExtractorBinding)(element_id[, strategy, ...])     | Bind one grammar element (or a cluster) to a strategy or a direct callable.                                                                       |
| [`ExtractorBindings`](#creel.ExtractorBindings)([bindings])                     | A collection of [`ExtractorBinding`](#creel.ExtractorBinding), looked up by element id.                                       |
| [`ExtractionPolicy`](#creel.ExtractionPolicy)([max_retries, ...])              | How the LLM extractor should try, escalate, and flag for review.                                                                                  |
| [`Resolver`](#creel.Resolver)(\*args, \*\*kwargs)                      | Decide whether two nodes denote the same real entity.                                                                                             |
| [`NormalizeResolver`](#creel.NormalizeResolver)([key, aliases])                 | Match by a normalized key attribute (+ an optional alias table).                                                                                  |
| [`RegistryResolver`](#creel.RegistryResolver)(registry[, key])                 | Resolve mentions to canonical ids via an authoritative lookup table (an org registry).                                                            |
| [`LLMResolver`](#creel.LLMResolver)(judge[, key])                         | Adjudicate hard pairs with an injected judge `(name_a, name_b) -> bool`.                                                                          |
| [`CascadeResolver`](#creel.CascadeResolver)(resolvers)                        | Try resolvers in order (cheapest first); two nodes match if ANY resolver matches.                                                                 |
| [`Annotation`](#creel.Annotation)(id, target, body[, motivation, ...])   | A standoff annotation linking a `target` to a `body` with a `motivation`.                                                                         |
| [`Selection`](#creel.Selection)(id, source_id, selector)                | A reified, shareable selection of a source region (id + a grounding selector).                                                                    |
| [`AnnotatedGraph`](#creel.AnnotatedGraph)(graph[, annotations, ...])         | The render contract: graph + standoff annotation overlay + presentation hints.                                                                    |
| [`GraphRenderer`](#creel.GraphRenderer)(\*args, \*\*kwargs)                 | Render an [`AnnotatedGraph`](#creel.AnnotatedGraph) into a [`RenderArtifact`](#creel.RenderArtifact). |
| [`RenderArtifact`](#creel.RenderArtifact)(content, media_type[, metadata])   | The output of a renderer: content (str/bytes/dict) + its media type.                                                                              |
| [`TraceIndex`](#creel.TraceIndex)(graph)                                 | A rebuildable index from source locations to the elements grounded there.                                                                         |
| [`Evidence`](#creel.Evidence)(provenance[, grounding, confidence])     | The full audit record for one element: provenance + grounding + confidence.                                                                       |
| [`Provenance`](#creel.Provenance)(derived_from, generated_by[, ...])     | Where an element came from (PROV-lite + PAV as plain JSON keys).                                                                                  |
| [`Confidence`](#creel.Confidence)(method, score[, verified, ...])        | How sure we are, tagged with the *method* (scores are not cross-comparable).                                                                      |
| [`TextQuoteSelector`](#creel.TextQuoteSelector)(exact[, prefix, suffix])        | Anchor by quoting the exact source text plus a little surrounding context.                                                                        |
| [`TextPositionSelector`](#creel.TextPositionSelector)(start, end[, source_id])     | Anchor by character offsets `[start, end)` within a source.                                                                                       |
| [`Verifier`](#creel.Verifier)(\*args, \*\*kwargs)                      | A strategy that scores an `actual` value against an `expected` one.                                                                               |
| [`Verdict`](#creel.Verdict)(score, passed[, reason, details])         | The result of a verification: a normalised score plus an audit trail.                                                                             |
| [`VerificationContext`](#creel.VerificationContext)([element_type, spec, ...])    | Optional context a verifier may consult (element schema, services, config).                                                                       |
| [`ExactMatch`](#creel.ExactMatch)()                                      | `score=1.0` iff `actual == expected`; else `0.0`.                                                                                                 |
| [`NormalizedMatch`](#creel.NormalizedMatch)([casefold, strip, collapse_ws])   | Equality after normalising strings (casefold / strip / collapse whitespace).                                                                      |
| [`NumericTolerance`](#creel.NumericTolerance)([abs_tol, rel_tol])              | Compare numbers within an absolute and/or relative tolerance.                                                                                     |
| [`SetMatch`](#creel.SetMatch)([key, threshold])                        | Set-based precision/recall/F1 over (canonicalised) collections.                                                                                   |
| [`SchemaConstraint`](#creel.SchemaConstraint)([spec, predicate, description])  | Property-based check with **no expected value** — validates `actual` itself.                                                                      |
| [`SemanticSimilarity`](#creel.SemanticSimilarity)([threshold])                   | Similarity of free text.                                                                                                                          |
| [`Composite`](#creel.Composite)([components, threshold])                | Weighted combination of named sub-verifiers (promptfoo-style).                                                                                    |
| [`GraphMatch`](#creel.GraphMatch)([spec, attribute_verifiers, ...])      | Score an `actual` [`Graph`](#creel.Graph) against an `expected` one (partial credit).                              |
| [`LLMRubric`](#creel.LLMRubric)(criterion[, threshold, ...])            | Grade `actual` (optionally against `expected`) by a natural-language criterion.                                                                   |
| [`CorpusCase`](#creel.CorpusCase)(name, sources, spec, bindings, ...)    | One evaluation item: inputs + how to extract + the expected graph.                                                                                |
| [`CaseResult`](#creel.CaseResult)(name, verdict, actual_graph)           | The outcome of evaluating one case: the verdict + the produced graph.                                                                             |
| [`CorpusResult`](#creel.CorpusResult)(cases)                               | Aggregate outcome over a corpus.                                                                                                                  |

### Exceptions

| [`GraphValidationError`](#creel.GraphValidationError)(issues)   | Raised by [`validate_graph()`](#creel.validate_graph) when `raise_on_error` and issues exist.   |
|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|

### *class* creel.AnnotatedGraph(graph, annotations=(), presentation=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The render contract: graph + standoff annotation overlay + presentation hints.

#### annotations_for(element_id)

Return the annotations whose target is (or starts at) `element_id`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Annotation`](creel.annotate.html.md#creel.annotate.Annotation)]

### *class* creel.Annotation(id, target, body, motivation='commenting', provenance=None, confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A standoff annotation linking a `target` to a `body` with a `motivation`.

`target`: an element id (str), an `(element_id, attribute)` tuple, or a
[`Selection`](#creel.Selection) (a source span). `body`: a graph-element/category ref (str),
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

### *class* creel.AttrSchema(name, range='string', required=False, multivalued=False, enum=None, minimum=None, maximum=None, pattern=None, description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Typed schema for a single attribute (a “leaf” value) of a node or edge.

These follow ordinary schema semantics: a value may be a freeform string or
number (or lists thereof via `multivalued`), or constrained to an `enum`,
bounded by `minimum`/`maximum`, or matched against a `pattern`.

The `description` is load-bearing: it doubles as the default natural-language
instruction for the *schema-as-extractor* and *schema-as-verifier* defaults, so
a usable extraction/verification can often be derived from the grammar alone.

#### NOTE
`minimum`/`maximum` are *value-level* constraints. Per decision D6
they are enforced in the verification pass, not by an LLM decoder’s grammar.

### *class* creel.Cache(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A minimal get/set cache. Implementations must be exact-match.

#### get(key)

Return the cached value for `key`, or `None` if absent.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### set(key, value)

Store `value` under `key`.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* creel.CascadeResolver(resolvers)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Try resolvers in order (cheapest first); two nodes match if ANY resolver matches.

#### canonical_id(cluster)

Use the first resolver that can name a canonical id; else the smallest id.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.CaseResult(name, verdict, actual_graph)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The outcome of evaluating one case: the verdict + the produced graph.

#### *property* passed *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the case met its verifier’s threshold.

#### *property* score *: [float](https://docs.python.org/3/builtins/functions.html#float)*

The case’s normalised score in `[0, 1]`.

### *class* creel.Composite(components=<factory>, threshold=0.5)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Weighted combination of named sub-verifiers (promptfoo-style).

### *class* creel.Confidence(method, score, verified=None, review_status='auto')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How sure we are, tagged with the *method* (scores are not cross-comparable).

#### to_dict()

Serialise to a plain dict, omitting an unset `verified` flag.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.CorpusCase(name, sources, spec, bindings, expected_graph, verifier=None, attribute_verifiers=<factory>, services=<factory>, on_missing_binding='skip')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One evaluation item: inputs + how to extract + the expected graph.

### *class* creel.CorpusResult(cases)

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

### *class* creel.DictCache

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A simple in-memory cache backed by a dict (handy for tests and single runs).

#### get(key)

Return the cached value for `key`, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### set(key, value)

Store `value` under `key`.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* creel.Edge(id, source, target, type, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph edge: a first-class, identity-bearing relation.

### *class* creel.EdgeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False, subject_type=None, object_type=None)

Bases: [`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)

An edge-type (a.k.a. link type): first-class, with its own typed attributes.

`subject_type` and `object_type` name the node-types this edge connects
(its endpoints). Edges have their own identity, so two `funds` edges between
the same donor and project (two distinct fundings) are distinguishable.

### *class* creel.ElementType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Base for a node-type or edge-type — a position in a recursive taxonomy.

The taxonomy is expressed by `is_a` (single-inheritance parent) plus
`mixins` (multiple inheritance). An element’s *effective* attributes are its
own plus all inherited ones (see [`effective_attributes()`](#creel.effective_attributes)). `id` is an
opaque identifier and may be a dotted path (e.g. `"result.outcome"`) by
convention, but the real hierarchy is the `is_a`/`mixins` graph.

#### attribute(name)

Return this type’s *own* attribute schema named `name` (no inheritance).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`AttrSchema`](creel.spec.model.html.md#creel.spec.model.AttrSchema)]

#### *property* parents *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

All direct supertype ids (`is_a` then `mixins`).

### *class* creel.EnumDef(name, permissible_values, description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A named, reusable set of permissible values (a constrained value-set).

### *class* creel.Evidence(provenance, grounding=(), confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The full audit record for one element: provenance + grounding + confidence.

#### to_dict()

Serialise the whole record to plain, JSON-ready dicts.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.ExactMatch

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

`score=1.0` iff `actual == expected`; else `0.0`. The auditable default.

### *class* creel.ExtractedEdge(id, type, source, target, attributes=<factory>, evidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An edge instance produced by an extractor (first-class, with own attributes).

### *class* creel.ExtractedNode(id, type, attributes=<factory>, evidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A node instance produced by an extractor (id + type label + attributes).

### *class* creel.Extraction(nodes=(), edges=(), notes=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The result of running one extractor: the nodes and/or edges it found.

#### *property* is_empty *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if the extraction produced no nodes and no edges.

### *class* creel.ExtractionContext(element_id, element_type, sources, spec, cache=<factory>, services=<factory>, config=<factory>, element_types=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything an extractor needs to do its job for one grammar element.

`element_id` is the taxonomy id being extracted (a node-type or edge-type id);
`element_type` is its typed schema (whose attribute `description``s drive the
schema-as-extractor default). ``services` carries injected dependencies (an LLM
client, an entity resolver, …) so the core never imports a provider SDK.

#### element_types *: [Sequence](https://docs.python.org/3/library/typing.html#typing.Sequence)[[ElementType](creel.spec.model.html.md#creel.spec.model.ElementType)]* *= ()*

The cluster of element types this pass covers (D-OP8). Defaults to just
`(element_type,)`; a cluster extractor reads all of them and emits instances
of each in a single LLM pass. `element_id`/`element_type` are the primary
(first) of the cluster, so single-element extractors are unaffected.

### *class* creel.ExtractionPolicy(max_retries=2, self_consistency_samples=1, review_below=0.5, overrides=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How the LLM extractor should try, escalate, and flag for review.

* **Parameters:**
  * **max_retries** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – validate-retry attempts for shape/constraint failures.
  * **self_consistency_samples** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – if >1, draw N samples and keep the modal result;
    confidence becomes the agreement fraction (`self_consistency` method).
  * **review_below** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – any element whose confidence score is below this is marked
    `needs_review` (human-in-the-loop gate).
  * **overrides** ([`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`ExtractionPolicy`](creel.policy.html.md#creel.policy.ExtractionPolicy)]) – per element-id or per type-id policies (most specific wins).

#### for_element(element_id, type_id=None)

Resolve the effective policy for an element (element-id → type-id → self).

* **Return type:**
  [`ExtractionPolicy`](creel.policy.html.md#creel.policy.ExtractionPolicy)

### *class* creel.Extractor(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A strategy that extracts instances of one grammar element from sources.

Any callable `(ExtractionContext) -> Extraction` satisfies this Protocol.

### *class* creel.ExtractorBinding(element_id, strategy=None, config=<factory>, extractor=None, elements=None)

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
  [`Extractor`](#creel.Extractor)

### *class* creel.ExtractorBindings(bindings=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A collection of [`ExtractorBinding`](#creel.ExtractorBinding), looked up by element id.

#### DEFAULT *= '\*'*

element id used for the catch-all / global default binding.

#### for_element(element_id)

Return the binding for `element_id`, else the global default, else `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ExtractorBinding`](creel.bindings.html.md#creel.bindings.ExtractorBinding)]

#### *classmethod* from_mapping(mapping)

Build bindings from `{element_id: spec}` where `spec` is flexible.

`spec` may be an [`ExtractorBinding`](#creel.ExtractorBinding), a `(strategy, config)` tuple,
a `{"strategy": ..., "config": ...}` dict, or a bare extractor callable.

* **Return type:**
  [`ExtractorBindings`](creel.bindings.html.md#creel.bindings.ExtractorBindings)

### *class* creel.Graph

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A labeled property (multi-)graph with stable ids on nodes and edges.

Edge ids are unique across the whole graph (not merely per node pair); this is
what makes the canonical JSON edge-by-id map and per-element provenance possible
(decision D4/D8).

#### add_edge(edge_id, , source, target, type, attributes=None)

Add a typed edge with an explicit, globally-unique id.

Raises `ValueError` if `edge_id` already exists (edge identity is
sacred) or if an endpoint is missing.

* **Return type:**
  [`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)

#### add_node(node_id, , types=(), attributes=None)

Add (or merge into) a node. Re-adding an id merges types/attributes.

Merging makes extraction idempotent: the same entity surfaced by two
extractors lands on one node rather than duplicating.

* **Return type:**
  [`Node`](creel.graph.model.html.md#creel.graph.model.Node)

#### edge(edge_id)

Return the [`Edge`](#creel.Edge) view, or raise `KeyError`.

* **Return type:**
  [`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)

#### edges()

Iterate over all edges.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### edges_between(source, target)

Iterate over all (parallel) edges from `source` to `target`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### edges_of_type(type_id)

Iterate over edges of relation type `type_id`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Edge`](creel.graph.model.html.md#creel.graph.model.Edge)]

#### evidence *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

element id -> evidence record (D8). Populated by
the facade; deliberately NOT part of the canonical JSON (joined on demand).

* **Type:**
  Separable audit sidecar

#### has_edge(edge_id)

True if an edge with this id exists.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### has_node(node_id)

True if a node with this id exists.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### node(node_id)

Return the [`Node`](#creel.Node) view, or raise `KeyError`.

* **Return type:**
  [`Node`](creel.graph.model.html.md#creel.graph.model.Node)

#### nodes()

Iterate over all nodes.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](creel.graph.model.html.md#creel.graph.model.Node)]

#### nodes_of_type(type_id)

Iterate over nodes carrying `type_id` as one of their labels.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Node`](creel.graph.model.html.md#creel.graph.model.Node)]

#### *property* number_of_edges *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Count of edges.

#### *property* number_of_nodes *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Count of nodes.

#### report *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

Free-form run report (e.g. skipped edges, unbound elements) attached by
the facade; also excluded from canonical JSON.

#### to_networkx()

Return a copy of the underlying `networkx.MultiDiGraph`.

* **Return type:**
  `MultiDiGraph`

### *class* creel.GraphMatch(spec=None, attribute_verifiers=<factory>, node_weight=1.0, edge_weight=1.0, attr_weight=1.0, threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Score an `actual` [`Graph`](#creel.Graph) against an `expected` one (partial credit).

### *class* creel.GraphRenderer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Render an [`AnnotatedGraph`](#creel.AnnotatedGraph) into a [`RenderArtifact`](#creel.RenderArtifact).

#### render(graph, , options=None)

Produce the rendered artifact.

* **Return type:**
  [`RenderArtifact`](creel.render.html.md#creel.render.RenderArtifact)

### *class* creel.GraphSpec(node_types=(), edge_types=(), enums=(), id=None, version='0.1.0', description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A complete graph grammar: node-types, edge-types, and reusable enums.

This is the graph-definition layer (SSOT). It knows nothing about extraction.

#### edge_type(type_id)

Return the edge-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`EdgeType`](creel.spec.model.html.md#creel.spec.model.EdgeType)]

#### element_type(type_id)

Return the node- or edge-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)]

#### enum(name)

Return the named enum, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`EnumDef`](creel.spec.model.html.md#creel.spec.model.EnumDef)]

#### is_subtype(type_id, ancestor_id)

True if `type_id` equals or descends from `ancestor_id` (is_a + mixins).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### iter_element_types()

Yield every node-type then every edge-type.

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)]

#### node_type(type_id)

Return the node-type with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`NodeType`](creel.spec.model.html.md#creel.spec.model.NodeType)]

#### with_(\*\*changes)

Return a copy of this spec with the given top-level fields replaced.

* **Return type:**
  [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec)

### *exception* creel.GraphValidationError(issues)

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

Raised by [`validate_graph()`](#creel.validate_graph) when `raise_on_error` and issues exist.

### *class* creel.LLMResolver(judge, key='name')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Adjudicate hard pairs with an injected judge `(name_a, name_b) -> bool`.

The judge is injected (testable with a fake; an LLM in production via `creel[llm]`).
Reserve this for pairs the cheap resolvers leave ambiguous — it is the costly tail.

### *class* creel.LLMRubric(criterion, threshold=0.5, reference_free=False, instructions=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Grade `actual` (optionally against `expected`) by a natural-language criterion.

Set `reference_free=True` to grade `actual` against the criterion alone (no
gold value). `threshold` sets the pass bar.

### *class* creel.Node(id, types, attributes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An immutable view of a graph node: its id, type label(s), and attributes.

### *class* creel.NodeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)

A node-type (a.k.a. point type). Carries typed attributes and a taxonomy.

### *class* creel.NormalizeResolver(key='name', aliases=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Match by a normalized key attribute (+ an optional alias table). The cheap default.

#### canonical_id(cluster)

A stable id from the normalized key + type.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.NormalizedMatch(casefold=True, strip=True, collapse_ws=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Equality after normalising strings (casefold / strip / collapse whitespace).

### *class* creel.NullCache

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The default cache: stores nothing, always misses.

#### get(key)

Always a miss (returns `None`).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

#### set(key, value)

No-op.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### *class* creel.NumericTolerance(abs_tol=0.0, rel_tol=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Compare numbers within an absolute and/or relative tolerance.

For funding amounts and indicator values on edges — a brittle `==` would
spuriously fail on `1000000` vs `1000000.0` or rounding.

### *class* creel.Provenance(derived_from, generated_by, attributed_to=None, attributed_kind=None, coded_by=None, was_revision_of=None, generated_at=None, version=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where an element came from (PROV-lite + PAV as plain JSON keys).

`attributed_kind` (`software_agent` | `person`) + `was_revision_of` make
the machine-extracted / manually-coded / human-corrected distinction *derivable*
(decision A5): non-destructive correction records a new provenance pointing at the
superseded one, rather than overwriting.

#### *property* is_corrected *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if this is a person’s revision of an earlier (machine or human) record.

#### *property* is_machine *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if attributed to a software agent and not a human correction.

#### *property* is_manual *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if attributed to a person with no machine antecedent (manual coding).

#### to_dict()

Serialise to a plain dict, omitting unset optional keys.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.RegexEdgeExtractor(pattern, source_id_template, target_id_template, edge_type=None, flags=0, casts=<factory>, exclude_groups=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Produce first-class edges from regex matches over text sources.

`source_id_template`/`target_id_template` build the endpoint node ids from
the captured groups (e.g. `"donor:{donor}"`); remaining groups not consumed by
the templates become edge attributes.

### *class* creel.RegexNodeExtractor(pattern, node_type=None, flags=0, id_attribute=None, casts=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Produce nodes from regex matches over text sources.

The named capture groups become the node’s attributes; `id_attribute` (or a
content hash) yields a stable node id; `casts` converts captured strings to
numbers where the grammar expects them.

### *class* creel.RegistryResolver(registry, key='name')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Resolve mentions to canonical ids via an authoritative lookup table (an org registry).

#### canonical_id(cluster)

The registry’s canonical id for the cluster.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* creel.RenderArtifact(content, media_type, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The output of a renderer: content (str/bytes/dict) + its media type.

### *class* creel.Resolver(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Decide whether two nodes denote the same real entity.

#### same(a, b, , context=None)

Return `True` if `a` and `b` are the same entity.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### *class* creel.SchemaConstraint(spec=None, predicate=None, description='schema constraint')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Property-based check with **no expected value** — validates `actual` itself.

Pass either a [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec) (validates a graph against the
grammar) or a `predicate(actual) -> bool` with a `description`.

### *class* creel.Selection(id, source_id, selector)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A reified, shareable selection of a source region (id + a grounding selector).

#### to_dict()

Serialise to a plain dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.SemanticSimilarity(threshold=0.8)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Similarity of free text. Uses an injected `embedder` if available, else a
deterministic lexical fallback (`difflib` ratio) — which is flagged, because
similarity is not equivalence.

### *class* creel.SetMatch(key=None, threshold=1.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Set-based precision/recall/F1 over (canonicalised) collections.

`key` maps each item to a hashable canonical form before comparing (so dicts
or fuzzy items can be aligned). `score` is the F1.

### *class* creel.Source(id, content, kind='text', schema=None, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One input unit: prose, a table, a JSON document, etc.

### *class* creel.SourceBundle(sources=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An addressable, iterable collection of [`Source`](#creel.Source) objects.

#### get(source_id)

Return the source with this id, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Source`](creel.sources.html.md#creel.sources.Source)]

#### of_kind(kind)

Iterate over sources whose `kind` equals `kind`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Source`](creel.sources.html.md#creel.sources.Source)]

#### texts()

Iterate over text (prose) sources.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Source`](creel.sources.html.md#creel.sources.Source)]

### *class* creel.TextPositionSelector(start, end, source_id=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor by character offsets `[start, end)` within a source.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.TextQuoteSelector(exact, prefix='', suffix='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor by quoting the exact source text plus a little surrounding context.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.TraceIndex(graph)

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

### *class* creel.ValidationIssue(element, element_id, code, message)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single grammar-conformance problem found in an instance graph.

### *class* creel.Verdict(score, passed, reason='', details=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The result of a verification: a normalised score plus an audit trail.

#### to_dict()

Serialise to a plain dict (reasons retained for audit).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.VerificationContext(element_type=None, spec=None, services=<factory>, config=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Optional context a verifier may consult (element schema, services, config).

`services` carries injected dependencies such as an LLM `"judge"` (which
must differ from the extractor model — D9) or an `"embedder"` for semantic
similarity. `element_type`/`spec` let a verifier read the schema (e.g. to
seed an `llm_rubric` from a `description`).

### *class* creel.Verifier(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A strategy that scores an `actual` value against an `expected` one.

### creel.attribute_evidence(graph, element_id, attribute)

Return the per-attribute evidence for `(element_id, attribute)`, or the
element-level evidence as a fallback, or `None`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Evidence`](creel.evidence.html.md#creel.evidence.Evidence)]

### creel.available_extractors()

Return the sorted names of all registered extractors (incl. entry points).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### creel.available_verifiers()

Return the sorted names of all registered verifiers (incl. entry points).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### creel.build_verifier(name, \*\*config)

Instantiate the named verifier with its `config`.

* **Return type:**
  [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)

### creel.coerce_sources(sources)

Normalise a flexible `sources` argument into a [`SourceBundle`](#creel.SourceBundle).

Accepts a bare string (→ one `text` source with id `"source"`), a single
[`Source`](#creel.Source), an existing [`SourceBundle`](#creel.SourceBundle), an iterable of sources, or a
`{id: content_or_source}` mapping.

* **Return type:**
  [`SourceBundle`](creel.sources.html.md#creel.sources.SourceBundle)

### creel.effective_attributes(spec, type_id)

Resolve the full attribute set for a type, including inherited attributes.

Walks `is_a` then `mixins` (depth-first), with a subtype’s own attributes
overriding inherited ones of the same name. Returns an insertion-ordered dict
keyed by attribute name. Unknown `type_id` yields an empty dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`AttrSchema`](creel.spec.model.html.md#creel.spec.model.AttrSchema)]

### creel.evaluate_case(case)

Extract `case.sources` and score the result against `case.expected_graph`.

* **Return type:**
  [`CaseResult`](creel.evaluation.html.md#creel.evaluation.CaseResult)

### creel.evaluate_corpus(cases)

Evaluate every case and aggregate the results.

* **Return type:**
  [`CorpusResult`](creel.evaluation.html.md#creel.evaluation.CorpusResult)

### creel.extract(sources, graph_spec, extractors=None, , cache=None, services=None, on_missing_binding='schema_as_extractor', schema_as_extractor=None, resolve=None)

Read `sources`, populate the graph described by `graph_spec`, return it.

Args (beyond the 3rd, keyword-only):
: cache: a [`Cache`](#creel.Cache) for expensive extractor calls.
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

### creel.from_canonical_dict(data, , validate=True)

Rebuild a [`Graph`](#creel.Graph) from a canonical dict.

With `validate=True` (default) the document is checked against
`CANONICAL_GRAPH_SCHEMA` before loading, so malformed input fails fast
with a clear error rather than a confusing `KeyError` mid-build.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.from_canonical_json(text, , validate=True)

Parse canonical JSON `text` into a [`Graph`](#creel.Graph) (see [`from_canonical_dict()`](#creel.from_canonical_dict)).

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.ingest(path, , source_id=None, loader=None)

Load the file at `path` into a [`Source`](creel.sources.html.md#creel.sources.Source).

The loader is chosen by file extension unless one is passed explicitly. The
`source_id` defaults to the file stem (so a binding can reference it by name).

* **Return type:**
  [`Source`](creel.sources.html.md#creel.sources.Source)

### creel.ingest_paths(paths)

Load several files into one [`SourceBundle`](creel.sources.html.md#creel.sources.SourceBundle).

* **Return type:**
  [`SourceBundle`](creel.sources.html.md#creel.sources.SourceBundle)

### creel.normalize_entity(text)

Normalize an entity mention for matching: casefold, strip punctuation/legal/honorific.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.reanchor(selector, text, , hint=None, fuzzy=True)

Re-locate a `TextQuoteSelector` in (possibly changed) `text`.

Strategy (Hypothes.is-style): exact match → disambiguate multiple hits by
prefix/suffix context (and `hint` position) → bounded fuzzy fallback. Returns the
`(start, end)` of the relocated quote, or `None` if it can’t be found. A caller
that resolves only via the fuzzy path should downgrade the element to needs-review.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)]]

### creel.register_extractor(name)

Decorator registering an extractor *factory* under `name`.

The decorated object is a factory `(**config) -> Extractor`. A plain extractor
callable can be registered by wrapping it in a factory that ignores config.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Extractor`](#creel.Extractor)]], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Extractor`](#creel.Extractor)]]

### creel.register_verifier(name)

Decorator registering a verifier *factory* under `name`.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis), [`Verifier`](creel.verify.protocol.html.md#creel.verify.protocol.Verifier)]]

### creel.reify(graph, edge_type, , node_type=None, subject_edge_type=None, object_edge_type=None)

Return a new graph with every `edge_type` edge promoted to a node.

Each promoted edge becomes a node (id = the edge’s id, type `node_type`,
carrying the edge’s attributes), with `source ──subject──▶ node ──object──▶ target`
connector edges. All other nodes/edges (and the evidence sidecar) pass through
unchanged. Other edge-types are untouched, so this is a per-edge-type toggle.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.resolve_graph(graph, resolver, , context=None)

Return a new graph with same-entity nodes merged and edges remapped.

Blocking (by node type-tuple) → matching (`resolver.same`) → merging (union-find;
one canonical node per cluster, attributes first-wins) → edge remap. The original
graph is untouched; the result’s `report["merges"]` lists each merge.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.schema_description_verifier(element_type, , threshold=0.5)

Build the default `llm_rubric` for an element, seeded from its `description`.

This is the schema-as-verifier default: the same `description` that drives the
schema-as-extractor also becomes the grading criterion.

* **Return type:**
  [`LLMRubric`](creel.verify.rubric.html.md#creel.verify.rubric.LLMRubric)

### creel.set_attribute_evidence(graph, element_id, attribute, evidence)

Attach an evidence record to a specific attribute value (key `(id, attribute)`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### creel.to_canonical_dict(graph, , spec=None)

Build the canonical dict for `graph` (edges id-sorted; ready to serialise).

If `spec` is given, a lightweight `{"id", "version"}` reference is recorded
so a reader knows which grammar the instance claims to conform to.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.to_canonical_json(graph, , spec=None, indent=2)

Serialise `graph` to canonical JSON text — deterministic and git-diffable.

Keys are sorted and edge arrays are id-sorted, so the same graph always yields
byte-identical output regardless of insertion order.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.to_cypher(graph)

Return `(statement, params)` pairs to load the graph into Neo4j safely.

Relationship *types* cannot be parameterized in Cypher, so a generic `:REL` is
used with a `type` property. Bind `params` via the driver — never interpolate.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]]

### creel.to_cytoscape(graph)

Project to Cytoscape.js `elements` (the reference interactive-view shape).

Node `data` is near-isomorphic to the canonical node object, which is why
Cytoscape is the natural default interactive view (decision D15).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.to_dot(graph, , label_attr=None)

Render the graph as Graphviz DOT (a directed multigraph).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.to_embedding_records(graph)

RAG-readiness: one `{"id","kind","type","text"}` record per element (EPIC 8.1).

`text` is a compact natural-language rendering of the element (type + attributes;
for edges, the relation and its endpoints) suitable for embedding into a vector
index, so the extracted graph flows into graph+vector RAG without coupling.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### creel.to_graphml(graph)

Emit GraphML XML (string attributes; one `<key>` per attribute, id-sorted).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.to_jgf(graph)

Project to JSON Graph Format (v2-style: nodes as an id→object map).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.to_mermaid(graph, , label_attr=None)

Render the graph as a Mermaid `flowchart` (ids aliased to be Mermaid-safe).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.to_node_edge_records(graph)

Flatten the graph to `{"nodes": [...], "edges": [...]}` of plain records.

Each node record is `{"id", "types", **attributes}`; each edge record is
`{"id", "type", "source", "target", **attributes}`. Ideal input for a
DataFrame, a table renderer, or a CSV export.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]]

### creel.to_table(graph, type_id)

Rows for a single node-type *or* edge-type — one record per element.

Returns node rows if `type_id` is a node-type present in the graph, else edge
rows for that edge-type (else an empty list).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

### creel.to_turtle(graph, , base='https://creel.dev/ns/')

Emit RDF-star Turtle; edge attributes annotate quoted triples `<< s p o >>`.

This is the lossless LPG↔RDF-star export (report R01). Caveat: parallel edges of
the same `(source, type, target)` annotate the same quoted triple — distinguish
them downstream by also reifying on the edge id if needed.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.unreify(graph, edge_type, , node_type=None, subject_edge_type=None, object_edge_type=None)

Invert [`reify()`](#creel.reify): collapse well-formed relation-nodes back into edges.

Only nodes of `node_type` that carry **both** a subject and object connector are
collapsed, and only *their* connector edges are removed — so foreign edges that
merely share the connector type, and incomplete/hand-authored nodes of the same
type, are preserved (the toggle is safe on partial/foreign input).

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.validate_canonical(data)

Validate a canonical document against the format schema.

Raises `jsonschema.ValidationError` if `data` is not a well-formed canonical
graph document.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### creel.validate_graph(graph, spec, , raise_on_error=False)

Return the list of grammar-conformance issues for `graph` under `spec`.

With `raise_on_error=True`, raises [`GraphValidationError`](#creel.GraphValidationError) if any issue
is found instead of returning the list.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](creel.spec.validate.html.md#creel.spec.validate.ValidationIssue)]

### creel.verify_anchor(selector, text)

True if the selector’s `exact` quote still occurs verbatim in `text`.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### Modules

| [`annotate`](creel.annotate.html.md#module-creel.annotate)     | Annotations — the standoff overlay for machine insight AND human coding (D-OP9 / A2).    |
|-------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`bindings`](creel.bindings.html.md#module-creel.bindings)     | The extraction-metadata layer: which strategy populates each grammar element.            |
| [`evaluation`](creel.evaluation.html.md#module-creel.evaluation) | The evaluation runner — score an extraction corpus with pluggable verifiers.             |
| [`evidence`](creel.evidence.html.md#module-creel.evidence)     | Evidence — the separable per-element audit record (provenance + grounding + confidence). |
| [`export`](creel.export.html.md#module-creel.export)         | Export adapters — interchange formats for the canonical graph (EPIC 3.4 / 8.4).          |
| [`facade`](creel.facade.html.md#module-creel.facade)         | The facade: `extract(sources, graph_spec, extractors) -> graph`.                         |
| [`graph`](creel.graph.html.md#module-creel.graph)           | creel graph layer: the in-memory LPG and its canonical JSON serialisation.               |
| [`join`](creel.join.html.md#module-creel.join)             | Join the grammar and the extraction-metadata layers into a runnable plan.                |
| [`policy`](creel.policy.html.md#module-creel.policy)         | ExtractionPolicy — the operational policy layer for LLM extraction (decision #13).       |
| [`render`](creel.render.html.md#module-creel.render)         | The renderer contract — the three-layer annotated-graph renderers consume (D15).         |
| [`resolve`](creel.resolve.html.md#module-creel.resolve)       | Entity resolution — merge nodes that name the same real entity (decision #14 / D-OP8).   |
| [`sources`](creel.sources.html.md#module-creel.sources)       | Sources — the heterogeneous inputs creel reads.                                          |
| [`spec`](creel.spec.html.md#module-creel.spec)             | creel grammar layer: declare *what* graph to extract, and validate instances.            |
| [`temporal`](creel.temporal.html.md#module-creel.temporal)     | Reserved temporal vocabulary (decision #15 / D-OP9 — reserved, not yet enforced).        |
| [`trace`](creel.trace.html.md#module-creel.trace)           | Bidirectional source↔graph traceability (ADR D-OP9 — A1, A3, A4).                        |
| [`verify`](creel.verify.html.md#module-creel.verify)         | creel evaluation layer: pluggable verifiers (not hardcoded equality).                    |
| [`view`](creel.view.html.md#module-creel.view)             | Projections of the graph into views — "one model, many views" (decision D15).            |
