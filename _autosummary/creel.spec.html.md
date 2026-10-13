# creel.spec

creel grammar layer: declare *what* graph to extract, and validate instances.

Re-exports the grammar model ([`creel.spec.model`](creel.spec.model.html.md#module-creel.spec.model)) and instance validation
([`creel.spec.validate`](creel.spec.validate.html.md#module-creel.spec.validate)).

### Functions

| [`effective_attributes`](#creel.spec.effective_attributes)(spec, type_id)               | Resolve the full attribute set for a type, including inherited attributes.                                              |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`validate_graph`](#creel.spec.validate_graph)(graph, spec, \*[, raise_on_error]) | Return the list of grammar-conformance issues for `graph` under `spec`.                                                 |
| [`validate_spec`](#creel.spec.validate_spec)(spec)                               | Check the grammar's own referential integrity (independent of any instance).                                            |
| [`to_linkml`](#creel.spec.to_linkml)(spec)                                   | Emit a LinkML schema dict (pass to `yaml.safe_dump` to write a `.yaml`).                                                |
| [`load_linkml`](#creel.spec.load_linkml)(schema)                               | Parse a LinkML schema (dict, or a path to a `.yaml`) into a [`GraphSpec`](#creel.spec.GraphSpec). |
| [`generate_json_schema`](#creel.spec.generate_json_schema)(spec)                        | Generate a JSON Schema with a `$def` per node/edge type (for external validators).                                      |
| [`generate_pydantic`](#creel.spec.generate_pydantic)(spec)                           | Generate one Pydantic v2 model per node/edge type (typed access at the IO boundary).                                    |

### Classes

| [`AttrSchema`](#creel.spec.AttrSchema)(name[, range, required, ...])          | Typed schema for a single attribute (a "leaf" value) of a node or edge.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`EdgeType`](#creel.spec.EdgeType)(id[, description, is_a, mixins, ...])    | An edge-type (a.k.a.                                                      |
| [`ElementType`](#creel.spec.ElementType)(id[, description, is_a, mixins, ...]) | Base for a node-type or edge-type — a position in a recursive taxonomy.   |
| [`EnumDef`](#creel.spec.EnumDef)(name, permissible_values[, description])  | A named, reusable set of permissible values (a constrained value-set).    |
| [`GraphSpec`](#creel.spec.GraphSpec)([node_types, edge_types, enums, ...])   | A complete graph grammar: node-types, edge-types, and reusable enums.     |
| [`NodeType`](#creel.spec.NodeType)(id[, description, is_a, mixins, ...])    | A node-type (a.k.a.                                                       |
| [`ValidationIssue`](#creel.spec.ValidationIssue)(element, element_id, code, ...)   | A single grammar-conformance problem found in an instance graph.          |

### Exceptions

| [`GraphValidationError`](#creel.spec.GraphValidationError)(issues)   | Raised by [`validate_graph()`](#creel.spec.validate_graph) when `raise_on_error` and issues exist.   |
|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|

### *class* creel.spec.AttrSchema(name, range='string', required=False, multivalued=False, enum=None, minimum=None, maximum=None, pattern=None, description=None)

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

### *class* creel.spec.EdgeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False, subject_type=None, object_type=None)

Bases: [`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)

An edge-type (a.k.a. link type): first-class, with its own typed attributes.

`subject_type` and `object_type` name the node-types this edge connects
(its endpoints). Edges have their own identity, so two `funds` edges between
the same donor and project (two distinct fundings) are distinguishable.

### *class* creel.spec.ElementType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Base for a node-type or edge-type — a position in a recursive taxonomy.

The taxonomy is expressed by `is_a` (single-inheritance parent) plus
`mixins` (multiple inheritance). An element’s *effective* attributes are its
own plus all inherited ones (see [`effective_attributes()`](#creel.spec.effective_attributes)). `id` is an
opaque identifier and may be a dotted path (e.g. `"result.outcome"`) by
convention, but the real hierarchy is the `is_a`/`mixins` graph.

#### attribute(name)

Return this type’s *own* attribute schema named `name` (no inheritance).

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`AttrSchema`](creel.spec.model.html.md#creel.spec.model.AttrSchema)]

#### *property* parents *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

All direct supertype ids (`is_a` then `mixins`).

### *class* creel.spec.EnumDef(name, permissible_values, description=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A named, reusable set of permissible values (a constrained value-set).

### *class* creel.spec.GraphSpec(node_types=(), edge_types=(), enums=(), id=None, version='0.1.0', description=None)

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

### *exception* creel.spec.GraphValidationError(issues)

Bases: [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

Raised by [`validate_graph()`](#creel.spec.validate_graph) when `raise_on_error` and issues exist.

### *class* creel.spec.NodeType(id, description=None, is_a=None, mixins=(), attributes=(), abstract=False)

Bases: [`ElementType`](creel.spec.model.html.md#creel.spec.model.ElementType)

A node-type (a.k.a. point type). Carries typed attributes and a taxonomy.

### *class* creel.spec.ValidationIssue(element, element_id, code, message)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single grammar-conformance problem found in an instance graph.

### creel.spec.effective_attributes(spec, type_id)

Resolve the full attribute set for a type, including inherited attributes.

Walks `is_a` then `mixins` (depth-first), with a subtype’s own attributes
overriding inherited ones of the same name. Returns an insertion-ordered dict
keyed by attribute name. Unknown `type_id` yields an empty dict.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`AttrSchema`](creel.spec.model.html.md#creel.spec.model.AttrSchema)]

### creel.spec.generate_json_schema(spec)

Generate a JSON Schema with a `$def` per node/edge type (for external validators).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.spec.generate_pydantic(spec)

Generate one Pydantic v2 model per node/edge type (typed access at the IO boundary).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/builtins/functions.html#type)]

### creel.spec.load_linkml(schema)

Parse a LinkML schema (dict, or a path to a `.yaml`) into a [`GraphSpec`](#creel.spec.GraphSpec).

* **Return type:**
  [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec)

### creel.spec.to_linkml(spec)

Emit a LinkML schema dict (pass to `yaml.safe_dump` to write a `.yaml`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.spec.validate_graph(graph, spec, , raise_on_error=False)

Return the list of grammar-conformance issues for `graph` under `spec`.

With `raise_on_error=True`, raises [`GraphValidationError`](#creel.spec.GraphValidationError) if any issue
is found instead of returning the list.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](creel.spec.validate.html.md#creel.spec.validate.ValidationIssue)]

### creel.spec.validate_spec(spec)

Check the grammar’s own referential integrity (independent of any instance).

Every edge endpoint type and every `is_a` parent must resolve to a declared
node type — otherwise a spec that references a nonexistent node-type is silently
accepted and never caught. Returns `[]` for a sound grammar.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ValidationIssue`](creel.spec.validate.html.md#creel.spec.validate.ValidationIssue)]

### Modules

| [`linkml`](creel.spec.linkml.html.md#module-creel.spec.linkml)     | LinkML bridge + schema codegen for the grammar (EPIC 2.4, decision D3).                                                                                                   |
|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`model`](creel.spec.model.html.md#module-creel.spec.model)       | The grammar layer: a typed description of *what* graph creel should extract.                                                                                              |
| [`validate`](creel.spec.validate.html.md#module-creel.spec.validate) | Validate an instance [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph) against a [`GraphSpec`](#creel.spec.GraphSpec). |
