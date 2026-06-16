# creel

**Extract a typed graph from a mess of sources.**

creel is a general, AI-powered **source-to-graph extraction engine**. You give it
(a) **sources** — freeform prose, tables, JSON, schema specs; (b) a **grammar** of
the graph you want — its node-types and edge-types and the typed values they carry;
and (c) **extractors** — pluggable strategies that know how to find each element.
creel returns a clean, auditable, typed **property graph** as a single source of
truth, canonically a JSON graph specification:

```python
extract(sources, graph_spec, extractors) -> graph
```

Everything downstream — persistence, query, graph-RAG, annotation, rendering to
slides/reports/video — is a *projection* of that one graph.

> **Status — early development.** The `v0.1` **data layer** (grammar, the in-memory
> Labeled Property Graph, and deterministic canonical JSON) is implemented and
> tested. The `extract()` facade and the extractor/verifier strategy layers are
> being built next — see [`misc/docs/design/ROADMAP.md`](misc/docs/design/ROADMAP.md).

## Install

```bash
pip install creel                 # core: pydantic, jsonschema, networkx
pip install "creel[llm]"          # + the default LLM-extraction adapter
pip install "creel[query]"        # + SQL/JSON query extractors (duckdb, jmespath)
pip install "creel[eval]"         # + the verifier/evaluation backend
```

## A first taste (the data layer, today)

Declare a grammar, build a graph against it, validate it, and emit canonical JSON:

```python
from creel import (
    GraphSpec, NodeType, EdgeType, AttrSchema, EnumDef,
    Graph, validate_graph, to_canonical_json,
)

spec = GraphSpec(
    enums=(EnumDef("Currency", ("USD", "EUR", "CHF")),),
    node_types=(
        NodeType("donor", attributes=(AttrSchema("name", required=True),)),
        NodeType("project", attributes=(AttrSchema("title", required=True),)),
    ),
    edge_types=(
        EdgeType(
            "funds", subject_type="donor", object_type="project",
            attributes=(
                AttrSchema("amount", range="decimal", required=True, minimum=0),
                AttrSchema("currency", range="Currency", required=True),
            ),
        ),
    ),
)

g = Graph()
g.add_node("d:gov-x", types=("donor",), attributes={"name": "Government X"})
g.add_node("p:wash", types=("project",), attributes={"title": "WASH programme"})
# Edges are first-class: attributes (funding amounts!) live ON the edge, and each
# edge has its own id, so two distinct fundings are distinguishable.
g.add_edge("f:1", source="d:gov-x", target="p:wash", type="funds",
           attributes={"amount": 1_000_000, "currency": "USD"})

assert validate_graph(g, spec) == []          # conforms to the grammar
print(to_canonical_json(g, spec=spec))         # deterministic, git-diffable JSON
```

## Design at a glance

- **Labeled Property Graph** internal model — attributes live *on edges*, which have
  their own identity (parallel edges stay distinguishable).
- **Two physically separate layers, joined by id** — the *grammar* (what the graph
  is) and the *extraction/verification metadata* (how to populate and check it) are
  recombined on demand, so each is reused independently.
- **Strategy pattern throughout** — extractors, verifiers, renderers are pluggable
  `Protocol`s; new mechanisms slot in without touching old ones.
- **Schema-as-extractor / schema-as-verifier defaults** — an attribute's
  description doubles as the default extraction instruction and verification
  criterion, so simple cases stay simple.
- **Auditability over opaqueness** — every node, edge, and value will carry a
  separable evidence record (provenance + grounding back to the source span +
  confidence).
- **Evaluation is verifier-based, not equality-based** — comparing extracted output
  to expected output uses pluggable verifiers (numeric tolerance, set/graph
  matching with partial credit, LLM rubrics), never a brittle `==`.

The full reasoning lives in the research + design docs: start with the
[synthesis](misc/docs/research/00-synthesis-and-design-implications.md) (decisions
D1–D15), then the [roadmap](misc/docs/design/ROADMAP.md) and
[decision log](misc/docs/design/DECISIONS.md).

## License

MIT.
