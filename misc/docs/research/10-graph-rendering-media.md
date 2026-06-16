# 10 — Graph rendering, annotation & media generation

> **TL;DR.** Creel's "one model, many views" goal is well-served by the ecosystem, but only if creel resists the temptation to ship renderers in core. Every mainstream graph renderer (Graphviz/DOT, Mermaid, Cytoscape.js, D3, vis.js, Sigma.js, pyvis) consumes some flavor of a **node/edge list with an opaque per-element attribute bag** — they differ mostly in *where* visual styling lives and *how* it scales, not in the graph contract. The right move is therefore (a) a tiny, stable **"annotated graph" contract** (typed node/edge list + a *separable* annotation overlay modeled on the **W3C Web Annotation Data Model** standoff pattern), and (b) a **renderer-plugin protocol** (`render(annotated_graph, *, options) -> artifact`) that each downstream package implements. Cytoscape.js is the closest existing format to creel's typed graph and should be the reference web renderer; Graphviz/DOT and Mermaid are the cheap "schema-as-renderer" defaults; python-pptx / Quarto / Jinja+Pandoc are the report/media targets, all of which want a *flattened, denormalized view* of the same graph rather than the graph itself. Keep annotations standoff so insights/comments/captions attach by reference and never mutate the source-of-truth graph.

## Background / landscape

Creel produces a canonical JSON graph: typed nodes and **first-class typed edges** (funding amounts, indicator values live *on edges*), organized in recursively subdivided taxonomies, with full source traceability. The downstream "render" family must turn that single model into many media — interactive web graphs, static diagrams, tables, slide decks, PDF/HTML reports, narrated video — without forking the model per output. This is the classic **model/view separation** problem, and the graph-visualization and annotation-standards worlds have largely converged on patterns creel can borrow wholesale.

Three observations frame the whole survey:

1. **Almost every renderer's input is a node-list + edge-list + opaque attribute bag.** Cytoscape.js wants `{ data: { id, source, target, ...arbitrary } }` per element [1]; D3's force layout wants `{ nodes: [{id, ...}], links: [{source, target, ...}] }` [2]; Sigma.js/graphology want nodes/edges with attribute objects [3]; DOT wants `node [attrs]; a -> b [attrs];` [4]; Mermaid wants `A[label] --> B` text [5]. The *graph contract* is nearly invariant across renderers. What varies is **(a) styling location, (b) edge expressiveness, (c) scale ceiling, (d) interactivity.**

2. **Styling is increasingly *separated from data* by selector/stylesheet — exactly creel's "physical separation" posture.** Cytoscape.js explicitly tells you *not* to put `style` on elements and to use a selector-based stylesheet instead [1]. This mirrors creel's split of the "graph definition" layer from "extraction/verification metadata," and suggests a third separable layer: **presentation metadata** (also joined on demand).

3. **Annotation standards already solved "attach insight without touching the source."** The W3C Web Annotation Data Model [6] and STAM [7] both model an annotation as a *standoff* triple — a **Body** (the insight/comment/caption) related to a **Target** (a node, edge, or subgraph) identified by a **Selector** — stored separately from the annotated resource. This is the right shape for creel's annotation overlay.

## Comparative analysis

### Graph renderers — input shape and fit to a typed graph

| Renderer | Input shape | Edge attributes | Styling location | Scale ceiling | Output | Fit to creel typed graph |
|---|---|---|---|---|---|---|
| **Graphviz / DOT** [4] | Text DSL: `node [a=b]; x -> y [a=b];` | Yes (edge attr lists) | Inline attrs on element | 1k–10k (static layout) | SVG/PNG/PDF | High for static; trivial to emit from node/edge list. The "schema-as-renderer" default. |
| **Mermaid** [5] | Markdown-like text: `A[lbl] --> B` | Limited (edge labels, classes) | `classDef` + class assignment | Low–mid (hundreds) | SVG (in HTML/MD) | High for docs/embeds; weak for rich typed-edge attributes. |
| **Cytoscape.js** [1] | JSON `{elements:{nodes,edges}}`, `data:{id,source,target,...}` | **Yes, arbitrary on `data`** | **Separate stylesheet + selectors** | ~5k–50k (canvas) | Interactive web | **Best structural match.** Typed edge attrs map directly to `data`; styling is already separated. |
| **D3 (force / node-link)** [2] | `{nodes:[{id,...}], links:[{source,target,...}]}` | Yes (on link objects) | Imperative, in render code | ~1k–5k smooth (SVG) | Bespoke interactive | High flexibility, high effort; mutates arrays in place (adds x/y/vx/vy). |
| **vis.js (vis-network)** [8] | `{nodes:DataSet, edges:DataSet}` | Yes (per-edge options) | Per-element options or groups | ~5k (canvas + physics) | Interactive web | Good; physics + clustering built-in; styling tends to live on elements. |
| **Sigma.js + graphology** [3] | graphology graph; node/edge attribute objects (`x,y,size,...`) | Yes (edge attributes) | Attributes + reducers | **100k–500k (WebGL)** | Interactive web (large) | Best for *large* extracted graphs; needs a layout pass (x/y). |
| **pyvis** [9] | Python `add_node/add_edge` (wraps vis.js) | Yes | Python kwargs → vis.js | ~5k | Standalone HTML | Best *Python-side* quick interactive view; thin wrapper over vis.js. |
| **netwulf** | Interd. with networkx; interactive layout → styled export | via networkx attrs | Interactive UI → style dict | mid | PNG/SVG + style JSON | Niche; good for human-in-loop styling of networkx graphs. |

Key takeaway: **the JSON node/edge-with-attribute-bag is the lingua franca.** Cytoscape.js is the canonical match because (i) edges are first-class objects carrying arbitrary `data` (creel needs edge attributes), and (ii) it already enforces data/style separation [1]. Sigma.js is the escape hatch for very large extracted graphs (WebGL, 100k+ nodes) [3]. DOT and Mermaid are the cheapest static/embeddable defaults [4,5].

### Annotation models — how to attach insights as a separable overlay

| Model | Annotation unit | How it targets | Separability | Standardization |
|---|---|---|---|---|
| **W3C Web Annotation Data Model** [6] | `Annotation` = Body + Target | Target by IRI + **Selector** (TextQuote, TextPosition, Fragment, CSS, XPath, SVG, Range) | **Fully standoff** via `SpecificResource` + `selector`; source untouched | W3C Recommendation (JSON-LD) |
| **STAM** [7] | Annotation over text, "in your own terms" | Offset/selector into plain UTF-8 text | **Fully standoff**; primary data is read-only | Community spec, schemas + impls |
| **Inline / embedded markup (XML/HTML)** | Tag in the data stream | Position in tree | **Not** separable; can't overlap hierarchies cleanly [10] | n/a |

The W3C model's three-part shape — **Annotation → (Body, Target via Selector)** — is exactly what creel needs, generalized from "text spans" to "graph elements." The decisive argument for standoff is the same one that motivates it in text: standoff annotations *may freely overlap* and don't have to conform to the host structure [10], and the **source of truth is never mutated** — which is creel's core design posture (auditability, SSOT). One caveat to flag honestly: standoff's classic fragility is that **if the underlying resource changes, offset/position selectors break** [7,10]. For creel this is *less* severe than in text, because graph elements have stable **IDs** rather than character offsets — so creel should target by element ID (an IRI-like stable key), not by positional selector.

### Media generators — input shape and the "flatten the graph" requirement

| Target | Library / tool | Input shape it wants | Recency |
|---|---|---|---|
| **Tables** | pandas / native | Rows of records (denormalized join of nodes+edges) | n/a |
| **Slides (PPTX)** | python-pptx 1.0.0 [11] | Imperative shape/table/chart API per slide; commonly driven from JSON/DB payload | 1.0.0 (2024) |
| **Reports (PDF/HTML)** | Quarto [12] | Markdown/notebook **template + parameters**; render per-param | Active; parameterized-report Python support 2025 [12] |
| **Reports (lightweight)** | Jinja2 + Pandoc [13] | YAML/dict data → Jinja template → Markdown → Pandoc → PDF/HTML | Pandoc templating ~Jinja-like [13] |
| **Data narrative / auto-insight** | NLG (Quill/Wordsmith), LLM, Power BI narratives [14] | Structured records + a narrative spec; LLM reads graph + annotations | Industry-standard NLG; LLM now dominant |
| **Narrated video** | Slide+TTS pipelines (Paper2Video, PresentAgent, etc.) [15] | Slides/structured content → LLM script → TTS → synced video | Active 2025 research [15] |

The uniform lesson: **media generators do not want the graph; they want a flattened, denormalized *view* of it.** A table wants rows. A slide wants a title + bullets + maybe one chart. A report wants sections keyed by node-type/taxonomy level. A narrative wants records + the annotation overlay as the "what's interesting" signal. So between the canonical graph and these renderers there must be a **view/projection layer** that joins nodes, their typed edges, and their annotations into renderer-shaped records.

## Deep section: the minimal "annotated graph" contract

Creel core's *output* is the canonical JSON graph. Renderers should consume a slightly enriched, still-minimal structure. I propose three physically separable but joinable layers (mirroring creel's existing definition/extraction split):

1. **Graph layer (SSOT).** Typed node-list + typed edge-list. Each element: stable `id`, `type` (a path in the taxonomy, e.g. `objective/outcome`), and a typed `attributes` bag (values constrained per the grammar). Edges additionally carry `source`, `target`, and their own `attributes` (funding amount, indicator value). This is essentially **Cytoscape.js `data` objects** without the cytoscape-specific keys — a deliberate near-isomorphism so the reference web renderer is a 1:1 map.

2. **Annotation overlay (standoff, separable).** A list of annotations, each modeled on W3C Web Annotation [6]:
   - `target`: a **stable element ID** (node id, edge id, or a set of ids for a subgraph) — *not* a positional selector, to avoid standoff fragility [7].
   - `body`: the insight/comment/caption (freeform text, or typed: `kind ∈ {insight, caption, warning, citation, ...}`).
   - `motivation`/`role` (optional, from the W3C roles vocabulary): e.g. `commenting`, `highlighting`, `describing`.
   - `provenance`: who/what produced it (LLM agent, human reviewer) + source trace — reusing creel's auditability metadata.
   This overlay is stored **separately and joined on demand**, so the same graph renders with or without annotations, and multiple overlays (analyst A vs. analyst B; draft vs. final) coexist over one graph.

3. **Presentation hints (optional, separable).** Selector→style mappings in the Cytoscape.js spirit [1] (e.g. "edges of type `funding` → width ∝ `amount`"). Kept out of the graph layer so styling never pollutes the SSOT.

A renderer therefore receives `(graph_layer, annotation_overlay?, presentation_hints?)`. Minimal viable contract = **graph_layer alone**; everything else is progressive disclosure.

## Deep section: the renderer-plugin interface

Renderers must **not** live in creel core (core stays an extraction engine). Define a thin protocol in core and let consumer packages implement it — strategy pattern, dependency injection, open/closed.

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class GraphRenderer(Protocol):
    # Declarative metadata so a registry/facade can pick a renderer.
    name: str                      # e.g. "cytoscape", "dot", "pptx"
    output_media_type: str         # e.g. "text/html", "image/svg+xml", "application/pptx"
    consumes_annotations: bool     # whether it uses the overlay

    def render(
        self,
        graph: "AnnotatedGraph",   # the minimal contract above
        *,
        options: dict[str, Any] | None = None,
    ) -> "RenderArtifact": ...     # bytes/path/handle + media_type + metadata
```

Design notes tied to creel's posture:

- **Strategy + registry.** Renderers register by `name`/`output_media_type`; a facade `render(graph, view="pptx")` dispatches. Same shape as creel's pluggable *extractors*, giving the package a consistent mental model (extract-strategy in, render-strategy out).
- **Projection helpers in a shared `creel.view` module, not in each renderer.** Provide reusable, side-effect-free projections: `to_node_edge_records(graph)` (for D3/Cytoscape), `to_dot(graph)`, `to_mermaid(graph)`, `to_table(graph, by=...)` (denormalized rows), `to_sections(graph, taxonomy_level=...)` (for reports/slides). These are the "flatten the graph" layer every media generator needs; renderers consume *projections*, not raw graph internals. Per the iterables principle, these return generators/iterables of records, not eager structures, where size warrants.
- **Annotations are optional input, never required.** A renderer that ignores annotations still works; one that uses them reads the overlay as "what to caption/highlight/narrate." This makes the annotation overlay the natural bridge to the **data-narrative and narrated-video** targets [14,15]: the LLM script generator reads `(graph + overlay)` and the overlay's `body` text becomes caption/narration seed material.
- **Audit-preserving rendering.** Because every node/edge is source-traceable in creel, renderers should be able to surface provenance (e.g. Cytoscape tooltips, report footnotes, slide speaker-notes) by reading the trace metadata already on each element. Recommend a convention: any renderer *may* emit a "provenance" channel (tooltip/footnote/note) but never silently drops it.

## Design implications for creel

1. **Do not ship renderers in core; ship the contract + projections + a Protocol.** Core emits the canonical graph; a `creel.view` module offers stable projections; consumer packages (`creel-cytoscape`, `creel-pptx`, `creel-quarto`, …) implement `GraphRenderer`. This keeps core an extraction engine and honors open/closed + DI.

2. **Make the annotation overlay a standoff layer keyed by element ID, modeled on W3C Web Annotation [6].** Body+Target+(role/provenance), stored separately, joined on demand — exactly parallel to creel's definition/extraction split. Target by **stable ID, not positional selector**, to dodge standoff fragility [7,10]. This gives "attach insight without mutating the SSOT" for free and lets multiple overlays coexist.

3. **Adopt Cytoscape.js element shape as the near-canonical graph layer.** Since creel needs first-class typed edges and data/style separation, and Cytoscape.js already provides exactly that [1], align the internal graph-layer keys (`id/source/target/attributes`) so the reference web renderer is an (almost) identity map and other renderers are simple projections.

4. **Provide DOT and Mermaid as zero-config "schema-as-renderer" defaults.** They're text, versionable, dependency-light, and embed in docs/READMEs/issues [4,5]. They satisfy progressive disclosure: a user gets a picture with no renderer install. Reserve Sigma.js/WebGL [3] as the documented escape hatch for very large extracted graphs.

5. **Insert an explicit projection/flatten layer between graph and media generators.** Tables want rows, slides want title+bullets+chart, reports want taxonomy-keyed sections, narratives want records+overlay [11,12,13,14]. A single `to_*` projection family serves all of them and is independently testable.

6. **Treat the annotation overlay as the narrative seed for slides/reports/video.** Auto-insight and slide+TTS pipelines [14,15] consume "what's interesting" signals; creel's overlay (LLM- or human-authored `body` text per element) is precisely that signal, so the narrative renderers should read the overlay first and the raw attributes second.

## Recommendation

**Define a three-layer "annotated graph" contract and a single `GraphRenderer` Protocol, then keep all concrete renderers out of core.** Concretely: (1) the **graph layer** is a typed node/edge list whose element keys are intentionally isomorphic to **Cytoscape.js `data` objects** [1] (`id`, `source`, `target`, plus a typed `attributes` bag, including edge attributes); (2) the **annotation overlay** is a *standoff* list of W3C-Web-Annotation-style records [6] (`body` + `target`-by-ID + role/provenance) stored and joined separately; (3) **presentation hints** are optional selector→style mappings. Core ships this contract plus a `creel.view` projection family (`to_dot`, `to_mermaid`, `to_node_edge_records`, `to_table`, `to_sections`) and the `GraphRenderer` Protocol; consumer packages implement renderers (Cytoscape.js as reference interactive view, Graphviz/Mermaid as default static views, Sigma.js for scale, python-pptx/Quarto/Jinja+Pandoc for media). Rationale: this is the *minimum* that gives "one model, many views," preserves the SSOT and auditability creel is built on (nothing mutates the graph; provenance flows through), matches the strategy/DI pattern already used for extractors, and aligns with the de-facto standards every renderer and annotation tool already speaks — so each downstream package is a thin, well-understood adapter rather than a new model.

## References

1. [Cytoscape.js — official documentation (element JSON: `data:{id,source,target,...}`, parent compound nodes, stylesheet/selector separation)](https://js.cytoscape.org/)
2. [JSON Graph Data: Adjacency List & D3.js Format (D3 `nodes`/`links` node-link shape)](https://jsonic.io/guides/json-graph-data) and [How to Implement a D3.js Force-directed Graph (2025)](https://dev.to/nigelsilonero/how-to-implement-a-d3js-force-directed-graph-in-2025-5cl1)
3. [Sigma.js — Graph data docs (graphology backend; node/edge attributes; x/y/size)](https://www.sigmajs.org/docs/advanced/data/) and [sigma.js repository](https://github.com/jacomyal/sigma.js/)
4. [DOT (graph description language) — Wikipedia](https://en.wikipedia.org/wiki/DOT_(graph_description_language)) and [Graphviz documentation](https://graphviz.org/documentation/)
5. [Mermaid — Flowchart syntax (declarative text; classDef styling)](https://mermaid.js.org/syntax/flowchart.html) and [mermaid-js/mermaid repository](https://github.com/mermaid-js/mermaid)
6. [W3C Web Annotation Data Model (Recommendation): Annotation/Body/Target, Selectors, SpecificResource standoff pattern](https://www.w3.org/TR/annotation-model/)
7. [STAM: Stand-off Text Annotation Model (specification & repository)](https://annotation.github.io/stam/) and [annotation/stam on GitHub](https://github.com/annotation/stam)
8. [vis.js / vis-network comparison and data model overview](https://www.pkgpulse.com/guides/cytoscape-vs-vis-network-vs-sigma-graph-visualization-2026)
9. [pyvis — Python interactive network graphs over vis.js (repository)](https://github.com/WestHealth/pyvis) and [Network visualizations with Pyvis and VisJS (SciPy 2020)](https://arxiv.org/abs/2006.04951)
10. [Standoff annotation overview / overlapping-hierarchy motivation (STAM intro)](https://annotation.github.io/stam/) and [Extending standoff annotation (LREC 2014)](https://aclanthology.org/L14-1274/)
11. [python-pptx 1.0.0 documentation (generate slides from JSON/DB payloads)](https://python-pptx.readthedocs.io/)
12. [Quarto — Parameterized reports with the Jupyter engine (2025)](https://quarto.org/docs/blog/posts/2025-07-24-parameterized-reports-python/index.html) and [Automating Quarto reports with parameters (Posit)](https://posit.co/blog/parameterized-quarto)
13. [Creating PDF Reports with Pandas, Jinja and WeasyPrint](https://pbpython.com/pdf-reports.html) and [roboprose: Jinja2 + Pandoc document generation](https://github.com/jduckles/roboprose)
14. [Get natural language narratives in Power BI Reports (Microsoft)](https://powerbi.microsoft.com/en-us/blog/get-natural-language-narratives-in-power-bi-reports/) and [Quill / Narrative Science NLG overview](https://en.wikipedia.org/wiki/Automated_Insights)
15. [Generating Narrated Lecture Videos from Slides with Synchronized Highlights (arXiv 2025)](https://arxiv.org/pdf/2505.02966) and [PresentAgent: Multimodal Agent for Presentation Video Generation (arXiv 2025)](https://arxiv.org/pdf/2507.04036)
