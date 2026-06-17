"""The UNHCR RBM mini-corpus: grammar, extractors, expected graph & verifiers.

This is creel's first-consumer integration fixture (decision D14, EPIC 7). It models
a faithful slice of the UNHCR results model — donors, projects, cross-cutting areas,
outputs, outcomes, indicators, with funding amounts and indicator values **on
edges** — and extracts it from three synthetic-but-realistic sources using all the
deterministic strategy families available today:

- a prose donor agreement  -> ``regex_node`` / ``regex_edge`` (donors, projects,
  cross-cutting areas; ``funds`` and ``addresses`` edges);
- a results matrix CSV      -> a ``function`` extractor (outputs, outcomes;
  ``delivers`` / ``contributes_to`` edges);
- an indicators CSV         -> a ``function`` extractor (indicators; ``measured_by``
  edges carrying baseline/target/actual values).

It graduates to the ``creel-unhcr`` package at v0.4. The expected graph lives in
``expected_graph.json``; regenerate it with ``python -m tests.data.unhcr.corpus``
(or by running this file) after an intentional grammar/extractor change.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from creel.evaluation import CorpusCase
from creel.graph.canonical import from_canonical_json
from creel.sources import TABLE, TEXT, Source, SourceBundle
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
            EdgeType("measured_by", subject_type="result", object_type="indicator", attributes=(
                AttrSchema("baseline", range="decimal"),
                AttrSchema("target", range="decimal"),
                AttrSchema("actual", range="decimal"),
                AttrSchema("period", range="string"),
            )),
        ),
    )


# --- sources ------------------------------------------------------------------
def load_sources() -> SourceBundle:
    """Load the three source docs (prose kept as text; CSVs parsed into row dicts)."""
    prose = Source("donor_agreement", (SOURCES / "donor_agreement.md").read_text(), kind=TEXT)
    matrix = Source("results_matrix", _read_csv(SOURCES / "results_matrix.csv"), kind=TABLE)
    indicators = Source("indicators", _read_csv(SOURCES / "indicators.csv"), kind=TABLE)
    return SourceBundle([prose, matrix, indicators])


def _read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(io.StringIO(path.read_text())))


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
        # indicators CSV -> declarative table_map
        "indicator": ("table_map", {
            "records_source": "indicators", "kind": "node", "type": "indicator",
            "id_template": "indicator:{indicator_code}",
            "attributes": {"name": "indicator_name", "measure": "measure"}}),
        "measured_by": ("table_map", {
            "records_source": "indicators", "kind": "edge", "type": "measured_by",
            "source_template": "output:{output_code}", "target_template": "indicator:{indicator_code}",
            "attributes": {"baseline": "baseline", "target": "target", "actual": "actual", "period": "period"},
            "casts": {"baseline": "int", "target": "int", "actual": "int"}}),
    }


# --- per-attribute verifier overrides (numeric_tolerance for amounts/values) --
def attribute_verifiers() -> dict:
    """Attach the right verifier kind to each value-bearing attribute (by taxonomy path)."""
    num = NumericTolerance()
    return {
        ("funds", "amount"): num,
        ("addresses", "marker"): ExactMatch(),
        ("measured_by", "baseline"): num,
        ("measured_by", "target"): num,
        ("measured_by", "actual"): num,
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
