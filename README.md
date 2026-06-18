# creel

**Extract a typed graph from a mess of sources.**

creel is a general, AI-powered **source-to-graph extraction engine**. You give it
(a) **sources** — freeform prose, tables, JSON, PDFs; (b) a **grammar** of the graph
you want — its node-types and edge-types and the typed values they carry; and (c)
**extractors** — pluggable strategies that know how to find each element. creel returns
a clean, auditable, typed **property graph** as a single source of truth, canonically a
JSON graph specification:

```python
extract(sources, graph_spec, extractors) -> graph
```

Everything downstream — persistence, query, graph-RAG, annotation, rendering to
slides/reports — is a *projection* of that one graph.

## Install

```bash
pip install creel                 # core: pydantic, jsonschema, networkx
pip install "creel[query]"        # SQL/JSON query extractors (duckdb, jmespath)
pip install "creel[ingest]"       # file loaders: PDF/DOCX/PPTX via docling, HTML via trafilatura, XLSX via openpyxl
pip install "creel[aix]"          # real LLM extraction/judging/embedding via aix (default)
pip install "creel[anthropic]"    # real LLM extraction via the Anthropic SDK directly
pip install "creel[semantic]"     # LinkML .yaml round-trip + RDF/SHACL validation (pyyaml, linkml, rdflib, pyshacl)
```

LinkML *dict* authoring and RDF-star/Turtle *export* are pure-Python and need no
extra — `[semantic]` only adds `.yaml`-file authoring and downstream validators.
Other extras reserve optional backends: `graphdb` (Neo4j/Oxigraph), `er` (Splink),
`eval` (DeepEval), `ocr` (Tesseract). The headline ones above cover most use;
`pip install "creel[llm]"` is an alias for the default provider (`aix`).

## A first taste

Declare a grammar, extract a graph from prose, validate it, emit canonical JSON:

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

# Deterministic pattern extractors (no LLM): regex over prose.
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
assert validate_graph(g, spec) == []
print(to_canonical_json(g))                 # deterministic, git-diffable JSON
print(g.evidence)                            # every element traced back to its source span
```

### With a real LLM (schema-as-extractor)

The attribute `description`s become the extraction instruction; the LLM client is
injected (no provider SDK in the core). This block is self-contained:

```python
from creel import GraphSpec, NodeType, AttrSchema, extract
from creel.extract.llm import aix_client

spec = GraphSpec(node_types=(
    NodeType("donor", description="An entity that provides funding.",
             attributes=(AttrSchema("name", required=True,
                                    description="The donor's official name."),)),
))
prose = "Donor: Foundation Alpha (ref 301). Donor: Agency Beta (ref 918)."
g = extract(prose, spec, {"donor": ("llm", {})},
            services={"llm": aix_client()}, on_missing_binding="skip")
```

## Skills (the AI-native interface)

creel is **AI-first**, and that includes how you *learn and drive it*. It ships
**agent skills** — `SKILL.md` cheat-sheets that make Claude (and any `gh skill`-aware
agent: Copilot, Cursor, Codex, Gemini) actually good at using creel, instead of
guessing from docstrings. They install with `pip` (bundled, offline) **or** `gh skill`:

```bash
# All consumer skills ride along with the package:
pip install creel            # creel/data/skills/* is bundled in the wheel

# …or install individually into your agent (cross-agent, pinnable):
gh skill install thorwhalen/creel creel-extract       # the end-to-end workflow
gh skill install thorwhalen/creel creel-grammar       # author a typed GraphSpec
gh skill install thorwhalen/creel creel-bindings      # choose extractor strategies
gh skill install thorwhalen/creel creel-evaluation    # pluggable verifiers (≠ ==)
gh skill install thorwhalen/creel creel-ai            # real LLM extraction
gh skill install thorwhalen/creel creel-projections   # resolve / view / export / trace
# add --agent <copilot|cursor|codex|gemini|claude> to target a host; @vX.Y.Z to pin
```

Once installed, just ask in plain language ("extract a graph from these documents with
creel", "write a verifier for the amounts") — the matching skill triggers automatically.
The skills cross-reference each other, so an agent that starts at `creel-extract` is
handed off to `creel-grammar`/`creel-bindings`/`creel-ai`/`creel-evaluation` as needed.
Prefer hand-written API calls? Scroll on — everything below still applies.

## What you get

- **Labeled Property Graph** — attributes (funding amounts, indicator values) live *on
  edges*, which have their own identity; deterministic, git-diffable canonical JSON.
- **Three extractor families** behind one `Extractor` protocol: deterministic
  **pattern/function**, **query** (DuckDB SQL / JMESPath over structured sources), and
  **LLM** (schema-as-extractor, validate-retry, faithfulness gate) — plus **cluster-pass**
  (extract several coupled types in one LLM call).
- **Ingestion** (`ingest()`): route-by-format file loaders (md/csv/json/txt built-in;
  PDF/DOCX/XLSX/HTML via extras).
- **Auditability**: every node/edge/value carries a separable **evidence** record
  (provenance + grounding selector back to the exact source span + confidence). A
  **reverse-trace index** answers "which elements did this passage produce?", and a
  re-anchoring resolver keeps highlights valid across re-ingestion.
- **Evaluation by pluggable verifiers, not `==`**: `numeric_tolerance`, `set_match`,
  `graph_match` (partial credit), `llm_rubric` (NL-defined, G-Eval), … with a corpus runner.
- **Entity resolution** cascade (normalize → registry → LLM), the **reify** edge↔node
  toggle, **views** (DOT/Mermaid/Cytoscape/tables), and **export** adapters (JGF, GraphML,
  parameterized Cypher, RDF-star).

## Design & docs

The full reasoning lives in the research + design docs: start with the
[synthesis](misc/docs/research/00-synthesis-and-design-implications.md) (decisions
D1–D15), then the [roadmap](misc/docs/design/ROADMAP.md), the
[decision log](misc/docs/design/DECISIONS.md), and the
[progress log](misc/docs/design/PROGRESS.md). A worked example is in
[`examples/`](examples/).

## License

MIT.
