# 12 — Pluggable strategy-based extraction architecture

> **TL;DR.** Creel's design posture maps cleanly onto a small, well-understood set of Python idioms: model extraction mechanisms as **Protocol-typed callables** (strategy pattern via composition, not inheritance); discover and swap them through a **decorator registry** for in-tree strategies plus **`importlib.metadata` entry points** for third-party plugins (reserve `pluggy` for the day creel needs *multiple* cooperating hooks per extension point — it doesn't yet); express the public surface as a single **facade function** `extract(sources, graph_spec, extractors) -> graph`; keep the **graph-definition layer physically separate** from the **extraction/verification metadata** using a data-oriented / entity-component "schema join" so the same taxonomy can be reused with different extractor bindings; carry records as **`dataclasses` internally, Pydantic at the LLM/IO boundary**; orchestrate with **thin hand-composed callables** (or Hamilton if/when lineage and auto-DAG resolution earn their keep) rather than a macro-orchestrator like Prefect; and cache expensive LLM calls on a **deterministic key of (prompt, model params, element spec)**. Package it as a **uv workspace monorepo** with an `src/` layout, core and consumer packages co-located but separately versioned.

## Background / landscape

Creel is a parameterized facade — `extract(sources, graph_spec, extractors) -> graph` — whose whole value proposition is *swappability*: the same graph grammar can be populated by an LLM agent reading a natural-language description, by a SQL-like query over a table, by a Mongo-like query over JSON, or by a regex/function over text. That is the textbook motivation for the **strategy pattern**: "define a family of algorithms, encapsulate each one, and make them interchangeable, letting the algorithm vary independently from the clients that use it" [1]. The classic distinction matters here — Template Method selects an algorithm at *compile time via subclassing*, while Strategy selects at *runtime via composition* [1]. Creel needs the latter: extractors are chosen per element, per run, from config.

In modern Python the strategy pattern rarely needs a class hierarchy at all. `typing.Protocol` gives **structural subtyping** — any object with the right call signature satisfies the interface, no inheritance required [2][3]. Combined with the fact that functions are first-class objects, the most Pythonic encoding of a "strategy" is simply *a callable that conforms to a Protocol*, injected as a parameter. This is the "favour composition over inheritance / program to an interface, not an implementation" guidance that underpins dependency injection [1][2][4].

For *discovery* of strategies, the ecosystem offers a ladder of increasing power and cost:

1. **Decorator/dictionary registries** — a function registers itself by being defined, replacing hard-coded conditionals with a dict lookup; this is the lightest way to honour the Open/Closed Principle [5].
2. **`importlib.metadata` entry points** — the packaging-standard mechanism letting *separately installed* packages advertise plugins under a named group, discovered with `entry_points(group=...)` and lazily materialised via `.load()` [6][7].
3. **`pluggy`** — the "minimalist production-ready plugin system" behind pytest, tox and devpi, built around **hook specifications** (the host's call signatures) and **hook implementations** (plugin-provided), invoked as a *1:N* call loop, with `firstresult=True` for the "only one plugin should answer" case [8][9].

For *orchestration*, the field splits into **micro-orchestrators** (libraries running in one process — Hamilton, which turns functions-as-nodes/parameter-names-as-edges into a DAG with built-in lineage and caching [10][11]) and **macro-orchestrators** (platforms — Prefect, Airflow, Dagster — that schedule jobs and provision compute) [10][12]. Hamilton explicitly positions itself as *complementary* to, not a replacement for, Prefect [10][12]. For *records*, `dataclasses` are the fast stdlib default (validation deferred to a static checker) while **Pydantic v2** is a parsing/validation library with a Rust core, roughly 5–7× slower than a bare dataclass but guaranteeing types at runtime — the consensus is "dataclasses internally, Pydantic at the edges" [13][14]. Pydantic is also the de-facto schema language for **structured LLM extraction** (Instructor, native structured outputs), including knowledge-graph node/edge skeletons [15][16].

## Comparative analysis

### Plugin / strategy discovery mechanisms

| Mechanism | Best for | Coupling | Discovery cost | Multi-impl per hook | Verdict for creel |
|---|---|---|---|---|---|
| Decorator registry (dict) | In-tree, first-party strategies | None (import-time) | Trivial | No (last-write-wins) | **Primary** — built-in extractors |
| `importlib.metadata` entry points | Third-party packages extending creel | Loose (packaging metadata) | Low; lazy `.load()` [6][7] | Yes (iterate group) | **Secondary** — external plugins |
| `pluggy` hooks | Many plugins *cooperating* on one extension point | Moderate (hookspec contract) | Low | **Yes, 1:N call loop** [8][9] | **Deferred** — adopt only if/when needed |
| Class-hierarchy + ABC | Shared default behaviour | Tight (inheritance) | n/a | n/a | **Avoid** for strategies |

The decisive question between entry points and pluggy is: *does a single extension point need many plugins to contribute simultaneously?* Pluggy's reason to exist is the 1:N call loop where N plugins all respond to one hook [8][9]. Creel's extractor binding is fundamentally **1:1** — each graph element resolves to *one* chosen strategy (you don't want three extractors all writing the same edge). That makes entry points + a registry the right tool and pluggy premature complexity. Renderers later are also 1:1 (one renderer per target format). The place pluggy *could* eventually pay off is verification/audit, where you might want several independent verifiers to all weigh in on one element — note that as a future hook, not a current need.

### Orchestration: thin callables vs micro- vs macro-orchestrator

| Option | What it buys | Overhead | When warranted for creel |
|---|---|---|---|
| Hand-composed callables | Full control, zero deps, trivial to test | You write the wiring | **Default now** — extraction is a fan-out/collect, not a deep DAG |
| Hamilton (micro) | Auto-DAG from function signatures, lineage, built-in caching, runs anywhere [10][11] | A dependency + naming discipline | When inter-element dependencies, provenance, and caching become load-bearing |
| Prefect/Airflow/Dagster (macro) | Scheduling, retries, distributed compute, UI [10][12] | A platform/server | Likely **never in core**; a downstream deployment concern |

Hamilton's model is attractive *philosophically* for creel — functions as nodes, parameter names as edges, self-documenting, built-in caching and lineage [10][11] — and its auditability story rhymes with creel's "every element traceable to source." But adopting it in core would couple the engine to a framework before the shape of the dependency graph is known. The honest read: extraction over a graph_spec is mostly **embarrassingly parallel fan-out** (extract each element) plus a join (assemble graph). That is a `map` over callables, not a DAG. Keep orchestration as thin composition; leave a clean seam so a Hamilton (or Prefect) *adapter* can wrap creel later without touching core.

### Records: dataclasses vs Pydantic

| Aspect | `dataclasses` | Pydantic v2 |
|---|---|---|
| Runtime validation | No (static only) [13] | Yes, Rust-backed [14] |
| Speed | Baseline (fastest) [13][14] | ~5–7× slower than dataclass [13][14] |
| JSON Schema export | Manual | Built-in (drives LLM structured output) [15][16] |
| Right role in creel | Internal graph records, hot paths | `graph_spec` parsing, LLM IO boundary, untrusted input |

## Deep dive: physically separating graph-definition from extraction metadata

This is the most consequential architectural decision and the one most specific to creel's posture ("PHYSICAL SEPARATION of the graph definition layer from the extraction/verification metadata layer, joined on demand for reuse"). The right mental model comes from **Entity-Component-System (ECS) / data-oriented design**, where object instances are bare identifiers and their data lives in *separately stored components* keyed by that identity — effectively an **in-memory relational database supporting equijoins** (match component rows by entity id) [17][18]. Components are pure data with no behaviour [17][18].

Translate that to creel:

- **Graph-definition layer** (the grammar / SSOT): node-types and edge-types organised as recursively subdivided taxonomies, each carrying *typed attribute schemas* (freeform, enum, range). This layer is pure declarative data — it describes *what* a valid graph looks like and knows nothing about *how* anything is extracted. Identity is the element's stable address in the taxonomy (e.g. a dotted path `objectives.protection.indicators`).

- **Extraction/verification-metadata layer**: for each element id, *zero or more* strategy bindings — an NL description, a SQL/Mongo query, a regex/function — plus verification rules. This is a second "component table" keyed by the same element id.

- **The join**: at run time, `extract()` performs an **equijoin** of the definition layer against a chosen extractor-binding layer on element id, producing a fully-resolved extraction plan. Different binding tables (one per source corpus, or per consumer) reuse the *same* grammar — exactly the "schema join for reuse" goal.

Why physical separation (two tables joined on demand) beats one fat object per element:

1. **Reuse without duplication** — the consumer taxonomy (donors, objectives, cross-cutting areas, projects, outputs, outcomes, indicators) is authored once; a new source set ships only a new binding table.
2. **Progressive disclosure** — if an element has *no* binding, fall back to the default "schema-as-extractor": synthesise an NL description from the attribute schema and hand it to the LLM. Bindings are purely additive overrides.
3. **Auditability** — verification metadata lives beside extraction metadata, separate from the canonical grammar, so the SSOT (the graph) stays clean while provenance and verification are joinable on demand.
4. **Canonical JSON output stays minimal** — the emitted graph references element ids; the (heavy) extractor/verifier metadata is a side-car, not inlined into every node/edge.

Concretely, model this as two dict-like stores keyed by element id — `GraphSpec` (definition) and `ExtractorBindings` (metadata) — and a pure `join(spec, bindings) -> ResolvedPlan` function. Edges are **first-class** in all three layers: an edge-type is an entity with its own attribute schema (funding amounts, indicator values live *on* edges), its own binding, its own verifier. Do not model edges as a property of nodes.

## Deep dive: the key Python interfaces

The core contract is one Protocol. Everything else composes around it.

```python
from typing import Protocol, runtime_checkable, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class ExtractionContext:
    element_id: str            # address in the taxonomy
    element_schema: "AttrSchema"   # typed attributes for this node/edge type
    sources: "SourceBundle"    # the heterogeneous inputs
    # ... run-scoped services (llm client, cache) injected here

@dataclass(frozen=True)
class Extraction:
    value: Any                 # extracted attribute value(s) / node(s) / edge(s)
    provenance: "Provenance"   # source span(s) -> auditability
    confidence: float | None = None

@runtime_checkable
class Extractor(Protocol):
    def extract(self, ctx: ExtractionContext) -> Extraction: ...

@runtime_checkable
class Verifier(Protocol):
    def verify(self, extraction: Extraction, ctx: ExtractionContext) -> "Verification": ...

@runtime_checkable
class Renderer(Protocol):            # downstream, same shape
    def render(self, graph: "Graph", *, target: str) -> bytes | str: ...
```

`NLExtractor`, `QueryExtractor` (SQL/Mongo), and `PatternExtractor` (regex/function) are *implementations* of `Extractor` — plain callables/objects, no shared base class, conforming structurally [2][3]. A regex or arbitrary `source -> value` function can be adapted into the Protocol with a trivial wrapper, satisfying "functions-as-parameters over inheritance" [1][2][4]. Dependency injection is constructor/parameter injection: the LLM client and cache are passed into `ExtractionContext` (or curried into the extractor), never reached for as globals — the composition-root pattern [4].

Registry skeleton (decorator for in-tree, entry points for external):

```python
_REGISTRY: dict[str, type[Extractor] | callable] = {}

def register_extractor(name):                      # decorator registry [5]
    def deco(obj): _REGISTRY[name] = obj; return obj
    return deco

def load_extractor(name):
    if name in _REGISTRY:
        return _REGISTRY[name]
    from importlib.metadata import entry_points     # third-party plugins [6][7]
    (ep,) = [e for e in entry_points(group="creel.extractors") if e.name == name]
    return ep.load()                                # lazy import
```

Third-party packages then advertise:

```toml
[project.entry-points."creel.extractors"]
my_sql = "my_pkg.extractors:SqlExtractor"
```

## Caching expensive LLM calls

LLM calls dominate cost and are the main reason to cache. Follow LangChain's proven key design: the cache key is the **prompt string plus a deterministic string of the model parameters** (`llm_string`), so the same prompt under different models/params never collides [19]. For creel, extend the key to `hash(prompt, model, params, element_id, source_fingerprint)` so a re-run over unchanged sources is a pure cache hit (reinforcing reproducibility/auditability). Use a persistent disk/SQLite cache for exact-match by default [19]; semantic caches (GPTCache) exist but add embedding+vector infra and approximate hits [19][20] — overkill and *anti-auditability* for an extraction engine where exact reproducibility matters. Inject the cache via the context, keep it pluggable (a `Cache` Protocol with `get/set`), and make it a no-op default so "simple things stay simple."

## Monorepo layout

Use a **uv workspace** — multiple packages, one repo, one lockfile, one virtualenv, internal deps resolved from the workspace (editable) rather than PyPI [21][22]. Inspired by Cargo, it suits "interconnected packages needing unified resolution, such as libraries with plugin systems" [22]. Caveats from the docs: a single `requires-python` (intersection of members) and no enforced import isolation between members [22] — acceptable for a core+consumers split.

```
creel/                      # repo root = workspace
  pyproject.toml            # [tool.uv.workspace] members = ["packages/*"]
  uv.lock                   # single lockfile
  packages/
    creel-core/             # the engine (src layout)
      src/creel/...         # facade, Protocols, registry, join, dataclasses
    creel-extractors-llm/   # default NL/LLM strategy (optional split)
    creel-consumer/         # FIRST CONSUMER: results-framework use case
      src/creel_consumer/...   # taxonomy + bindings, NOT in core
```

Keep core free of consumer-specific taxonomies. The consumer grammar and its extractor bindings are *data + a thin package* in `creel-consumer`, proving the separation-of-layers design by construction.

## Design implications for creel

1. **One Protocol to rule the strategies.** Define `Extractor` (and parallel `Verifier`, `Renderer`) as `runtime_checkable` Protocols; every mechanism is a callable conforming structurally. No `ABC` inheritance for strategies — reserve classes for stateful controllers only [2][3].
2. **Two-table data model, joined on demand.** Physically separate `GraphSpec` (definition SSOT) from `ExtractorBindings` (extraction+verification metadata), both keyed by element id (ECS/equijoin) [17][18]. `join(spec, bindings)` is a pure function producing a resolved plan. This is what makes grammars reusable across source sets and keeps canonical JSON lean.
3. **Registry now, entry points for plugins, pluggy later (maybe).** Decorator registry for built-ins [5]; `importlib.metadata` entry points under group `creel.extractors`/`creel.renderers` for third parties [6][7]. Only adopt pluggy if a *verification* extension point genuinely needs N cooperating implementations [8][9].
4. **Thin orchestration; framework as adapter, not core.** Implement extraction as a `map` of resolved `Extractor` callables + a graph-assembly join. Leave a seam so Hamilton (lineage/caching) or Prefect (scheduling) can wrap creel downstream without invading core [10][12].
5. **Dataclasses inside, Pydantic at the boundary.** `dataclasses` for `Extraction`/graph records; Pydantic v2 for parsing `graph_spec`, validating untrusted sources, and driving LLM structured output / JSON-Schema [13][14][15][16].
6. **Deterministic, exact, pluggable LLM cache.** Key on `(prompt, model, params, element_id, source_fingerprint)` [19]; persistent exact-match default, semantic cache avoided for auditability [19][20]; injected via context behind a `Cache` Protocol.

## Recommendation

**Build creel's core as a single facade function over Protocol-typed callable strategies, with a physically separated two-layer data model (graph-definition vs extraction/verification metadata) joined on demand, discovered via a decorator registry plus `importlib.metadata` entry points — and explicitly defer pluggy, Hamilton, and any macro-orchestrator until a concrete need forces them.** Rationale: this is the smallest design that fully honours creel's stated posture — strategy pattern throughout, DI/functions-over-inheritance, SSOT, progressive disclosure (schema-as-extractor default when a binding is absent), and auditability (provenance on every `Extraction`, exact-match caching for reproducibility). It adds zero heavyweight dependencies to core, keeps "simple things simple" (one `extract()` call, sensible defaults) while leaving every advanced seam — third-party extractors, alternative renderers, DAG orchestration, graph-DB persistence — open for extension without modification (Open/Closed) [5][6]. Package it as a uv workspace so `creel-core` and the first consumer live together yet stay independently versioned and dependency-isolated by intent [21][22].

## References

1. [Strategy pattern — Template vs Strategy, runtime vs compile-time selection (O'Reilly, *Learning Python Design Patterns*)](https://www.oreilly.com/library/view/learning-python-design/9781785888038/ch08s06.html)
2. [Pythonic Dependency Injection: A Practical Guide — Protocols, structural subtyping, composition over inheritance (S. Debel, Medium)](https://medium.com/@suneandreasdybrodebel/pythonic-dependency-injection-a-practical-guide-83a1b1299280)
3. [Best Practices for Python Dependency Injection — Protocol-based design (ArjanCodes)](https://arjancodes.com/blog/python-dependency-injection-best-practices/)
4. [How to Implement Dependency Injection in Python — constructor injection, composition root (OneUptime)](https://oneuptime.com/blog/post/2026-02-03-python-dependency-injection/view)
5. [Python Registry Pattern — self-registering decorators, Open/Closed via dict lookup (SughoshKulkarni, GitHub)](https://github.com/SughoshKulkarni/Python-Registry)
6. [Creating and discovering plugins — naming convention, namespace packages, entry points (Python Packaging User Guide)](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
7. [`importlib.metadata` — entry points discovery and lazy `.load()` (Python 3.12 docs)](https://docs.python.org/3.12/library/importlib.metadata.html)
8. [pluggy — minimalist production-ready plugin system; hookspec/hookimpl, 1:N call loop (pytest-dev, GitHub)](https://github.com/pytest-dev/pluggy)
9. [Writing hook functions; firstresult and hook execution (pytest documentation)](https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html)
10. [Why use Apache Hamilton? — functions-as-nodes DAG, micro- vs macro-orchestrator, lineage, caching (Hamilton docs)](https://hamilton.apache.org/get-started/why-hamilton/)
11. [Apache Hamilton — testable, modular, self-documenting dataflows (apache/hamilton, GitHub)](https://github.com/apache/hamilton)
12. [Declarative data orchestration: Dagster & Hamilton — complementary roles (DAGWorks blog)](https://blog.dagworks.io/p/declarative-data-orchestration-dagster)
13. [Pydantic vs Dataclasses — runtime vs static validation, "dataclass inside, Pydantic at edges" (softwarelogic.co)](https://softwarelogic.co/en/blog/pydantic-vs-dataclasses-which-excels-at-python-data-validation)
14. [Pydantic v2 vs dataclass performance benchmark — ~5–7× validation overhead, Rust core (TildAlice)](https://tildalice.io/pydantic-vs-dataclass-fastapi-performance-benchmark/)
15. [Instructor — structured, validated LLM outputs via Pydantic schemas (567-labs/instructor, GitHub)](https://github.com/567-labs/instructor)
16. [Knowledge Graph Extraction in Pydantic — typed node/edge skeletons from LLMs (DEV Community)](https://dev.to/jhagerer/knowledge-graph-extraction-in-pydantic-32on)
17. [Deep-diving into Entity Component System (ECS) and Data-Oriented Programming — components as pure data, separation of data/logic (PRDeving)](https://prdeving.wordpress.com/2023/12/14/deep-diving-into-entity-component-system-ecs-architecture-and-data-oriented-programming/)
18. [The Entity-Component-System Design Pattern — entities as ids, components stored separately (umlboard.com)](https://www.umlboard.com/design-patterns/entity-component-system.html)
19. [How to cache LLM calls — prompt + deterministic `llm_string` key, SQLite/disk cache (LangChain docs)](https://reference.langchain.com/python/langchain-community/cache)
20. [GPTCache — semantic cache for LLMs, exact vs similarity matching (zilliztech/GPTCache, GitHub)](https://github.com/zilliztech/GPTCache)
21. [How to set up a Python monorepo with uv workspaces — members, single lockfile, single venv (pydevtools)](https://pydevtools.com/handbook/how-to/how-to-set-up-a-python-monorepo-with-uv-workspaces/)
22. [uv Workspaces — Cargo-inspired members/root, editable internal deps, single requires-python, no import isolation (Astral uv docs)](https://docs.astral.sh/uv/concepts/projects/workspaces/)
