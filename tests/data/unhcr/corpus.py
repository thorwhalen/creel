"""The UNHCR RBM mini-corpus: grammar, extractors, expected graph & verifiers.

This is creel's first-consumer integration fixture (decision D14, EPIC 7). It models
a faithful slice of the UNHCR results model — donors, projects, cross-cutting areas,
outputs, outcomes, indicators, and **AGD-disaggregated readings** — with funding
amounts **on edges** and indicator values on reified **reading nodes** (decision #12:
a disaggregated reading is n-ary, so it is promoted to a node sliceable by
sex/age/location). It extracts from four synthetic-but-realistic sources using the
deterministic strategy families available today:

- a prose donor agreement  -> ``regex_node`` / ``regex_edge`` (donors, projects,
  cross-cutting areas; ``funds`` and ``addresses`` edges);
- a results matrix CSV      -> ``table_map`` (outputs, outcomes; ``delivers`` /
  ``contributes_to`` edges);
- an indicators CSV         -> ``table_map`` (indicator definition nodes);
- a readings CSV            -> ``table_map`` (AGD-disaggregated ``reading`` nodes +
  ``measures`` / ``assesses`` edges to the indicator and output).

It graduates to the ``creel-unhcr`` package at v0.4. The expected graph lives in
``expected_graph.json``; regenerate it with ``python -m tests.data.unhcr.corpus``
(or by running this file) after an intentional grammar/extractor change.
"""

from __future__ import annotations

from pathlib import Path

from creel.evaluation import CorpusCase
from creel.graph.canonical import from_canonical_json
from creel.ingest import ingest_paths
from creel.sources import SourceBundle
from creel.spec.model import AttrSchema, EdgeType, EnumDef, GraphSpec, NodeType
from creel.verify.kinds import ExactMatch, NormalizedMatch, NumericTolerance

DIR = Path(__file__).resolve().parent
SOURCES = DIR / "sources"
EXPECTED = DIR / "expected_graph.json"


# --- grammar ------------------------------------------------------------------
def build_spec() -> GraphSpec:
    """The ``unhcr-rbm`` mini grammar (COMPASS-flavoured taxonomy + IATI-shaped edges)."""
    return GraphSpec(
        id="unhcr-rbm",
        version="0.1.0",
        description="UNHCR results-based-management mini grammar (synthetic).",
        enums=(
            EnumDef("Currency", ("USD", "EUR", "CHF")),
            EnumDef("TransactionType", ("commitment", "disbursement")),
            EnumDef("Measure", ("number", "percentage")),
            # AGD disaggregation dimensions (age / gender / diversity) — UNHCR core.
            EnumDef("Sex", ("total", "female", "male", "other")),
            EnumDef("AgeGroup", ("total", "0-4", "5-11", "12-17", "18-59", "60plus")),
        ),
        node_types=(
            NodeType("result", abstract=True,
                     attributes=(AttrSchema("statement", required=True,
                                            description="The results statement (a measurable change)."),)),
            NodeType("outcome", is_a="result", description="A change in the lives of people of concern."),
            NodeType("output", is_a="result", description="A product or service delivered by a project."),
            NodeType("donor", attributes=(
                AttrSchema("name", required=True),
                AttrSchema("dac_code", pattern=r"^\d{3,5}$"),
            )),
            NodeType("project", attributes=(
                AttrSchema("title", required=True),
                AttrSchema("code", pattern=r"^PRJ-\d+$"),
            )),
            NodeType("indicator", attributes=(
                AttrSchema("name", required=True),
                AttrSchema("measure", range="Measure"),
            )),
            NodeType("cross_cutting_area", attributes=(AttrSchema("name", required=True),)),
            # A reified, AGD-disaggregated indicator READING (n-ary: indicator + output
            # + value + period + disaggregation). Promoted to a node (decision #12) so
            # readings can be sliced by sex/age/location and merged across periods.
            NodeType("reading", description="A disaggregated measurement of an indicator.",
                     attributes=(
                         AttrSchema("actual", range="decimal", required=True,
                                    description="The measured value for this disaggregation."),
                         AttrSchema("baseline", range="decimal"),
                         AttrSchema("target", range="decimal"),
                         AttrSchema("period", range="string",
                                    description="Reporting period, e.g. 2026-Q2."),
                         AttrSchema("sex", range="Sex"),
                         AttrSchema("age_group", range="AgeGroup"),
                         AttrSchema("location", range="string"),
                     )),
        ),
        edge_types=(
            EdgeType("funds", subject_type="donor", object_type="project", attributes=(
                AttrSchema("amount", range="decimal", required=True, minimum=0),
                AttrSchema("currency", range="Currency", required=True),
                AttrSchema("transaction_type", range="TransactionType", required=True),
            )),
            EdgeType("addresses", subject_type="project", object_type="cross_cutting_area",
                     attributes=(AttrSchema("marker", range="integer", required=True, minimum=0, maximum=2),)),
            EdgeType("delivers", subject_type="project", object_type="output"),
            EdgeType("contributes_to", subject_type="output", object_type="outcome"),
            # The reading's two participants (the n-ary relation, reified as a node):
            EdgeType("measures", subject_type="reading", object_type="indicator"),
            EdgeType("assesses", subject_type="reading", object_type="output"),
        ),
    )


# --- sources ------------------------------------------------------------------
def load_sources() -> SourceBundle:
    """Load the four source docs via the ingestion layer (route-by-format).

    ``ingest`` defaults each ``source_id`` to the file stem, so the bindings reference
    ``donor_agreement`` / ``results_matrix`` / ``indicators`` / ``readings`` by name.
    The ``.md`` becomes a text source; the ``.csv`` files become table sources.
    """
    return ingest_paths([
        SOURCES / "donor_agreement.md",
        SOURCES / "results_matrix.csv",
        SOURCES / "indicators.csv",
        SOURCES / "readings.csv",
    ])


# --- bindings -----------------------------------------------------------------
def build_bindings() -> dict:
    """Map each grammar element to its extractor strategy (the metadata layer).

    Prose elements use the pattern (regex) family; the two CSV tables use the
    declarative ``table_map`` query extractor — each binding is a pure-data spec.
    """
    return {
        # prose -> pattern extractors
        "donor": ("regex_node", {
            "pattern": r"Donor:\s*(?P<name>[A-Za-z ]+?)\s*\(DAC\s*(?P<dac_code>\d+)\)",
            "id_attribute": "name"}),
        "project": ("regex_node", {
            "pattern": r"Project:\s*(?P<title>[A-Za-z ]+?)\s*\((?P<code>PRJ-\d+)\)",
            "id_attribute": "code"}),
        "cross_cutting_area": ("regex_node", {
            "pattern": r"addresses (?P<name>[A-Za-z ]+?) \(marker", "id_attribute": "name"}),
        "funds": ("regex_edge", {
            "pattern": r"(?P<donor>[A-Za-z ]+?) (?:commits|disburses) (?P<currency>[A-Z]{3}) "
                       r"(?P<amount>[\d,]+) to (?P<project>PRJ-\d+) \((?P<transaction_type>commitment|disbursement)\)",
            "source_id_template": "donor:{donor}", "target_id_template": "project:{project}",
            "casts": {"amount": "int"}, "exclude_groups": ("donor", "project")}),
        "addresses": ("regex_edge", {
            "pattern": r"(?P<project>PRJ-\d+) addresses (?P<cca>[A-Za-z ]+?) \(marker (?P<marker>[0-2])\)",
            "source_id_template": "project:{project}", "target_id_template": "cross_cutting_area:{cca}",
            "casts": {"marker": "int"}, "exclude_groups": ("project", "cca")}),
        # results matrix CSV -> declarative table_map (pure-data specs)
        "output": ("table_map", {
            "records_source": "results_matrix", "kind": "node", "type": "output",
            "id_template": "output:{output_code}", "attributes": {"statement": "output_statement"}}),
        "outcome": ("table_map", {
            "records_source": "results_matrix", "kind": "node", "type": "outcome",
            "id_template": "outcome:{outcome_code}", "attributes": {"statement": "outcome_statement"}}),
        "delivers": ("table_map", {
            "records_source": "results_matrix", "kind": "edge", "type": "delivers",
            "source_template": "project:{project_code}", "target_template": "output:{output_code}"}),
        "contributes_to": ("table_map", {
            "records_source": "results_matrix", "kind": "edge", "type": "contributes_to",
            "source_template": "output:{output_code}", "target_template": "outcome:{outcome_code}"}),
        # indicators CSV -> indicator definition nodes
        "indicator": ("table_map", {
            "records_source": "indicators", "kind": "node", "type": "indicator",
            "id_template": "indicator:{indicator_code}",
            "attributes": {"name": "indicator_name", "measure": "measure"}}),
        # readings CSV -> AGD-disaggregated reading nodes + their two relation edges
        "reading": ("table_map", {
            "records_source": "readings", "kind": "node", "type": "reading",
            "id_template": "reading:{indicator_code}-{sex}-{age_group}-{location}-{period}",
            "attributes": {"actual": "actual", "baseline": "baseline", "target": "target",
                           "period": "period", "sex": "sex", "age_group": "age_group",
                           "location": "location"},
            "casts": {"actual": "int", "baseline": "int", "target": "int"}}),
        "measures": ("table_map", {
            "records_source": "readings", "kind": "edge", "type": "measures",
            "source_template": "reading:{indicator_code}-{sex}-{age_group}-{location}-{period}",
            "target_template": "indicator:{indicator_code}"}),
        "assesses": ("table_map", {
            "records_source": "readings", "kind": "edge", "type": "assesses",
            "source_template": "reading:{indicator_code}-{sex}-{age_group}-{location}-{period}",
            "target_template": "output:{output_code}"}),
    }


# --- per-attribute verifier overrides (numeric_tolerance for amounts/values) --
def attribute_verifiers() -> dict:
    """Attach the right verifier kind to each value-bearing attribute (by taxonomy path)."""
    num = NumericTolerance()
    return {
        ("funds", "amount"): num,
        ("addresses", "marker"): ExactMatch(),
        ("reading", "baseline"): num,
        ("reading", "target"): num,
        ("reading", "actual"): num,
        ("outcome", "statement"): NormalizedMatch(),
        ("output", "statement"): NormalizedMatch(),
    }


# --- the case -----------------------------------------------------------------
def build_case() -> CorpusCase:
    """Assemble the full :class:`CorpusCase` (loads the committed expected graph)."""
    expected = from_canonical_json(EXPECTED.read_text()) if EXPECTED.exists() else None
    return CorpusCase(
        name="unhcr-rbm",
        sources=load_sources(),
        spec=build_spec(),
        bindings=build_bindings(),
        expected_graph=expected,
        attribute_verifiers=attribute_verifiers(),
        on_missing_binding="skip",
    )


def regenerate_expected() -> str:
    """Run extraction and (re)write ``expected_graph.json``. Used to bootstrap/refresh."""
    from creel.facade import extract
    from creel.graph.canonical import to_canonical_json

    spec = build_spec()
    graph = extract(load_sources(), spec, build_bindings(), on_missing_binding="skip")
    text = to_canonical_json(graph, spec=spec)
    EXPECTED.write_text(text + "\n")
    return text


if __name__ == "__main__":  # pragma: no cover - regeneration helper
    print(regenerate_expected())
