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
from creel.evidence import CellSelector, deterministic_evidence
from creel.extract.pattern import _slug
from creel.extract.protocol import ExtractedEdge, ExtractedNode, Extraction
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


# --- function extractors for the two tables -----------------------------------
def _results_matrix_extractor(ctx) -> Extraction:
    """Emit outputs/outcomes (nodes) and delivers/contributes_to (edges) per element."""
    rows = ctx.sources.get("results_matrix").content
    nodes, edges = [], []
    for i, row in enumerate(rows):
        proj = f"project:{_slug(row['project_code'])}"
        outp = f"output:{_slug(row['output_code'])}"
        outc = f"outcome:{_slug(row['outcome_code'])}"
        ev = lambda col: deterministic_evidence(
            source_id="results_matrix", generated_by=f"function:results_matrix:{ctx.element_id}",
            grounding=(CellSelector("results_matrix", i, col),))
        if ctx.element_id == "output":
            nodes.append(ExtractedNode(outp, "output", {"statement": row["output_statement"]}, ev("output_statement")))
        elif ctx.element_id == "outcome":
            nodes.append(ExtractedNode(outc, "outcome", {"statement": row["outcome_statement"]}, ev("outcome_statement")))
        elif ctx.element_id == "delivers":
            edges.append(ExtractedEdge(f"delivers:{i}", "delivers", proj, outp, {}, ev("project_code")))
        elif ctx.element_id == "contributes_to":
            edges.append(ExtractedEdge(f"contributes_to:{i}", "contributes_to", outp, outc, {}, ev("outcome_code")))
    return Extraction(nodes=nodes, edges=edges)


def _indicators_extractor(ctx) -> Extraction:
    """Emit indicator nodes and measured_by edges (with baseline/target/actual values)."""
    rows = ctx.sources.get("indicators").content
    nodes, edges = [], []
    for i, row in enumerate(rows):
        ind = f"indicator:{_slug(row['indicator_code'])}"
        outp = f"output:{_slug(row['output_code'])}"
        ev = lambda col: deterministic_evidence(
            source_id="indicators", generated_by=f"function:indicators:{ctx.element_id}",
            grounding=(CellSelector("indicators", i, col),))
        if ctx.element_id == "indicator":
            nodes.append(ExtractedNode(ind, "indicator",
                                       {"name": row["indicator_name"], "measure": row["measure"]}, ev("indicator_name")))
        elif ctx.element_id == "measured_by":
            edges.append(ExtractedEdge(f"measured_by:{i}", "measured_by", outp, ind, {
                "baseline": int(row["baseline"]), "target": int(row["target"]),
                "actual": int(row["actual"]), "period": row["period"],
            }, ev("actual")))
    return Extraction(nodes=nodes, edges=edges)


# --- bindings -----------------------------------------------------------------
def build_bindings() -> dict:
    """Map each grammar element to its extractor strategy (the metadata layer)."""
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
        # results matrix -> one function extractor bound to each element it produces
        "output": _results_matrix_extractor,
        "outcome": _results_matrix_extractor,
        "delivers": _results_matrix_extractor,
        "contributes_to": _results_matrix_extractor,
        # indicators -> one function extractor bound to each element it produces
        "indicator": _indicators_extractor,
        "measured_by": _indicators_extractor,
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
