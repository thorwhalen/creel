# creel.spec.linkml

LinkML bridge + schema codegen for the grammar (EPIC 2.4, decision D3).

LinkML is creel’s optional **build-time authoring front-end**, not the runtime SSOT
(the Python [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec) is). This module bridges the two and
generates validation artifacts — all **dependency-free** for the common subset (a
LinkML schema is YAML with `classes` / `attributes` / `enums`), so it is fully
testable without the heavy `linkml` package:

- [`to_linkml()`](#creel.spec.linkml.to_linkml) — `GraphSpec` → a LinkML schema dict (YAML-able).
- [`load_linkml()`](#creel.spec.linkml.load_linkml) — a LinkML schema (dict or YAML path) → `GraphSpec`.
- [`generate_json_schema()`](#creel.spec.linkml.generate_json_schema) — `GraphSpec` → JSON Schema (a `$def` per type,
  with enums/ranges/cardinality) for external validators.
- [`generate_pydantic()`](#creel.spec.linkml.generate_pydantic) — a Pydantic model per node/edge type for typed access.

Edges are LinkML classes flagged `represents_relationship: true` (the LinkML idiom
for first-class, attribute-bearing relations).

### Functions

| [`to_linkml`](#creel.spec.linkml.to_linkml)(spec)            | Emit a LinkML schema dict (pass to `yaml.safe_dump` to write a `.yaml`).             |
|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| [`load_linkml`](#creel.spec.linkml.load_linkml)(schema)        | Parse a LinkML schema (dict, or a path to a `.yaml`) into a `GraphSpec`.             |
| [`generate_json_schema`](#creel.spec.linkml.generate_json_schema)(spec) | Generate a JSON Schema with a `$def` per node/edge type (for external validators).   |
| [`generate_pydantic`](#creel.spec.linkml.generate_pydantic)(spec)    | Generate one Pydantic v2 model per node/edge type (typed access at the IO boundary). |

### creel.spec.linkml.generate_json_schema(spec)

Generate a JSON Schema with a `$def` per node/edge type (for external validators).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.spec.linkml.generate_pydantic(spec)

Generate one Pydantic v2 model per node/edge type (typed access at the IO boundary).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/builtins/functions.html#type)]

### creel.spec.linkml.load_linkml(schema)

Parse a LinkML schema (dict, or a path to a `.yaml`) into a `GraphSpec`.

* **Return type:**
  [`GraphSpec`](creel.spec.model.html.md#creel.spec.model.GraphSpec)

### creel.spec.linkml.to_linkml(spec)

Emit a LinkML schema dict (pass to `yaml.safe_dump` to write a `.yaml`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
