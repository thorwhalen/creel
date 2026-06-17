"""Tests for bidirectional traceability: per-attribute grounding, reverse index, reanchor."""

from creel.evidence import (
    CellSelector,
    TextPositionSelector,
    TextQuoteSelector,
    deterministic_evidence,
)
from creel.graph.model import Graph
from creel.trace import (
    TraceIndex,
    attribute_evidence,
    reanchor,
    set_attribute_evidence,
    verify_anchor,
)


def test_per_attribute_grounding_a1():
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "Gov X", "dac_code": "301"})
    ev = deterministic_evidence(source_id="s", generated_by="t")
    set_attribute_evidence(g, "d:1", "dac_code", ev)
    assert attribute_evidence(g, "d:1", "dac_code") is ev
    # fallback to element-level evidence when no per-attribute record exists
    g.evidence["d:1"] = ev
    assert attribute_evidence(g, "d:1", "name") is ev


def test_reverse_trace_index_a3():
    g = Graph()
    g.add_node("d:1", types=("donor",))
    g.add_node("p:1", types=("project",))
    g.evidence["d:1"] = deterministic_evidence(
        source_id="doc", generated_by="t",
        grounding=(TextPositionSelector(start=10, end=20, source_id="doc"),))
    g.evidence["p:1"] = deterministic_evidence(
        source_id="doc", generated_by="t",
        grounding=(TextPositionSelector(start=30, end=45, source_id="doc"),))
    g.evidence["row:1"] = deterministic_evidence(
        source_id="tbl", generated_by="t", grounding=(CellSelector("tbl", 2, "amount"),))

    idx = TraceIndex(g)
    assert idx.elements_at("doc", 15) == ["d:1"]        # offset 15 falls in d:1's span
    assert idx.elements_at("doc", 25) == []             # gap between spans
    assert idx.elements_overlapping("doc", 18, 35) == ["d:1", "p:1"]
    assert idx.elements_in_cell("tbl", 2, "amount") == ["row:1"]


def test_reanchor_unique_and_context_disambiguation_a4():
    # quote moved (text changed upstream) -> exact match relocates it
    sel = TextQuoteSelector(exact="Government of Norway", prefix="Donor: ", suffix=" (DAC")
    text = "Intro paragraph added.\n\nDonor: Government of Norway (DAC 301)."
    span = reanchor(sel, text)
    assert span is not None and text[span[0]:span[1]] == "Government of Norway"
    # disambiguate two occurrences by prefix context
    sel2 = TextQuoteSelector(exact="Norway", prefix="of ", suffix="")
    text2 = "Norway. The Government of Norway funds it."
    s = reanchor(sel2, text2)
    assert text2[s[0]:s[1]] == "Norway" and s[0] > 10  # picked the 'of Norway' one


def test_verify_and_fuzzy_fallback():
    sel = TextQuoteSelector(exact="clean water access")
    assert verify_anchor(sel, "indicator: clean water access") is True
    assert verify_anchor(sel, "something else entirely") is False
    # fuzzy fallback when the quote changed slightly (re-OCR)
    span = reanchor(TextQuoteSelector(exact="clean water access"), "clean water acess here", fuzzy=True)
    assert span is not None
    assert reanchor(TextQuoteSelector(exact="zzzzz nowhere"), "unrelated text", fuzzy=True) is None
