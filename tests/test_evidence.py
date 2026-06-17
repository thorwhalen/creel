"""Tests for the evidence layer: grounding selectors, provenance, confidence."""

from creel.evidence import (
    DETERMINISTIC,
    BoundingBoxSelector,
    CellSelector,
    Confidence,
    Evidence,
    JsonPathSelector,
    PageSelector,
    Provenance,
    TextPositionSelector,
    TextQuoteSelector,
    deterministic_evidence,
)


def test_selectors_carry_type_discriminator():
    assert TextQuoteSelector("x").to_dict()["type"] == "TextQuoteSelector"
    assert TextPositionSelector(0, 3, "s").to_dict()["type"] == "TextPositionSelector"
    assert CellSelector("s", 2, "col").to_dict() == {
        "type": "CellSelector", "source": "s", "row": 2, "column": "col"}
    assert JsonPathSelector("a.b", "s").to_dict()["expression"] == "a.b"


def test_page_selector():
    assert PageSelector("doc", 4).to_dict() == {"type": "PageSelector", "source": "doc", "page": 4}


def test_bounding_box_selector():
    d = BoundingBoxSelector("doc", 4, (0.1, 0.2, 0.3, 0.4)).to_dict()
    assert d["type"] == "BoundingBoxSelector"
    assert d["bbox"] == [0.1, 0.2, 0.3, 0.4]
    assert d["normalized"] is True


def test_provenance_omits_unset_optionals():
    p = Provenance(derived_from="s1", generated_by="pattern:x")
    assert p.to_dict() == {"derived_from": "s1", "generated_by": "pattern:x"}


def test_confidence_method_recorded():
    c = Confidence(method=DETERMINISTIC, score=1.0, verified=True)
    d = c.to_dict()
    assert d["method"] == "deterministic" and d["verified"] is True and d["review_status"] == "auto"


def test_evidence_to_dict_is_json_ready():
    ev = deterministic_evidence(
        source_id="s1", generated_by="pattern:x",
        grounding=(TextQuoteSelector("amount 100"), PageSelector("s1", 1)),
    )
    d = ev.to_dict()
    assert d["confidence"]["method"] == "deterministic"
    assert {g["type"] for g in d["grounding"]} == {"TextQuoteSelector", "PageSelector"}
