# 08 — Evaluation, verifiers & LLM-as-judge

> **TL;DR.** Evaluating a source-to-graph extractor is *not* one comparison but many: matching nodes, matching typed edges, and checking each typed attribute — each of which needs a *different* notion of "equal." The mature IE/KG literature already treats this as set-based precision/recall/F1 over canonicalized elements, with graph-edit-distance and fuzzy alignment for harder cases; the modern LLM-eval ecosystem (DeepEval, Inspect, OpenAI Evals, promptfoo, Ragas) has converged on a near-identical abstraction — a **scorer/grader/metric** that returns a score in [0,1] plus a reason, where the comparison logic is *pluggable* and one important kind of grader is "a natural-language rubric judged by an LLM" (G-Eval / model-graded). For creel this maps cleanly onto a single `Verifier` protocol (`actual, expected, context -> VerdictScore`) with a small taxonomy of built-in kinds (exact, normalized, set/graph, schema/constraint, numeric-tolerance, semantic-similarity, LLM-rubric, composite) that mirror creel's *extractor* strategy taxonomy. The opinionated recommendation: make the **LLM-instruction verifier first-class and the default fallback**, but always pair it with cheaper deterministic verifiers, mitigate known judge biases by construction, and physically separate the verifier metadata from the graph definition so the same test corpus can be re-scored under different verifier policies.

## Background / landscape

Creel's core promise — `extract(sources, graph_spec, extractors) -> graph` — only becomes trustworthy if we can answer *"is this extracted graph correct?"* against a labeled corpus, and creel's design posture (auditability, strategy pattern, single source of truth) demands that the *comparison* itself be a pluggable strategy rather than hardcoded equality. The need is not exotic: it sits at the intersection of three well-developed bodies of work.

1. **Information-extraction / knowledge-graph evaluation.** Decades of NLP work (relation extraction, slot filling, knowledge-base population) evaluate extraction with precision/recall/F1 over *elements* — entities, types, and relation triples — where matching requires canonicalization and equivalence handling, not string identity [1][6][9].
2. **Semantic-equivalence checking.** When the gold and predicted values are free text, equivalence is judged by embeddings, natural-language inference (entailment), or normalization rather than exact match [7][8].
3. **LLM-as-judge & eval frameworks.** Since 2023, "LLM-as-a-judge" has become a standard way to grade open-ended output, formalized by G-Eval [4] and validated against humans by MT-Bench/Chatbot Arena [11]; every serious eval library now exposes a *grader/scorer/metric* abstraction that composes deterministic and model-graded checks [2][3][5][10][12].

The unifying insight across all three: **comparison is a function of (actual, expected, criteria) returning a score, and the implementation behind that function is swappable.** That is precisely the `Verifier` abstraction creel needs.

## Comparative analysis

### Metrics for KG/IE extraction

| Metric family | What it scores | When it fits creel | Caveats |
|---|---|---|---|
| Entity P/R/F1 | Set match of extracted vs gold nodes (TP/FP/FN) [1] | Did we find the right donors, projects, indicators? | Needs entity canonicalization first |
| Typing precision (P^T) | Whether a found entity got the right node-type [1] | Node-taxonomy correctness | Partial credit on sub-taxonomy depth not standard |
| Triple/edge P/R/F1 | A triple counts as TP only if *all three* of (head, relation, tail) match [1][6] | Edge correctness (funds, contributes-to) | Strictest; one wrong endpoint = full miss |
| Slot-filling F1 (TAC-KBP) | Attribute values per (entity, slot); equivalence classes collapse redundant fillers, credit once [9] | Typed *attributes on nodes/edges* (funding amount, indicator value) | Equivalence rules must be specified per slot |
| CEAF | Optimal alignment between predicted and gold entity clusters [9] | Coreference / dedup of same real-world entity | Requires solving an assignment problem |
| Graph edit distance (GED) | Min edit cost to transform predicted graph into gold [a] | Holistic structural similarity | NP-hard; usually approximated [a] |
| Fuzzy entity alignment | Embedding/fuzzy-set similarity for "same entity, different surface form" [b][c] | Cross-source entity reconciliation | Similarity ≠ equivalence; threshold-sensitive [b] |

A recurring and important warning from this literature: **canonicalize before you compare.** Edit-distance-based or ontology-constrained canonicalization (e.g. "same entities must share a type") is applied so that surface variants map to one canonical node before P/R/F1 is computed [c]. Skipping this inflates false positives/negatives. Triple-level F1 is the default reported in "thousands of papers" but is unforgivingly strict — a single wrong endpoint zeroes the triple [1] — which argues for *partial-credit* / per-element scoring in creel rather than only whole-triple match.

### Semantic-equivalence checking (for free-text attribute values)

| Technique | Mechanism | Strength | Weakness |
|---|---|---|---|
| Exact / normalized match | Lowercase, strip, unit-normalize, then `==` | Cheap, deterministic, auditable | Brittle to paraphrase |
| Embedding cosine similarity | Sentence-embedding distance, threshold | Catches paraphrase | "similarity as a proxy for equivalence" — not the same thing [7] |
| NLI / entailment | DeBERTa-style premise→hypothesis classifier; **bidirectional** entailment ≈ equivalence [7] | Closer to true equivalence | Gap between strict entailment and "same core answer" [7] |
| LLM-judged equivalence | Ask an LLM "do these mean the same?" | Most robust to wording | Cost, latency, bias [11] |

The literature is explicit that embedding similarity and entailment are *imperfect proxies*: embedding similarity conflates "related" with "equivalent" [7], and strict textual entailment is narrower than answer-equivalence [7]. This is the central reason creel should support a *ladder* of equivalence checks and let LLM-judgment be the robust fallback.

### LLM-as-judge methodology

| Axis | Options | Notes for creel |
|---|---|---|
| Granularity | **Pointwise** (score one output) vs **Pairwise** (A-vs-B preference) | Creel verification is inherently *reference-based pointwise* (actual vs expected), so pointwise rubric grading is the right default |
| Reference | Reference-free vs **reference-based** | Creel always has gold → reference-based, which is easier and more reliable |
| Criteria | Free-form prompt vs **rubric/criteria-based** | Rubrics improve consistency and auditability [13] |
| Method | G-Eval: auto-generate CoT eval steps from criteria, form-filling, probability-weighted score [4] | Strong human correlation; reproducible |

**G-Eval** is the canonical method: it takes a natural-language *criterion*, has the LLM auto-generate chain-of-thought *evaluation steps*, then fills a score form; it re-weights discrete scores by output-token probabilities to get a smoother, tie-breaking continuous score, reaching **Spearman 0.514 with humans on SummEval** (then state-of-the-art) [4][5]. It is reference-free by design but trivially adapted to reference-based grading by putting the gold answer in the prompt.

**Agreement with humans.** GPT-4-class judges reach **~85% agreement with humans on MT-Bench (excluding ties), versus ~81% human-human**, and 83–87% on Chatbot Arena [11]. The critical caveat (verified against a second source): raw agreement *ignores chance agreement*; chance-corrected Cohen's κ is materially lower (commonly ~0.4–0.7), so headline "matches humans" claims are optimistic [11]. Creel should report κ-style chance-corrected agreement when validating its own judges, not raw accuracy.

**Known biases (every untreated judge pipeline exhibits them) [13][14] + mitigations:**

| Bias | Symptom | Mitigation |
|---|---|---|
| **Position** | Prefers first-listed option (pairwise) or score-options at certain rubric positions (rubric is implicitly multiple-choice) [13][14] | Swap order / average over permutations ("balanced permutation"); randomize rubric option order [13] |
| **Verbosity** | Prefers longer answers | Length-controlled prompting; penalize unsupported length |
| **Self-preference** | Judge favors text from its own model family (G-Eval explicitly flags LLM bias toward LLM-generated text) [4] | Use a *different* model to judge than to extract; ensemble judges |
| **Authority/style** | Swayed by confident tone, citations | Rubric pins judgment to evidence, not style |

For creel, reference-based pointwise grading sidesteps most position/pairwise bias, but self-preference matters: **the judge model should differ from the extractor model**, and rubric option ordering should be randomized.

### Verifier abstractions in eval frameworks (how they compose)

| Framework | Abstraction | Built-in deterministic | Model-graded | Composition |
|---|---|---|---|---|
| **Inspect AI** | `Scorer` → `Score(value, answer, explanation, metadata)` | `match`, `includes`, `pattern`, `exact`, `f1`, `answer`, `choice`, `math` (SymPy) [12] | `model_graded_qa`, `model_graded_fact`; multi-model majority vote; `grader` model-role [12] | Multiple scorers per task; metrics/reducers aggregate |
| **DeepEval** | `BaseMetric` → `measure()`/`a_measure()`, attrs `score∈[0,1]`, `threshold`, `success`, `reason` [10] | G-Eval (rubric), DAG (deterministic decision tree), subclass BaseMetric | G-Eval, RAG/agent metrics | Metrics run independently; pass if score ≥ threshold |
| **OpenAI Evals** | `Grader` | `string_check`, `text_similarity` (fuzzy/BLEU/ROUGE/METEOR) [a] | `score_model`, `label_model` (passing_labels) | `python` grader + `multigrader` chain [a] |
| **promptfoo** | `assert` entries | `equals`, `contains`, `regex`, `is-json`, `levenshtein`, `javascript`/`python`, `rouge`/`bleu` | `llm-rubric`, `factuality`, `g-eval`, `answer-relevance` | **Weighted average** over assertions; `metric` tags for aggregate [2] |
| **Ragas** | metric objects | — | `faithfulness`, `answer_correctness`, `context_recall` (claim-decomposition + LLM) [3] | Compose metric set per dataset |

The convergence is striking and is the strongest signal for creel's design: **all five expose the same shape** — a named comparison that returns a normalized score (often + reason), mixing cheap deterministic checks with LLM-graded ones, composed by weighted aggregation and gated by thresholds. promptfoo's weighted-average-with-named-metrics and Inspect's "score + explanation + metadata" are the most directly reusable models for creel.

### Assertion / property-based testing for non-deterministic output

Because LLM output is non-deterministic, exact-match assertions are infeasible; the field uses **semantic assertions** (meaning, not text), **property/constraint checks** (is-json, required keys, value in range, no prohibited terms), and **LLM-graded assertions** [2][15]. Property-based testing is explicitly recommended where exact expected outputs are infeasible: assert *invariants* the output must satisfy rather than its exact value [15] (e.g. "every extracted edge's `funding_amount` is a positive number with a currency", "every project links to ≥1 objective"). The PROMPTEVALS work catalogs assertions/guardrails for production LLM pipelines as a first-class artifact [15]. For creel this means verifiers should include *schema/constraint verifiers* that test structural invariants of the produced graph independent of any specific gold value.

## Design implications for creel

**1. A single `Verifier` protocol, mirroring the extractor strategy pattern.** Define one structural interface — verifiers are the evaluation-time dual of extractors. Concretely:

```python
class VerdictScore(TypedDict):
    score: float          # normalized [0,1]; 1.0 == fully correct
    passed: bool          # score >= threshold
    reason: str           # auditable explanation (esp. for LLM verifiers)
    details: dict         # per-component scores, matched pairs, etc.

class Verifier(Protocol):
    def verify(self, actual, expected, *, context: VerifyContext) -> VerdictScore: ...
```

`context` carries the source text/spans, the graph-spec element being checked (so a verifier knows the attribute's type/enum/range), and the threshold. This matches Inspect's `Score(value, explanation, metadata)` and DeepEval's `score/reason/success` so creel can interoperate with either as a backend.

**2. A verifier-kind taxonomy that parallels the node/edge taxonomy.** Ship these built-ins, each a `Verifier`:

- `exact` / `normalized` (lowercase, trim, unit/number normalization) — the auditable default for enums and IDs.
- `numeric_tolerance` (abs/rel tolerance) — for funding amounts, indicator values that live *on edges*.
- `set_match` and `graph_match` — set-based P/R/F1 over canonicalized nodes/edges with partial credit; optional GED/fuzzy-alignment for hard cases [1][6][a][b]. Triple match should be *decomposable* (credit head/relation/tail separately) rather than all-or-nothing.
- `schema_constraint` — property-based invariants over the produced graph (types, enums, ranges, required edges) [15]; runs with no gold value.
- `semantic_similarity` — embedding or NLI/bidirectional-entailment for free-text attributes, with explicit threshold [7].
- `llm_rubric` (G-Eval-style) — the robust fallback, see (3).
- `composite` — weighted combination of sub-verifiers with named sub-metrics, exactly like promptfoo's weighted assert blocks [2].

**3. The LLM-instruction verifier is first-class, specified declaratively, executed via G-Eval.** A verifier should be fully expressible as *natural language* — e.g. `{"kind": "llm_rubric", "criteria": "The extracted objective text conveys the same goal as the expected one, even if reworded; ignore phrasing, focus on intended outcome.", "threshold": 0.7, "judge_model": "...", "reference": true}`. Execution follows G-Eval [4]: auto-generate CoT evaluation steps from `criteria`, form-fill a 1–5 (or 0–1) score with the gold answer in-context, normalize. Bake bias mitigation into the runner *by construction*: (a) **judge model ≠ extractor model** to kill self-preference [4]; (b) randomize rubric option order / average over permutations for position bias [13][14]; (c) require the `reason` field and store it for audit. This is the natural extension of creel's progressive-disclosure posture: schema-as-extractor by default, **schema-description-as-verifier by default** — the *same* natural-language element descriptions that drive extraction can seed the rubric that verifies it.

**4. Physically separate verifier metadata from the graph definition (join on demand).** Exactly as creel separates extraction metadata from graph definition: the graph-spec says *what* a node/edge/attribute is; a parallel **verifier-spec** says *how to judge* it. Store verifiers keyed by the same taxonomy path (e.g. `node.donor.name → normalized`, `edge.funds.amount → numeric_tolerance(rel=0.01)`, `node.objective.text → llm_rubric(...)`), with a default-resolution chain (element-specific → type-default → global default = `llm_rubric` seeded from the element's description). This keeps a single source of truth, lets the same test corpus be re-scored under different verifier *policies* (strict vs lenient), and makes every score traceable to (source span, element, verifier, reason).

**5. Test corpus layout: gold graph + per-element verifier attachment.** A corpus item = `{sources, expected_graph, verifier_overrides?}`. Because verifiers attach by taxonomy path, most items need *no* per-item verifier config — they inherit the policy. Scoring produces a structured report: per-element scores roll up to per-type and per-graph P/R/F1, and the LLM-judge `reason`s are retained for the auditability the creel context demands.

**6. Always pair LLM verifiers with cheap deterministic ones, and report chance-corrected agreement.** Run deterministic verifiers first (free, fast, fully auditable); only fall through to `semantic_similarity` / `llm_rubric` when they fail or for inherently free-text fields. When validating creel's own judges against human labels, report Cohen's κ, not raw agreement, since the latter overstates reliability [11].

## Recommendation

**Adopt a single `Verifier` protocol — `verify(actual, expected, *, context) -> {score, passed, reason, details}` — with a built-in kind taxonomy that parallels creel's node/edge/attribute taxonomy, and make the natural-language `llm_rubric` verifier both first-class and the *default fallback*, seeded automatically from each element's own schema description (G-Eval execution), while resolving to cheaper deterministic verifiers wherever the element's type permits.**

Rationale: this is the one design that satisfies all of creel's stated postures simultaneously. It is the *strategy pattern* (verification mirrors extraction), it preserves the *single source of truth* and *physical separation* (verifier-spec joined to graph-spec on demand by taxonomy path), it delivers *progressive disclosure* (zero-config default via schema-as-verifier, full control via per-element overrides), and it maximizes *auditability* (every verdict carries a `reason` traceable to source). It is also the abstraction the entire eval ecosystem has independently converged on (Inspect `Scorer`, DeepEval `BaseMetric`, OpenAI `Grader`, promptfoo `assert`, Ragas metrics) [2][3][10][12][a], so creel can use any of them as a pluggable backend rather than reinventing scoring — and can borrow their hardest-won lesson: deterministic-first, LLM-graded-as-fallback, biases mitigated by construction (judge ≠ extractor, randomized option order, mandatory reasons) and reported with chance-corrected agreement.

## References

[1] [Iterative Zero-Shot LLM Prompting for Knowledge Graph Construction (arXiv:2307.01128)](https://arxiv.org/pdf/2307.01128) — entity/type/relation P, R, F1; triple-as-TP-only-if-all-three-match.

[2] [Promptfoo — Assertions & Metrics (LLM Output Validation)](https://www.promptfoo.dev/docs/configuration/expected-outputs/) — deterministic + model-graded assertion types, weighted-average composition, named metrics.

[3] [Ragas — List of available metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) — faithfulness, answer_correctness, context recall/precision; claim-decomposition + LLM grading.

[4] [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment (arXiv:2303.16634)](https://arxiv.org/abs/2303.16634) — CoT auto eval-steps, form-filling, probability-weighted scoring, Spearman 0.514 on SummEval, bias toward LLM-generated text.

[5] [G-Eval — DeepEval docs](https://deepeval.com/docs/metrics-llm-evals) — practical G-Eval (rubric → CoT → score) implementation and weighting.

[6] [Understanding the Effect of Knowledge Graph Extraction Error on Downstream Graph Analyses (arXiv:2506.12367)](https://arxiv.org/pdf/2506.12367) — edge-tuple P/R/F1 as the dominant KG-extraction metric.

[7] [A Practical Guide for Evaluating LLMs and LLM-Reliant Systems (arXiv:2506.13023)](https://arxiv.org/pdf/2506.13023) — embedding similarity vs equivalence, NLI/bidirectional entailment, normalization.

[8] [Improving Sentence Embeddings with an Automatically Generated NLI Dataset (arXiv:2402.15132)](https://arxiv.org/html/2402.15132v1) — NLI-based sentence embeddings for semantic similarity/equivalence.

[9] [Task Description for English Slot Filling at TAC-KBP 2014 (NIST)](https://tac.nist.gov/2014/KBP/ColdStart/guidelines/KBP2014_TaskDefinition_EnglishSlotFilling_1.1.pdf) — slot-filling F1, equivalence classes for redundant fillers, CEAF for entity discovery/linking.

[10] [Introduction to LLM Metrics — DeepEval](https://deepeval.com/docs/metrics-introduction) — `BaseMetric` interface (`measure`/`a_measure`, `score`, `threshold`, `success`, `reason`); statistical vs model-based vs G-Eval vs DAG.

[11] [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (arXiv:2306.05685)](https://arxiv.org/abs/2306.05685) — ~85% GPT-4↔human agreement (excl. ties), position/verbosity/self-enhancement biases; chance-correction caveat.

[12] [Scorers — Inspect AI](https://inspect.aisi.org.uk/scorers.html) — `Scorer`/`Score`, built-ins (match/includes/pattern/exact/f1/answer/choice/math), `model_graded_qa`/`model_graded_fact`, multi-model majority vote, metrics/reducers.

[13] [Am I More Pointwise or Pairwise? Revealing Position Bias in Rubric-Based LLM-as-a-Judge (arXiv:2602.02219)](https://arxiv.org/abs/2602.02219) — rubric grading as implicit multiple-choice → position bias; balanced-permutation mitigation.

[14] [Judging the Judges: A Systematic Investigation of Position Bias in Pairwise LLM-as-a-Judge (arXiv:2406.07791)](https://arxiv.org/html/2406.07791v5) — systematic position-bias analysis and mitigation.

[15] [PROMPTEVALS: A Dataset of Assertions and Guardrails for Custom Production LLM Pipelines (arXiv:2504.14738)](https://arxiv.org/pdf/2504.14738) — assertions/guardrails/property checks as first-class artifacts for non-deterministic output.

[a] [Graders — OpenAI API Reference](https://platform.openai.com/docs/api-reference/graders) — `string_check`, `text_similarity` (fuzzy/BLEU/ROUGE/METEOR), `score_model`, `label_model`, `python` grader, `multigrader`.

[b] [FLORA: Unsupervised Knowledge Graph Alignment by Fuzzy Logic (arXiv:2510.20467)](https://arxiv.org/abs/2510.20467) — fuzzy entity alignment; similarity vs distance are not interchangeable.

[c] [A survey: knowledge graph entity alignment research based on graph embedding (Springer, 2024)](https://link.springer.com/article/10.1007/s10462-024-10866-4) — entity-alignment methods, ontology-constrained canonicalization, edit-distance thresholds; relation to graph edit distance.
