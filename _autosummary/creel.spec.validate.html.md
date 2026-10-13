# creel.spec.validate

Validate an instance [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph) against a `GraphSpec`.

This is *structural/shape* validation of an extracted graph against its grammar
(decision D6: the grammar enforces shape; deeper semantic faithfulness is the job
of the verifier subsystem). It checks that node/edge types are declared, that edge
endpoints have conformant node-types, that required attributes are present, and
that attribute values respect their declared range / enum / bounds / pattern.

Use [`validate_graph()`](#creel.spec.validate.validate_graph) to collect issues, or pass `raise_on_error=True` to
raise a [`GraphValidationError`](#creel.spec.validate.GraphValidationError) summarising them.

### Functions

| [`validate_attributes`](#creel.spec.validate.validate_attributes)(attributes, type_id, spec, \*)   | Validate a single element's `attributes` against its type's effective schema.   |
|-------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`validate_graph`](#creel.spec.validate.validate_graph)(graph, spec, \*[, raise_on_error])    | Return the list of grammar-conformance issues for `graph` under `spec`.         |
| [`validate_spec`](#creel.spec.validate.validate_spec)(spec)                                  | Check the grammar's own referential integrity (independent of any instance).    |

### Classes

| [`ValidationIssue`](#creel.spec.validate.ValidationIssue)(element, element_id, code, ...)   | A single grammar-conformance problem found in an instance graph.   |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|

### Exceptions

| [`GraphValidationError`](#creel.spec.validate.GraphValidationError)(issues)   | Raised by [`validate_graph()`](#creel.spec.validate.validate_graph) when `raise_on_error` and issues exist.   |
|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|

### *exception* creel.spec.validate.GraphValidationError(issues)

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

Raised by [`validate_graph()`](#creel.spec.validate.validate_graph) when `raise_on_error` and issues exist.

### *class* creel.spec.validate.ValidationIssue(element, element_id, code, message)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single grammar-conformance problem found in an instance graph.

### creel.spec.validate.validate_attributes(attributes, type_id, spec, , element_id='')

Validate a single element’s `attributes` against its type’s effective schema.

Used by the LLM extractor’s validate-retry loop (decision D6): the LLM emits
shape-valid JSON, and value-level constraints (enums, ranges, required) are
checked here so the model can be re-asked with the specific failures.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](#creel.spec.validate.ValidationIssue)]

### creel.spec.validate.validate_graph(graph, spec, , raise_on_error=False)

Return the list of grammar-conformance issues for `graph` under `spec`.

With `raise_on_error=True`, raises [`GraphValidationError`](#creel.spec.validate.GraphValidationError) if any issue
is found instead of returning the list.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](#creel.spec.validate.ValidationIssue)]

### creel.spec.validate.validate_spec(spec)

Check the grammar’s own referential integrity (independent of any instance).

Every edge endpoint type and every `is_a` parent must resolve to a declared
node type — otherwise a spec that references a nonexistent node-type is silently
accepted and never caught. Returns `[]` for a sound grammar.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](#creel.spec.validate.ValidationIssue)]
