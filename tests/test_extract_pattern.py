"""Tests for the pattern/function extractor family and evidence attachment."""

from creel.evidence import DETERMINISTIC, TextPositionSelector, TextQuoteSelector
from creel.extract.pattern import RegexEdgeExtractor, RegexNodeExtractor
from creel.extract.protocol import ExtractionContext
from creel.extract.registry import available_extractors, build_extractor
from creel.sources import Source, SourceBundle
from creel.spec.model import GraphSpec, NodeType


def _ctx(element_id, text):
    spec = GraphSpec(node_types=(NodeType(element_id),))
    return ExtractionContext(
        element_id=element_id,
        element_type=spec.element_type(element_id) or NodeType(element_id),
        sources=SourceBundle([Source("s1", text)]),
        spec=spec,
    )


def test_regex_node_extracts_attributes_and_stable_id():
    ex = RegexNodeExtractor(pattern=r"Donor:\s*(?P<name>.+)", id_attribute="name")
    out = ex(_ctx("donor", "Donor: Government X\nDonor: Foundation Y"))
    ids = [n.id for n in out.nodes]
    assert ids == ["donor:government-x", "donor:foundation-y"]
    assert out.nodes[0].attributes == {"name": "Government X"}


def test_regex_node_id_is_deterministic_across_runs():
    ex = RegexNodeExtractor(pattern=r"Donor:\s*(?P<name>.+)", id_attribute="name")
    ctx = _ctx("donor", "Donor: Government X")
    assert ex(ctx).nodes[0].id == ex(ctx).nodes[0].id == "donor:government-x"


def test_regex_node_casts_numbers():
    ex = RegexNodeExtractor(
        pattern=r"Amount:\s*(?P<amount>[\d,]+)", casts={"amount": "int"}, id_attribute="amount"
    )
    out = ex(_ctx("line", "Amount: 1,000,000"))
    assert out.nodes[0].attributes["amount"] == 1_000_000


def test_extraction_carries_deterministic_evidence_with_grounding():
    ex = RegexNodeExtractor(pattern=r"Donor:\s*(?P<name>.+)", id_attribute="name")
    node = ex(_ctx("donor", "Note. Donor: Government X")).nodes[0]
    ev = node.evidence
    assert ev is not None
    assert ev.confidence.method == DETERMINISTIC and ev.confidence.score == 1.0
    selectors = {type(s) for s in ev.grounding}
    assert TextQuoteSelector in selectors and TextPositionSelector in selectors
    quote = next(s for s in ev.grounding if isinstance(s, TextQuoteSelector))
    assert quote.exact == "Donor: Government X"


def test_regex_edge_builds_endpoints_and_excludes_ref_groups():
    text = "Government X funds Water programme with USD 1000000."
    ex = RegexEdgeExtractor(
        pattern=r"(?P<donor>[\w ]+?) funds (?P<project>[\w ]+?) with (?P<currency>[A-Z]{3}) (?P<amount>[\d,]+)",
        source_id_template="donor:{donor}",
        target_id_template="project:{project}",
        casts={"amount": "int"},
        exclude_groups=("donor", "project"),
    )
    edge = ex(_ctx("funds", text)).edges[0]
    assert edge.source == "donor:government-x"
    assert edge.target == "project:water-programme"
    assert edge.attributes == {"currency": "USD", "amount": 1_000_000}


def test_builtin_strategies_registered():
    assert {"regex_node", "regex_edge", "function"} <= set(available_extractors())
    ex = build_extractor("regex_node", pattern=r"(?P<x>\w+)")
    assert isinstance(ex, RegexNodeExtractor)
