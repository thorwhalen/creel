# 11 — Results-based management & logframe domain (UNHCR)

> **TL;DR.** Creel's first consumer — extracting a graph of donors, objectives, cross-cutting areas, projects, outputs, outcomes and indicators from UNHCR ESA documents — sits squarely inside a mature, internationally-standardised domain: **Results-Based Management (RBM)**. Three layers of standards already define almost every node and edge type creel needs. (1) The generic **results chain** (inputs → activities → outputs → outcomes → impact) and its tabular expression, the **logframe**, both downstream of a **Theory of Change** [1][2][8]. (2) **UNHCR's COMPASS / Global Results Framework (GRF)**, a concrete RBM taxonomy of *4 impact areas, 16 outcome areas, 5 enabling areas* with **76 core indicators** at impact/outcome/output levels [3][4][5][9]. (3) Donor/funding standards — the **IATI Activity Standard** (results + transactions data model) and **OECD-DAC policy markers** (gender, environment, Rio markers, scored 0/1/2) — which give us a ready-made vocabulary for *funding amounts on edges*, *indicator values on edges*, and *cross-cutting markers as edge attributes* [6][7][10][11][12]. The strongest design move for creel is to **adopt the IATI result/indicator/period model verbatim for indicator-bearing edges, and the COMPASS impact/outcome/output taxonomy as the default node grammar**, so the UNHCR use case ships with a faithful, auditable schema out of the box rather than a hand-rolled one.

## Background / landscape

**Results-Based Management (RBM)** is a management strategy by which organisations ensure that their processes, products and services contribute to the achievement of clearly stated *results*. Its planning backbone, the **logical framework ("logframe")**, was adopted by USAID from the US Department of Defense in the 1960s and scaled across UN agencies and NGOs from the 1990s onward [1]. The logframe is built on a *hierarchy of levels* linking inputs, activities, outputs, outcomes and goals, with an assumed cause-and-effect relationship where lower levels contribute to those above [1][2].

The conceptual spine of RBM is the **results chain**: *the sequence of results considered necessary to achieve desired objectives, beginning with inputs, used to carry out activities and deliver outputs, designed to help bring about outcomes that eventually contribute to the desired impact* [1]. The chain splits naturally into two halves: the *implementation* segment (inputs, activities — what the organisation controls) and the *results* segment (outputs = operational results; outcomes = development results; impact = long-term change it only contributes to) [1].

A **Theory of Change (ToC)** sits *upstream* of the logframe: it articulates the assumptions, causal pathways and mechanisms — the "missing middle" — by which activities are expected to produce long-term change, working *backward* from goals to the conditions that must hold, and making external factors and assumptions explicit [8]. The widely-cited relationship is: **"The Theory of Change is the basis upon which we design a results chain and logframe, not the other way around"** [8]. A ToC is non-linear and holistic (multiple pathways, actors, assumptions); a logframe is a linear, tabular *what* derived from it [8].

**Indicators** are the measurement layer. The canonical quality bar is **SMART** — Specific, Measurable, Achievable, Relevant, Time-bound [13]. In logframe practice an *Objectively Verifiable Indicator (OVI)* names *who, by how much, by when, and verified how* [13]. Each indicator carries a **baseline** (a starting value, captured before the intervention, with the year/date taken), a **target** (the value to reach by a date), an **actual** (the measured value), and **means of verification (MoV)** — the instrument, who collects it, and how often [13]. These four constructs (baseline / target / actual / MoV) are universal across RBM systems and map directly onto IATI's data model (below).

**UNHCR** operationalises all of this through **COMPASS**, its RBM approach (aligned with the *Strategic Directions 2022–2026*), under which every strategy moves through three phases — **PLAN for results, GET results, SHOW results** — with the PLAN phase producing a situation analysis, vision, **theory of change**, a *costed results framework*, and an M&E plan [3][9][14]. COMPASS tracks results through a simplified chain aligned to the UN system of **impacts, outcomes and outputs**, and "strategies operate at three results levels: output, outcome and impact" [3][9].

## Comparative analysis

### The three vocabularies creel must reconcile

| Layer | Source | Node-ish concepts | Edge-ish / measurement concepts | Recency |
|---|---|---|---|---|
| Generic RBM / logframe | INTRAC, tools4dev, eval literature | inputs, activities, outputs, outcomes, impact/goal; objectives | indicators (SMART/OVI), baseline, target, MoV, assumptions/risks | INTRAC guide updated 2024 [1]; evergreen concepts [13] |
| UNHCR COMPASS / GRF | UNHCR Programme Handbook, Assessment & Monitoring Resource Centre | impact areas (4), outcome areas (16), enabling areas (5), objectives, strategy, operation | 76 core impact/outcome/output indicators; baselines & targets (impact indicators carry *no* target) [4][5] | GRF current under Strategic Directions 2022–2026 [3][9] |
| Donor / funding standards | IATI Activity Standard 2.03; OECD-DAC | activity, participating-org (funding/accountable/extending/implementing), result (output/outcome/impact) | transaction (commitment/disbursement, value, currency, provider-org→receiver-org); result→indicator→baseline→period(target/actual); DAC policy markers (0/1/2) | IATI 2.03 current [6][7][10]; DAC GEM handbook current [11][12] |

### Results-chain levels: terminology crosswalk

| Results chain [1] | Logframe row [2] | UNHCR COMPASS [3][9] | IATI result `@type` [10] | Controlled by | Typical indicator |
|---|---|---|---|---|---|
| Impact | Goal / overall objective | **Impact statement** (impact area) | `3` (impact) | Society (contribution only) | rights-level; **no target** in COMPASS [4] |
| Outcome | Purpose / specific objective | **Outcome statement** (outcome area) | `2` (outcome) | Partly (contributes to) | target vs baseline |
| Output | Output / result | **Output statement** | `1` (output) | Yes (delivers) | target vs baseline |
| Activity | Activity | (activity / sub-output) | — (activity-level) | Yes | process/milestone |
| Input | Input / means | budget / resources | transaction `value` | Yes | cost |

This crosswalk is the single most important asset for creel: it shows the **same five-level spine** under three names, so a creel `graph_spec` can use one canonical taxonomy and treat the others as label aliases.

### UNHCR Global Results Framework — the concrete taxonomy

**Four impact areas** (from the four Strategic Directions 2022–2026) [3][5][9]:

1. **Protect** — protect, secure and defend the rights of forcibly displaced and stateless people.
2. **Respond** — respond rapidly and effectively in emergencies and beyond.
3. **Empower** — empower the people served to determine and build their futures.
4. **Solve** — pursue solutions to displacement and statelessness.

**Sixteen outcome areas** [5] (verify against the official GRF before production use; list assembled from UNHCR Global Focus / Global Report taxonomy):

1. Access to territory, registration and documentation; 2. Status determination; 3. Protection policy and law; 4. Gender-based violence; 5. Child protection; 6. Safety and access to justice; 7. Community engagement and women's empowerment; 8. Well-being and basic needs; 9. Sustainable housing and settlements; 10. Healthy lives; 11. Education; 12. Clean water, sanitation and hygiene (WASH); 13. Self-reliance, economic inclusion and livelihoods; 14. Voluntary repatriation and sustainable reintegration; 15. Resettlement and complementary pathways; 16. Local integration and other local solutions.

**Five enabling areas** (EA 17–21) — UNHCR's management/support work [5][15]:

- EA 17 **Systems and processes**; EA 18 **Operational support and supply chain**; EA 19 **People and culture**; EA 20 **External engagement and resource mobilization**; EA 21 **Leadership and governance**.

**Measurement convention:** COMPASS includes **76 core indicators** spanning impact, outcome and output levels [9]. Critically, **impact indicators do not require targets** (they are at the level of *rights*), whereas operations *do* set targets for outcome and output indicators, tracked against a **baseline** established for the strategy [4]. This asymmetry must be modelled — a creel indicator-attribute schema cannot assume every indicator has a target.

### IATI Activity Standard — the funding & results data model

IATI gives creel a battle-tested, machine-readable model for exactly the two things the ESA use case puts *on edges*: **funding amounts** and **indicator values**.

**Funding (transactions).** An `iati-activity` lists **participating-org**s with one of four roles — **funding, accountable, extending, implementing** [7]. Money flows are **transaction**s; the standard distinguishes *commitments* (the promise of money) from *disbursements/incoming funds* (the actual transfer), each with a **value** (positive/negative, decimal), **currency**, and **provider-org → receiver-org**, optionally referencing the source/destination activity id for **traceability** [7][16]. `currency`, `finance-type`, `flow-type`, `aid-type` and `tied-status` can default at activity level [7].

**Results (indicators).** Each activity may contain many `result` elements (type `1`/`2`/`3` = output/outcome/impact), each containing one or more `indicator`s [10]. The `indicator` element's structure is the gold standard for creel's indicator-bearing edges [6][10]:

```
result (@type: 1=output|2=outcome|3=impact)
  title, description
  indicator (@measure: unit|percentage|currency|qualitative;
             @ascending: true/false (is "up" good?);
             @aggregation-status)
    title, description
    reference (@vocabulary, @code, @indicator-uri)   # e.g. SDG indicator
    baseline (@year, @iso-date, @value) + location, dimension, comment
    period
      period-start, period-end
      target (@value) + dimension, location, comment
      actual (@value) + dimension, location, comment
```

Key modelling lessons for creel:
- An indicator value is **never a scalar** — it is a `(measure, baseline, target, actual, period, dimensions)` tuple. The `@measure` distinguishes count/percentage/currency/qualitative; `@ascending` encodes whether increase is good (essential for verification logic).
- **Disaggregation** is first-class: `dimension` elements break values down "by gender, age or sex" [10] — directly relevant to UNHCR's AGD requirement.
- `reference` links an indicator to an external framework (SDGs, the GRF itself), enabling the *auditability/traceability* creel prizes.

### OECD-DAC policy markers — cross-cutting areas as scored attributes

Cross-cutting themes (gender, environment, climate) are represented in donor data as **policy markers**, scored on a three-point scale per activity [11][12]:

| Score | Label | Meaning |
|---|---|---|
| **0** | Not targeted | Screened, no relevant element |
| **1** | Significant | An important, deliberate objective, but not the principal reason for the activity |
| **2** | Principal | The theme is the main objective; the activity would not exist without it |

Markers in scope include the **Gender Equality Policy Marker (GEM)** [11][12], the **environment** marker, and the four **Rio markers** (biodiversity, climate change mitigation, climate change adaptation, desertification) [17]. Markers are reported *at activity level* via the CRS reporting form alongside **CRS purpose/sector codes** [12][17]. The DAC recommends a *dual strategy*: targeted interventions (usually score 2) plus mainstreaming (usually score 1) [12].

UNHCR's own cross-cutting frame is **Age, Gender and Diversity (AGD)**, revised 2018, bundling inclusive programming, **Accountability to Affected People (AAP)**, and commitments to women and girls; UNHCR is integrating AGD dimensions *into COMPASS* for proposal assessment, monitoring and reporting [18][19]. So creel must represent cross-cutting areas in **two compatible idioms**: a *scored marker* (DAC 0/1/2, for donor docs) and a *categorical AGD/protection tag* (for UNHCR internal docs).

## Candidate node / edge taxonomy for creel

This taxonomy is opinionated for the UNHCR ESA use case but is deliberately a *recursive taxonomy* (per creel's `graph_spec` grammar): `Impact > Outcome > Output` are subdivisions of one **Result** node-type; impact/outcome/enabling *areas* are a recursively-subdivided controlled vocabulary.

### Node types

| Node type | Subdivides into | Key typed attributes | Source of truth |
|---|---|---|---|
| **Donor** | (bilateral, multilateral, private, pooled-fund) | name, IATI org-id, role∈{funding, accountable, extending, implementing} | IATI participating-org [7] |
| **Objective / Strategy** | impact-area → outcome-area | level∈{impact,outcome,output}, area-code (GRF), statement (freeform), strategy-period | COMPASS [3][5] |
| **CrossCuttingArea** | AGD (age,gender,diversity); environment; protection; AAP | kind∈{gender,environment,climate,protection,AAP}, dac_marker∈{0,1,2}, rio_marker? | DAC markers [11][17] + AGD [18] |
| **Project / Activity** | (sub-activities) | title, iati-activity-id, country/location (ESA), start/end, budget, currency, sector(CRS) | IATI activity [7] |
| **Output** | — | output-statement, GRF output-area, responsible-org | COMPASS/IATI [4][10] |
| **Outcome** | — | outcome-statement, GRF outcome-area | COMPASS [4] |
| **Indicator** | impact/outcome/output indicator | name, measure∈{unit,%,currency,qualitative}, ascending?, disaggregation[], MoV, reference(SDG/GRF) | IATI indicator [6][10] |

### Edge types (edges are first-class, carry typed attributes)

| Edge type | From → To | Edge attributes (the payload) | Standard basis |
|---|---|---|---|
| **funds** | Donor → Project | amount (decimal), currency, transaction_type∈{commitment,disbursement}, value_date, period | IATI transaction [7][16] |
| **delivers** | Project → Output | quantity, period, responsible-org | results chain [1] |
| **contributes-to** | Output → Outcome | contribution_weight?, assumption/risk note | results chain [1][8] |
| **advances** | Outcome → Objective/Impact-area | (contribution only; impacts have no target) | COMPASS [4] |
| **addresses** | Project/Output → CrossCuttingArea | dac_marker∈{0,1,2}, rationale | DAC markers [11][12] |
| **measured-by** | {Outcome,Output,Impact} → Indicator | **baseline(value,year)**, **target(value,date)**, **actual(value,period)**, measure, disaggregation | IATI result/indicator/period [10] |
| **aligned-to** | Indicator → external framework | vocabulary∈{SDG,GRF}, code, uri | IATI reference [10] |

Note that **indicator values and funding amounts live on edges** (`measured-by` and `funds` respectively), exactly as creel's brief requires — and both are *temporal tuples*, not scalars, because IATI's `period` and `transaction` models are inherently time-indexed.

## Synthetic-but-realistic example documents (test corpus seeds)

These are **synthetic** (invented values/orgs) but structured to mirror real UNHCR/IATI/DAC artefacts. They exercise all three extractor strategies: prose (donor agreement), table (results matrix), table (indicator table).

### Doc A — Donor agreement excerpt (freeform prose → tests LLM extractor)

> **Contribution Agreement — Schedule 1**
> The **Kingdom of Norway** (the "Donor", IATI org-id `NO-BRC-971277882`) agrees to provide an **earmarked contribution of USD 4,500,000** to **UNHCR** (the "Recipient") for the period **1 January 2025 – 31 December 2026** in support of the **East and Horn of Africa, and Great Lakes Region** operation. Of this amount, **USD 2,000,000 is committed** upon signature, with the balance disbursed in two tranches subject to satisfactory reporting. Funds shall support activities under outcome area **Gender-based violence (OA4)** and **Child protection (OA5)**. The intervention is classified **Gender Equality Policy Marker = 2 (principal)** and **Environment marker = 0**. The Donor's role is *funding*; UNHCR acts as *accountable* and *implementing* organisation. Reporting follows UNHCR COMPASS; a results matrix (Schedule 2) is attached.

*Expected graph:* Donor(Norway) —funds[amount=4.5M USD, commitment=2.0M, period=2025–2026]→ Project(ESA GBV/CP); Project —addresses[dac_marker=2]→ CrossCuttingArea(gender); links to Outcome(OA4), Outcome(OA5).

### Doc B — Project results matrix (table → tests SQL-like extractor)

| Level | Statement | GRF area | Responsible | Linked to |
|---|---|---|---|---|
| Impact | Forcibly displaced persons in ESA enjoy improved protection from violence | Protect | UNHCR | — |
| Outcome 1 | Survivors of GBV have timely access to quality response services | OA4 GBV | UNHCR + IRC | Impact |
| Output 1.1 | GBV case-management workers trained and deployed in 12 sites | OA4 | IRC | Outcome 1 |
| Output 1.2 | Safe spaces for women and girls established and operational | OA4 | UNHCR | Outcome 1 |
| Outcome 2 | Unaccompanied and separated children receive appropriate care | OA5 CP | Save the Children | Impact |
| Output 2.1 | Best-interests procedures applied for identified UASC | OA5 | Save the Children | Outcome 2 |

### Doc C — Indicator table (table → tests query + functional extractors; values on edges)

| Indicator | Level | Measure | Ascending | Baseline (2024) | Target (2026) | Actual (mid-2025) | Disagg. | MoV |
|---|---|---|---|---|---|---|---|---|
| % of GBV survivors receiving services within 72h | Outcome 1 | percentage | true | 45% | 80% | 62% | sex, age | Case-mgmt database (quarterly) |
| # of safe spaces operational | Output 1.2 | unit | true | 3 | 12 | 9 | location | Site monitoring report (monthly) |
| # of GBV workers trained | Output 1.1 | unit | true | 0 | 240 | 180 | sex | Training records (per cohort) |
| # of UASC with active BIA | Output 2.1 | unit | true | 120 | 600 | 410 | sex, age | proGres registration (continuous) |
| % UASC in family-based care | Outcome 2 | percentage | true | 30% | 70% | 48% | age | Child-protection IMS (quarterly) |

*Each row becomes a `measured-by` edge whose attributes are the baseline/target/actual tuple — directly mirroring IATI `indicator/baseline` + `period/target` + `period/actual` [10].*

## Design implications for creel

1. **Ship the COMPASS taxonomy and IATI indicator model as the default `graph_spec` for the UNHCR use case — do not hand-roll.** The 4 impact / 16 outcome / 5 enabling areas are a *recursively subdivided taxonomy with controlled-vocabulary codes* (OA1–16, EA17–21), which is exactly creel's `graph_spec` grammar. Encoding them as the bundled default delivers progressive disclosure: a user pointing creel at ESA docs gets a faithful schema for free [3][4][5].

2. **Model indicator values as temporal tuples on edges, never as scalars.** Adopt IATI's `(measure, ascending, baseline{value,year}, target{value,date}, actual{value,period}, dimensions[])` shape verbatim for the `measured-by` edge's attribute schema [10]. The `@ascending` flag and `@measure` enum are essential for any *verification* extractor (you can't check "on track" without knowing whether up is good and whether the unit is count/%/currency).

3. **Make `target` optional and level-aware.** COMPASS impact indicators carry **no target** by design [4]. The constrained-attribute layer must allow `target = null` at impact level — a hard "required target" constraint would reject valid UNHCR data.

4. **Represent cross-cutting areas as a dual-idiom node + a scored `addresses` edge.** Carry both the DAC marker (`0/1/2` ordinal) and the categorical AGD/protection tag on the `addresses` edge so the same schema ingests donor CRS-style docs *and* UNHCR AGD prose [11][12][18]. This is a clean fit for creel's "freeform-or-constrained typed attributes."

5. **Exploit the standards as ready-made verifiers and reference anchors.** IATI's `reference(@vocabulary,@code,@uri)` and CRS purpose codes give creel an *external ground truth* to link extracted indicators/sectors to — feeding the auditability/traceability goal: every extracted indicator can be cross-checked against the GRF/SDG codelist [10][12].

6. **Separate the "graph definition" layer from the "extraction metadata" exactly along the standard's seams.** The node/edge *grammar* (COMPASS+IATI shapes) is reusable across all donors and operations; the *extractor strategies* (prose vs results-matrix table vs indicator table — see Docs A/B/C) differ per source type. The three sample docs are designed to validate that the same `graph_spec` joins cleanly with three different extractor sets.

## Recommendation

**Bundle a single canonical `graph_spec` — "unhcr-rbm" — whose node/edge grammar is the COMPASS results spine (impact/outcome/output + objectives/projects + donors + cross-cutting areas) and whose indicator-bearing and funding-bearing *edges* adopt the IATI Activity Standard data model (result/indicator/baseline/period and transaction) attribute-for-attribute, with OECD-DAC 0/1/2 markers as the cross-cutting edge attribute.** Rationale: these are not arbitrary modelling choices — they are the *de facto and de jure standards the UNHCR ESA documents are themselves written against*. Reusing them (a) makes the bundled schema demonstrably faithful and auditable, (b) gives creel free interoperability with the entire IATI/OECD donor-data ecosystem (the eventual persistence/graph-RAG/reporting downstream), and (c) embodies creel's own posture — single source of truth, physical separation of definition vs extraction metadata, strategy pattern, progressive disclosure. Build the three synthetic documents above into the test corpus immediately; they exercise prose, table-query, and functional extractors against one shared spec and will catch schema-join regressions early. **One caveat to resolve before production:** the exact wording/numbering of the 16 outcome and 5 enabling areas should be re-verified against the current official GRF codelist (the UNHCR site blocks automated fetch; obtain the GRF PDF or codelist directly), since labels evolve across Global Appeal editions.

## References

1. [INTRAC — *Results-Based Management* (guidance paper, 2024 ed.)](https://www.intrac.org/app/uploads/2024/12/Results-based-Management.pdf)
2. [Adaptation Fund — *Results-Based Management Framework*](https://www.adaptation-fund.org/wp-content/uploads/2015/01/AFB.B.8.8_RBM.pdf)
3. [UNHCR — *COMPASS*](https://www.unhcr.org/what-we-do/build-better-futures/compass)
4. [UNHCR Assessment & Monitoring Resource Centre — *Global Results Framework*](https://www.unhcr.org/handbooks/assessment/design/defining-analytical-framework/global-results-framework)
5. [UNHCR — *UNHCR's Results Areas (A4)*](https://www.unhcr.org/sites/default/files/2023-05/UNHCR%20Results%20Areas_A4.pdf)
6. [IATI Standard 2.03 — *indicator* element reference](https://iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/result/indicator/)
7. [IATI — *Financial transactions* guidance](https://iatistandard.org/en/guidance/standard-guidance/financial-transactions/)
8. [tools4dev — *Logframe vs Theory of Change: What's the difference?*](https://tools4dev.org/blog/logframe-vs-theory-of-change-whats-the-difference/)
9. [UNHCR Programme Partner Hub — *PLAN Section 5: Multi-Year Results Framework*](https://www.unhcr.org/handbooks/programme-partnerhub/unhcr-programme-handbook-partners/plan-results/plan-section-5-multi-year-results-framework)
10. [IATI — *Understanding results data* guidance](https://iatistandard.org/en/guidance/standard-guidance/understanding-results/)
11. [OECD-DAC — *The DAC gender equality policy marker*](https://www.oecd.org/dac/gender-development/thedacgenderequalitypolicymarker.htm)
12. [OECD-DAC — *Handbook on the OECD-DAC Gender Equality Policy Marker*](https://canwach.ca/wp-content/uploads/2020/10/Handbook-OECD-DAC-Gender-Equality-Policy-Marker.pdf)
13. [EvalCommunity — *SMART Indicators in Monitoring and Evaluation (M&E)*](https://www.evalcommunity.com/career-center/smart-indicators/)
14. [UNHCR Programme Partner Hub — *PLAN Section 4: Vision, Strategic Priorities and the Theory of Change*](https://www.unhcr.org/handbooks/programme-partnerhub/unhcr-programme-handbook-partners/plan-results/plan-section-4-vision-strategic-priorities-and-theory-change)
15. [UNHCR Global Focus — *Enabling Areas (Global Report 2023)*](https://reporting.unhcr.org/global-report-2023/enabling-areas)
16. [IATI — *Traceability* guidance](https://iatistandard.org/en/guidance/standard-guidance/traceability/)
17. [OECD-DAC — *Rio Markers for Climate: Handbook*](https://wwflac.awsassets.panda.org/downloads/rio_marker___revised_climate_marker_handbook_final.pdf)
18. [UNHCR — *Age, Gender and Diversity (AGD)* (Emergency Handbook)](https://emergency.unhcr.org/protection/protection-principles/age-gender-and-diversity-agd)
19. [UNHCR — *Age, Gender and Diversity Accountability Report 2024*](https://www.unhcr.org/sites/default/files/2025-06/age-gender-and-diversity-accountability-report-2024.pdf)
