---
name: creel-grammar
description: Use when you need to define a creel grammar (a GraphSpec) — the typed schema for the graph you want to extract. Covers declaring node-types and edge-types with AttrSchema attributes; first-class edges that carry their own typed attributes (a funds edge with amount/currency); attribute options (required, range, enum, minimum/maximum, pattern, multivalued, description); reusable EnumDef value-sets and named ranges; inheritance via is_a/abstract/mixins; validating a grammar (validate_spec) and an instance graph (validate_graph); and optionally authoring in LinkML to generate JSON-Schema or Pydantic. Trigger on "define a creel grammar", "declare node-types and edge-types", "typed attributes on edges", "enums/ranges/inheritance for graph extraction", "schema for graph extraction", "LinkML authoring", or "validate a spec".
metadata:
  audience: users
---

# creel-grammar — author a typed graph grammar

A **grammar** is your typed schema: it declares *what graph you want*. In creel
the grammar is a `GraphSpec` — a small, immutable, extraction-agnostic description
of **node-types**, **edge-types**, and the **typed attributes** each carries. It is
the single source of truth for the graph's shape.

Mental model: the grammar enforces **shape** (which types exist, which attributes
they have, which endpoints an edge connects, enum membership, required fields). A
separate **verify** pass enforces **values** (numeric ranges, faithfulness to the
source). So declaring `minimum=0` documents intent and powers JSON-Schema/Pydantic
generation, but the trusted range check happens in verification, not in the decoder.

Once you have a grammar, hand it to `extract()` (see **creel-extract**), map each
element to an extractor (see **creel-bindings**), and check extracted values with
**creel-evaluation**. Each attribute's `description` doubles as the default LLM
extraction prompt and the default verifier criterion (see **creel-ai**).

## The smallest useful grammar

```python
from creel.spec.model import GraphSpec, NodeType, EdgeType, AttrSchema

spec = GraphSpec(
    node_types=(
        NodeType("donor", attributes=(AttrSchema("name", required=True),)),
        NodeType("project", attributes=(AttrSchema("title", required=True),)),
    ),
    edge_types=(
        EdgeType(
            "funds", subject_type="donor", object_type="project",
            attributes=(AttrSchema("amount", range="decimal", minimum=0),),
        ),
    ),
)
spec.node_type("donor").id            # 'donor'
spec.edge_type("funds").subject_type  # 'donor'
```

## First-class edges carry attributes (creel's defining feature)

An edge is **not** a bare triple — it is an element with its own identity and its
own typed attributes. Funding amounts, currencies, and indicator values live **on
the edge**, not on either endpoint. `subject_type`/`object_type` name the
node-types the edge connects:

```python
EdgeType(
    "funds", subject_type="donor", object_type="project",
    attributes=(
        AttrSchema("amount", range="decimal", required=True, minimum=0),
        AttrSchema("currency", range="Currency", required=True),
    ),
)
```

Two `funds` edges between the same donor and project are distinct fundings, because
edges have identity. This is why creel is a Labeled Property Graph, not RDF triples.

## Attribute options (`AttrSchema`)

| option | meaning |
|---|---|
| `range` | type of the value: a primitive (`"string"` default, `"integer"`, `"decimal"`, `"float"`, `"boolean"`, `"date"`, `"datetime"`) **or** the name of an `EnumDef` |
| `required` | must be present (shape check) |
| `enum` | inline list of permissible values, e.g. `enum=["open", "closed"]` |
| `minimum` / `maximum` | numeric bounds — **value-level**, enforced in the verify pass |
| `pattern` | regex the string value must match, e.g. `pattern=r"^PRJ-\d+$"` |
| `multivalued` | value is a list of the range type |
| `description` | natural-language meaning; **doubles** as the default LLM extraction instruction and the default verifier criterion |

## Reusable enums + named ranges (`EnumDef`)

Declare a value-set once and reference it by name from any attribute's `range`:

```python
from creel.spec.model import EnumDef

EnumDef("Currency", ("USD", "EUR", "CHF"))
# ...then use it as a range:
AttrSchema("currency", range="Currency", required=True)
```

Inline `enum=[...]` is fine for one-off sets; a named `EnumDef` is reusable across
many attributes and survives the LinkML round-trip.

## Inheritance: `is_a`, `abstract`, `mixins`

Factor shared attributes into a parent type. A subtype's *effective* attributes are
its own plus all inherited; an own attribute overrides an inherited one of the same
name. `abstract=True` marks a type you never instantiate directly.

```python
NodeType("result", abstract=True,
         attributes=(AttrSchema("statement", required=True),))
NodeType("outcome", is_a="result")   # inherits the required 'statement'
NodeType("output",  is_a="result")
```

`mixins=(...)` adds multiple inheritance. Use `effective_attributes(spec, "outcome")`
to see the resolved set, and `spec.is_subtype("outcome", "result")` to test the
taxonomy.

## Validate the grammar, then an instance

`validate_spec(spec)` checks the grammar's own integrity (every edge endpoint and
every `is_a` parent resolves to a declared node-type). It returns a list of issues
— empty means sound:

```python
from creel.spec.validate import validate_spec, validate_graph
assert validate_spec(spec) == []
```

`validate_graph(graph, spec)` checks an extracted graph against the grammar
(declared types, conformant endpoints, required attributes present, values respect
range/enum/bounds/pattern). Pass `raise_on_error=True` to raise instead of return:

```python
issues = validate_graph(graph, spec)              # list[ValidationIssue]
validate_graph(graph, spec, raise_on_error=True)  # raises GraphValidationError
```

## Optional: author in LinkML, generate JSON-Schema / Pydantic

If you prefer YAML authoring, write a LinkML schema and `load_linkml(path_or_dict)`
it into a `GraphSpec`; `to_linkml(spec)` goes the other way. From any spec you can
emit external-validator and typed-access artifacts:

```python
from creel.spec.linkml import (
    to_linkml, load_linkml, generate_json_schema, generate_pydantic,
)
schema = to_linkml(spec)                # GraphSpec -> LinkML dict (yaml.safe_dump-able)
spec2 = load_linkml(schema)             # LinkML (dict or .yaml path) -> GraphSpec
json_schema = generate_json_schema(spec)  # a $def per type, with bounds/enums
models = generate_pydantic(spec)          # one Pydantic model per node/edge type
```

Edges become LinkML classes flagged `represents_relationship: true`. The
`generate_*` helpers carry value bounds (unlike the LLM decode schema) so external
validators see the full constraints.

## A complete, runnable grammar

```python
from creel.spec.model import GraphSpec, NodeType, EdgeType, AttrSchema, EnumDef
from creel.spec.validate import validate_spec

spec = GraphSpec(
    id="funding",
    description="Donors funding projects that deliver results.",
    enums=(
        EnumDef("Currency", ("USD", "EUR", "CHF")),
        EnumDef("TransactionType", ("commitment", "disbursement")),
    ),
    node_types=(
        # abstract parent: shared, required attribute inherited by subtypes
        NodeType("result", abstract=True,
                 attributes=(AttrSchema("statement", required=True,
                                        description="The measurable change."),)),
        NodeType("outcome", is_a="result",
                 description="A change in the served population."),
        NodeType("output", is_a="result",
                 description="A product or service delivered."),
        NodeType("donor", attributes=(
            AttrSchema("name", required=True),
            AttrSchema("org_code", pattern=r"^\d{3,5}$"),
        )),
        NodeType("project", attributes=(
            AttrSchema("title", required=True),
            AttrSchema("code", pattern=r"^PRJ-\d+$"),
        )),
    ),
    edge_types=(
        # first-class edge: amount/currency live ON the edge
        EdgeType("funds", subject_type="donor", object_type="project",
                 attributes=(
                     AttrSchema("amount", range="decimal", required=True, minimum=0,
                                description="Amount funded, in the given currency."),
                     AttrSchema("currency", range="Currency", required=True),
                     AttrSchema("transaction_type", range="TransactionType",
                                required=True),
                 )),
        EdgeType("delivers", subject_type="project", object_type="output"),
        EdgeType("contributes_to", subject_type="output", object_type="outcome"),
    ),
)

assert validate_spec(spec) == []   # grammar is referentially sound
```

## Next steps

- **creel-extract** — run `extract(sources, spec, bindings)` to build the graph.
- **creel-bindings** — map each grammar element id to an extractor strategy.
- **creel-evaluation** — verify extracted *values* (the second half of the
  shape-vs-values split).
- **creel-ai** — how each attribute's `description` becomes the LLM prompt /
  verifier criterion.
