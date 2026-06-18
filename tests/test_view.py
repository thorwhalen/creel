"""Tests for the graph projections (D15): records, tables, DOT, Mermaid, Cytoscape."""

from creel.graph.model import Graph
from creel.view import (
    to_cytoscape,
    to_dot,
    to_mermaid,
    to_node_edge_records,
    to_table,
)


def _graph():
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "Gov X"})
    g.add_node("p:1", types=("project",), attributes={"title": "Water"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds", attributes={"amount": 100})
    return g


def test_node_edge_records():
    rec = to_node_edge_records(_graph())
    assert rec["nodes"][0] == {"id": "d:1", "types": ["donor"], "name": "Gov X"}
    assert rec["edges"][0] == {"id": "f:1", "type": "funds", "source": "d:1",
                               "target": "p:1", "amount": 100}


def test_table_for_node_and_edge_types():
    g = _graph()
    assert to_table(g, "donor") == [{"id": "d:1", "name": "Gov X"}]
    assert to_table(g, "funds") == [{"id": "f:1", "source": "d:1", "target": "p:1", "amount": 100}]
    assert to_table(g, "nonexistent") == []


def test_dot_is_wellformed_and_deterministic():
    g = _graph()
    dot = to_dot(g)
    assert dot.startswith("digraph creel {") and dot.endswith("}")
    assert '"d:1" -> "p:1" [label="funds"];' in dot
    assert to_dot(g) == to_dot(g)  # deterministic


def test_mermaid_aliases_ids_and_links():
    g = _graph()
    mer = to_mermaid(g, label_attr="name")
    assert mer.startswith("flowchart LR")
    # ids are aliased (n0/n1) so colons don't break Mermaid; labels carry the content
    assert 'n0["Gov X"]' in mer
    assert "-->|funds|" in mer


def test_cytoscape_elements_shape():
    cy = to_cytoscape(_graph())
    node = cy["elements"]["nodes"][0]["data"]
    assert node["id"] == "d:1" and node["label"] == "donor" and node["name"] == "Gov X"
    edge = cy["elements"]["edges"][0]["data"]
    assert edge == {"id": "f:1", "source": "d:1", "target": "p:1", "type": "funds", "amount": 100}


def test_projections_round_on_rbm_graph():
    # Smoke: the projections run on a richer graph (the disaggregation corpus) without error.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent / "data" / "rbm"))
    import corpus  # noqa: E402

    from creel.evaluation import evaluate_case

    g = evaluate_case(corpus.build_case()).actual_graph
    assert "flowchart LR" in to_mermaid(g)
    assert len(to_node_edge_records(g)["nodes"]) == 17  # 12 base + 5 reading nodes
    assert len(to_table(g, "reading")) == 5
