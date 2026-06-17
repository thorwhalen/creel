# 15 — Bidirectional Traceability, Source Grounding & Human Annotation/Coding

> **TL;DR.** creel already has the right *shape* for auditability — a separable per-element evidence sidecar (`graph.evidence`) carrying PROV-lite provenance, W3C Web-Annotation grounding selectors, and method-tagged confidence with a `review_status` enum (D8). The user's vision — *click a graph element, highlight the source passages that caused it (and back); manually "code" a passage onto a node/edge/category; and see whether each entry was machine-extracted, manually coded, or human-corrected* — does **not** require a redesign. It requires four targeted, low-cost extensions that the industry has already converged on: **(1)** push evidence granularity from per-element down to **per-attribute** by keying the sidecar on `(element_id, attribute_path)` using the existing `JsonPathSelector` vocabulary [13][20]; **(2)** make D15's standoff overlay a **first-class W3C Web-Annotation Body+Target record** that serves *both* machine output and human input, so "manual coding" is just an Annotation with a source-span Target, a node/category Body, and `attributed_to = HUMAN` [7][14][22]; **(3)** add a **derived, rebuildable reverse index** (source span → elements) as an interval-stabbing projection over the grounding selectors creel already stores [12][23]; **(4)** adopt the **Hypothes.is multi-selector redundancy + ordered re-anchoring** discipline (quote = system of record, position = disposable hint) so links survive re-ingestion/re-OCR [9][11][17]. The machine-vs-manual-vs-corrected distinction the user wants is **derivable, not a new field**: it falls out of PROV-O's agent kind (`SoftwareAgent` vs `Person`) plus `wasRevisionOf` for non-destructive correction [6]. **Do not build yet:** the front-end, RDF-star/PROV-O export, per-annotator adjudication/IAA, or REFI-QDA round-trip — reserve the contract for them. This report seeds **ADR D-OP9** and **EPIC 8** (the annotated-graph contract).

---

## Standoff annotation & anchor robustness (selectors; re-anchoring across re-ingestion)

**The W3C Web Annotation Data Model [7] is the settled foundation, and creel already implements a correct subset.** The model defines a "selector zoo" — `TextQuoteSelector(exact, prefix, suffix)`, `TextPositionSelector(start, end)` (0-based char offsets, start-inclusive/end-exclusive), `DataPositionSelector` (byte offsets), `CssSelector`/`XPathSelector` (structural, `value` = a path), `FragmentSelector` (`value` + `conformsTo`, e.g. media-fragments `#xywh=` for images, RFC 5147 `#char=` for text), `RangeSelector(startSelector/endSelector)`, and `SvgSelector` for non-rectangular regions. creel's `TextQuoteSelector`, `TextPositionSelector`, `CellSelector`, `JsonPathSelector`, `PageSelector`, and `BoundingBoxSelector` (with a `normalized` flag) cover the everyday cases. The real gaps versus the full model are **`RangeSelector`**, **structural `Css/XPath` selectors**, and — most importantly — the **`refinedBy` composition mechanism**.

**The single most important robustness primitive is "multiple selectors on one Target," plus `refinedBy` [7][8].** The spec is explicit: multiple selectors SHOULD select the same content at differing precision, so a consumer can fall back across them; `refinedBy` lets a coarse selector be narrowed by a finer one (e.g. a `CssSelector` *refinedBy* a `TextPositionSelector`, where the position is then relative to the parent element's text — far more stable than a global document offset). This composition is the recommended pattern and is the key piece creel is missing.

**Hypothes.is's production "fuzzy anchoring" [9] is the canonical re-anchoring strategy.** It stores **three** selectors per target and tries them fastest-then-most-robust: (1) `RangeSelector` (XPath + offset) — fast if structure is intact; (2) `TextPositionSelector` — works if structure changed but content is stable; (3) context-first fuzzy quote match (locate prefix near the expected position, then suffix, then verify exact); (4) selector-only fuzzy match on the exact text as a last resort. Each failure degrades gracefully into a fuzzier strategy rather than losing the anchor. Fuzzy matching uses google-diff-match-patch (Bitap approximate search) with ~32 characters of prefix/suffix captured on each side [9].

**The precision/robustness tradeoff is settled in the literature.** `TextPositionSelector` is a fast *hint* but brittle: any upstream insertion/deletion shifts every later offset, and re-parsing or re-OCR invalidates it wholesale. `TextQuoteSelector` is the durable *foundation* because it re-locates by content. Jon Udell's annotation-SDK notes [10] and the W3C multiple-selectors discussion [8] both conclude: **store position to disambiguate/seek and quote to verify/recover** — position alone cannot even *detect* that the document changed, but a co-stored quote can. PDF/OCR adds two independent pitfalls: PDF native user space is 72pt/inch with a **bottom-left origin (y up)** while rasterized/web pixel space is top-left and DPI-dependent [18][19], and extracted character order ≠ reading order (PDF text is emitted in *draw* order [21]) — so a global char-offset computed on one extraction will not survive a different extractor/OCR pass. **Conclusion: char-offset anchors are disposable cache, never the system of record; the durable anchor is quote+structural, and bboxes must always be `normalized` and carry their coordinate-origin convention, page size, rotation, and DPI.** TEI stand-off markup [15] is the mature precedent (markup in a separate layer pointing into a read-only source via id+XPointer); its documented failure mode — pure offset/ID pointers break the moment the base text is re-tokenized [16] — is *exactly* creel's re-ingestion problem, and is precisely why the Web-Annotation world layered redundant quote+context selectors on top of structural pointers. For document **images**, IIIF [24] is the right model: regions are a media-fragment `xywh` in an abstract *Canvas* coordinate space decoupled from any rendered resolution — directly analogous to creel's normalized `BoundingBoxSelector`.

---

## Human annotation / qualitative coding & mixed human-machine provenance

**CAQDAS tools converge on a reified "segment" object that codes hang off of — not codes pointing directly at text [1][2].** In ATLAS.ti the *quotation* is a first-class object (a marked data segment with its own id/comment) and codes, memos, and hyperlinks all attach to it [1]. The REFI-QDA exchange standard formalizes this: a `PlainTextSelection` (attrs `guid`, `startPosition`, `endPosition`) contains child `Coding` elements (each referencing a `CodeRef`) plus notes [2]. **The takeaway for creel: the source-span SELECTION should be a reified entity, and a "coding" is a separate link object `{selection → graph element}`** — exactly mirroring creel's existing selector plus a new coding link.

**Human coding decomposes into the same primitives creel already extracts.** NLP's brat standoff format [3] shows the minimal set: `T` = text-bound span with char offsets (and discontinuous spans), `R` = typed relation between two annotations, `N` = normalization/**entity-linking to an external KB id**, `#` = free-text note — all in a separate `.ann` file that never mutates the text. **The brat `N` primitive is precisely "link a highlighted span to a graph NODE," and `R` is "to an EDGE."** This is the standoff principle creel already uses.

**The W3C Web Annotation motivation vocabulary [7] supplies the human-coding semantics for free.** A manual "coding" act = an Annotation whose **Body** is the code/category/node/edge reference, **Target** is creel's existing selector, and **motivation** is one of `classifying`/`identifying`/`tagging`/`linking`/`commenting`/`editing`/`highlighting`. It carries a `creator` (Agent), `created`/`modified` timestamps, and a `generator` (the client). **This means D15's planned overlay (Body+Target keyed by element id) is the SAME structure needed for human input — input and output annotations differ only by `motivation` and `creator`, so one model serves both** [7][22].

**Pre-annotation + human correction is a solved pattern, and the best tools keep machine and human output as PARALLEL, separately-attributed records rather than overwriting [4][5].** Label Studio stores model `predictions` and human `annotations` as distinct collections, preserving region IDs when a prediction is accepted so you can trace which human annotation came from which model region [4]. INCEpTION [5] runs the full lifecycle: recommenders suggest, the annotator accepts/rejects/corrects (feeding active learning), roles are explicit, and a **separate curation/adjudication stage** merges layers and computes inter-annotator agreement. **Design lesson: keep each annotator's (and the machine's) work in its own layer; treat the merged graph as a derived artifact with its own provenance.**

**W3C PROV-O [6] gives the vocabulary for mixed human/machine provenance and non-destructive correction.** An Entity `wasGeneratedBy` an Activity and `wasAttributedTo` an Agent — where the Agent can be a `prov:SoftwareAgent` *or* a `prov:Person`. This directly supports creel's `attributed_to = model id OR HUMAN id`. Critically, **`prov:wasRevisionOf` models a correction as a NEW entity derived from the prior one**, preserving the chain instead of overwriting. So the user's three-way distinction is *derivable*, not a hardcoded flag: **machine-extracted** = software-agent & no revision; **manually-coded** = person & no machine antecedent; **human-corrected** = person & `wasRevisionOf` → a software-agent record. Per-attribute grounding is the same "evidence span per claim" pattern from fact-extraction research: KILT [25] attaches a set of provenance spans to *each* claim (allowing multiple valid sets), confirming creel should key evidence to `(element_id, attribute_name)`, not only `(element_id)`. **REFI-QDA (`.qdpx`/`.qdc`) [2] is the de-facto human-coding interchange format** (NVivo, ATLAS.ti, MAXQDA, Dedoose, Taguette, QualCoder) and maps cleanly onto creel — category tree → `CodeBook`, coding → `Coding`, span → `PlainTextSelection`, with `creatingUser`/`creationDateTime` audit attrs — but it is an **escape hatch to reserve, not build now**.

---

## Bidirectional source↔graph trace: data contract & interaction patterns

**Per-attribute grounding is the production norm, not a stretch goal.** Anthropic's Citations API [20] attaches to each *claim text block* a list of typed location objects whose `type` discriminates the selector (`char_location`, `page_location`, `content_block_location`) — essentially creel's grounding-selector list, but keyed to a *claim/value* rather than a node/edge. LandingAI's Agentic Document Extraction [13] grounds *each extracted field value* with `chunk_references` (page + bounding-box) **plus per-field confidence**, schema-shaped as `{field: {value, confidence, grounding:[{page,bbox,chunk_id}]}}`. **This directly validates creel limitation (1): element-level evidence is now below the bar legal/finance buyers expect — per-attribute is table stakes.** Two contract details matter for auditability: (a) store the **resolved `cited_text` snapshot** alongside the selector so a stale offset can still be verified/re-anchored after re-ingestion [20]; (b) inline per-value citations conflict with strict structured-output/JSON-constrained decoding [20], which argues for a **two-pass posture** — pass 1 extract typed values, pass 2 ground each value (locate span, emit selector + confidence). The grounding pass is also exactly what human correction reuses.

**The reverse index is a classic interval-stabbing problem with an off-the-shelf answer [12][23].** Per source document, maintain an interval index keyed by `(start, end)` offsets, augmented so each node stores its subtree's max endpoint — giving O(log n + k) stabbing/overlap queries (find all spans covering a clicked offset, or overlapping a selection). Interval trees / segment trees / HINT [12] are standard. **The forward direction (element → spans) is just the grounding list creel already stores; the reverse direction (span → elements) is a derived projection over the same offsets — cheap to rebuild, never ground truth.** STAM [22] shows the standoff model yields the reverse index for free via inverse relations (`referenced_by`).

**Linked-view UIs all reduce to a shared address space + a bidirectional lookup [26].** Elicit/scite/Perplexity/ChatDoc all implement the same interaction: numbered inline claims ↔ highlighted source spans, click-to-jump in both directions. The enabling contract is a stable mutual id space: every source span has an id/offset, every element has an id, and **one queryable link relation `{element_id, attribute_path?, source_id, selector, evidence_id, provenance_summary}` indexed by *either* key.** Click-element → highlight = `WHERE element_id = ?`; click-passage → show-elements = interval query → `element_id`s. No view owns the link — it is a separate queryable relation. GraphRAG/KG systems [27] reinforce making sources first-class graph citizens so `answer → claim → evidence → document` is a traversable path; for creel this argues the sidecar should be **joinable from the query layer**, not only a lookup-by-id, so one query can return an element + its evidence + its source spans (powering both the linked-view UI and audit exports). "Explain this value" then maps onto a PROV-O backward traversal [6]: `value → wasGeneratedBy(activity) → used(source) → grounding selectors → resolved cited_text`, uniform across nodes, edges, and attribute values. Keep source addressing stable across versions with a content-versioned id (`source_id@content_hash`) so a re-ingested document re-anchors + flags review rather than orphaning existing codings or evidence.

---

## How creel's CURRENT model supports this (honest audit)

creel's existing design is **unusually well-positioned** — most of the vision is already latent in the D8 evidence record and D7 separability. The audit:

**What already works (keep, don't touch):**

- **Separable, joinable sidecar (D7/D8).** `Graph.evidence: dict[element_id → Evidence]` (`creel/graph/model.py`) is *deliberately excluded from canonical JSON and joined on demand* — the nanopublication separation-with-joinability pattern, done right. This is the spine the whole vision hangs on.
- **PROV-aligned provenance vocabulary (`creel/evidence.py`).** `Provenance{derived_from, generated_by, attributed_to, generated_at, version}` is already PROV verbs: `wasDerivedFrom`/`wasGeneratedBy`/`wasAttributedTo`/`generatedAtTime` [6]. `attributed_to` is *already documented* as "model id+version **or** human id" — the machine/human axis is anticipated.
- **Web-Annotation selectors, implemented and serializable.** Both `TextQuoteSelector(exact, prefix, suffix)` and `TextPositionSelector(start, end, source_id)` exist, plus cell/jsonpath/page/bbox. `BoundingBoxSelector` already has the `normalized` flag — the correct DPI mitigation [18][24]. `grounding` is a *Sequence*, so storing multiple redundant selectors per element is already legal.
- **Review-state enum, present and correct.** `Confidence.review_status ∈ {auto, needs_review, confirmed, rejected, corrected}` exactly matches the Prodigy/Label-Studio/INCEpTION convergence [4][5]. `method`-tagged scores (never cross-comparable) is also right.
- **Evidence rides on extraction results.** `ExtractedNode`/`ExtractedEdge` each carry `evidence: Optional[Evidence]` (`creel/extract/protocol.py`); the facade collects them into the sidecar (`creel/facade.py`). Standoff-by-construction.

**Honest gaps versus the vision:**

1. **Evidence is per-element only.** Both the docstring of `Evidence` and D8 *claim* "every node, edge, **and value**," but the wiring stops at the element: the facade keys `graph.evidence[node.id]` / `[edge.id]`, and `Evidence` has no notion of *which attribute* it grounds. **A user cannot today trace a single PROPERTY to its source span** — limitation (1) is real and is the biggest gap.
2. **The standoff overlay is framed as OUTPUT only.** D15/EPIC 8.2 describe the annotation overlay (Body+Target keyed by element id) purely as *insights laid over the graph*. There is **no input path**: no way for a human to highlight a passage and attach it to a node/edge/category. The Body+Target machinery is right; it is simply not yet bidirectional in *direction of authorship*.
3. **No reverse index.** Grounding selectors flow element → source only. There is **no span → elements** lookup, so "click a passage, see what it produced" is unbuildable today. (It is a pure projection of data creel already has — cheap, but absent.)
4. **No re-anchoring discipline.** creel *can* store quote+position but has no policy mandating both, no precedence rule (quote = truth, position = hint), and no resolver that re-anchors after re-ingestion. Today a re-parse could silently trust stale offsets — exactly the TEI failure mode [16].
5. **Correction is an enum, not a chain.** `review_status = corrected` records *that* something was corrected but not *what it superseded*. There is no `wasRevisionOf`, so the machine-vs-manual-vs-corrected distinction the user wants is **not yet derivable** and corrections risk being destructive.

**Verdict:** the data model is right; the *granularity*, the *input direction*, the *reverse projection*, and the *re-anchoring policy* are missing. None requires breaking the existing schema.

---

## Minimal additions to keep the evolution clean

Five additions, ordered by leverage. Each is a **superset/extension**, not a fork — existing per-element evidence remains the default (progressive disclosure: simple cases stay simple).

**A1 — Per-attribute grounding granularity *(fixes gap 1).*** Let an evidence record key on an **optional finer id**: keep `evidence[element_id]` for node/edge-level facts, and add `evidence[(element_id, attribute_path)]` for value-level facts. Reuse `JsonPathSelector` syntax for `attribute_path` so the **same selector vocabulary addresses both the source (where the value came from) and the target attribute (which property it grounds)** [13][20][25]. This is a keying change, not a schema fork. *Do NOT* mandate per-attribute evidence everywhere — only where an extractor can actually attribute a value (the two-pass grounding posture makes this natural [20]).

**A2 — A first-class Annotation contract (human coding as an auditable standoff link) *(fixes gap 2).*** Introduce **one** record type that serves both D15 output and human input, in the standoff layer, never inside the node:

```
Annotation { id,
             target,      # element_id | (element_id, attribute_path) | source span (existing selectors)
             body,        # node_ref | edge_ref | category_ref | insight | free-text comment
             motivation,  # classifying | identifying | tagging | linking | commenting | editing | highlighting
             provenance,  # attributed_to {kind: software_agent | person, id}, generated_by/coded_by, timestamps
             confidence } # reuse existing block incl. review_status
```

Machine insight (D15) and manual coding are **the same object**, differing only by `motivation` + `attributed_to.kind` [7][14][22]. Reify the **Selection** (id + selector + source_id) as an addressable record so multiple codings can share one highlighted span [1][2]. *Do NOT* build per-annotator adjudication, IAA metrics, or REFI-QDA export now — tag each Annotation with its agent/layer id so those become a later projection, and stop there.

**A3 — A derived reverse-trace index (span → elements) *(fixes gap 3).*** Build a **rebuildable cache**, not a source of truth: per `source_id`, an augmented interval tree / sorted `(start,end)` array over text spans, with parallel structures for `CellSelector` by `(row,col)`, `PageSelector` by page, and `BoundingBoxSelector` by `(page, normalized-grid-cell)` [12][23]. Payload `= {element_id, attribute_path?, evidence_id}`. Expose two primitives: `elements_at(source_id, offset)` (stabbing) and `elements_overlapping(source_id, start, end)` (range). For modest docs a sorted array + binary search suffices. *Do NOT* persist it as canonical state — rebuild it from the sidecar on ingest.

**A4 — Anchor robustness (quote + position + context) for re-ingestion *(fixes gap 4).*** Make it **policy** to emit, for every text grounding, BOTH a `TextQuoteSelector` (exact + ~32-char prefix/suffix) AND a `TextPositionSelector`, plus the resolved `cited_text` snapshot — a policy change, since both selector types already exist. Declare precedence in docs: **quote = system of record, position = disposable hint recomputed every re-ingest.** Add an ordered re-anchoring resolver mirroring Hypothes.is [9]: (1) structural/position fast-path → (2) verify text at that position still equals the stored quote → (3) **bounded** fuzzy search (diff-match-patch/Bitap) in a window around the stored position, prefix→suffix context-first → (4) whole-document quote search as last resort. Always bound the window (diff-match-patch is pathologically slow on misses [9]) and normalize whitespace/unicode first. When an anchor resolves only via fuzzy match, **emit a re-anchor score and downgrade `review_status` to `needs_review`.** The most robust default to recommend: a **structural anchor (block/cell/JSONPath/page id) `refinedBy` a TextQuoteSelector**, plus a position/normalized-bbox hint — which needs the small additions of `RangeSelector` + structural selectors + `refinedBy` [7][8]. *Do NOT* re-anchor eagerly on every read — only on re-ingestion of a changed source version (`source_id@content_hash`).

**A5 — Manual-vs-auto-vs-corrected provenance, *derived* not hardcoded *(fixes gap 5).*** Add an **agent kind** to `attributed_to` (`software_agent | person`) and record corrections **non-destructively** as a NEW evidence/annotation record carrying `wasRevisionOf → superseded_record_id` [6]. Then the three-way state is a query, not a field: machine-extracted = software-agent & no revision; manually-coded = person & no machine antecedent; human-corrected = person & `wasRevisionOf` → software-agent record. Keep `generated_by` (strategy+extractor) for machines and a parallel `coded_by` (tool/UI id) for humans. This satisfies "see whether an entry was machine-extracted vs manually coded vs human-corrected" essentially for free, and keeps the machine record intact for audit. *Do NOT* add a separate `entry_kind` enum — it would duplicate (and drift from) the derivable truth.

**Explicitly NOT yet (reserve the contract, don't build):** the front-end linked-view UI; RDF-star / PROV-O / JSON-LD export of the evidence graph (the plain-JSON cores already chosen keep this open [6][7]); per-annotator layers, adjudication, and inter-annotator-agreement scoring [5]; REFI-QDA `.qdpx`/`.qdc` round-trip [2]; an active-learning retraining loop off accept/reject signals [4][5]; editable graph **specification/config** UI (a separate concern that can reuse the category schema later). The five additions above are necessary and sufficient to make the vision *buildable on top* without another schema migration — they seed **ADR D-OP9** (the annotated-graph + evidence-granularity contract) and **EPIC 8** (downstream annotated-graph contract).

---

## References (Vancouver)

[1] ATLAS.ti. *Quotation Level (Quotations)* — Windows manual. [https://manuals.atlasti.com/Win/en/manual/Quotations/QuotationLevel.html](https://manuals.atlasti.com/Win/en/manual/Quotations/QuotationLevel.html)

[2] REFI-QDA. *QDA-XML Project Exchange Standard (1.5)* — the QDA Software Standard. [https://www.qdasoftware.org/](https://www.qdasoftware.org/); spec [https://openqda.github.io/refi-tools/docs/standard/REFI-QDA-1-5.pdf](https://openqda.github.io/refi-tools/docs/standard/REFI-QDA-1-5.pdf); import/export overview [https://www.maxqda.com/help/report-and-export/export-and-import-refi-qda-projects](https://www.maxqda.com/help/report-and-export/export-and-import-refi-qda-projects)

[3] brat. *Standoff format* — brat rapid annotation tool. [https://brat.nlplab.org/standoff.html](https://brat.nlplab.org/standoff.html)

[4] Label Studio. *Predictions / pre-annotations and human annotations.* [https://labelstud.io/guide/predictions.html](https://labelstud.io/guide/predictions.html)

[5] INCEpTION. *Semantic annotation platform with recommenders, curation & active learning.* [https://inception-project.github.io/](https://inception-project.github.io/); INCEpTALYTICS [https://github.com/catalpa-cl/inceptalytics](https://github.com/catalpa-cl/inceptalytics)

[6] W3C. *PROV-O: The PROV Ontology* (Recommendation, 2013). [https://www.w3.org/TR/prov-o/](https://www.w3.org/TR/prov-o/)

[7] W3C. *Web Annotation Data Model* (Recommendation, 2017). [https://www.w3.org/TR/annotation-model/](https://www.w3.org/TR/annotation-model/)

[8] W3C Web Annotation WG. *Issue #93 — multiple selectors / precision fallback.* [https://github.com/w3c/web-annotation/issues/93](https://github.com/w3c/web-annotation/issues/93)

[9] Hypothes.is. *Fuzzy anchoring.* [https://web.hypothes.is/blog/fuzzy-anchoring/](https://web.hypothes.is/blog/fuzzy-anchoring/)

[10] Udell J. *Notes for an annotation SDK.* [https://blog.jonudell.net/2021/09/03/notes-for-an-annotation-sdk/](https://blog.jonudell.net/2021/09/03/notes-for-an-annotation-sdk/)

[11] Hypothes.is / dom-anchor-text-quote. *Quote anchoring with prefix/suffix context.* [https://github.com/tilgovi/dom-anchor-text-quote](https://github.com/tilgovi/dom-anchor-text-quote)

[12] Christodoulou G, Bouros P, Mamoulis N. *HINT: A Hierarchical Index for Intervals in Main Memory.* arXiv:2104.10939. [https://arxiv.org/pdf/2104.10939](https://arxiv.org/pdf/2104.10939)

[13] LandingAI. *Agentic Document Extraction — per-field grounding & chunk_references.* [https://landing.ai/llms/contract-data-extraction-for-enterprise-legal-teams](https://landing.ai/llms/contract-data-extraction-for-enterprise-legal-teams)

[14] W3C Web Annotation WG. *Model FPWD — provenance discussion.* [https://w3c.github.io/web-annotation/model/fpwd/](https://w3c.github.io/web-annotation/model/fpwd/)

[15] TEI. *Stand-off markup* (TEI Wiki); TEI Guidelines ch. 17. [https://wiki.tei-c.org/index.php/Stand-off_markup](https://wiki.tei-c.org/index.php/Stand-off_markup); [https://tei-c.org/release/doc/tei-p5-doc/en/html/SA.html](https://tei-c.org/release/doc/tei-p5-doc/en/html/SA.html)

[16] Bański P. *Why TEI stand-off annotation doesn't quite work…* Balisage Series on Markup Technologies, vol. 5. [https://www.balisage.net/Proceedings/vol5/html/Banski01/](https://www.balisage.net/Proceedings/vol5/html/Banski01/BalisageVol5-Banski01.html)

[17] google/diff-match-patch. *Bitap approximate matching & Myers diff.* [https://github.com/google/diff-match-patch](https://github.com/google/diff-match-patch)

[18] Apryse. *PDF coordinates and PDF processing.* [https://apryse.com/blog/pdf-coordinates-and-pdf-processing](https://apryse.com/blog/pdf-coordinates-and-pdf-processing)

[19] Datalogics. *Understanding the PDF coordinate system.* [https://www.datalogics.com/blog/](https://www.datalogics.com/blog/)

[20] Anthropic. *Citations* — Claude API (typed location objects; Citations vs Structured Outputs). [https://platform.claude.com/docs/en/build-with-claude/citations](https://platform.claude.com/docs/en/build-with-claude/citations)

[21] Mozilla pdf.js. *Issue #4843 — extracted text order ≠ reading order.* [https://github.com/mozilla/pdf.js/issues/4843](https://github.com/mozilla/pdf.js/issues/4843)

[22] STAM. *Stand-off Text Annotation Model (inverse relations / reverse index).* [https://github.com/annotation/stam](https://github.com/annotation/stam)

[23] Cormen TH, Leiserson CE, Rivest RL, Stein C. *Interval Trees* — Introduction to Algorithms (augmented red-black trees; O(log n) stabbing). MIT Press.

[24] IIIF. *Presentation API 2.1 + Selector Registry (media-fragment xywh; Canvas coordinate space).* [https://iiif.io/api/presentation/2.1/](https://iiif.io/api/presentation/2.1/); [https://iiif.io/api/registry/selectors/](https://iiif.io/api/registry/selectors/)

[25] Petroni F, et al. *KILT: a Benchmark for Knowledge Intensive Language Tasks* (per-claim provenance spans). arXiv:2009.02252. [https://arxiv.org/pdf/2009.02252](https://arxiv.org/pdf/2009.02252)

[26] Atlas Workspace. *AI with references — linked claim↔source interaction.* [https://www.atlasworkspace.ai/blog/ai-with-references](https://www.atlasworkspace.ai/blog/ai-with-references)

[27] Neo4j. *The GraphRAG Manifesto — provenance as first-class graph citizens.* [https://neo4j.com/blog/genai/graphrag-manifesto/](https://neo4j.com/blog/genai/graphrag-manifesto/)
