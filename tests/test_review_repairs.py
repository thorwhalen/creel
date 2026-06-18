"""Regression tests for the adversarial-review repairs.

Each test pins a previously-confirmed bug so it can't silently come back. Grouped by
subsystem; all offline (no LLM). See the PR that introduced them for the full report.
"""

import math

import pytest

from creel import (
    AttrSchema,
    EdgeType,
    GraphSpec,
    NodeType,
    extract,
    to_canonical_json,
)
from creel.graph.model import Graph


# --- core: slug / cast / templates -------------------------------------------
def test_slug_keeps_unicode_distinct_and_ascii_stable():
    from creel.extract.transforms import slug

    assert slug("日本") != slug("中国")  # distinct non-Latin names don't collapse
    assert slug("café") == "café"
    assert slug("Foundation Alpha") == "foundation-alpha"  # ASCII unchanged
    assert slug("Water Access") == "water-access"
    assert slug("!!!") == "x"  # all-punctuation -> fallback


def test_cast_value_tolerates_non_numbers_and_handles_containers():
    from creel.extract.transforms import apply_casts, cast_value

    assert cast_value("2020-01-01", "int") == "2020-01-01"  # date, not a crash
    assert cast_value("12-34", "int") == "12-34"  # code, not a crash
    assert cast_value("3.4.5", "float") == "3.4.5"
    assert cast_value("USD 1,000", "int") == 1000  # real numeric still parses
    assert apply_casts({"a": [1, 2, 3]}, {"a": "int"}) == {"a": [1, 2, 3]}  # element-wise
    assert apply_casts({"a": {"k": 1}}, {"a": "int"}) == {"a": {"k": 1}}  # mapping unchanged


def test_fill_template_missing_field_is_informative():
    from creel.extract.transforms import fill_template

    with pytest.raises(KeyError, match="available fields"):
        fill_template("donor:{name}", {"oops": "x"})


def test_regex_edge_ids_unique_across_sources():
    from creel.extract.pattern import RegexEdgeExtractor
    from creel.extract.protocol import ExtractionContext
    from creel.sources import Source, SourceBundle

    spec = GraphSpec(edge_types=(EdgeType("funds", subject_type="d", object_type="p"),))
    ex = RegexEdgeExtractor(
        pattern=r"(?P<donor>\w+) funds (?P<project>\w+)",
        source_id_template="donor:{donor}",
        target_id_template="project:{project}",
        exclude_groups=("donor", "project"),
    )
    ctx = ExtractionContext(
        element_id="funds", element_type=spec.edge_type("funds"),
        sources=SourceBundle([Source("s1", "X funds Y"), Source("s2", "X funds Y")]),
        spec=spec, services={}, config={},
    )
    ids = [e.id for e in ex(ctx).edges]
    assert len(ids) == len(set(ids)) == 2


# --- core: canonical JSON / graph model --------------------------------------
def test_canonical_json_rejects_nan_and_tolerates_mixed_keys():
    g = Graph()
    g.add_node("n", types=("t",), attributes={"v": float("nan")})
    with pytest.raises(ValueError):
        to_canonical_json(g)
    g2 = Graph()
    g2.add_node("n", types=("t",), attributes={1: "a", "b": 2})  # mixed-type keys
    assert '"1"' in to_canonical_json(g2)  # coerced to str, no sort crash


def test_add_node_records_attribute_conflicts():
    g = Graph()
    g.add_node("x", types=("t",), attributes={"name": "Alice"})
    g.add_node("x", types=("t",), attributes={"name": "Bob"})  # conflict
    assert g.node("x").attributes["name"] == "Bob"  # merge stays last-wins
    conflicts = g.report["attribute_conflicts"]
    assert conflicts == [{"node": "x", "attribute": "name", "old": "Alice", "new": "Bob"}]


# --- verify: graph_match -----------------------------------------------------
def test_graph_match_no_vacuous_inflation():
    from creel.verify.graph_match import GraphMatch

    exp = Graph()
    exp.add_node("a", types=("t",))
    exp.add_node("b", types=("t",))
    assert GraphMatch()(Graph(), exp).score == 0.0  # empty extraction -> 0, not 0.667
    assert GraphMatch()(Graph(), Graph()).score == 1.0  # empty vs empty -> trivially 1


def test_graph_match_parallel_edges_no_double_credit():
    from creel.verify.graph_match import GraphMatch

    exp = Graph()
    exp.add_node("A", types=("d",))
    exp.add_node("B", types=("p",))
    exp.add_edge("e1", source="A", target="B", type="funds", attributes={"amount": 100})
    exp.add_edge("e2", source="A", target="B", type="funds", attributes={"amount": 200})
    act = Graph()
    act.add_node("A", types=("d",))
    act.add_node("B", types=("p",))
    act.add_edge("f1", source="A", target="B", type="funds", attributes={"amount": 100})
    verdict = GraphMatch()(act, exp)
    assert verdict.details["attributes"]["compared"] == 1  # one actual edge -> one match
    assert verdict.details["edges"]["recall"] == 0.5  # the missed parallel shows here


# --- verify: rubric / trace --------------------------------------------------
def test_rubric_extract_json_balanced_braces():
    from creel.verify.rubric import _extract_json

    text = '{"score": 0.9, "reason": "ok"}. Note: see item }here'
    import json

    assert json.loads(_extract_json(text))["score"] == 0.9


def test_reanchor_fuzzy_span_within_text():
    from creel.evidence import TextQuoteSelector
    from creel.trace import reanchor

    span = reanchor(TextQuoteSelector(exact="ABCDEFGHIJ"), "xx ABCDEFG", fuzzy=True)
    assert span is not None and span[1] <= len("xx ABCDEFG")


# --- resolve / reify: evidence is not lost -----------------------------------
def test_resolve_carries_member_and_per_attribute_evidence():
    from creel.resolve import NormalizeResolver, resolve_graph

    g = Graph()
    g.add_node("org:a", types=("org",), attributes={"name": "Foo"})
    g.add_node("org:b", types=("org",), attributes={"name": "Foo"})
    g.evidence["org:b"] = "ELEM-B"  # evidence on the non-canonical member
    g.evidence[("org:a", "name")] = "ATTR-A"  # per-attribute (A1) evidence
    merged = resolve_graph(g, NormalizeResolver(key="name"))
    cid = next(iter(merged.nodes_of_type("org"))).id
    assert cid in merged.evidence  # element-level survived
    assert any(isinstance(k, tuple) for k in merged.evidence)  # per-attr survived


def test_reify_roundtrip_preserves_per_attribute_evidence():
    from creel.reify import reify, unreify

    g = Graph()
    g.add_node("d", types=("donor",))
    g.add_node("i", types=("ind",))
    g.add_edge("m1", source="d", target="i", type="measured_by", attributes={"value": 5})
    g.evidence[("m1", "value")] = "ATTR-VAL"
    reified = reify(g, "measured_by", node_type="reading")
    assert any(isinstance(k, tuple) and k[0] == "m1" for k in reified.evidence)
    back = unreify(reified, "measured_by", node_type="reading")
    assert ("m1", "value") in back.evidence


# --- export ------------------------------------------------------------------
def test_graphml_well_formed_with_hostile_attribute_name():
    import xml.dom.minidom

    from creel.export import to_graphml

    g = Graph()
    g.add_node("n1", types=("t",), attributes={'x"y<z&': "v"})
    xml.dom.minidom.parseString(to_graphml(g))  # raises if malformed


def test_turtle_guards_non_finite_floats():
    from creel.export import to_turtle

    g = Graph()
    g.add_node("n1", types=("t",), attributes={"v": float("nan"), "i": math.inf})
    out = to_turtle(g)
    assert " nan " not in out and " inf " not in out


# --- spec / api --------------------------------------------------------------
def test_validate_spec_catches_dangling_endpoint():
    from creel.spec.validate import validate_spec

    bad = GraphSpec(
        node_types=(NodeType("donor"),),
        edge_types=(EdgeType("funds", subject_type="donor", object_type="NOPE"),),
    )
    codes = {i.code for i in validate_spec(bad)}
    assert "unknown-endpoint-type" in codes


def test_version_is_a_string():
    import creel

    assert isinstance(creel.__version__, str) and creel.__version__


def test_binding_errors_name_the_element_and_strategy():
    spec = GraphSpec(node_types=(NodeType("donor", attributes=(AttrSchema("name", required=True),)),))
    with pytest.raises(ValueError, match="regex_node"):  # missing required pattern
        extract("Donor: X", spec, {"donor": ("regex_node", {})}, on_missing_binding="skip")
    with pytest.raises(ValueError, match="mapping"):  # params not a dict
        extract("Donor: X", spec, {"donor": ("regex_node", ["pattern"])}, on_missing_binding="skip")


def test_unbound_default_fallback_without_llm_is_actionable():
    spec = GraphSpec(node_types=(NodeType("donor"), NodeType("project")))
    with pytest.raises(ValueError, match="on_missing_binding='skip'"):
        extract("x", spec, {"donor": ("regex_node", {"pattern": r"(?P<name>X)"})})


# --- query -------------------------------------------------------------------
def test_query_where_tolerates_cross_type_and_validates_in():
    from creel.extract.query import _matches

    assert _matches({"amount": "100"}, {"amount": {"$gt": 50}}) is True  # str vs int
    assert _matches({"amount": "abc"}, {"amount": {"$gt": 50}}) is False  # incomparable
    with pytest.raises(ValueError, match=r"\$in operand"):
        _matches({"x": 1}, {"x": {"$in": 3}})  # scalar operand rejected


def test_duckdb_query_escapes_hostile_column_name():
    pytest.importorskip("duckdb")
    from creel.extract.query import _duckdb_query

    rows = [{'a");DROP TABLE t;--': "v"}]
    out = _duckdb_query(rows, "SELECT * FROM t", [])  # must not break out of the DDL
    assert len(out) == 1
