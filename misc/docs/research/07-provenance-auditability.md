# 07 — Provenance, grounding, confidence & auditability

> **TL;DR.** Creel's "auditability over opaqueness" mandate decomposes into three orthogonal questions for every extracted node, edge, and attribute value: *Where did this come from?* (provenance), *Where exactly in the source?* (grounding / text anchoring), and *How sure are we?* (confidence). The mature, lightweight standards answer the first two directly — **W3C PROV-O** [1][2] gives a minimal entity/activity/agent vocabulary for derivation chains, **PAV** [5][6] adds authoring/curation/versioning roles on top, **nanopublications** [3][4] supply the architectural pattern of *physically separating* an assertion from its provenance and publication-info graphs joined by a shared id, and the **W3C Web Annotation Data Model** [7][8] gives robust standoff text anchors (`TextQuoteSelector` with exact/prefix/suffix, plus `TextPositionSelector` character offsets). The third question has no single standard but a clear research consensus: **token logprobs** are cheap but only well-calibrated for closed-form choices and unavailable for most hosted models; **self-consistency / sampling agreement** is the most reliable black-box signal [13]; **verbalized confidence** (just ask the model) is surprisingly well-calibrated on RLHF models and often beats raw logprobs [14][16]; calibration should be measured with **Expected Calibration Error** and operationalized via **selective prediction / abstention thresholds** routing low-confidence items to human review [17][18]. Recommendation: attach a small, separable JSON "evidence record" to every graph element, keyed by a stable element id, carrying (a) a PROV-lite provenance triple, (b) one or more Web-Annotation-style source selectors, and (c) a confidence block combining a method tag, a numeric score, and a review status — stored in a sidecar layer and joined on demand.

## Background / landscape

Creel produces a JSON graph (typed nodes, typed edges, typed attribute values) from heterogeneous sources via pluggable extractors. For each produced fact, auditability requires three independently useful pieces of metadata:

1. **Provenance** — the causal/derivational story: which source document, which extractor strategy, which agent (LLM/model version or human), when, derived from what. This is what PROV, PAV and nanopublications standardize.
2. **Grounding / anchoring** — the precise *location* in the source that backs the fact: a character span, a quoted snippet with context, a table cell, a JSON path. This is what the Web Annotation Data Model standardizes for text, with parallel selector ideas for structured data.
3. **Confidence** — a calibrated estimate of how likely the fact is correct, plus the human-review state. This is the LLM-uncertainty literature; no W3C standard, but converging best practice.

The strong architectural lesson from the standards world — especially **nanopublications** — is *physical separation with joinability*: a nanopublication is one named-graph bundle holding three distinct graphs (the **assertion**, its **provenance**, and the **publication info**) plus a head graph that ties them together under one citable identifier [3][4]. This is exactly creel's stated posture: keep the graph definition layer separate from extraction/verification metadata, joined on demand by a shared key. Creel should treat that pattern as a first-class design constraint rather than reinventing it.

### Provenance data models

**W3C PROV** is a family of recommendations (2013). **PROV-DM** is the conceptual data model; **PROV-O** expresses it as a lightweight OWL ontology in namespace `http://www.w3.org/ns/prov#` [1][2]. "Lightweight" is concrete here: PROV-O conforms to the OWL-RL profile (with five exceptions), so it is computationally cheap and broadly implementable [1]. Its three core classes are **Entity** (a thing with fixed aspects — e.g., an extracted value or a source document), **Activity** (something occurring over time that acts on entities — e.g., an extraction run), and **Agent** (something bearing responsibility — an LLM, a tool, a person) [1]. The "starting-point" relations are the ones creel actually needs: `wasGeneratedBy` (entity ← activity), `used` (activity → entity), `wasDerivedFrom` (entity → entity), `wasAttributedTo` (entity → agent), `wasAssociatedWith` (activity → agent), `actedOnBehalfOf` (delegation), plus temporal `generatedAtTime`/`startedAtTime`/`endedAtTime` [1].

**PAV** (Provenance, Authoring and Versioning) [5][6] specializes PROV-O precisely where it is too generic: PROV-O gives derivation but no vocabulary to distinguish *author* vs *contributor* vs *curator* vs *the agent that created a particular representation* [5]. PAV separates three axes — Provenance (data about the artifact's origin/access/transformation), Authoring (intellectual-property/knowledge creation), and Versioning (evolution over time) — with terms like `pav:createdBy`, `pav:authoredBy`, `pav:curatedBy`, `pav:importedFrom`, `pav:derivedFrom`, `pav:retrievedFrom`, `pav:version`, `pav:lastUpdatedOn` [5][6]. PAV is deliberately "just enough" — a good fit for creel's progressive-disclosure ethos.

**Nanopublications** [3][4] contribute the *architecture* rather than new vocabulary: each nanopub = head + assertion + provenance + publication-info named graphs, each independently addressable and citable by a unique (often content-derived, cryptographically verifiable) identifier [3][4]. The split between "provenance of the *assertion*" and "publication info about the *nanopublication record itself*" maps directly onto creel's distinction between "how was this fact extracted" and "who/what wrote this evidence record and when."

### Standoff annotation & text anchoring

The **W3C Web Annotation Data Model** (Recommendation, 2017) [7][8] models an Annotation as a wrapper connecting one or more **Body** resources to one or more **Target** resources; an annotation must have at least one target [7]. A target can carry a **Selector** that pins to a *segment* of the source. The selectors creel cares about:

- **TextQuoteSelector** — `exact` (the matched text) plus optional `prefix` and `suffix` context to disambiguate repeated strings [7][8]. Robust to minor edits and reflowing because it is content-based, not offset-based.
- **TextPositionSelector** — `start`/`end` character offsets into the normalized text stream (position 0 precedes the first char) [7]. Precise but brittle if the source bytes change.
- **FragmentSelector** (media-type URI fragments, e.g. `#t=30,60` for video, `#row=4` style for CSV via RFC 7111), **RangeSelector** (chains `startSelector`/`endSelector`), and **XPathSelector** for DOM/XML [7].
- **`refinedBy`** composes selectors (e.g., a position selector refining a fragment selector), and **State** (`TimeState` with `sourceDate`, `HttpRequestState`) records *which representation* of a changing source was annotated [7].

"Standoff" means the annotation/anchor lives *outside* the source document and points back in — exactly creel's separability requirement. The Apache incubator "Annotator" project and FragmentSelector/`#:~:text=` text-fragment URLs are the practical lineage [8].

### LLM grounding, citation & confidence

For LLM-based extraction (creel's default strategy), grounding means making the model emit the *supporting span* alongside each extracted value. Recent work formalizes attribution as mapping each output statement to one or more cited source passages, evaluated by citation **recall** (coverage) and **precision** (sufficiency) [9][12]. Fine-grained methods have the model extract a *supporting quote* (a contiguous span appearing verbatim in the source) tied to a document id, which both grounds the answer and yields a ready-made `TextQuoteSelector` [11][12]. A crucial 2025 distinction: **citation correctness ≠ citation faithfulness** — a cited passage may *support* a claim without the model actually having *relied* on it; correctness is necessary but not sufficient for genuine grounding [10]. For creel this means: verify that the quoted span actually contains the value, don't just trust that the model attached a citation.

Confidence/uncertainty methods fall into three families [13][15]:

- **Token-level (logprobs).** Cheap; well-calibrated for multiple-choice / yes-no / closed-form outputs, but most hosted models don't expose logprobs, and they are poorly calibrated for free-form generation [13].
- **Consistency / self-consistency.** Sample the extraction multiple times; agreement (or low entropy) over samples tracks correctness and is the most reliable signal in black-box settings [13]. Cost scales with sample count.
- **Verbalized confidence.** Ask the model to state a probability/confidence. On RLHF models (GPT-4, Claude, ChatGPT), verbalized confidences are *often better calibrated than the model's own logprobs*, reducing ECE by ~50% relative on TriviaQA/SciQ/TruthfulQA [14][16] — but reliability is strongly prompt-dependent [16].

Calibration is measured with **Expected Calibration Error (ECE)**: bin predictions by stated confidence and sum the weighted absolute gaps between confidence and observed accuracy [17]. Operationally, confidence feeds **selective prediction**: choose a threshold, *abstain* (defer to a human) below it, and trade coverage for accuracy on what you keep; the **risk-coverage curve / AURC** quantifies this [17][18].

### Human-in-the-loop review

HITL for extraction is mature and convergent [19][20][21]: route to human review when (a) confidence falls below a threshold, (b) extractors disagree (the LLM strategy and a regex/query strategy conflict), or (c) the source type is novel. **Uncertainty sampling / active learning** surfaces the most informative items first so reviewer effort is spent where it matters [19][21]. The dominant pattern is *machine-proposes-human-verifies*: the system pre-fills candidate extractions with their anchors and confidence, and the reviewer accepts/edits/rejects — recorded as a state transition, not a silent overwrite [20].

## Comparative analysis

### Provenance models

| Model | Scope | Granularity fit for creel | Weight | Best for creel |
|---|---|---|---|---|
| **PROV-O / PROV-DM** [1][2] | Generic entity/activity/agent derivation | Excellent — value ← extraction-activity ← agent | Lightweight (OWL-RL) | The backbone vocabulary |
| **PAV** [5][6] | Authoring/curation/versioning, specializes PROV-O | Excellent for "who authored vs curated vs imported" | Very light ("just enough") | Role + version terms on top of PROV |
| **Nanopublications** [3][4] | Architectural pattern: assertion+provenance+pubinfo named graphs, citable id | Pattern, not vocabulary | Light pattern, RDF-heavy if literal | The *separation+join-by-id* blueprint |

### Confidence methods

| Method | Needs model internals? | Calibration | Cost | Verdict for creel |
|---|---|---|---|---|
| Token logprobs [13] | Yes (logprobs) | Good for closed-form, poor for free-form | ~free | Use when available + output is constrained (enums, yes/no) |
| Self-consistency / sampling [13] | No | Best black-box signal | N× inference | Reserve for high-stakes / ambiguous elements |
| Verbalized confidence [14][16] | No | Often beats logprobs on RLHF models; prompt-sensitive | +1 field | **Default** — cheap, model-agnostic |
| Internal-state probes [15] | Yes (hidden states) | Strong but research-grade | Custom | Out of scope for creel core |

### Text-anchoring selectors

| Selector | Pins to | Robust to source edits? | Use in creel |
|---|---|---|---|
| TextQuoteSelector (exact+prefix+suffix) [7][8] | Quoted snippet + context | Yes (content-based) | **Primary anchor for prose** |
| TextPositionSelector (start/end) [7] | Char offsets | No (brittle) | Secondary, for exact re-highlighting |
| FragmentSelector [7] | Media fragment (CSV row, video time, page) | Depends on media | Tables/CSV (RFC 7111), media targets |
| Query selector (creel-native) | SQL/Mongo predicate or cell coords | Schema-stable | Structured sources (tables, JSON) |

## Design implications for creel

1. **Make the evidence record a separate layer keyed by element id (nanopub pattern).** Every node, edge, and attribute value in the graph definition gets a stable `id`. A *sidecar* store maps `id → evidence record`. The graph spec stays clean and downstream-friendly; the evidence layer is joined on demand for audit/rendering. This is creel's stated SSOT + physical-separation posture, validated by nanopublications [3][4]. Crucially, **attribute values and edge attributes are first-class evidence targets**, not just nodes — funding amounts on edges and indicator values need their own anchors and confidence.

2. **Adopt a PROV-lite + PAV vocabulary, not full RDF.** Don't force RDF/OWL on creel's JSON. Borrow PROV's three roles and a handful of relations as plain JSON keys: `derived_from` (source entity/document id), `generated_by` (extractor/activity descriptor), `attributed_to` (agent: model id + version, or human id), `generated_at` (timestamp) [1]. Add PAV-style `version`/`imported_from` where curation matters [5]. Provide an optional exporter to true PROV-O/JSON-LD for users who want interoperability — progressive disclosure.

3. **Standardize anchors as Web-Annotation-style selectors, one schema across source types.** For prose (LLM strategy), require a `TextQuoteSelector` (exact + prefix/suffix) and optionally a `TextPositionSelector` [7][8]. For tables, use a fragment/cell selector (RFC 7111-style `row`/`column` or a query predicate). For JSON, use a JSONPath/Mongo-query selector. Unify them under one `selector` field with a `type` discriminator — this *is* the strategy pattern applied to grounding, mirroring creel's extractor strategies.

4. **Tie the confidence method to the extractor strategy.** Deterministic strategies (regex, SQL/Mongo query, pure functions) are *exact-by-construction* → confidence = 1.0 with method `deterministic`; their anchor is the matched span/cell, and they need no model uncertainty. LLM strategies → default to **verbalized confidence** (one extra output field) [14][16], escalate to **self-consistency voting** for flagged high-stakes elements [13], and use **logprobs** only when the model exposes them and the output is constrained (enums, ranges) [13]. Record the *method* alongside the *score* so scores are never compared across incommensurable methods.

5. **Build review as a state machine over the evidence layer, driven by selective-prediction thresholds.** Each element carries `review_status ∈ {auto, needs_review, confirmed, rejected, corrected}`. A configurable confidence threshold (per node/edge type) auto-routes low-confidence or extractor-conflict items to `needs_review` [17][18][20]. Human decisions are appended as new provenance (a curation activity `attributed_to` a person), never silent overwrites — preserving the audit trail [20]. Surface most-uncertain-first (uncertainty sampling) to spend reviewer effort well [19][21].

6. **Verify, don't just cite (faithfulness gate).** Because citation correctness ≠ faithfulness [10], add a cheap deterministic post-check: confirm the extracted value (or a normalized form) actually occurs within the quoted span / resolved selector. A failed check downgrades confidence and flags `needs_review`. This turns the anchor into a *verifier*, realizing "every element verifiable + traceable to source."

## Recommendation

**Attach to every node, edge, and attribute value a small, separable JSON "evidence record," stored in a sidecar layer keyed by the element's stable id, structured as three blocks — `provenance`, `grounding`, and `confidence` — using a PROV/PAV-lite vocabulary, Web-Annotation-style selectors, and a method-tagged confidence with a review-status field.** Concretely:

```jsonc
// evidence[element_id]  (kept physically separate from the graph spec)
{
  "provenance": {                       // PROV-lite (+ PAV where useful)
    "derived_from": "src:results-framework.pdf#doc",
    "generated_by": { "strategy": "llm", "extractor": "objective.detect.v1" },
    "attributed_to": { "agent": "claude-opus-4-8", "kind": "model" },
    "generated_at": "2026-06-16T12:00:00Z",
    "version": 1
  },
  "grounding": [                        // W3C Web Annotation selectors
    { "source": "src:results-framework.pdf",
      "selector": { "type": "TextQuoteSelector",
                    "exact": "USD 4.2 million", "prefix": "allocated ", "suffix": " to the program" },
      "secondary": { "type": "TextPositionSelector", "start": 18432, "end": 18446 } }
  ],
  "confidence": {                       // method-tagged, never bare
    "method": "verbalized",             // deterministic | logprob | verbalized | self_consistency
    "score": 0.82,
    "samples": null,                    // populated for self_consistency
    "verified": true,                   // faithfulness gate: value found in span
    "review_status": "needs_review"     // auto | needs_review | confirmed | rejected | corrected
  }
}
```

**Rationale.** This single record answers all three audit questions for every element, satisfies creel's physical-separation-with-join-by-id mandate (the nanopublication pattern [3][4]), reuses *only* the lightweight, battle-tested cores of PROV-O/PAV [1][5] and the Web Annotation Model [7] rather than their full RDF stacks (progressive disclosure: plain JSON now, PROV-O/JSON-LD export later), and operationalizes confidence in the way the evidence supports — verbalized-by-default with self-consistency escalation [13][14][16], measured by ECE and acted on through selective-prediction thresholds that feed a non-destructive human-review state machine [17][18][20]. It is the minimum structure that makes *every node, edge, and attribute value independently verifiable and traceable to its exact source location*, which is precisely creel's "auditability over opaqueness" promise.

## References

[1] [PROV-O: The PROV Ontology — W3C Recommendation (2013)](https://www.w3.org/TR/prov-o/)
[2] [PROV-DM: The PROV Data Model — W3C Recommendation (2013)](https://www.w3.org/TR/prov-dm/)
[3] [Kuhn et al., "Nanopublications: A Growing Resource of Provenance-Centric Scientific Linked Data" (arXiv:1809.06532)](https://arxiv.org/pdf/1809.06532)
[4] [Kuhn et al., "A Unified Nanopublication Model for Effective and User-Friendly Access to the Elements of Scientific Publishing" (arXiv:2006.06348)](https://arxiv.org/pdf/2006.06348)
[5] [Ciccarese et al., "PAV ontology: provenance, authoring and versioning", Journal of Biomedical Semantics 4:37 (2013)](https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-4-37)
[6] [PAV — Provenance, Authoring and Versioning (ontology site & GitHub)](https://pav-ontology.github.io/pav/)
[7] [Web Annotation Data Model — W3C Recommendation (2017)](https://www.w3.org/TR/annotation-model/)
[8] [Web Annotation Vocabulary — W3C Recommendation (2017)](https://www.w3.org/TR/annotation-vocab/)
[9] [Gao et al. / attribution evaluation: citation recall & precision (RAG attribution survey)](https://arxiv.org/abs/2405.07437)
[10] [Wallat et al., "Correctness is not Faithfulness in Retrieval Augmented Generation Attributions", ICTIR 2025](https://staff.fnwi.uva.nl/m.derijke/wp-content/papercite-data/pdf/wallat-2025-correctness.pdf)
[11] [Hu et al., "Learning Fine-Grained Grounded Citations for Attributed Large Language Models" (arXiv:2408.04568)](https://arxiv.org/pdf/2408.04568)
[12] ["Cite Before You Speak: Enhancing Context-Response Grounding in LLM Agents" (arXiv:2503.04830)](https://arxiv.org/pdf/2503.04830)
[13] ["Systematic Evaluation of Uncertainty Estimation Methods in Large Language Models" (arXiv:2510.20460)](https://arxiv.org/html/2510.20460v1)
[14] [Tian et al., "Just Ask for Calibration: Strategies for Eliciting Calibrated Confidence Scores from Language Models Fine-Tuned with Human Feedback", EMNLP 2023](https://aclanthology.org/2023.emnlp-main.330/)
[15] [Beigi et al., "InternalInspector: Robust Confidence Estimation in LLMs through Internal States" (arXiv:2406.12053)](https://arxiv.org/pdf/2406.12053)
[16] ["On Verbalized Confidence Scores for LLMs" (arXiv:2412.14737)](https://arxiv.org/html/2412.14737v2)
[17] [Ragas / RAG metrics & calibration overview; "A Primer on Uncertainty and Calibration in Deep Learning"](https://vizuara.substack.com/p/a-primer-on-uncertainty-and-calibration)
[18] ["Explicit Abstention Knobs for Predictable Reliability" (arXiv:2601.00138) — selective prediction / risk-coverage](https://arxiv.org/html/2601.00138v1)
[19] [Humans in the Loop — "Human-in-the-Loop for Active Learning" (uncertainty sampling)](https://humansintheloop.org/solutions/human-in-the-loop-for-active-learning/)
[20] [Comet, "Human-in-the-Loop Review Workflows for LLM Applications & Agents"](https://www.comet.com/site/blog/human-in-the-loop/)
[21] ["Human-in-the-Loop Artificial Intelligence: A Systematic Review of Concepts, Methods, and Applications", Entropy 28(4):377 (2026)](https://www.mdpi.com/1099-4300/28/4/377)
