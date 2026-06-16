# 04 — LLM-based information & knowledge-graph extraction

> **TL;DR.** As of early 2026, extracting *typed, structured* graphs from documents with LLMs has converged on a recognizable recipe: **schema/ontology-guided extraction** (the schema is the prompt), enforced by **constrained-decoding structured output** (JSON-Schema → grammar → token masking), decomposed over long inputs by **chunk → map → reduce → consolidate/dedup**, and made trustworthy by **grounding entities to identifiers and tracing every fact back to source spans**. The classical IE building blocks (NER, relation extraction, coreference, entity linking) survive as *strategies* inside LLM pipelines rather than as the whole pipeline. The most directly reusable systems for creel are **SPIRES/OntoGPT** (recursive, field-by-field, schema-driven, ontology-grounded — the cleanest match to creel's "schema-as-extractor" default), **Microsoft GraphRAG** (gleaning + auto-tuned few-shot + edge-as-first-class extraction), and **iText2KG/ATOM** (separated entity/relation passes + incremental graph integration). For Claude specifically, Anthropic's November-2025 **Structured Outputs** (now GA, grammar-compiled, `output_config.format` + strict tool use) is the production-grade enforcement layer creel's NL-description strategy should compile down to. The single biggest design lever: **make the graph-definition layer emit a JSON Schema per node/edge type and run extraction as constrained decoding, not free-form parsing.**

---

## Background / landscape

Knowledge-graph (KG) construction traditionally ran a brittle multi-stage pipeline: **named-entity recognition (NER) → coreference resolution → relation extraction (RE) → entity linking/resolution → schema mapping**, with errors compounding across stages [1][7]. Open Information Extraction (OpenIE) relaxed the schema requirement, emitting open `(subject, relation, object)` triples but leaving normalization unsolved. The first big LLM-era shift was **end-to-end generation**: REBEL (EMNLP 2021) reframed RE as seq2seq "translation" of text into linearized triplets using special tokens (`<triplet>`, `<subj>`, `<obj>`), covering 200+ relation types in one autoregressive pass and collapsing the multi-step pipeline [8]. REBEL still needed supervised training per relation set; the LLM era's second shift was **zero/few-shot, schema-guided extraction** where the *schema itself becomes the prompt* and no task-specific training is required.

The October-2025 survey *LLM-empowered Knowledge Graph Construction* [7] frames the field cleanly along two axes that map almost perfectly onto creel's design posture: **schema-based** paradigms (structure, normalization, consistency — an ontology as a fixed or dynamically-selected semantic backbone) versus **schema-free** paradigms (flexibility, open discovery), applied across three stages — ontology engineering, knowledge extraction, knowledge fusion. Creel sits deliberately on the **schema-based** side (the `graph_spec` grammar is the SSOT), while keeping a schema-free escape hatch (freeform attributes, LLM-chosen properties).

Around this core, an ecosystem of concrete document-to-KG systems matured: **LangChain `LLMGraphTransformer`**, **LlamaIndex `PropertyGraphIndex`**, **Microsoft GraphRAG**, **SPIRES/OntoGPT** (Monarch Initiative), **iText2KG → ATOM**, and schema-guided agent systems like **OneKE** and Apple's **ODKE+** [4][6]. Orthogonally, the **structured-output** infrastructure (Instructor, Outlines, XGrammar, provider-native JSON modes including Anthropic's Structured Outputs) turned "get valid typed JSON out of an LLM" from a parsing gamble into a near-guarantee.

---

## Comparative analysis

### Document-to-KG systems

| System | Schema model | Extraction strategy | Edge attributes | Long-doc handling | Grounding/audit | Reusable idea for creel |
|---|---|---|---|---|---|---|
| **REBEL** [8] | Fixed relation set (trained) | Seq2seq triplet generation (BART) | No (bare triples) | N/A | Weak | Linearized triplet decoding as a *pattern* extractor |
| **LangChain LLMGraphTransformer** [9] | `allowed_nodes`, typed `(src,REL,tgt)` tuples | Tool/function-calling (default) or few-shot prompt (fallback) | **Yes, but all string-typed, global not per-type** | Per-doc, async parallel | `strict_mode` post-filter | Three-tuple edge typing; tool-call default w/ prompt fallback |
| **LlamaIndex PropertyGraphIndex** [10] | Pluggable `kg_extractors` (schema or free) | Per-chunk extractors attach entities/relations as node metadata | Yes (properties on relations) | Chunk-level, composable extractors | Source node provenance | Pluggable per-chunk extractor *strategy* slot |
| **Microsoft GraphRAG** [11][12] | Few-shot entity/relation types; **auto-tuned** to domain | Prompt + **gleaning** (multi-turn re-ask) | **Yes — descriptions/weights live on edges** | Chunk → extract → **community summaries** (map-reduce) | Source-doc IDs per claim | Gleaning loop; auto-tuned few-shot; edges as first-class |
| **SPIRES / OntoGPT** [3][5] | **LinkML** data model (declarative) | **Recursive, field-by-field** prompting | Yes (typed slots, incl. nested classes on relations) | Recursive over nested ranges | **Ontology IDs via OAKlib (98% vs 3% F1 grounding)** | Field-decomposition + ontology grounding |
| **iText2KG / ATOM** [2] | JSON-shaped schema as guide | **Separate** entity pass then relation pass; graph integrator | Yes | Incremental, "atomic facts", topic-independent | Entity dedup at integration | Separate passes + incremental consolidation |
| **OneKE / ODKE+** [4][6] | Schema-guided agent; dynamic "ontology snippets" | Multi-agent; pattern rules + ontology-guided prompts | Yes | Agentic | Evidence retrieval per fact | Dynamic schema-subset selection per entity |

> **Verified claim, flagged.** GraphRAG's "gleaning" is a *completeness* loop (re-prompt the LLM to extract entities/relations it missed over multiple turns), confirmed across the GraphRAG docs and independent write-ups [11][12]. The default GraphRAG prompt ships only 3 entity types (organization, person, geo) with ~15 entity / ~12 relation examples; **auto-tuning** generates domain-appropriate few-shot examples — important because creel's domains (e.g. UNHCR strategic frames) are nothing like the defaults [11].

### Structured-output / enforcement mechanisms

| Mechanism | How it constrains | Guarantee | Typed attributes / enums / ranges | Notes for creel |
|---|---|---|---|---|
| **Prompt-only JSON ("please return JSON")** | None (instruction) | None — parse-and-retry | Soft | Baseline; brittle |
| **Function/tool calling** | Schema as tool params | Schema-shaped, not guaranteed valid pre-2025 | Enums yes; numeric ranges weakly | LangChain's default mode |
| **Provider JSON mode + JSON Schema** | Schema attached to response | Valid JSON; structure enforced | Enums yes; some numeric limits | OpenAI 2024; Anthropic 2025 |
| **Constrained decoding / grammar (Outlines, XGrammar, llguidance)** | JSON-Schema → CFG → **token-mask logits** | **Cannot emit invalid tokens** | Enums/const strong; numeric *range* weak | XGrammar is default backend in vLLM/SGLang/TensorRT-LLM; <40 µs/token [overhead] |
| **Anthropic Claude Structured Outputs** [13] | JSON-Schema **compiled to grammar**, constrained decoding, grammar cached 24 h | **Always valid; types & required fields guaranteed** | Enums/const/formats yes; **numeric min/max & string length NOT enforced** | GA on Opus 4.5+/Sonnet 4.5+/Haiku 4.5; `output_config.format` + per-tool `strict:true` |
| **Validation libraries (Instructor + Pydantic)** [14] | Post-hoc validate → auto-retry | Eventually valid; custom validators | **Full Pydantic validators (ranges, regex, cross-field)** | Provider-agnostic; the place to enforce what grammars can't |

> **Important nuance for creel's "constrained" attributes.** Grammar-level enforcement guarantees *enums*, *types*, *required fields*, and string *formats* (date, uri, email, uuid). It does **not** reliably enforce numeric **ranges** (`minimum`/`maximum`), `multipleOf`, or string length — both XGrammar-class backends and Anthropic's Structured Outputs explicitly list these as unsupported [13]. Creel's `graph_spec` allows ranges on attributes (e.g. an indicator value in `[0,100]`, a funding amount > 0). **Those constraints must be enforced post-decode with Pydantic validators (Instructor-style), not assumed from the schema.** This is a load-bearing fact, cross-checked against the Anthropic docs' explicit limitations table and the constrained-decoding literature.

---

## Schema/ontology-guided extraction: the central pattern

Every serious 2024–2026 system makes the schema the primary control surface, and they differ mainly in *how rigid* the schema is and *how much of it is shown to the model at once*:

- **Static schema-as-backbone** (early): the full ontology constrains a single extraction pass — high consistency, low flexibility [7].
- **Dynamic ontology snippets** (ODKE+): select a *subset* of the ontology relevant to the entity at hand and inject only that into the prompt — context-aware, token-efficient, scales to large ontologies [6].
- **Field-by-field decomposition** (SPIRES): instead of one mega-prompt for the whole object, generate one targeted prompt **per attribute**, parse each response according to that field's declared range/cardinality, and **recurse** when a field's range is itself a class (e.g. a recipe → steps → ingredients → quantities) [3][5]. This is the cleanest answer to "complex, deeply-typed, recursively-subdivided schemas" — exactly creel's taxonomy structure.
- **Separated entity/relation passes** (iText2KG, the survey's general finding): extracting entities first, then relations conditioned on the resolved entity set, measurably improves precision over joint extraction [2][7].

**Ontology grounding** is the differentiator between a pretty-but-wrong graph and an auditable one. SPIRES reports an F1 of ~98% for grounding entities to Gene Ontology IDs *with* its grounding step versus ~3% from the raw LLM — i.e. LLMs are competent at *spotting* an entity and hopeless at *assigning it the correct canonical ID* unsupervised [3]. The fix is to treat grounding as a separate, deterministic strategy: LLM proposes a surface form + type; a lookup/annotator (OAKlib, an embedding index, a SQL dimension table) resolves it to a canonical node ID.

---

## Long-document and multi-document strategies

The consensus pipeline for inputs that exceed context (or simply benefit from focus):

1. **Chunk** with *overlapping windows* so cross-boundary entities/relations appear intact in at least one chunk; chunk on semantic/structural boundaries (sections, table rows) where possible [GraphRAG, Hyper-KGGen].
2. **Map**: run the schema-guided extractor per chunk, optionally with a **gleaning** loop (re-ask "what did you miss?") to raise recall [11].
3. **Reduce / consolidate**: merge per-chunk graphs, resolving **inter-chunk conflict** (contradictory values) via confidence calibration and **inter-chunk dependency** (a fact needing context from another chunk) [LLM×MapReduce].
4. **Dedup / entity resolution**: collapse co-referent nodes. Cheap signal first (normalized string / Jaccard threshold ~0.75), then embedding similarity, then an LLM adjudication pass for the ambiguous tail; relations dedup by `(canonical_src, type, canonical_tgt)` [iText2KG, Hyper-KGGen].

Multi-document consolidation is the same reduce step at a higher level: the graph is the join key, so two documents mentioning the same donor or objective converge on one node — *provided* grounding assigns stable IDs. GraphRAG additionally builds **community summaries** over the consolidated graph, which is a downstream concern for creel (graph RAG) but validates the "graph as SSOT, summaries derived on demand" stance.

---

## Tables, JSON, and schema-bearing sources

When a source already carries structure, **using an LLM to read it cell-by-cell is the wrong default** — it's slow, expensive, and hallucination-prone. The literature and tooling favor *exploiting the source's own schema*:

- **Tables / relational sources**: prefer **deterministic queries** (text-to-SQL or direct SQL/DataFrame ops) where the mapping from columns → node/edge attributes is known; use the LLM only to *author* the mapping or to handle messy free-text cells. Surveys of tabular LLM use (TAP4LLM-style table packing, text-to-SQL for enterprise analytics) consistently show that providing the LLM the *schema* (column names/types) and letting it emit a query beats asking it to transcribe values [text-to-SQL refs in survey set].
- **JSON / semi-structured**: a Mongo-like projection/filter over the source is both cheaper and verifiable; the source schema *is* the extractor spec.
- **Hybrid**: route per-field — structured fields via query/pattern extractors, free-text fields via the LLM extractor. This is precisely what ODKE+'s "hybrid knowledge extractors" (pattern rules + LLM prompting) and GraphRAG's mixed pipelines do [6][11].

This directly validates creel's three extractor strategy families: **(a) NL-description/LLM**, **(b) query forms (SQL-like for tables, Mongo-like for JSON)**, **(c) pattern/functional (regex / `source→value`)** — with the query and pattern strategies being *preferred* whenever the source's structure makes them applicable.

---

## Hallucination, faithfulness & auditability

Two failure modes matter [15][16]: **factuality** hallucination (inventing facts) and **faithfulness** hallucination (output unsupported by the *given* source). For an extraction engine, faithfulness is the dominant risk — and creel's "auditability over opaqueness" posture is the correct mitigation strategy. Concrete, reusable techniques:

- **Span grounding / provenance**: require the extractor to return the *source span* (offset or quoted text) that justifies each node/edge/attribute. SPIRES, GraphRAG (source-doc IDs per claim), and recent "auditable hallucination detection" work all attach provenance per fact [3][11][16]. This is non-negotiable for creel — every element must be traceable to source.
- **Verification as a separate strategy**: creel already models a `verify` step per element. Implement it as: (i) re-read the cited span and confirm it entails the extracted value (NLI/LLM-judge), and (ii) for grounded entities, confirm the ID exists in the target namespace. FaithLens-style detect-and-explain can be the verifier's backbone [16].
- **Constrained label sets**: in RE with a fixed relation/enum vocabulary, hallucination shows up as *invented relations outside the label set* — constrained decoding eliminates this class entirely [13][15].
- **Closed-book refusal handling**: when grounding fails or the source is silent, the extractor should emit a typed "absent/uncertain" rather than confabulate; Anthropic's `stop_reason: "refusal"` and explicit nullable fields support this [13].

---

## Prompt / skill design for extraction instructions

Patterns that recur across GraphRAG's tunable prompt, SPIRES templates, and LangChain's transformer [9][11]:

1. **Four-part extraction prompt** (GraphRAG): instructions → typed few-shot examples → source placeholder → gleaning continuation [11].
2. **Domain-tuned few-shot beats generic** — auto-generate examples for the actual domain; generic examples (person/org/geo) actively mislead in specialized domains [11].
3. **One concept per prompt** when types are complex (SPIRES field decomposition) — smaller, well-scoped prompts parse more reliably than one giant object request [3].
4. **Declarative attribute descriptions** travel *with* the schema (LinkML `description`/`comments`, JSON-Schema `description`) so the natural-language extraction instruction is a *property of the graph definition*, not a separate artifact — this is the key to creel's "schema-as-extractor" default.

---

## Design implications for creel

1. **Compile the graph-definition layer to JSON Schema and run extraction as constrained decoding — make NL-description the *default* but never the *only* enforcement.** Each node-type/edge-type in `graph_spec` should mechanically derive a JSON Schema (Pydantic model). The default extractor reads the schema's `description` fields as the LLM instruction (progressive disclosure: schema *is* the extractor), and Claude Structured Outputs (`output_config.format`, grammar-compiled, GA on Opus/Sonnet/Haiku 4.5+) guarantees the output shape [13]. This is the single highest-leverage decision.

2. **Enforce creel's "constrained" attributes (ranges, `multipleOf`, length) in a post-decode Pydantic/Instructor validation layer — do not trust the grammar for them.** Grammars and Anthropic Structured Outputs enforce types/enums/formats/required but explicitly *not* numeric ranges or string lengths [13][14]. Since funding amounts and indicator values (range-constrained, living *on edges*) are central to the UNHCR use case, range validation must be a first-class, separately-pluggable verification strategy with auto-retry on violation.

3. **Adopt SPIRES-style field decomposition + separated entity/relation passes for deep taxonomies.** Creel's recursively-subdivided node/edge taxonomies map directly onto SPIRES recursion over inlined class ranges [3]. Extract entities (nodes) first, resolve/ground them, then extract edges conditioned on the resolved node set — this measurably beats joint extraction [2][7] and makes edge attributes (the funding amount *on* the `donor→objective` edge) a clean second pass.

4. **Make edges first-class with their own typed-attribute schemas — most tools fumble this; treat it as a differentiator.** LangChain forces all properties to `string` and global-not-per-type [9]; GraphRAG and SPIRES carry richer edge data. Creel's physical separation of "graph definition" from "extraction metadata" lets each edge-type own a full typed-attribute schema *and* its own extractor strategy. Lean into it.

5. **Route by source type before choosing a strategy; prefer query/pattern over LLM whenever structure allows.** For tables → SQL-like query extractor (LLM authors the column→attribute mapping, doesn't transcribe values); for JSON → Mongo-like projection; for prose → LLM extractor. This hybrid routing (ODKE+, GraphRAG) is cheaper, faster, and inherently more auditable [6][11]. The source's own schema should be a *recognized extractor strategy*, not a special case.

6. **Bake grounding + provenance into the data model, not the prompt.** Every extracted element carries (a) a canonical node/edge ID from a resolver strategy (lookup table / embedding index / OAKlib-style annotator) and (b) a source span. The LLM proposes; a deterministic resolver disposes [3]. Consolidation/dedup across chunks and documents then becomes a graph join on stable IDs (Jaccard → embedding → LLM-adjudication cascade) [2].

## Recommendation

**Build creel's extraction core as a two-layer engine: a *schema-compilation* layer that turns each `graph_spec` node/edge type into a JSON-Schema/Pydantic model, and a *strategy-dispatch* layer that, per element, picks one of {grammar-constrained LLM extraction, query, pattern/function} and then runs a uniform *verification* pass (grounding to a canonical ID + source-span entailment check + Pydantic range/constraint validation with retry).** Default the LLM strategy to **Anthropic Claude Structured Outputs** for guaranteed-shape decoding, but treat the grammar as enforcing only *shape* — push every value-level constraint (ranges, cross-field rules) and every faithfulness check into the verification pass.

Rationale: this composition is exactly where the 2024–2026 state of the art has converged, and it satisfies all four of creel's stated postures simultaneously — *single source of truth* (the schema drives both extraction and validation), *strategy pattern* (per-element extractor + verifier are pluggable), *physical separation* (the schema layer is independent of, and joined on demand with, the extraction/verification-metadata layer), and *auditability* (grounding IDs + source spans + a deterministic verifier make every element traceable and checkable). SPIRES/OntoGPT is the closest existing blueprint to copy structurally; GraphRAG supplies the long-document gleaning/auto-tuning patterns; Anthropic Structured Outputs supplies the production enforcement substrate. Do **not** rely on the model's free-form JSON, and do **not** assume the grammar validates numeric ranges — those two mistakes are the recurring failure modes the literature warns against.

---

## References

1. Bian H, et al. [LLM-empowered Knowledge Graph Construction: A Survey](https://arxiv.org/abs/2510.20345). arXiv:2510.20345, Oct 2025. *(Also [7].)*
2. Lairgi Y, Moncla L, et al. [iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models](https://github.com/AuvaLab/itext2kg) (GitHub + Springer WISE 2024); successor [ATOM: Adaptive and Optimized dynamic Temporal KG construction](https://arxiv.org/pdf/2510.22590), arXiv:2510.22590.
3. Caufield JH, et al. [SPIRES: Structured Prompt Interrogation and Recursive Extraction of Semantics — a method for populating knowledge bases using zero-shot learning](https://academic.oup.com/bioinformatics/article/40/3/btae104/7612230). *Bioinformatics* 40(3), 2024. [arXiv:2304.02711](https://arxiv.org/abs/2304.02711).
4. Liu Y, et al. [OneKE: A Dockerized Schema-Guided LLM Agent-based Knowledge Extraction System](https://arxiv.org/pdf/2412.20005). arXiv:2412.20005, Dec 2024.
5. Monarch Initiative. [OntoGPT — LLM-based ontological extraction tools, including SPIRES](https://github.com/monarch-initiative/ontogpt). GitHub.
6. Apple Machine Learning Research. [ODKE+: Ontology-Guided Open-Domain Knowledge Extraction with LLMs](https://machinelearning.apple.com/research/odke). 2025.
7. Bian H. [LLM-empowered knowledge graph construction: A survey](https://arxiv.org/pdf/2510.20345) (schema-based vs schema-free; ontology engineering / extraction / fusion). arXiv:2510.20345, 2025.
8. Huguet Cabot P-L, Navigli R. [REBEL: Relation Extraction By End-to-end Language generation](https://aclanthology.org/2021.findings-emnlp.204/). Findings of EMNLP 2021. [Model card](https://huggingface.co/Babelscape/rebel-large).
9. Bratanic T. [Building Knowledge Graphs with LLM Graph Transformer](https://medium.com/data-science/building-knowledge-graphs-with-llm-graph-transformer-a91045c49b59) (LangChain `LLMGraphTransformer`: tool vs prompt mode, `allowed_nodes`, typed `(src,REL,tgt)` tuples, string-only global properties, `strict_mode`). *Towards Data Science*, 2024.
10. LlamaIndex. [Using a Property Graph Index](https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/) (pluggable `kg_extractors`, per-chunk extraction). Official docs.
11. Microsoft Research. [GraphRAG documentation](https://microsoft.github.io/graphrag/) and [GraphRAG auto-tuning](https://www.microsoft.com/en-us/research/blog/graphrag-auto-tuning-provides-rapid-adaptation-to-new-domains/) (entity/relation extraction, gleaning, four-part prompt, auto-tuned few-shot).
12. Edge D, et al. (Microsoft). [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://microsoft.github.io/graphrag/index/methods/) (community summaries, map-reduce over the graph).
13. Anthropic. [Structured outputs — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) (GA on Opus/Sonnet/Haiku 4.5+; `output_config.format` + strict tool use; grammar compilation & 24h cache; supported JSON-Schema subset and *explicit non-support* for numeric range / string-length constraints). Plus [Introducing advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use), Nov 2025.
14. 567-labs. [Instructor — structured outputs for LLMs](https://python.useinstructor.com/) ([GitHub](https://github.com/567-labs/instructor)); Pydantic-validated extraction with auto-retry; provider-agnostic. See also [Outlines (FSM token-masking)](https://github.com/dottxt-ai/outlines) and XGrammar (default constrained-decoding backend in vLLM/SGLang/TensorRT-LLM).
15. [Large Language Models Hallucination: A Comprehensive Survey](https://arxiv.org/html/2510.06265v2) (factuality vs faithfulness taxonomy). arXiv:2510.06265, 2025.
16. [FaithLens: Detecting and Explaining Faithfulness Hallucination](https://arxiv.org/pdf/2512.20182), arXiv:2512.20182, 2025; and [HalluGraph: Auditable Hallucination Detection for Legal RAG](https://arxiv.org/pdf/2512.01659), arXiv:2512.01659, 2025.
