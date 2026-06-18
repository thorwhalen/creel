---
name: creel-extract
description: >-
  Extract a typed property graph from messy sources with creel. Use when the user
  wants to turn prose, tables, JSON, or PDFs/documents into a clean, typed graph —
  i.e. run extract(), build a property graph, go sources->graph, use the creel
  facade, or get started with creel. Triggers on "extract a graph from documents",
  "build a knowledge/property graph with creel", "creel quickstart", "how do I call
  extract()", "sources to graph", "turn this prose/table/JSON into a typed graph",
  "ingest a folder of files/PDFs into a graph", "the one-call creel workflow". This
  is the ENTRY/orchestrator skill: it covers the end-to-end extract(sources,
  graph_spec, extractors) -> graph call, its keyword args (services,
  on_missing_binding, resolve, cache), and how to read the returned Graph (nodes,
  edges, evidence, report, validate_graph, to_canonical_json). Hand off to
  creel-grammar, creel-bindings, creel-ai, creel-evaluation, creel-projections for
  the deeper pieces.
metadata:
  audience: users
---

# creel-extract — sources → typed graph in one call

creel reads heterogeneous **sources** (prose, tables, JSON, files), conforms them to
a typed **grammar** you supply, and returns one clean, auditable **Labeled Property
Graph** (LPG) — the single source of truth. Everything else (query, export,
rendering) is a projection of that graph.

```python
extract(sources, graph_spec, extractors) -> graph
```

## The three inputs

1. **`sources`** — what to read. Flexible (see `coerce_sources`):
   - a bare `str` → one text source;
   - a `Source(id, content, kind=...)` (`kind` is `"text"`, `"table"`, or `"json"`);
   - a `SourceBundle([...])` of several sources;
   - a list of `Source`s, or a `{id: content}` mapping;
   - files via `ingest(path)` / `ingest_paths([...])` (md/csv/json/txt built-in; PDF/DOCX/XLSX/HTML need `pip install "creel[ingest]"`).
2. **`graph_spec`** — a `GraphSpec`: the typed grammar (node-types, edge-types, the
   attributes they carry, enums). **→ skill `creel-grammar`** to author it.
3. **`extractors`** — bindings: `{element_id: (strategy, config)}` (or a callable, or
   `ExtractorBindings`). Says *how* to find each node/edge type. **→ skill
   `creel-bindings`** for the strategy catalogue.

## Ingesting files into sources

Handed a folder of files? Turn them into sources first — `ingest` routes by file
extension to a loader and tags each `Source` with the right `kind`:

```python
from creel import ingest, ingest_paths
src    = ingest("report.pdf")                  # one file -> Source(id="report", kind="text", ...)
bundle = ingest_paths(["a.md", "data.csv"])    # many -> SourceBundle (md->text, csv->table)
g = extract(bundle, spec, bindings)
```

`source_id` defaults to the file **stem** (so a `table_map` binding can name it via
`records_source="data"`); pass `source_id=`/`loader=` to override. Tabular formats
(`.csv`/`.tsv`/`.xls`/`.xlsx`) load as `table` sources, `.json` as `json`, the rest
as `text`.

| Extensions | Loader | Needs |
|---|---|---|
| `.md` `.txt` `.csv` `.tsv` `.json` | stdlib | core (no extra) |
| `.pdf` `.docx` `.pptx` | docling | `pip install "creel[ingest]"` |
| `.html` `.htm` | trafilatura | `creel[ingest]` |
| `.xls` `.xlsx` | openpyxl | `creel[ingest]` |

```python
from creel.ingest.loaders import supported_extensions, register_loader
supported_extensions()        # every routed extension (regardless of backend installed)
```

A file whose extension routes to an uninstalled backend raises a clear `ImportError`
("Install with: `pip install 'creel[ingest]'`"); an unknown extension raises
`ValueError` (pass an explicit `loader=`). Register a custom format with
`@register_loader(".ext")` over a `(path, *, source_id) -> Source` function.

## Facade keyword args (all optional, keyword-only past the 3rd)

- **`on_missing_binding`** — what to do for grammar elements with no binding:
  `"skip"` (drop them — best for pure pattern runs), `"error"` (raise), or
  `"schema_as_extractor"` (the default: route them to an LLM that uses each
  attribute's `description` as the instruction — needs `services={"llm": ...}`).
- **`services`** — injected dependencies, e.g. `{"llm": aix_client()}` for LLM
  extraction. The core pins no provider SDK. **→ skill `creel-ai`**.
- **`resolve`** — an optional `Resolver` to merge same-entity nodes across sources
  (messy multi-source corpora). **→ skill `creel-projections`**.
- **`cache`** — a `Cache` (e.g. `DictCache()`) to memoise expensive extractor calls.

## What comes back: a `Graph` (the SSOT)

Read it with typed accessors:

```python
g.nodes()                  # iterate Node(id, types, attributes)
g.edges()                  # iterate Edge(id, source, target, type, attributes)
g.node(id) / g.edge(id)    # one element by id
g.nodes_of_type("donor")   # filter by node label
g.edges_of_type("funds")   # filter by edge type
g.evidence[element_id]     # audit record: provenance + grounding span + confidence
g.report                   # run diagnostics: unbound_elements, skipped_edges, ...
```

Validate against the grammar, then serialise to **deterministic, git-diffable JSON**:

```python
from creel import validate_graph, to_canonical_json, from_canonical_json
issues = validate_graph(g, spec)        # [] means the graph conforms
text = to_canonical_json(g)             # stable keys + id-sorted edges → one-line diffs
g2 = from_canonical_json(text)          # round-trips byte-identically
```

## Complete minimal example (regex bindings, no LLM)

```python
from creel import (
    GraphSpec, NodeType, EdgeType, AttrSchema, EnumDef,
    extract, validate_graph, to_canonical_json,
)

spec = GraphSpec(
    enums=(EnumDef("Currency", ("USD", "EUR")),),
    node_types=(
        NodeType("donor", attributes=(AttrSchema("name", required=True),)),
        NodeType("project", attributes=(AttrSchema("title", required=True),)),
    ),
    edge_types=(
        EdgeType("funds", subject_type="donor", object_type="project",
                 attributes=(AttrSchema("amount", range="integer", required=True, minimum=0),
                             AttrSchema("currency", range="Currency", required=True))),
    ),
)

bindings = {
    "donor": ("regex_node", {"pattern": r"Donor:\s*(?P<name>.+)", "id_attribute": "name"}),
    "project": ("regex_node", {"pattern": r"Project:\s*(?P<title>.+)", "id_attribute": "title"}),
    "funds": ("regex_edge", {
        "pattern": r"(?P<donor>[\w ]+?) funds (?P<project>[\w ]+?) with (?P<currency>[A-Z]{3}) (?P<amount>\d+)",
        "source_id_template": "donor:{donor}", "target_id_template": "project:{project}",
        "casts": {"amount": "int"}, "exclude_groups": ("donor", "project")}),
}

src = "Donor: Gov X\nProject: Water\nGov X funds Water with USD 1000000"

g = extract(src, spec, bindings, on_missing_binding="skip")
assert validate_graph(g, spec) == []                    # conforms to the grammar
funds = next(iter(g.edges_of_type("funds")))
assert funds.attributes["amount"] == 1000000            # amount lives ON the edge
print(to_canonical_json(g))                             # deterministic JSON
print(g.evidence[funds.id].to_dict())                   # traced back to the source span
```

Use `on_missing_binding="skip"` whenever you have not bound every element (e.g. pure
pattern runs) — otherwise the default LLM fallback will demand a `services["llm"]`
client and raise an actionable error.

## What next — sibling skills

- **`creel-grammar`** — author the `GraphSpec` (node/edge types, `AttrSchema`,
  enums, required fields, ranges). Start here if the grammar is what you are shaping.
- **`creel-bindings`** — the extractor strategy catalogue: `regex_node`/`regex_edge`,
  query (`table_map`/`sql`/`json_query`), cluster passes, custom callables.
- **`creel-ai`** — real LLM extraction (`creel.extract.llm`: `aix_client`,
  schema-as-extractor, validate-retry, faithfulness gate); install `creel[aix]`.
- **`creel-evaluation`** — check correctness with pluggable **verifiers**
  (`numeric_tolerance`, `set_match`, `graph_match`, `llm_rubric`), never `==`.
- **`creel-projections`** — downstream of the graph: `resolve` (entity resolution),
  `reify`, `view` (Mermaid/DOT/Cytoscape/tables), and `export` (JGF/GraphML/Cypher/RDF-star).
