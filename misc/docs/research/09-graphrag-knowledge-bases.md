# 09 — GraphRAG & graph knowledge bases

> **TL;DR.** GraphRAG and graph knowledge bases are the natural downstream consumers of creel's extracted graph. The major systems — Microsoft GraphRAG, LlamaIndex `PropertyGraphIndex`, the Neo4j GraphRAG package, Graphiti (temporal), LightRAG, and HippoRAG — all converge on the same underlying need: a **labeled property graph** with **typed nodes and typed edges**, **stable canonical IDs**, **provenance back to source text**, and **embeddings-ready descriptive text** on every element. They diverge mostly in what they add on top (community detection + summaries in GraphRAG; bi-temporal edges in Graphiti; Personalized PageRank in HippoRAG; dual-level retrieval in LightRAG). Creel should therefore emit a canonical JSON graph that is *already* an LPG-shaped structure — stable IDs, edges-as-first-class with attributes, provenance spans, and an optional `text_for_embedding` field per element — plus thin, **optional adapters** (not core dependencies) that materialize that JSON into each target system. The single most important affordance: **stable, deterministic IDs + provenance on every node and edge**, because every downstream system either requires it or degrades badly without it, and it is the one thing creel can provide that the downstream cannot reconstruct cheaply.

## Background / landscape

"GraphRAG" is now an umbrella term for retrieval-augmented generation where the retrieval index is (at least partly) a graph rather than a flat vector store. The motivation is well-documented: vector RAG retrieves locally similar chunks but struggles with *multi-hop* reasoning and *global/sensemaking* questions ("what are the main themes across this corpus?"), because the answer is distributed across many chunks that are not individually similar to the query [1][6]. Graph structure lets retrieval *traverse* relationships and *summarize communities*, which is exactly what these queries need.

The field splits into two construction postures, and creel sits upstream of both:

1. **Build-the-graph-from-text systems** (Microsoft GraphRAG, LlamaIndex `PropertyGraphIndex`, LightRAG, HippoRAG, Graphiti). These run their *own* LLM extraction over raw documents to produce the graph. Creel competes with / replaces this extraction layer — its output can be injected to *skip* their extraction step.
2. **Bring-your-own-graph systems** (Neo4j GraphRAG package, any graph DB + retriever). These assume a graph already exists and provide retrieval patterns over it. Creel's output feeds these directly.

This distinction matters for creel's design: its highest-leverage role is as the **trusted, auditable extraction front-end** whose output can be *loaded into* any of these systems, bypassing their opaque, non-auditable LLM extraction. The UNHCR ESA use case (donors → objectives → projects → outputs → outcomes → indicators, with funding amounts and indicator values on edges) is precisely the kind of structured, attribute-rich graph that generic LLM extractors handle poorly but creel's typed grammar + strategy-based extractors handle well.

## Comparative analysis

| System | Graph model | Extraction approach | Distinctive retrieval | Incremental update | Temporal? | What it needs from an input graph |
|---|---|---|---|---|---|---|
| **MS GraphRAG** [1][7][8] | Entities, relationships, **communities** (Leiden, hierarchical), community reports, text units, optional claims/covariates | Multi-pass LLM extract → summarize → Leiden → community summaries | **Global** (map-reduce over community summaries) vs **Local** (entity neighborhood) vs **DRIFT** (hybrid) | Possible but costly: community re-detection is expensive [2][7] | Weak (community `period` field only) | Entities w/ descriptions, typed relations, text-unit provenance |
| **LlamaIndex PropertyGraphIndex** [3][14] | Labeled property graph: `EntityNode`/`ChunkNode` w/ labels + properties; typed relations w/ properties | Schema-guided OR free-form OR implicit | Composable retrievers: synonym, vector-context, **Text2Cypher**, custom (run concurrently) | Insert nodes/relations incrementally | Via property timestamps (manual) | Labeled nodes, typed relations, `MENTIONS`/`SOURCE` links, node embeddings |
| **Neo4j GraphRAG (py)** [9][10] | Native Neo4j LPG | BYO graph (or KG builder pipeline) | Vector, Vector-Cypher, Hybrid, **Hybrid-Cypher**, Text2Cypher | Native DB upserts | Via properties (manual) | Existing graph; vector index on `:Chunk`/entity embeddings |
| **Graphiti / Zep** [4][11][12] | **Bi-temporal** LPG; edges carry `t_valid`/`t_invalid` validity intervals + ingestion time | Continuous episode ingestion; resolve entities against existing nodes | Hybrid semantic + keyword + graph search | **Real-time incremental**; no full recompute | **Yes — bi-temporal** (valid time + ingestion time) | Entities, edges w/ timestamps, source episode refs |
| **LightRAG** [5][13] | Entity/relation graph + dual KV stores; entity & relation "keywords" | LLM extract; lightweight | **Dual-level** (low-level entity + high-level theme) retrieval | **Cheap incremental** — add nodes/edges, no community rebuild [5][13] | No (by default) | Entities, typed relations, descriptive text per element |
| **HippoRAG** [6] | Open KG (triples) + passage nodes; synonymy edges | OpenIE LLM extraction | **Personalized PageRank** over KG seeded by query entities | Add triples; PPR recomputed at query | No | Entities, relations, entity↔passage links, synonym edges |

A few cross-cutting observations, verified against multiple sources:

- **Cost of community detection is the major axis of disagreement.** GraphRAG's Leiden community detection + per-community LLM summaries are what make its *global* search work, but they make incremental updates expensive because adding documents can force community restructuring and re-summarization [2][5][7]. LightRAG was explicitly designed to avoid this — it keeps the entity/relation graph but drops global community summaries in favor of dual-level retrieval, so incremental updates "simply add new nodes and edges without rebuilding the entire index" [5][13]. This is a real, repeatedly-stated trade-off, not marketing.
- **Bi-temporal modeling is Graphiti's signature.** Each edge carries *two* timelines: when the fact was true in the world (valid time) and when it was ingested (transaction/ingestion time). Superseded facts are **invalidated, not deleted** (`t_invalid` set), preserving history and enabling point-in-time queries and auditable conflict resolution [4][11][12]. This is classic bi-temporal database theory applied to agent memory.
- **Provenance/auditability is under-served by the generic LLM-extraction systems.** Most build-from-text systems keep a link from entity → source text unit, but the extraction itself is opaque (one LLM pass, no per-claim verification). This is exactly the gap creel's "auditability over opaqueness" posture targets.

## Deep dive: what each system actually consumes

### Microsoft GraphRAG

GraphRAG's pipeline is: chunk text into *text units* → LLM extracts entities + relationships (and optionally *claims/covariates*) per unit → entity descriptions are summarized across units → a graph is built → **Leiden** community detection produces a *hierarchy* of communities (Level 0 fine-grained, higher levels coarser/cheaper) → an LLM writes a *community report* (summary) for each community [1][7][8]. Outputs are persisted as parquet tables (entities, relationships, communities, community_reports, text_units), each row carrying IDs and human-readable titles/descriptions [7].

Query modes: **Local search** seeds from query-relevant entities and expands to their neighborhood + the community reports they belong to; **Global search** runs map-reduce over community summaries to answer corpus-wide sensemaking questions; **DRIFT search** (Dynamic Reasoning and Inference with Flexible Traversal) is a hybrid — a "primer" phase pulls relevant community reports and generates follow-up questions, then a local-search "follow-up" phase refines, balancing global breadth with local specificity [14]. There is also a "dynamic community selection" refinement to global search [7].

**What creel can give it:** entities with rich `description` text (used verbatim in summaries and embeddings), typed relationships with descriptions, and text-unit provenance. If creel emits stable IDs and descriptions, GraphRAG's expensive *extraction + description-summarization* passes can be skipped, and only Leiden + summary generation remain.

### LlamaIndex PropertyGraphIndex

The cleanest *general* target. It models a labeled property graph where nodes (`EntityNode`, `ChunkNode`) carry labels + arbitrary properties and relations carry labels + properties — explicitly richer than subject-predicate-object triples [3]. Extraction can be **schema-guided** (LLM only emits types in your schema), **free-form**, or **implicit** (uses chunk PREVIOUS/NEXT/SOURCE links). Text chunks link to entities via `MENTIONS`/`SOURCE` relations. All nodes are embedded by default and it supports a vector store layered on the graph store for hybrid search. Retrievers (synonym, vector-context, Text2Cypher, custom) compose and run concurrently [3][14].

**What creel can give it:** essentially a 1:1 mapping. Creel's typed node/edge grammar *is* a schema; creel can emit `EntityNode`-shaped records with labels = node-types and properties = typed attributes, plus relations with edge-type labels and on-edge attributes (funding amounts, indicator values). The `MENTIONS`/`SOURCE` links come straight from creel's provenance.

### Neo4j GraphRAG package

A BYO-graph retrieval toolkit over native Neo4j. It offers Vector, Vector-Cypher, Hybrid (vector + full-text), Hybrid-Cypher (adds graph traversal), and Text2Cypher retrievers [9][10]. It expects an existing LPG with vector indexes on chunk/entity embeddings. Creel's output loads here via straightforward Cypher `MERGE` on stable IDs.

### Graphiti / Zep (temporal)

Purpose-built for *agent memory* with continuous, real-time ingestion. Its bi-temporal edges and "invalidate-don't-delete" conflict resolution make it the reference design for **versioned/temporal graph KBs** [4][11][12]. It resolves new entities against existing nodes on ingest and uses semantic + keyword + graph search to detect conflicts. For creel, Graphiti is relevant less as a direct target and more as the **model to imitate** if/when creel emits *change-sets* over time (the UNHCR strategic frame evolves across planning cycles — last year's funding amount on an edge should be superseded, not overwritten).

### LightRAG & HippoRAG

LightRAG keeps the graph but ditches expensive global community summarization, using **dual-level retrieval** (low-level specific entities + high-level themes via entity/relation "keywords") and cheap incremental updates [5][13]. HippoRAG models the corpus as an open KG and runs **Personalized PageRank** seeded by query entities to do single-shot multi-hop retrieval — reportedly up to ~20% better on multi-hop QA and far cheaper than iterative methods [6]. Both need the same inputs: typed entities, typed relations, descriptive text. HippoRAG additionally benefits from **synonym edges**, which is just entity resolution output.

### Knowledge-base construction & maintenance

Across the entity-resolution literature, the consistent recommendations are: create **canonical entity nodes with stable IDs**, link raw mentions to canonical nodes via `SAME_AS`/`MENTIONS` edges for provenance, and use **cascading matchers** (rules → ML → LLM) with *blocking* to keep comparisons sub-quadratic [15][17]. For maintenance, the temporal/versioned approaches (Graphiti, VersionRAG) favor **append + invalidate** over destructive update, so history and audit trails survive [4][11]. Conflict resolution is driven by temporal metadata: the newer valid-time fact supersedes, the older one is marked invalid but retained [4][12].

## Design implications for creel

1. **Emit a labeled-property-graph-shaped JSON, not bare triples.** Creel's grammar already has typed node-types, typed edge-types, and typed attributes on *both* nodes and edges — this maps exactly onto LlamaIndex `EntityNode`/relations-with-properties and Neo4j LPG. Do **not** flatten to subject-predicate-object; that would throw away on-edge attributes (funding amounts, indicator values) that are central to the UNHCR case and are the hardest thing for downstream systems to reconstruct.

2. **Stable, deterministic IDs are non-negotiable and belong in core.** Every node and edge must carry a stable ID that survives re-extraction and incremental runs. Without it, *every* downstream system (Graphiti's resolve-against-existing, GraphRAG/LightRAG incremental updates, Neo4j `MERGE`, HippoRAG synonym links) either breaks or duplicates. Derive IDs deterministically (e.g. hash of canonical-type + canonical-key attributes) so the same real-world entity gets the same ID across runs. This is the SSOT discipline applied to identity.

3. **Provenance spans are a core column, carried per element, not bolted on.** Each node/edge should reference the source(s) and span(s) it was extracted from, plus the extractor strategy that produced it. This directly powers (a) creel's own auditability posture and (b) downstream `MENTIONS`/`SOURCE`/text-unit links that GraphRAG and PropertyGraphIndex consume. It also lets the verification layer attach a confidence/verified flag per element — keep that in the *extraction/verification metadata layer* (physically separate per the creel design), joined to the graph on demand.

4. **Add an optional, derivable `text_for_embedding` field per element — RAG-readiness without coupling.** Every system embeds entities/relations using a short natural-language description. Creel already produces descriptions for LLM-strategy elements; expose an optional, lazily-computed `text_for_embedding` (default: synthesized from type + attributes + description) so the graph is embeddings-ready, but compute *no* embeddings in core (no vector-store dependency, progressive disclosure).

5. **Design the output as an append-friendly change-set, with optional temporal stamps on edges.** To flow into temporal KBs (Graphiti) and to support the UNHCR multi-cycle reality, make the canonical output expressible as additive change-sets and allow optional `valid_from`/`valid_to` (and ingestion timestamp) attributes on edges. Default is non-temporal (a plain snapshot); the temporal fields are an opt-in affordance. Crucially, prefer **invalidate-don't-delete** semantics in any update adapter so audit history survives — this matches both Graphiti and creel's auditability ethos.

6. **Ship downstream integration as thin, optional adapters — keep the core graph-DB-agnostic.** Per creel's strategy-pattern + DI posture, provide separate optional packages/modules (`creel.export.llamaindex`, `creel.export.neo4j`, `creel.export.graphrag_parquet`, etc.) that translate the canonical JSON into each target's load format. The core depends on none of them. This is the "downstream enabled, not implemented in core" principle made concrete, and it lets creel's auditable extraction *replace* the opaque LLM-extraction step inside GraphRAG/LightRAG/PropertyGraphIndex.

## Recommendation

**Make creel's canonical output a labeled-property-graph JSON whose single load-bearing invariant is: every node and every edge carries a stable deterministic ID plus provenance (source span + extractor strategy), with edges first-class and attribute-bearing.** Everything else downstream systems need — embeddings, community detection, PageRank, temporal validity, vector indexes — is either derivable from this shape or is the downstream system's own job. Stable-IDs-plus-provenance is the one property that (a) *every* surveyed system requires or strongly benefits from, (b) the downstream cannot cheaply reconstruct after the fact, and (c) aligns perfectly with creel's SSOT and auditability mandates.

Then add two *optional* RAG-readiness affordances that cost almost nothing and unlock everything: a derivable `text_for_embedding` per element (embeddings-ready, but compute none in core) and opt-in temporal stamps on edges with invalidate-don't-delete update semantics. Deliver all concrete system integrations (GraphRAG parquet, LlamaIndex `PropertyGraphIndex`, Neo4j Cypher, Graphiti episodes) as **thin optional adapters** so the core stays dependency-free and graph-store-agnostic. This positions creel not as yet another GraphRAG, but as the **trusted, auditable extraction front-end** that feeds all of them.

## References

[1] [From Local to Global: A GraphRAG Approach to Query-Focused Summarization (Microsoft Research, arXiv:2404.16130)](https://arxiv.org/pdf/2404.16130)

[2] [GraphRAG Implementation Guide: Entity Extraction, Query Routing & When It Beats Vector RAG (PremAI, 2026)](https://blog.premai.io/graphrag-implementation-guide-entity-extraction-query-routing-when-it-beats-vector-rag-2026/)

[3] [Introducing the Property Graph Index (LlamaIndex blog)](https://www.llamaindex.ai/blog/introducing-the-property-graph-index-a-powerful-new-way-to-build-knowledge-graphs-with-llms)

[4] [Graphiti: Knowledge Graph Memory for an Agentic World (Neo4j Developer Blog)](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)

[5] [LightRAG: Simple and Fast Retrieval-Augmented Generation (arXiv:2410.05779)](https://arxiv.org/html/2410.05779v1)

[6] [HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models (NeurIPS'24, arXiv:2405.14831)](https://arxiv.org/abs/2405.14831)

[7] [GraphRAG: Improving global search via dynamic community selection (Microsoft Research)](https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/)

[8] [Community detection — GraphRAG documentation](https://www.mintlify.com/microsoft/graphrag/concepts/community-detection)

[9] [GraphRAG Python package: Accelerating GenAI with knowledge graphs (Neo4j)](https://neo4j.com/blog/news/graphrag-python-package/)

[10] [User Guide: RAG — neo4j-graphrag-python documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)

[11] [Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956)](https://arxiv.org/abs/2501.13956)

[12] [What Is a Temporal Knowledge Graph? (Zep)](https://www.getzep.com/ai-agents/temporal-knowledge-graph/)

[13] [LightRAG: Graph-Enhanced Text Indexing and Dual-Level Retrieval (Prompt Engineering)](https://promptengineering.org/lightrag-graph-enhanced-text-indexing-and-dual-level-retrieval/)

[14] [DRIFT Search — GraphRAG documentation](https://microsoft.github.io/graphrag/query/drift_search/)

[15] [Entity Resolution at Scale: Deduplication Strategies for Knowledge Graph Construction (Medium, Jan 2026)](https://medium.com/@shereshevsky/entity-resolution-at-scale-deduplication-strategies-for-knowledge-graph-construction-7499a60a97c3)

[16] [HybridRAG and Why Combine Vector Embeddings with Knowledge Graphs for RAG (Memgraph)](https://memgraph.com/blog/why-hybridrag)

[17] [LLM-Powered Knowledge Graphs for Enterprise Intelligence and Analytics (arXiv:2503.07993)](https://arxiv.org/pdf/2503.07993)
