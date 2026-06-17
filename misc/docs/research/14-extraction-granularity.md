# Extraction Granularity & Decomposition for LLM-Based Typed-Graph Extraction: A Best-Practices Report

**Author: Thor Whalen** · June 2026

> **How to use this document:** This is authored as a downloadable Markdown (`.md`) file. Save the content below as `extraction-granularity-decomposition.md`. It uses progressive disclosure — the TL;DR and decision procedure are up front; deeper sections follow. References are Vancouver-style, numbered inline with a REFERENCES section at the end.

---

## TL;DR

- **The central decision — how many LLM passes to split extraction into — is a separation-of-concerns problem, and the right default for a non-trivial typed graph is a *hybrid*: group co-dependent attributes and tightly-coupled node+edge types into a single pass, but split weakly-coupled classes into their own passes (class-by-class), because focused prompts beat one giant schema once the schema is large or the document is long.** Empirically, narrow prompts dodge the "lost-in-the-middle" degradation (Liu et al. show a U-shaped positional accuracy curve; a secondary analysis quantifies "a 30%+ accuracy drop on multi-document question answering when the answer document moved from position 1 to position 10 in a 20-document context" [1]) and structured-output accuracy falls as schema depth/field-count rises [16][17].
- **Prompt caching has fundamentally changed the cost arithmetic that used to penalize many-pass extraction.** When you re-send the same document across N class-by-class passes, the document tokens are a cacheable prefix: Anthropic charges ~10% of input rate on cache hits (90% off), OpenAI's automatic prefix caching gives 50% off (raised to as much as 90% on newer models), and Gemini implicit caching gives ~75% off — and Batch APIs stack another 50% off [9][10][11]. The naive "N passes = N× document cost" model is wrong; with caching it is closer to "1× document + N× tiny deltas."
- **Single-shot structured output is the right default for cost/latency; add agentic loops (validate-retry, self-verify, reflect) only where the marginal accuracy is worth the multiplied cost.** Pydantic validation-retry (Instructor) is cheap insurance and almost always worth it; self-consistency and Reflexion-style loops give real gains (Reflexion "achieves a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%" [14]) but multiply token spend and latency, so reserve them for high-value or low-confidence fields.

---

## Key Findings

1. **Terminology matters and maps cleanly onto software design.** The NLP "joint vs pipelined" debate over entity+relation extraction is the same axis as "single-pass/holistic vs multi-pass/decomposed" prompting. Pipelining buys separation of concerns and focus at the cost of error propagation and broken cross-pass coreference; joint extraction preserves interdependence at the cost of context-budget and prompt complexity [5][6][7].
2. **Focused prompts are more accurate on long inputs.** "Lost in the middle" (Liu et al., TACL 2024) is the load-bearing empirical result: a U-shaped positional accuracy curve that justifies chunking and narrow extraction scopes [1]. GraphRAG's own measurements show that "in the HotPotQA dataset, a 600-token chunk extracted nearly twice as many entity references as a 2400-token chunk" (generic entity-extraction prompt, GPT-4-turbo) [4].
3. **Decomposition is a published, named technique with measured gains.** Decomposed Prompting / DecomP [2], Least-to-Most [3], chain-of-thought, and self-consistency [12] all formalize "split the hard task into smaller sub-tasks." Least-to-most "solves the SCAN benchmark… with an accuracy of 99.7% using 14 examples versus an accuracy of 16.2% by chain-of-thought prompting" (GPT-3 code-davinci-002) [3].
4. **Caching + batch inverts the cost case against multi-pass.** See the quantitative worked example in §2.4.
5. **Production tools have converged on decomposition patterns:** LangExtract (chunk + parallel + multi-pass for recall, with character-offset source grounding) [8][18]; GraphRAG (extract → gleanings → dedup → community summarize) [4]; SPIRES/OntoGPT (recursive, class-by-class, ontology-grounded) [13][19]; LangChain LLMGraphTransformer (schema-constrained `allowed_nodes`/`allowed_relationships`) [20]; Instructor (Pydantic validate-retry) [15].
6. **Multi-chunk consolidation is a first-class problem, not an afterthought.** Merging requires blocking → matching → merging (entity resolution), and conflict resolution across chunks; LLMs now do semantic ER but it adds passes [21][22].

---

## Details

### 1. Canonical taxonomy & terminology

This design axis governs **how extraction work is divided into LLM passes** when populating a typed graph (nodes, edges, attributes) defined by a schema. For a Python architect, it is exactly the *decomposition / separation-of-concerns* question applied to prompts: how many "responsibilities" does one LLM call own?

**Single-pass / holistic extraction.** One prompt carries the full schema and asks the model to emit the entire typed graph (all node types, edge types, attributes) for a given text in one structured response. Maximally context-efficient (the document is sent once) and preserves all interdependencies, but stresses instruction-following and is vulnerable to long-context degradation and schema-size effects. LangChain's `LLMGraphTransformer` in its basic form is holistic: one call returns nodes + relationships [20].

**Multi-pass / decomposed extraction.** The schema (or the document) is split, and multiple LLM calls each handle a sub-task. Three sub-flavors:
- **Class-by-class extraction** — one ontology/schema class per pass. This is the SPIRES/OntoGPT pattern: extract one class at a time, recursing into nested classes [13].
- **Schema/attribute grouping** — bundle attributes that share context or require joint reasoning into one pass, split the rest.
- **Stage pipelines** — e.g., extract entities in pass 1, then relations in pass 2 (the classic NLP pipeline), or extract → ground → verify.

**Joint vs pipelined entity-relation extraction.** The classical NLP framing. *Pipelined* approaches run NER first, then relation classification over entity pairs; they "suffer from error propagation, where relation classification can be affected by errors introduced during entity recognition" [5][6]. *Joint* (non-pipeline) approaches model entities and relations together, reducing error propagation and exploiting interdependence; controlled studies find "the best joint approach still outperforms the best pipeline model, but improperly designed joint approaches may have poor performance" [7]. In the LLM era this maps directly: a holistic prompt is "joint"; a stage pipeline is "pipelined." The trade-offs carry over almost verbatim — joint preserves the entity↔relation coupling; pipelined gives focus and debuggability but propagates upstream errors and can break coreference across passes.

**Decomposed Prompting (DecomP) and relatives.** DecomP (Khot et al., 2022) decomposes a complex task "into simpler sub-tasks that can be delegated to a library of prompting-based LLMs," explicitly drawing the software analogy: "the decomposer defines the top-level program… using interfaces to simpler, sub-task functions" [2]. Least-to-Most prompting (Zhou et al., 2022) separates a decomposition phase from a sequential solve phase and demonstrated dramatic compositional-generalization gains (SCAN 16.2% → 99.7%) [3]. Chain-of-thought and self-consistency [12] round out the "decompose the reasoning" family. For graph extraction, the actionable idea is: treat each class/edge-type extractor as a *function* with its own optimized prompt, composed by an orchestrator.

### 2. The empirical trade-offs

#### 2.1 Accuracy: focused prompts vs long-context degradation

The foundational result is **"Lost in the Middle"** (Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni, Liang; *Transactions of the ACL*, vol. 12, pp. 157–173, 2024; DOI 10.1162/tacl_a_00638; arXiv 2307.03172) [1]. Across multi-document QA and key-value retrieval, performance is highest when relevant information is at the beginning or end of the context and degrades significantly in the middle — a U-shaped curve that holds "even for explicitly long-context models." A secondary analysis (Morph, "Lost in the Middle LLM") quantifies the magnitude: "Liu et al. (2024) measured a 30%+ accuracy drop on multi-document question answering when the answer document moved from position 1 to position 10 in a 20-document context" [1]. Follow-on 2024–2025 work attributes the effect to attention/positional biases and continues to reproduce it.

**Implication for extraction:** a giant holistic prompt over a long document buries mid-document entities/attributes in the low-attention zone, hurting recall. Narrowing the input (chunking) and the task (class-by-class) keeps the relevant evidence near the edges of a shorter context. GraphRAG empirically confirms the input-length effect: with a single extraction round on the HotPotQA dataset, a 600-token chunk extracted nearly **twice as many** entity references as a 2400-token chunk (GPT-4-turbo, generic extraction prompt) [4]. Separately, structured-output accuracy degrades as **schema complexity** rises: benchmarks bucket schemas as trivial (<10 fields) through ultra (>500 fields), and field-match accuracy "consistently degrade[s]" with schema depth, with small models dropping ~40% at depth >6 [16][17]. Smaller models also exhibit "attention decay" across schema fields — accuracy on the first quartile of fields can be ~2× that on the last quartile [17]. This is a direct argument for splitting large schemas.

#### 2.2 Cross-field & cross-entity consistency and coreference

Decomposition's main hazard is **breaking coreference and entity linking.** If "Dr. Smith," "she," and "the author" are resolved in one pass but the affiliation edge is extracted in another pass over a different chunk, the two passes may mint inconsistent or duplicate entities. Mitigations: (a) keep co-referential, co-dependent attributes in the *same* pass (see §3); (b) carry a canonical-entity context (a running list of already-resolved entities/IDs) into later passes; (c) ground to stable identifiers early (SPIRES grounds to ontology IDs, which makes cross-pass identity unambiguous) [13]; and (d) run an explicit entity-resolution stage after extraction (§5). The STAGE pipeline formalizes a "normalization-before-merge" rule precisely because raw chunk-level mentions "exhibit surface variation, ambiguous scope, or inconsistent typing" [22].

#### 2.3 Cost & latency of many-pass extraction

Naively, N passes over a D-token document cost N×D input tokens, and sequential passes add N× latency. Two levers defeat both: **parallelism** (independent class/chunk passes run concurrently — LangExtract uses a `ThreadPoolExecutor` with up to 10 `max_workers` in parallel [8]) and **caching** (below). Latency for *independent* passes is therefore ~max, not sum; cost is dominated by the (cacheable) document, not the (small) per-class schema deltas.

#### 2.4 How prompt caching & batch APIs rewrite the cost model

This is the single most important cost insight for class-by-class extraction. When the same document is re-sent as the prefix of many prompts, that prefix is cached:

- **Anthropic prompt caching:** cache reads cost ~10% of base input (a 90% discount); cache writes cost a 25% premium (1.25×) for the 5-minute TTL or 2.0× for the 1-hour TTL; minimum 1,024 tokens (2,048 for Haiku). Break-even is the second hit [9][11].
- **OpenAI automatic prefix caching:** automatic, zero-config for prompts ≥1,024 tokens, originally a 50% discount and raised to as much as 90% on newer models; static content must be the identical prefix [10].
- **Gemini context/implicit caching:** implicit caching on Gemini 2.5 charges cached tokens at ~0.25× (a 75% discount); explicit caching adds a time-based storage fee [10][11].
- **Batch APIs:** Anthropic, OpenAI, and others run async at exactly 50% off, and this stacks with caching [9][11].

**Worked example (illustrative arithmetic, not a quote).** Suppose a 50,000-token document and a schema split into 10 class-by-class passes, each adding ~500 tokens of class-specific instructions and producing ~500 output tokens, on a Sonnet-class model at ~$3/M input.
- *Naive model:* 10 × 50,000 = 500,000 input tokens ≈ **$1.50** input, paid every run.
- *With prefix caching:* first pass writes the 50K prefix once (≈1.25 × 50,000 = 62,500 token-equivalents), and the next 9 passes read it at 0.10× (9 × 50,000 × 0.10 = 45,000 token-equivalents), plus 10 × 500 uncached delta tokens. Total ≈ 62,500 + 45,000 + 5,000 ≈ 112,500 token-equivalents ≈ **$0.34** — roughly a **77% reduction**, consistent with the ~78.5% net saving reported for a 10× reused prefix [11].
- *Add Batch (50%):* ≈ **$0.17**.

The takeaway: **class-by-class / multi-pass extraction is far cheaper than naive cost models suggest**, because the document is the cacheable prefix and the per-pass schema is the only "fresh" cost. This neutralizes the historical cost objection to SPIRES-style recursion (which "targets one object at a time… at the cost of increased LLM consumption" [19]). Caveat: caches have short TTLs (Anthropic 5 min default; OpenAI 5–10 min), so passes must be fired in a burst, and the cached prefix must be byte-identical (put the document first, vary only the trailing class instruction).

### 3. Heuristics: when to GROUP vs SPLIT (the hybrid middle ground)

**Group into one pass when:**
- Attributes are **co-dependent / jointly reasoned** — e.g., a relation and its two endpoint roles, or `start_date`/`end_date`/`duration` where one constrains the others. Joint extraction avoids the error-propagation of splitting them [5][6].
- Fields share **coreference** — anything that depends on resolving the same mention (entity + its attributes + its local relations) belongs together.
- The combined schema is **small** (rule of thumb: well under ~30–50 fields / shallow nesting) and the chunk is short enough to keep evidence out of the lost-in-the-middle zone.

**Split into separate passes when:**
- The schema is **large or deeply nested** (field-match accuracy degrades with depth/count [16][17]) — split by class.
- Classes are **weakly coupled** (e.g., "Document metadata" vs "clinical findings") — independent passes, run in parallel.
- A sub-task needs a **different prompt style, different model, or different few-shot examples** (DecomP's modularity argument [2]) — e.g., route cheap high-volume classes to Haiku/Flash and hard reasoning classes to a frontier model.
- **Context budget** forces it: the document alone is long enough that adding a big schema pushes you into degradation.

**The hybrid default:** *one pass per cohesive class-cluster.* Cluster the schema into groups of tightly-coupled node+edge+attribute types; extract each cluster in its own (cacheable, parallel) pass; carry resolved canonical entities forward; then run a consolidation/ER pass. This is "single-responsibility per extractor, composed by an orchestrator."

### 4. Single-shot structured output vs agentic extraction loops

**Single-shot structured output** (one call, schema-constrained decoding / function-calling, validated against a Pydantic or JSON-Schema model) is the **right default**: lowest cost and latency, and modern providers enforce schema-valid syntax via constrained decoding. But "structured output is not reliable output" — schema-valid does not mean factually correct; type-correct hallucinations slip through [16].

**Agentic loops** add cost for accuracy:
- **Validation-and-retry (Instructor):** wraps the LLM client, validates the response against a Pydantic model, and on `ValidationError` re-asks the model with the error message appended (retries via Tenacity, `max_retries`) [15]. This is *cheap insurance* — it mostly fixes format/constraint violations in 0–2 extra calls and should almost always be on.
- **Self-consistency:** sample K reasoning paths, majority-vote the answer. Wang et al. report that self-consistency boosts chain-of-thought by large absolute margins — **GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2%, StrategyQA +6.4%, ARC-challenge +3.9%** (PaLM-540B/GPT-3) [12] — but it costs K× and only helps where there's a discrete answer to vote on. LangExtract's multi-pass recall strategy is a close cousin: run extraction several times and merge, relying on stochasticity to surface missed entities [8].
- **Self-verification:** the model checks its own answer (forward-reasoning then backward-verification); Weng et al. report consistent accuracy gains on arithmetic, commonsense, and logical reasoning tasks [12].
- **Reflexion / self-refine (propose → critique → revise):** Reflexion "achieves a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%" and adds ~20 points on HotPotQA vs ReAct [14]; Self-Refine outputs "improv[e] by ~20% absolute on average in task performance" across seven tasks (GPT-3.5/ChatGPT/GPT-4) [14]. But counter-evidence shows much of Reflexion's gain comes from *across-episode* learning, not within a single self-correction, and the compute footprint is heavy [14].

**When each pays off:** Use validate-retry always. Add self-consistency / verification on **high-value, low-confidence, or safety-critical fields** (e.g., a dosage, a monetary amount, a controlling-ownership edge), where a wrong value is expensive. Avoid full reflection loops for high-volume, low-stakes bulk extraction — the cost multiplier rarely clears the bar, and prompt-level fixes or better few-shot examples often beat runtime self-correction.

### 5. Long-document strategies

- **Chunking & sliding windows:** split into overlapping segments (overlap preserves cross-boundary mentions). LangExtract's `max_char_buffer` controls chunk size with an optional `context_window_chars`; smaller chunks raise recall but cost more calls [8][18]. Propositional/semantic chunking (atomic facts) outperforms naive fixed-size for extraction [supporting work].
- **Map-reduce extraction:** *map* = extract per chunk in parallel; *reduce* = merge/consolidate. GraphRAG and long-doc summarization both use this; the Refine strategy (sequential accumulation) is more accurate than Map-Reduce but slower, so Map-Reduce wins when throughput matters [4][23].
- **Retrieval-augmented extraction (RAG for extraction):** retrieve only chunks relevant to a given class/field before extracting, reducing context and dodging lost-in-the-middle. Useful when the schema targets sparse information in a huge document.
- **Multi-chunk / multi-document consolidation & deduplication (the hard part):** entities/relations extracted from different chunks must be merged. The canonical pipeline is **blocking → matching → merging**: a cheap blocking function groups candidate-duplicate nodes (to avoid n² comparisons), a matching function (rules → embeddings → LLM) decides equality with a confidence score, `SAME_AS` edges form connected components, and each component is merged into one canonical node (fields become deduplicated lists) [21]. **Conflict resolution** across chunks: prefer grounded IDs, use voting/most-frequent value, or LLM adjudication; STAGE normalizes mentions *before* merging and has an LLM adjudicate each merge cluster on "narrative identity, role consistency," explicitly avoiding category-level over-merges [22]. GraphRAG matches entities primarily by name today, a known weakness that better disambiguation improves [4].

### 6. Concrete patterns from production tools (2024–2026)

**Google LangExtract** [8][18]. Gemini-powered open-source library. Granularity choices: (1) **chunking** (`max_char_buffer`) into overlapping segments; (2) **parallel passes** (`max_workers`, up to 10 chunks concurrently — improves speed at no extra token cost); (3) **multiple extraction passes** (`extraction_passes`, default 1) that re-run extraction independently and merge with a "first-pass-wins" rule for conflicts, raising recall by exploiting stochasticity; (4) **source grounding** — every extraction is mapped to exact character offsets in the source, and extractions that can't be located (`char_interval = None`) are filtered as likely hallucinations. *Lesson:* recall is a function of decomposition (chunk + multi-pass), and grounding is the cheap audit layer that makes decomposition trustworthy.

**Instructor** [15]. Pydantic-first structured outputs across 15+ providers. Granularity choice: it deliberately does *one thing* — schema-constrained extraction with **validation-and-retry** (Pydantic validators + Tenacity, `max_retries`, `response_model`). *Lesson:* the validate-retry loop is the minimum viable "agentic" pattern and belongs in every extraction pipeline; keep the schema as the contract and let validation drive correction.

**SPIRES / OntoGPT** [13][19]. The archetypal **recursive, class-by-class** extractor (Caufield et al., *Bioinformatics* 2024). `SPIRES(S, C, T)` generates a per-attribute pseudo-YAML prompt for class `C`, completes it, then **recurses**: per the paper's parsing rules, "If the range is a primitive data type… then the value is returned as-is"; if the range is a non-inlined class or enumeration the value is **grounded**; and "if the range of the attribute is an inlined class, then SPIRES is called recursively: SPIRES(S, Range(a), v)" — e.g., parsing "2 tablespoons" via a recursive call on the `Quantity` class [13]. Grounding is decisive: on 100 random GO terms, "SPIRES returned the correct identifiers for 98 when using GPT-3.5-turbo and 97 with GPT-4-turbo. Without SPIRES, GPT-3.5-turbo returned just 3 correct identifiers" (the rest a "mass hallucination"); EMAPA was **100/100** with SPIRES, and MONDO **97/100** (GPT-3.5-turbo) [13]. *Lesson:* one class at a time + ground-to-IDs maximizes precision and makes cross-pass identity unambiguous; the cost of recursion is now mitigated by caching (§2.4).

**LangChain LLMGraphTransformer** [20]. Converts text to `GraphDocument` (nodes + relationships) using function-calling. Granularity choices are **schema constraints**: `allowed_nodes`, `allowed_relationships` (optionally as `(source_type, REL, target_type)` tuples for stricter typing), `node_properties`/`relationship_properties` to pull attributes, and `strict_mode` to drop anything off-schema. Default operation is **holistic** (one call → whole subgraph). *Lesson:* constraining the allowed types is the cheapest accuracy lever; for large ontologies, call it once per type-subset rather than with the full type list.

**Microsoft GraphRAG** [4]. Pipeline: chunk → **entity+relationship extraction** → **gleanings** → summarize → community detection (Leiden) → community summaries. **Gleanings** are the key decomposition idea: because "an LLM doesn't extract all the available information in a single extraction pass," GraphRAG runs *additional* extraction rounds on the same chunk to glean missed entities — multi-pass recall, configured by `max_gleanings` [4]. It quantifies the chunk-size trade-off (600-token chunks → ~2× entities vs 2400 on HotPotQA) and uses a cheaper model (e.g., gpt-4o-mini) to keep multi-pass cost down [4]. *Lesson:* gleanings = "ask again on the same text to boost recall," a complement to running more chunks; dedup/entity-resolution is a required downstream stage.

---

## Recommendations

**Stage 0 — Classify your problem.** Measure three inputs: **schema** (count node/edge types, attributes, nesting depth, and interdependence), **document size** (tokens vs model context, and where information density sits), and **budget** (cost ceiling, latency SLA, accuracy bar).

**Decision procedure (text flowchart):**

```
START
1. Is the document longer than ~half the model's comfortable context
   OR is information sparse across a long doc?
   ├─ YES → CHUNK (overlapping; semantic/proposition chunks if possible).
   │        Use RAG-for-extraction if the schema targets sparse facts.
   │        Plan a map-reduce + consolidation stage.
   └─ NO  → keep whole document as the (cacheable) prefix.

2. How big / interdependent is the schema?
   ├─ Small (<~30 fields, shallow, tightly coupled)
   │        → SINGLE-PASS / HOLISTIC (joint). One schema-constrained call.
   ├─ Medium, with separable concerns
   │        → HYBRID: cluster into cohesive class-groups; ONE PASS PER CLUSTER.
   └─ Large / deep / heterogeneous (>~50 fields or depth >3 or mixed domains)
            → CLASS-BY-CLASS (SPIRES-style), recurse into nested classes.

3. For every multi-pass choice, can passes run independently?
   ├─ YES → run in PARALLEL (ThreadPool / async); latency ≈ max, not sum.
   └─ NO (pass k needs pass k-1's entities) → pipeline sequentially,
            and CARRY canonical resolved entities/IDs forward.

4. Cost check for multi-pass:
   → Put the document FIRST (identical prefix) and enable PROMPT CACHING.
   → Fire passes in a burst within the cache TTL (~5 min).
   → If latency-tolerant, use the BATCH API (50% off, stacks with cache).
   With caching, prefer MORE, NARROWER passes over one giant prompt.

5. Accuracy hardening (per field, by value):
   → ALWAYS wrap in VALIDATION-RETRY (Pydantic + retry on error).
   → GROUND reference/enum fields to stable IDs as early as possible.
   → For HIGH-VALUE / LOW-CONFIDENCE fields only: add SELF-CONSISTENCY
     (k-sample + vote) or SELF-VERIFY; consider gleanings for recall.
   → Skip heavy REFLECTION loops for high-volume low-stakes bulk fields.

6. Consolidation (always, if you chunked or ran class-by-class):
   → ENTITY RESOLUTION: blocking → matching (rules→embeddings→LLM) → merge.
   → Normalize-before-merge; resolve conflicts by grounded ID / vote / LLM adjudication.
   → Validate final graph against the schema.
END
```

**Benchmarks/thresholds that change the plan:**
- If single-pass recall drops on long docs (measure entity recall vs a gold set) → chunk smaller and/or add gleanings/extra passes.
- If field-match accuracy falls on a large schema → split by class.
- If cache hit-rate is low (short prompts, spread-out calls) → consolidate passes or batch them; below the ~1,024-token cache minimum, caching won't fire.
- If validation-retry rate is high for a field → fix the prompt/few-shot or split that field into its own pass before reaching for self-consistency.

## Named-patterns reference list (cite by name)

- **Joint vs pipelined extraction** [5][6][7]
- **Single-pass / holistic vs multi-pass / decomposed extraction**
- **Class-by-class extraction** (SPIRES/OntoGPT) [13]
- **Decomposed Prompting (DecomP)** [2]; **Least-to-Most prompting** [3]; **chain-of-thought**; **self-consistency** [12]
- **Lost in the middle** (U-shaped positional degradation) [1]
- **Gleanings** (multi-round re-extraction for recall) [4]
- **Map-reduce extraction** [4][23]; **Refine strategy** [23]; **retrieval-augmented extraction**
- **Validation-retry loop** (Instructor / Pydantic) [15]
- **Self-verification**, **self-consistency**, **Reflexion / self-refine** [12][14]
- **Entity resolution** (blocking → matching → merging) / **semantic ER** / **normalize-before-merge** [21][22]
- **Source grounding** (character-offset alignment) [8][18]; **grounding-to-IDs** [13]
- **Schema-constrained extraction** (`allowed_nodes`/`allowed_relationships`, `strict_mode`) [20]
- **Prompt caching** (prefix caching) & **batch discounting** [9][10][11]

## Opinionated rules of thumb

1. **Default to hybrid class-cluster passes, not one giant prompt.** Single-responsibility per extractor.
2. **Put the document first; let caching pay for decomposition.** Many narrow passes ≈ one big pass in cost once cached.
3. **Ground early to stable IDs** — it fixes both precision and cross-pass identity.
4. **Validate-retry is non-negotiable; reflection is a luxury** — spend the agentic budget only where a wrong value is expensive.
5. **Recall is a decomposition knob** (smaller chunks, more passes, gleanings); **precision is a grounding + validation knob.**
6. **Always plan the consolidation/ER stage** the moment you chunk or split — duplicates are guaranteed, not hypothetical.
7. **Parallelize independent passes**; only serialize when a later pass truly needs an earlier pass's entities.

## Caveats

- Several quantitative claims rest on secondary or vendor sources. The LangExtract "12% higher recall" and "85–95% accuracy" figures circulating in write-ups come from blog/marketing material, not a peer-reviewed benchmark, and should be treated as indicative only. Provider caching/pricing numbers (Anthropic 90%, OpenAI 50→90%, Gemini 75%, batch 50%) are vendor-stated and change frequently — verify against current pricing pages before budgeting; the worked example in §2.4 is illustrative arithmetic, not a quote.
- "Lost in the middle" is robust and peer-reviewed [1], but some long-context benchmarks do not strongly reproduce it at all lengths, and newer frontier models mitigate it — treat it as a strong prior, not a law.
- Reflexion/self-refine gains are real but partly attributable to across-episode memory rather than single-shot self-correction [14]; don't assume a one-shot critique pass will replicate paper-level numbers.
- The SPIRES recursion "increased LLM consumption" cost-trade-off framing is from a secondary community description [19]; the peer-reviewed paper documents the recursive algorithm and the grounding numbers verbatim [13], but that explicit cost sentence is not in the version of record — do not attribute it to the journal article.
- Schema-complexity degradation results [16][17] are model-dependent (frontier models hold up far better than sub-4B models); calibrate thresholds to your actual model.

## REFERENCES

1. Liu NF, Lin K, Hewitt J, Paranjape A, Bevilacqua M, Petroni F, Liang P. Lost in the Middle: How Language Models Use Long Contexts. *Transactions of the Association for Computational Linguistics*. 2024;12:157–173. [aclanthology.org/2024.tacl-1.9](https://aclanthology.org/2024.tacl-1.9/) · secondary magnitude analysis: [morphllm.com/lost-in-the-middle-llm](https://www.morphllm.com/lost-in-the-middle-llm)
2. Khot T, Trivedi H, Finlayson M, Fu Y, Richardson K, Clark P, Sabharwal A. Decomposed Prompting: A Modular Approach for Solving Complex Tasks. arXiv:2210.02406. 2022. [arxiv.org/abs/2210.02406](https://arxiv.org/abs/2210.02406)
3. Zhou D, Schärli N, Hou L, Wei J, Scales N, Wang X, et al. Least-to-Most Prompting Enables Complex Reasoning in Large Language Models. arXiv:2205.10625. 2022. [arxiv.org/abs/2205.10625](https://arxiv.org/abs/2205.10625)
4. Edge D, et al. / Microsoft. From Local to Global: A Graph RAG Approach to Query-Focused Summarization; GraphRAG documentation, gleanings and chunk-size measurements (HotPotQA). [neo4j.com/blog/developer/microsoft-graphrag-neo4j](https://neo4j.com/blog/developer/microsoft-graphrag-neo4j/) · [microsoft.com/.../graphrag-auto-tuning](https://www.microsoft.com/en-us/research/blog/graphrag-auto-tuning-provides-rapid-adaptation-to-new-domains/)
5. Zhao X, et al. A Comprehensive Survey on Relation Extraction: Recent Advances and New Frontiers. arXiv:2306.02051. [arxiv.org/html/2306.02051v3](https://arxiv.org/html/2306.02051v3)
6. (Same survey, ACM Computing Surveys version.) [dl.acm.org/doi/full/10.1145/3674501](https://dl.acm.org/doi/full/10.1145/3674501)
7. Yan Z, Jia Z, Tu K. An Empirical Study of Pipeline vs. Joint approaches to Entity and Relation Extraction. AACL-IJCNLP 2022. [aclanthology.org/2022.aacl-short.55](https://aclanthology.org/2022.aacl-short.55/)
8. google/langextract — long documents, chunking, multi-pass, parallel workers (DeepWiki & repo). [deepwiki.com/google/langextract/6.2-long-documents](https://deepwiki.com/google/langextract/6.2-long-documents) · [github.com/google/langextract](https://github.com/google/langextract)
9. Anthropic. Prompt caching — Claude API docs. [platform.claude.com/docs/en/build-with-claude/prompt-caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
10. OpenAI. Prompt caching — API guide. [developers.openai.com/api/docs/guides/prompt-caching](https://developers.openai.com/api/docs/guides/prompt-caching)
11. Prompt caching in 2026: cost comparison across Anthropic/OpenAI/Gemini, batch, break-even. [digitalapplied.com/blog/prompt-caching-2026-cut-llm-costs-engineering-guide](https://www.digitalapplied.com/blog/prompt-caching-2026-cut-llm-costs-engineering-guide)
12. Wang X, Wei J, Schuurmans D, Le Q, Chi E, Narang S, Chowdhery A, Zhou D. Self-Consistency Improves Chain of Thought Reasoning in Language Models. arXiv:2203.11171. 2022. And Weng Y, et al. Large Language Models are Better Reasoners with Self-Verification. EMNLP Findings 2023. [aclanthology.org/2023.findings-emnlp.167](https://aclanthology.org/2023.findings-emnlp.167.pdf)
13. Caufield JH, Hegde H, Emonet V, Harris NL, Joachimiak MP, Matentzoglu N, et al. Structured Prompt Interrogation and Recursive Extraction of Semantics (SPIRES): a method for populating knowledge bases using zero-shot learning. *Bioinformatics*. 2024;40(3):btae104. DOI 10.1093/bioinformatics/btae104. [academic.oup.com/bioinformatics/article/40/3/btae104/7612230](https://academic.oup.com/bioinformatics/article/40/3/btae104/7612230)
14. Shinn N, Cassano F, Gopinath A, Narasimhan K, Yao S. Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS 2023; arXiv:2303.11366. And Madaan A, et al. Self-Refine: Iterative Refinement with Self-Feedback. arXiv:2303.17651, NeurIPS 2023. [arxiv.org/pdf/2303.11366](https://arxiv.org/pdf/2303.11366)
15. Instructor — structured outputs for LLMs (Pydantic, validation, retries). [python.useinstructor.com](https://python.useinstructor.com/) · [github.com/567-labs/instructor](https://github.com/567-labs/instructor)
16. Geng S, et al. Generating Structured Outputs from Language Models: Benchmark and Studies (JSONSchemaBench). arXiv:2501.10868. [arxiv.org/html/2501.10868v1](https://arxiv.org/html/2501.10868v1)
17. SO-Bench: A Structural Output Evaluation of Multimodal LLMs. arXiv:2511.21750. (See also VAREX, arXiv:2603.15118, on schema-field attention decay.) [arxiv.org/pdf/2511.21750](https://arxiv.org/pdf/2511.21750)
18. Google Developers Blog. Introducing LangExtract: A Gemini powered information extraction library. [developers.googleblog.com/introducing-langextract](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/)
19. OntoGPT / SPIRES community description of the recursive-extraction cost trade-off. [apex974.com/articles/ontogpt-for-schema-based-knowledge-extraction](https://apex974.com/articles/ontogpt-for-schema-based-knowledge-extraction)
20. LangChain LLMGraphTransformer (`allowed_nodes`, `allowed_relationships`, `strict_mode`, node/relationship properties). [deepwiki.com/langchain-ai/langchain-experimental/2.1-llmgraphtransformer](https://deepwiki.com/langchain-ai/langchain-experimental/2.1-llmgraphtransformer)
21. Jurney R. The Rise of Semantic Entity Resolution (blocking, matching, merging; LLM-automated merge). Towards Data Science, 2026. [towardsdatascience.com/the-rise-of-semantic-entity-resolution](https://towardsdatascience.com/the-rise-of-semantic-entity-resolution/)
22. STAGE: A Benchmark for Knowledge Graph Construction, Question Answering, and In-Script Role-Playing over Movie Screenplays (normalize-before-merge, LLM adjudication). arXiv:2601.08510. [arxiv.org/pdf/2601.08510](https://arxiv.org/pdf/2601.08510)
23. Enabling and Analyzing How to Efficiently Extract Information from Hybrid Long Documents with LLMs (Map-Reduce vs Refine). arXiv:2305.16344. [arxiv.org/pdf/2305.16344](https://arxiv.org/pdf/2305.16344)