"""Tests for the export adapters: JGF, GraphML, Cypher (params), RDF-star Turtle."""

import xml.etree.ElementTree as ET

from creel.export import to_cypher, to_graphml, to_jgf, to_turtle
from creel.graph.model import Graph


def _graph():
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "Gov X"})
    g.add_node("p:1", types=("project",), attributes={"title": "Water"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds", attributes={"amount": 100})
    return g


def test_jgf_shape():
    jgf = to_jgf(_graph())["graph"]
    assert jgf["directed"] is True
    assert jgf["nodes"]["d:1"]["metadata"]["name"] == "Gov X"
    assert jgf["edges"][0] == {"id": "f:1", "source": "d:1", "target": "p:1",
                               "relation": "funds", "metadata": {"amount": 100}}


def test_graphml_is_valid_xml_with_data():
    xml = to_graphml(_graph())
    root = ET.fromstring(xml)  # raises if malformed
    ns = "{http://graphml.graphdrawing.org/xmlns}"
    assert root.tag == f"{ns}graphml"
    nodes = root.findall(f"{ns}graph/{ns}node")
    assert {n.get("id") for n in nodes} == {"d:1", "p:1"}
    edge = root.find(f"{ns}graph/{ns}edge")
    assert edge.get("source") == "d:1" and edge.get("target") == "p:1"


def test_cypher_is_parameterized_data():
    stmts = to_cypher(_graph())
    # node + edge statements; values live in params, not interpolated into the string
    node_stmt = next((s, p) for s, p in stmts if p.get("id") == "d:1")
    assert "$id" in node_stmt[0] and node_stmt[1]["props"]["name"] == "Gov X"
    edge_stmt = next((s, p) for s, p in stmts if p.get("id") == "f:1")
    assert "$source" in edge_stmt[0] and edge_stmt[1]["type"] == "funds"
    assert edge_stmt[1]["props"] == {"amount": 100}
    # nothing dynamic is interpolated into any statement text
    assert all("Gov X" not in s and "100" not in s for s, _ in stmts)


def test_turtle_has_node_triples_and_rdf_star_edge_annotation():
    ttl = to_turtle(_graph())
    assert "creel:d_1 rdf:type creel:donor ." in ttl
    assert 'creel:d_1 creel:name "Gov X" .' in ttl
    assert "creel:d_1 creel:funds creel:p_1 ." in ttl
    # the edge attribute annotates the quoted triple (RDF-star)
    assert "<< creel:d_1 creel:funds creel:p_1 >> creel:amount 100 ." in ttl


def test_exports_deterministic():
    g = _graph()
    assert to_turtle(g) == to_turtle(g)
    assert to_graphml(g) == to_graphml(g)
