"""Tests for canonical JSON: determinism, round-trip, parallel-edge fidelity."""

import json
from pathlib import Path

from creel.graph.canonical import (
    CANONICAL_GRAPH_SCHEMA,
    CANONICAL_SCHEMA_URL,
    from_canonical_json,
    to_canonical_dict,
    to_canonical_json,
    validate_canonical,
)
from creel.graph.model import Graph

_SCHEMA_FILE = Path(__file__).resolve().parents[1] / "creel" / "schemas" / "graph-v1.schema.json"


def test_roundtrip_is_byte_identical(sample_graph, sample_spec):
    text1 = to_canonical_json(sample_graph, spec=sample_spec)
    g2 = from_canonical_json(text1)
    text2 = to_canonical_json(g2, spec=sample_spec)
    assert text1 == text2


def test_parallel_edges_preserved(sample_graph):
    g2 = from_canonical_json(to_canonical_json(sample_graph))
    funds = sorted(e.id for e in g2.edges_of_type("funds"))
    assert funds == ["f:1", "f:2"]
    # distinct attributes preserved on each parallel edge
    assert g2.edge("f:1").attributes["amount"] == 1_000_000
    assert g2.edge("f:2").attributes["currency"] == "EUR"


def test_node_and_edge_attributes_preserved(sample_graph):
    g2 = from_canonical_json(to_canonical_json(sample_graph))
    assert g2.node("d:gov-x").attributes["name"] == "Government X"
    assert g2.node("o:clean-water").types == ("output",)


def test_determinism_is_insertion_order_independent():
    # Two graphs with identical content but opposite insertion order must produce
    # byte-identical canonical JSON.
    g1 = Graph()
    g1.add_node("a", types=("t",), attributes={"z": 1, "a": 2})
    g1.add_node("b", types=("t",))
    g1.add_edge("e2", source="a", target="b", type="r")
    g1.add_edge("e1", source="b", target="a", type="r")

    g2 = Graph()
    g2.add_node("b", types=("t",))
    g2.add_node("a", types=("t",), attributes={"a": 2, "z": 1})
    g2.add_edge("e1", source="b", target="a", type="r")
    g2.add_edge("e2", source="a", target="b", type="r")

    assert to_canonical_json(g1) == to_canonical_json(g2)


def test_canonical_validates_against_schema(sample_graph):
    doc = to_canonical_dict(sample_graph)
    validate_canonical(doc)  # raises if invalid
    assert doc["$schema"] == CANONICAL_SCHEMA_URL
    assert isinstance(doc["nodes"], dict)
    assert isinstance(doc["edges"], list)


def test_spec_reference_recorded(sample_graph, sample_spec):
    doc = to_canonical_dict(sample_graph, spec=sample_spec)
    assert doc["spec"] == {"id": "sample", "version": "0.1.0"}


def test_committed_schema_file_matches_code():
    # The shipped schema file must not drift from the in-code source of truth.
    on_disk = json.loads(_SCHEMA_FILE.read_text())
    assert on_disk == CANONICAL_GRAPH_SCHEMA
