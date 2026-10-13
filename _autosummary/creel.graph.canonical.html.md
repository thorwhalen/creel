# creel.graph.canonical

Canonical JSON for creel graphs — the deterministic, versioned on-disk truth.

Per decision D4 the canonical form is creel-owned and versioned (`$schema` +
`version`), shapes nodes as an id→object map and edges as objects each with a
**required stable id**, and serialises with sorted keys + id-sorted arrays so that
diffs are one line and round-trips are byte-identical. That determinism is a tested
invariant (`to → from → to` reproduces the exact bytes).

## Public surface

- [`to_canonical_dict()`](#creel.graph.canonical.to_canonical_dict) / [`to_canonical_json()`](#creel.graph.canonical.to_canonical_json)
- [`from_canonical_dict()`](#creel.graph.canonical.from_canonical_dict) / [`from_canonical_json()`](#creel.graph.canonical.from_canonical_json)
- [`CANONICAL_SCHEMA_URL`](#creel.graph.canonical.CANONICAL_SCHEMA_URL), [`CANONICAL_VERSION`](#creel.graph.canonical.CANONICAL_VERSION), [`CANONICAL_GRAPH_SCHEMA`](#creel.graph.canonical.CANONICAL_GRAPH_SCHEMA)
- [`validate_canonical()`](#creel.graph.canonical.validate_canonical)

### Module Attributes

| [`CANONICAL_SCHEMA_URL`](#creel.graph.canonical.CANONICAL_SCHEMA_URL)   | The creel-owned `$schema` identifier for the canonical graph format.     |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`CANONICAL_VERSION`](#creel.graph.canonical.CANONICAL_VERSION)      | bump on additive/breaking changes).                                      |
| [`CANONICAL_GRAPH_SCHEMA`](#creel.graph.canonical.CANONICAL_GRAPH_SCHEMA) | JSON Schema (Draft 2020-12) describing a valid canonical graph document. |

### Functions

| [`from_canonical_dict`](#creel.graph.canonical.from_canonical_dict)(data, \*[, validate])    | Rebuild a `Graph` from a canonical dict.                                                                                 |
|-----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| [`from_canonical_json`](#creel.graph.canonical.from_canonical_json)(text, \*[, validate])    | Parse canonical JSON `text` into a `Graph` (see [`from_canonical_dict()`](#creel.graph.canonical.from_canonical_dict)). |
| [`to_canonical_dict`](#creel.graph.canonical.to_canonical_dict)(graph, \*[, spec])         | Build the canonical dict for `graph` (edges id-sorted; ready to serialise).                                              |
| [`to_canonical_json`](#creel.graph.canonical.to_canonical_json)(graph, \*[, spec, indent]) | Serialise `graph` to canonical JSON text — deterministic and git-diffable.                                               |
| [`validate_canonical`](#creel.graph.canonical.validate_canonical)(data)                     | Validate a canonical document against the format schema.                                                                 |

### creel.graph.canonical.CANONICAL_GRAPH_SCHEMA *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]* *= {'$id': 'https://creel.dev/schema/graph/v1', '$schema': 'https://json-schema.org/draft/2020-12/schema', 'additionalProperties': False, 'properties': {'$schema': {'type': 'string'}, 'directed': {'type': 'boolean'}, 'edges': {'items': {'additionalProperties': False, 'properties': {'attributes': {'type': 'object'}, 'id': {'type': 'string'}, 'source': {'type': 'string'}, 'target': {'type': 'string'}, 'type': {'type': 'string'}}, 'required': ['id', 'source', 'target', 'type', 'attributes'], 'type': 'object'}, 'type': 'array'}, 'nodes': {'additionalProperties': {'additionalProperties': False, 'properties': {'attributes': {'type': 'object'}, 'types': {'items': {'type': 'string'}, 'type': 'array'}}, 'required': ['types', 'attributes'], 'type': 'object'}, 'type': 'object'}, 'spec': {'type': ['object', 'null']}, 'version': {'type': 'string'}}, 'required': ['$schema', 'version', 'nodes', 'edges'], 'title': 'creel canonical property graph', 'type': 'object'}*

JSON Schema (Draft 2020-12) describing a valid canonical graph document.

### creel.graph.canonical.CANONICAL_SCHEMA_URL *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= 'https://creel.dev/schema/graph/v1'*

The creel-owned `$schema` identifier for the canonical graph format. This is a
stable placeholder URL (decision D-OP4); it need not resolve to host the schema.

### creel.graph.canonical.CANONICAL_VERSION *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)* *= '1.0'*

bump on additive/breaking changes).

* **Type:**
  Canonical-format version (SchemaVer-style

### creel.graph.canonical.from_canonical_dict(data, , validate=True)

Rebuild a `Graph` from a canonical dict.

With `validate=True` (default) the document is checked against
[`CANONICAL_GRAPH_SCHEMA`](#creel.graph.canonical.CANONICAL_GRAPH_SCHEMA) before loading, so malformed input fails fast
with a clear error rather than a confusing `KeyError` mid-build.

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.graph.canonical.from_canonical_json(text, , validate=True)

Parse canonical JSON `text` into a `Graph` (see [`from_canonical_dict()`](#creel.graph.canonical.from_canonical_dict)).

* **Return type:**
  [`Graph`](creel.graph.model.html.md#creel.graph.model.Graph)

### creel.graph.canonical.to_canonical_dict(graph, , spec=None)

Build the canonical dict for `graph` (edges id-sorted; ready to serialise).

If `spec` is given, a lightweight `{"id", "version"}` reference is recorded
so a reader knows which grammar the instance claims to conform to.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.graph.canonical.to_canonical_json(graph, , spec=None, indent=2)

Serialise `graph` to canonical JSON text — deterministic and git-diffable.

Keys are sorted and edge arrays are id-sorted, so the same graph always yields
byte-identical output regardless of insertion order.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### creel.graph.canonical.validate_canonical(data)

Validate a canonical document against the format schema.

Raises `jsonschema.ValidationError` if `data` is not a well-formed canonical
graph document.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
