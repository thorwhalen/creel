# A General Source-to-Graph Extraction Engine — Core Package Description

*Vision brief for an implementing agent. This document conveys intent and the
ideas behind the design; it is deliberately not an implementation or detailed
design specification. It captures **what** the package is for and the **shape**
of the thinking, so that design and implementation choices can be made
downstream without losing the original intent.*

**Author:** Thor Whalen
**Status:** Core description / vision — to hand to an implementing agent
**Working name:** TBD (candidates that fit the "one graph, many renders" theme:
*Prism*, *Loom*, *Lattice*)

---

## 1. What this package is

At its core, this is a tool that uses AI to **extract a typed graph from a
heterogeneous set of sources** — freeform documents, semi-structured documents,
tables, JSON, schema specifications, and so on — and emits that graph as a clean,
explicit data structure (canonically, a JSON graph specification).

Conceptually the package is a single parameterized function — a facade — of the
form:

```
extract(sources, graph_spec, extractors) → graph
```

where the caller supplies (a) the **sources** to read, (b) a **specification of
the graph** they want populated (its grammar of node and edge types and the
typed values these carry), and (c) the **extractors** — the instructions,
skills, and ETL tools that know how to detect and pull each element out of the
sources. The output is a graph that conforms to the supplied specification.

Everything else in the package — persistence, querying, annotation, rendering to
media — is **downstream** of this core, and treats the extracted graph as a
**single source of truth** from which many views are projected. The package's
primary job is to get faithfully and auditably from *sources* to *graph*; its
secondary job is to make those downstream uses as easy as possible to build
without prescribing how they must be built.

**First application.** The package is being built with one concrete first use in
mind: UNHCR ESA Bureau use case #3 (the strategic frame) — extracting, from a
pile of project and donor documents, a graph of donors, objectives,
cross-cutting areas, projects, outputs, outcomes, and indicators, with funding
amounts and indicator values on the edges. But the package itself is **general**:
the UN case is the first consumer of a tool meant to serve any source-to-graph
problem.

---

## 2. The graph grammar — *what* we extract

The thing being extracted is described by a **grammar**. At the top level the
grammar has exactly two general classes of element:

- **Nodes** (a.k.a. points)
- **Edges** (a.k.a. links)

Each of these two classes can carry a **taxonomy** — a set of subtypes — and each
subtype can be further subdivided, recursively, into more specific classes. (In
the UN case, for example, node subtypes include *Donor*, *Objective*,
*Cross-cutting area*, *Project*, *Output*, *Outcome*, and *Indicator*; edge
subtypes include relations such as *funds*, *delivers*, *contributes-to*,
*advances*, and *addresses*.)

Every element — node type or edge type — carries a set of **typed attributes**
(the "leaf" values). These follow ordinary schema semantics: a value may be a
freeform string or number (or lists thereof), or it may be constrained — drawn
from a fixed set of allowed values, bounded to a range, or otherwise restricted.
This is the usual schema machinery; the package needs a general way to express
it for both nodes and edges.

So the grammar gives us two schemas to design and keep general:

1. a schema for **describing an extracted graph** (the instances), and
2. a schema for **specifying the elements** of the grammar (the types,
   taxonomies, and attribute definitions).

---

## 3. Extraction specifications — *how* we detect and extract

Knowing *what* the graph should contain is only half the problem. The other half
is specifying **how to detect, extract, and verify** each element's values from
the sources.

These extraction specifications are **logically woven into the grammar**: every
element of the graph ideally comes paired with a specification of how to find it,
how to pull its values, and how to **verify** it — where verification goes beyond
mere schema/type checking into semantic validity, cross-checks, and confidence.

A strong hunch shapes the storage of this: although extraction/verification
metadata is *logically* part of each element, it should be **physically
separable** — at least when stored. Keeping the "how to extract" metadata
separate from the "what the graph is" definition makes **reuse by
combination/join** far easier: the same node-type definition can be paired with
different extraction strategies for different source types, and the same
extraction strategy reused across grammars, by joining the two layers rather than
duplicating them.

### Forms of extraction specification (use the strategy pattern)

Extraction specifications can take many forms, and the design should treat the
form as **pluggable** — a strategy — rather than fixing a single mechanism. Among
the forms to support:

- **Natural-language description** — the canonical default form: a plain-language
  account of what to look for, read and applied by an LLM-enabled agent.
- **Query forms over structured sources** — e.g. an SQL-like query for tables, or
  a Mongo-like query for JSON and lists of JSON.
- **Pattern/functional forms** — regular expressions, or any general function
  that maps source content to a value.

The strategy pattern should apply **here and elsewhere** in the package, so that
new extraction mechanisms can be added without touching existing ones
(open–closed), and so a given field can be matched to whatever mechanism suits
its source best.

### Defaults

The package should provide sensible defaults so simple cases stay simple. A
natural one: **the schema itself can serve as the extractor's description** — per
field or across multiple fields, the type/attribute definition is handed to the
extractor as the description of what is being looked for. This means a usable
extraction can often be derived directly from the grammar with no extra authoring.

---

## 4. Sources

Sources are heterogeneous and the design should embrace that:

- **Freeform documents** — prose, reports, narratives — handled primarily by
  LLM-driven natural-language extraction.
- **Structured and semi-structured sources** — tables, JSON, lists of JSON, and
  similar — which can (and should) arrive **with their own schemas**. When a
  source carries a schema, extraction can be made **more robust**: the schema
  constrains and guides what is pulled, reducing ambiguity and error.

The package should make it natural to mix these within a single extraction run,
applying the appropriate extraction strategy to each source type.

---

## 5. Design posture (ideas to carry, not prescriptions to lock)

Without fixing implementation, the following intentions should guide whoever
builds this:

- **Single source of truth.** The extracted graph is the SSOT; persistence,
  analysis, and media are projections of it, never parallel copies of the truth.
- **Separation of concerns with physical separation for reuse.** Keep the *graph
  definition* and the *extraction/verification metadata* in separate layers that
  are joined on demand, so each can be recombined and reused independently.
- **Strategy pattern throughout.** Extraction mechanisms, and later the renderers,
  should be swappable plugins. Favour composition and functions-as-parameters
  over hard-wired behaviour.
- **Progressive disclosure.** Simple things simple (schema-as-extractor defaults,
  one obvious path), complex things possible (custom extractors, custom
  verification, custom renders).
- **Auditability over opaqueness.** Because AI extraction can hallucinate or miss
  things, the graph must be explicit and reviewable, and elements should carry the
  means to be verified — the structure should never be buried in prose.

---

## 6. Downstream processes — *enabled here, implemented elsewhere*

The package's focus is **sources → graph**. We do not implement the downstream
consumers in the core, but we design so as to **enable them as fully as
possible**. Two downstream families matter most:

### 6.1 Persistence and operation (CRUD + query)

Once a graph exists, we want to store it and operate on it — create, read,
update, delete, and **query**. Target environments include **graph databases**,
**graph knowledge bases**, and **graph-based RAG**. The core should make the
extracted graph clean and well-typed enough to flow naturally into any of these,
without committing the core to any one of them.

### 6.2 Analysis and media production

We also want to turn the graph into **analysis media**. This involves two pieces:

- An **annotation layer** — insights, comments, captions, and other
  interpretation laid over the graph. Like the extraction metadata, this is
  **logically woven into** the graph but may be **physically separate**, so
  annotations can be versioned, swapped, and reused independently of the
  underlying graph.
- A set of **renderers** that take the annotated graph and produce output media:
  images, tables, PowerPoint presentations, written reports, even narrated video.
  Many renderers, one graph — the same "one model, many views" principle that
  motivates the whole package.

These downstream consumers may or may not themselves run on top of the
persistence system (e.g. a graph DB); the design should not assume they do.

---

## 7. Packaging strategy

How much belongs in the core package versus externalized into separate packages
is an open question, deliberately left open for now. The near-term approach:

- Go **monorepo**. Keep the downstream examples (a persistence consumer, a
  media/render consumer) **separate from the core but in the same repository**, as
  worked examples that prove the core enables them.
- As those examples mature, **graduate them into their own "consumer" packages**,
  leaving the core focused on the sources → graph mission.

---

## 8. Summary

The package is a **general, AI-powered source-to-graph extraction engine**:
a parameterized facade that takes heterogeneous sources, a grammar of node and
edge types with typed attributes, and a set of pluggable extraction/verification
strategies, and produces a clean, auditable, typed graph as a single source of
truth. Its core mission is extraction; it is designed to *enable* — without
implementing — downstream persistence/query (graph DBs, knowledge bases, RAG) and
downstream annotation-and-rendering into analysis media (tables, slides, reports,
video). It is being built first for the UNHCR ESA strategic-frame use case, but is
general by design.
