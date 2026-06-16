"""Tests for instance-graph validation against a grammar."""

import pytest

from creel.graph.model import Graph
from creel.spec.validate import GraphValidationError, validate_graph


def _codes(issues):
    return {i.code for i in issues}


def test_conforming_graph_has_no_issues(sample_spec, sample_graph):
    assert validate_graph(sample_graph, sample_spec) == []


def test_missing_required_attribute(sample_spec):
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={})  # 'name' is required
    assert "missing-required" in _codes(validate_graph(g, sample_spec))


def test_bad_enum_value(sample_spec, sample_graph):
    g = sample_graph
    g.add_node("p:2", types=("project",), attributes={"title": "T"})
    g.add_edge("f:bad", source="d:gov-x", target="p:2", type="funds",
               attributes={"amount": 10, "currency": "GBP"})  # GBP not in Currency
    assert "enum" in _codes(validate_graph(g, sample_spec))


def test_minimum_violation(sample_spec):
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "D"})
    g.add_node("p:1", types=("project",), attributes={"title": "T"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds",
               attributes={"amount": -5, "currency": "USD"})
    assert "minimum" in _codes(validate_graph(g, sample_spec))


def test_range_type_violation(sample_spec):
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "D"})
    g.add_node("p:1", types=("project",), attributes={"title": "T"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds",
               attributes={"amount": "a lot", "currency": "USD"})
    assert "range-type" in _codes(validate_graph(g, sample_spec))


def test_pattern_violation(sample_spec):
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "D", "dac_code": "XX"})
    assert "pattern" in _codes(validate_graph(g, sample_spec))


def test_edge_endpoint_type_mismatch(sample_spec):
    # 'funds' must go donor -> project; here we point it project -> donor.
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "D"})
    g.add_node("p:1", types=("project",), attributes={"title": "T"})
    g.add_edge("f:1", source="p:1", target="d:1", type="funds",
               attributes={"amount": 1, "currency": "USD"})
    assert "endpoint-type" in _codes(validate_graph(g, sample_spec))


def test_unknown_node_and_edge_types(sample_spec):
    g = Graph()
    g.add_node("x:1", types=("alien",))
    g.add_node("d:1", types=("donor",), attributes={"name": "D"})
    g.add_edge("e:1", source="x:1", target="d:1", type="beams-to")
    codes = _codes(validate_graph(g, sample_spec))
    assert "unknown-type" in codes


def test_raise_on_error(sample_spec):
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={})  # missing name
    with pytest.raises(GraphValidationError):
        validate_graph(g, sample_spec, raise_on_error=True)


def test_subtype_endpoint_accepted(sample_spec):
    # 'delivers' targets 'output'; 'output' is_a 'result'. A node typed 'output'
    # must be accepted as the object endpoint.
    g = Graph()
    g.add_node("p:1", types=("project",), attributes={"title": "T"})
    g.add_node("o:1", types=("output",), attributes={"statement": "S"})
    g.add_edge("e:1", source="p:1", target="o:1", type="delivers")
    assert validate_graph(g, sample_spec) == []
