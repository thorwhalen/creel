# 11 — Results-based management & logframe domain

> **TL;DR.** Creel's first-consumer use case — extracting a graph of donors, objectives, cross-cutting areas, projects, outputs, outcomes and indicators from results-based-management (RBM) documents — sits squarely inside a mature, internationally-standardised domain. Two layers of standards already define almost every node and edge type creel needs. (1) The generic **results chain** (inputs → activities → outputs → outcomes → impact) and its tabular expression, the **logframe**, both downstream of a **Theory of Change** [1][2][8]. (2) Donor/funding data standards — a **standard funding/results data model** (results + transactions) and **policy markers** (e.g. gender, environment, scored 0/1/2) — which give us a ready-made vocabulary for *funding amounts on edges*, *indicator values on edges*, and *cross-cutting markers as edge attributes* [6][7][10][11][12]. The strongest design move for creel is to **adopt the standard result/indicator/period model verbatim for indicator-bearing edges, and a generic impact/outcome/output taxonomy as the default node grammar**, so the first-consumer use case ships with a faithful, auditable schema out of the box rather than a hand-rolled one.

## Background / landscape

**Results-Based Management (RBM)** is a management strategy by which organisations ensure that their processes, products and services contribute to the achievement of clearly stated *results*. Its planning backbone, the **logical framework ("logframe")**, emerged from mid-20th-century institutional planning practice and scaled across international organisations and NGOs from the 1990s onward [1]. The logframe is built on a *hierarchy of levels* linking inputs, activities, outputs, outcomes and goals, with an assumed cause-and-effect relationship where lower levels contribute to those above [1][2].

The conceptual spine of RBM is the **results chain**: *the sequence of results considered necessary to achieve desired objectives, beginning with inputs, used to carry out activities and deliver outputs, designed to help bring about outcomes that eventually contribute to the desired impact* [1]. The chain splits naturally into two halves: the *implementation* segment (inputs, activities — what the organisation controls) and the *results* segment (outputs = operational results; outcomes = development results; impact = long-term change it only contributes to) [1].

A **Theory of Change (ToC)** sits *upstream* of the logframe: it articulates the assumptions, causal pathways and mechanisms — the "missing middle" — by which activities are expected to produce long-term change, working *backward* from goals to the conditions that must hold, and making external factors and assumptions explicit [8]. The widely-cited relationship is: **"The Theory of Change is the basis upon which we design a results chain and logframe, not the other way around"** [8]. A ToC is non-linear and holistic (multiple pathways, actors, assumptions); a logframe is a linear, tabular *what* derived from it [8].

**Indicators** are the measurement layer. The canonical quality bar is **SMART** — Specific, Measurable, Achievable, Relevant, Time-bound [13]. In logframe practice an *Objectively Verifiable Indicator (OVI)* names *who, by how much, by when, and verified how* [13]. Each indicator carries a **baseline** (a starting value, captured before the intervention, with the year/date taken), a **target** (the value to reach by a date), an **actual** (the measured value), and **means of verification (MoV)** — the instrument, who collects it, and how often [13]. These four constructs (baseline / target / actual / MoV) are universal across RBM systems and map directly onto the standard funding/results data model (below).

Many large organisations operationalise RBM through a documented results framework: a costed, multi-year strategy that moves through phases — broadly **plan for results, get results, show results** — with the planning phase producing a situation analysis, vision, **theory of change**, a *costed results framework*, and an M&E plan [3][9][14]. Such frameworks typically track results through a simplified chain aligned to the **impact, outcome and output** levels, with strategies operating at those three results levels [3][9].

## Comparative analysis

### The vocabularies creel must reconcile

| Layer | Source | Node-ish concepts | Edge-ish / measurement concepts | Recency |
|---|---|---|---|---|
| Generic RBM / logframe | INTRAC, tools4dev, eval literature | inputs, activities, outputs, outcomes, impact/goal; objectives | indicators (SMART/OVI), baseline, target, MoV, assumptions/risks | INTRAC guide updated 2024 [1]; evergreen concepts [13] |
| Organisational results framework | RBM handbooks, monitoring resource centres | impact areas, outcome areas, enabling/support areas, objectives, strategy, operation | core impact/outcome/output indicators; baselines & targets (some impact indicators carry *no* target) [4][5] | current results frameworks [3][9] |
| Donor / funding data standard | standard funding/results activity model; policy-marker handbooks | activity, participating-org (funding/accountable/extending/implementing), result (output/outcome/impact) | transaction (commitment/disbursement, value, currency, provider-org→receiver-org); result→indicator→baseline→period(target/actual); policy markers (0/1/2) | current activity standard [6][7][10]; gender-marker handbook current [11][12] |

### Results-chain levels: terminology crosswalk

| Results chain [1] | Logframe row [2] | Results framework [3][9] | Standard result `@type` [10] | Controlled by | Typical indicator |
|---|---|---|---|---|---|
| Impact | Goal / overall objective | **Impact statement** (impact area) | `3` (impact) | Society (contribution only) | rights-level; **target sometimes omitted** [4] |
| Outcome | Purpose / specific objective | **Outcome statement** (outcome area) | `2` (outcome) | Partly (contributes to) | target vs baseline |
| Output | Output / result | **Output statement** | `1` (output) | Yes (delivers) | target vs baseline |
| Activity | Activity | (activity / sub-output) | — (activity-level) | Yes | process/milestone |
| Input | Input / means | budget / resources | transaction `value` | Yes | cost |

This crosswalk is the single most important asset for creel: it shows the **same five-level spine** under three names, so a creel `graph_spec` can use one canonical taxonomy and treat the others as label aliases.

### A generic results-framework taxonomy

Organisational results frameworks typically organise their goals into a small set of high-level **impact areas**, a larger set of **outcome areas**, and a set of **enabling (management/support) areas** [3][5][9]. The exact wording and counts vary across organisations and across editions of a given framework, but the *shape* is consistent and maps cleanly onto a recursively-subdivided controlled vocabulary:

- **Impact areas** — a handful of top-level mission statements (e.g. protecting rights, responding to emergencies, empowering the served population, pursuing durable solutions).
- **Outcome areas** — thematic areas such as access to services and documentation; protection of vulnerable groups; basic needs and well-being; health; education; water, sanitation and hygiene; economic inclusion and livelihoods; and durable solutions.
- **Enabling areas** — internal management and support work such as systems and processes, operational support and supply chain, people and culture, external engagement and resource mobilisation, and leadership and governance.

**Measurement convention:** a results framework typically defines a set of **core indicators** spanning impact, outcome and output levels [9]. Critically, **some impact indicators do not require targets** (they are at the level of *rights* or long-term change), whereas operations *do* set targets for outcome and output indicators, tracked against a **baseline** established for the strategy [4]. This asymmetry must be modelled — a creel indicator-attribute schema cannot assume every indicator has a target.

### A standard funding & results data model

A standard funding/results activity model gives creel a battle-tested, machine-readable model for exactly the two things the first-consumer use case puts *on edges*: **funding amounts** and **indicator values**.

**Funding (transactions).** An activity lists **participating-org**s with one of four roles — **funding, accountable, extending, implementing** [7]. Money flows are **transaction**s; the standard distinguishes *commitments* (the promise of money) from *disbursements/incoming funds* (the actual transfer), each with a **value** (positive/negative, decimal), **currency**, and **provider-org → receiver-org**, optionally referencing the source/destination activity id for **traceability** [7][16]. `currency`, `finance-type`, `flow-type`, `aid-type` and `tied-status` can default at activity level [7].

**Results (indicators).** Each activity may contain many `result` elements (type `1`/`2`/`3` = output/outcome/impact), each containing one or more `indicator`s [10]. The `indicator` element's structure is the gold standard for creel's indicator-bearing edges [6][10]:

```
result (@type: 1=output|2=outcome|3=impact)
  title, description
  indicator (@measure: unit|percentage|currency|qualitative;
             @ascending: true/false (is "up" good?);
             @aggregation-status)
    title, description
    reference (@vocabulary, @code, @indicator-uri)   # e.g. a results-framework code
    baseline (@year, @iso-date, @value) + location, dimension, comment
    period
      period-start, period-end
      target (@value) + dimension, location, comment
      actual (@value) + dimension, location, comment
```

Key modelling lessons for creel:
- An indicator value is **never a scalar** — it is a `(measure, baseline, target, actual, period, dimensions)` tuple. The `@measure` distinguishes count/percentage/currency/qualitative; `@ascending` encodes whether increase is good (essential for verification logic).
- **Disaggregation** is first-class: `dimension` elements break values down by sex, age or location [10] — directly relevant to common disaggregation requirements.
- `reference` links an indicator to an external framework (e.g. a results-framework code), enabling the *auditability/traceability* creel prizes.

### Policy markers — cross-cutting areas as scored attributes

Cross-cutting themes (gender, environment, climate) are represented in donor data as **policy markers**, scored on a three-point scale per activity [11][12]:

| Score | Label | Meaning |
|---|---|---|
| **0** | Not targeted | Screened, no relevant element |
| **1** | Significant | An important, deliberate objective, but not the principal reason for the activity |
| **2** | Principal | The theme is the main objective; the activity would not exist without it |

Markers in scope typically include a **gender-equality marker** [11][12], an **environment** marker, and a family of **climate/biodiversity markers** (biodiversity, climate change mitigation, climate change adaptation, desertification) [17]. Markers are reported *at activity level* alongside **purpose/sector codes** [12][17]. Good practice recommends a *dual strategy*: targeted interventions (usually score 2) plus mainstreaming (usually score 1) [12].

Many organisations also maintain their own cross-cutting frame for inclusive programming — bundling accountability to the served population and commitments on equity and inclusion — and integrate its dimensions into their results framework for proposal assessment, monitoring and reporting [18][19]. So creel must represent cross-cutting areas in **two compatible idioms**: a *scored marker* (0/1/2, for donor docs) and a *categorical inclusion/protection tag* (for organisation-internal docs).

## Candidate node / edge taxonomy for creel

This taxonomy is opinionated for the first-consumer use case but is deliberately a *recursive taxonomy* (per creel's `graph_spec` grammar): `Impact > Outcome > Output` are subdivisions of one **Result** node-type; impact/outcome/enabling *areas* are a recursively-subdivided controlled vocabulary.

### Node types

| Node type | Subdivides into | Key typed attributes | Source of truth |
|---|---|---|---|
| **Donor** | (bilateral, multilateral, private, pooled-fund) | name, org-id, role∈{funding, accountable, extending, implementing} | standard participating-org [7] |
| **Objective / Strategy** | impact-area → outcome-area | level∈{impact,outcome,output}, area-code, statement (freeform), strategy-period | results framework [3][5] |
| **CrossCuttingArea** | gender; environment; climate; protection; accountability | kind∈{gender,environment,climate,protection,accountability}, marker∈{0,1,2}, climate_marker? | policy markers [11][17] + inclusion frame [18] |
| **Project / Activity** | (sub-activities) | title, activity-id, country/location, start/end, budget, currency, sector | standard activity [7] |
| **Output** | — | output-statement, output-area, responsible-org | results framework / standard [4][10] |
| **Outcome** | — | outcome-statement, outcome-area | results framework [4] |
| **Indicator** | impact/outcome/output indicator | name, measure∈{unit,%,currency,qualitative}, ascending?, disaggregation[], MoV, reference | standard indicator [6][10] |

### Edge types (edges are first-class, carry typed attributes)

| Edge type | From → To | Edge attributes (the payload) | Standard basis |
|---|---|---|---|
| **funds** | Donor → Project | amount (decimal), currency, transaction_type∈{commitment,disbursement}, value_date, period | standard transaction [7][16] |
| **delivers** | Project → Output | quantity, period, responsible-org | results chain [1] |
| **contributes-to** | Output → Outcome | contribution_weight?, assumption/risk note | results chain [1][8] |
| **advances** | Outcome → Objective/Impact-area | (contribution only; impacts may have no target) | results framework [4] |
| **addresses** | Project/Output → CrossCuttingArea | marker∈{0,1,2}, rationale | policy markers [11][12] |
| **measured-by** | {Outcome,Output,Impact} → Indicator | **baseline(value,year)**, **target(value,date)**, **actual(value,period)**, measure, disaggregation | standard result/indicator/period [10] |
| **aligned-to** | Indicator → external framework | vocabulary, code, uri | standard reference [10] |

Note that **indicator values and funding amounts live on edges** (`measured-by` and `funds` respectively), exactly as creel's brief requires — and both are *temporal tuples*, not scalars, because the standard's `period` and `transaction` models are inherently time-indexed.

## Synthetic-but-realistic example documents (test corpus seeds)

These are **synthetic** (invented values/orgs) but structured to mirror real RBM/funding artefacts. They exercise all three extractor strategies: prose (donor agreement), table (results matrix), table (indicator table).

### Doc A — Donor agreement excerpt (freeform prose → tests LLM extractor)

> **Contribution Agreement — Schedule 1**
> **Foundation Alpha** (the "Donor", org-id `XX-ORG-000123`) agrees to provide an **earmarked contribution of USD 4,500,000** to the implementing organisation (the "Recipient") for the period **1 January 2025 – 31 December 2026** in support of the regional protection operation. Of this amount, **USD 2,000,000 is committed** upon signature, with the balance disbursed in two tranches subject to satisfactory reporting. Funds shall support activities under outcome area **Protection of vulnerable groups (OA4)** and **Child protection (OA5)**. The intervention is classified **gender-equality marker = 2 (principal)** and **environment marker = 0**. The Donor's role is *funding*; the Recipient acts as *accountable* and *implementing* organisation. A results matrix (Schedule 2) is attached.

*Expected graph:* Donor(Foundation Alpha) —funds[amount=4.5M USD, commitment=2.0M, period=2025–2026]→ Project(regional protection); Project —addresses[marker=2]→ CrossCuttingArea(gender); links to Outcome(OA4), Outcome(OA5).

### Doc B — Project results matrix (table → tests SQL-like extractor)

| Level | Statement | Results area | Responsible | Linked to |
|---|---|---|---|---|
| Impact | The served population enjoys improved protection from violence | Protect | Implementing org | — |
| Outcome 1 | Survivors of violence have timely access to quality response services | OA4 Protection | Implementing org + Agency Beta | Impact |
| Output 1.1 | Case-management workers trained and deployed in 12 sites | OA4 | Agency Beta | Outcome 1 |
| Output 1.2 | Safe spaces for women and girls established and operational | OA4 | Implementing org | Outcome 1 |
| Outcome 2 | Unaccompanied and separated children receive appropriate care | OA5 CP | Agency Gamma | Impact |
| Output 2.1 | Best-interests procedures applied for identified children | OA5 | Agency Gamma | Outcome 2 |

### Doc C — Indicator table (table → tests query + functional extractors; values on edges)

| Indicator | Level | Measure | Ascending | Baseline (2024) | Target (2026) | Actual (mid-2025) | Disagg. | MoV |
|---|---|---|---|---|---|---|---|---|
| % of survivors receiving services within 72h | Outcome 1 | percentage | true | 45% | 80% | 62% | sex, age | Case-mgmt database (quarterly) |
| # of safe spaces operational | Output 1.2 | unit | true | 3 | 12 | 9 | location | Site monitoring report (monthly) |
| # of case-management workers trained | Output 1.1 | unit | true | 0 | 240 | 180 | sex | Training records (per cohort) |
| # of children with active best-interests assessment | Output 2.1 | unit | true | 120 | 600 | 410 | sex, age | Registration system (continuous) |
| % of children in family-based care | Outcome 2 | percentage | true | 30% | 70% | 48% | age | Child-protection IMS (quarterly) |

*Each row becomes a `measured-by` edge whose attributes are the baseline/target/actual tuple — directly mirroring the standard `indicator/baseline` + `period/target` + `period/actual` [10].*

## Design implications for creel

1. **Ship a generic results-framework taxonomy and the standard indicator model as the default `graph_spec` for the first-consumer use case — do not hand-roll.** A results framework's impact / outcome / enabling areas are a *recursively subdivided taxonomy with controlled-vocabulary codes* (OA-codes, EA-codes), which is exactly creel's `graph_spec` grammar. Encoding them as the bundled default delivers progressive disclosure: a user pointing creel at RBM docs gets a faithful schema for free [3][4][5].

2. **Model indicator values as temporal tuples on edges, never as scalars.** Adopt the standard's `(measure, ascending, baseline{value,year}, target{value,date}, actual{value,period}, dimensions[])` shape verbatim for the `measured-by` edge's attribute schema [10]. The `@ascending` flag and `@measure` enum are essential for any *verification* extractor (you can't check "on track" without knowing whether up is good and whether the unit is count/%/currency).

3. **Make `target` optional and level-aware.** Some impact indicators carry **no target** by design [4]. The constrained-attribute layer must allow `target = null` at impact level — a hard "required target" constraint would reject valid data.

4. **Represent cross-cutting areas as a dual-idiom node + a scored `addresses` edge.** Carry both the policy marker (`0/1/2` ordinal) and the categorical inclusion/protection tag on the `addresses` edge so the same schema ingests donor-style funding docs *and* organisation-internal inclusion prose [11][12][18]. This is a clean fit for creel's "freeform-or-constrained typed attributes."

5. **Exploit the standards as ready-made verifiers and reference anchors.** The standard's `reference(@vocabulary,@code,@uri)` and purpose/sector codes give creel an *external ground truth* to link extracted indicators/sectors to — feeding the auditability/traceability goal: every extracted indicator can be cross-checked against a published codelist [10][12].

6. **Separate the "graph definition" layer from the "extraction metadata" exactly along the standard's seams.** The node/edge *grammar* (results-framework + standard shapes) is reusable across all donors and operations; the *extractor strategies* (prose vs results-matrix table vs indicator table — see Docs A/B/C) differ per source type. The three sample docs are designed to validate that the same `graph_spec` joins cleanly with three different extractor sets.

## Recommendation

**Bundle a single canonical `graph_spec` — "rbm" — whose node/edge grammar is the generic results spine (impact/outcome/output + objectives/projects + donors + cross-cutting areas) and whose indicator-bearing and funding-bearing *edges* adopt the standard funding/results data model (result/indicator/baseline/period and transaction) attribute-for-attribute, with 0/1/2 policy markers as the cross-cutting edge attribute.** Rationale: these are not arbitrary modelling choices — they are the *de facto and de jure standards that RBM documents are themselves written against*. Reusing them (a) makes the bundled schema demonstrably faithful and auditable, (b) gives creel free interoperability with the wider donor-data ecosystem (the eventual persistence/graph-RAG/reporting downstream), and (c) embodies creel's own posture — single source of truth, physical separation of definition vs extraction metadata, strategy pattern, progressive disclosure. Build the three synthetic documents above into the test corpus immediately; they exercise prose, table-query, and functional extractors against one shared spec and will catch schema-join regressions early. **One caveat to resolve before production:** the exact wording/numbering of a target organisation's outcome and enabling areas should be re-verified against its current official results-framework codelist, since labels evolve across editions.

## References

1. [INTRAC — *Results-Based Management* (guidance paper, 2024 ed.)](https://www.intrac.org/app/uploads/2024/12/Results-based-Management.pdf)
2. [Adaptation Fund — *Results-Based Management Framework*](https://www.adaptation-fund.org/wp-content/uploads/2015/01/AFB.B.8.8_RBM.pdf)
3. *Results-Based Management Handbook* — a widely-used inter-agency RBM methodology handbook.
4. [BetterEvaluation — *Specify targets and baselines*](https://www.betterevaluation.org/methods-approaches/themes/monitoring)
5. *Glossary of Key Terms in Evaluation and Results-Based Management* — the standard evaluation/RBM terminology reference.
6. *Open activity-data standard — indicator element reference (results data)* — the public results-data model creel's indicator edges mirror.
7. *Open activity-data standard — financial-transactions guidance* — the public funding-transaction model creel's `funds` edges mirror.
8. [tools4dev — *Logframe vs Theory of Change: What's the difference?*](https://tools4dev.org/blog/logframe-vs-theory-of-change-whats-the-difference/)
9. [UNEG — *Norms and Standards for Evaluation*](http://www.unevaluation.org/document/detail/1914)
10. *Open activity-data standard — understanding results data* — guidance on the public results-data model.
11. *Policy-marker guidance — the gender-equality policy marker* — the standard 0/1/2 marker creel models as a cross-cutting edge attribute.
12. [*Handbook on the Gender Equality Policy Marker*](https://canwach.ca/wp-content/uploads/2020/10/Handbook-Gender-Equality-Policy-Marker.pdf)
13. [EvalCommunity — *SMART Indicators in Monitoring and Evaluation (M&E)*](https://www.evalcommunity.com/career-center/smart-indicators/)
14. [BetterEvaluation — *Develop a theory of change / programme theory*](https://www.betterevaluation.org/methods-approaches/themes/develop-programme-theory-theory-change)
15. [UNEG — *Enabling and support functions in results frameworks*](http://www.unevaluation.org/document/library)
16. *Open activity-data standard — traceability guidance* — provenance/traceability conventions in the public funding-data model.
17. [Climate/biodiversity marker handbook — *Rio Markers for Climate*](https://wwflac.awsassets.panda.org/downloads/rio_marker___revised_climate_marker_handbook_final.pdf)
18. [BetterEvaluation — *Accountability and inclusive programming*](https://www.betterevaluation.org/methods-approaches/themes/equity-focused-evaluation)
19. *Development co-operation guidance — Mainstreaming cross-cutting issues* — rationale for cross-cutting areas as first-class graph entities.
