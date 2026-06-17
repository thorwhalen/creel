"""Tests for the reification toggle (#12 / D1): edge <-> relation-node, losslessly."""

from creel import reify, unreify
from creel.evidence import deterministic_evidence
from creel.graph.canonical import to_canonical_json
from creel.graph.model import Graph


def _reading_graph():
    """A mini results graph: an output measured by an indicator over two periods."""
    g = Graph()
    g.add_node("output:op-1", types=("output",), attributes={"statement": "Water delivered"})
    g.add_node("indicator:ind-1", types=("indicator",), attributes={"name": "People reached"})
    # two parallel 'measured_by' edges = a two-point time-series (different periods)
    g.add_edge("measured_by:0", source="output:op-1", target="indicator:ind-1", type="measured_by",
               attributes={"actual": 4000, "period": "2026-Q1"})
    g.add_edge("measured_by:1", source="output:op-1", target="indicator:ind-1", type="measured_by",
               attributes={"actual": 4200, "period": "2026-Q2"})
    g.evidence["measured_by:0"] = deterministic_evidence(source_id="t", generated_by="test")
    return g


def test_roundtrip_is_lossless():
    g = _reading_graph()
    there = reify(g, "measured_by", node_type="reading")
    back = unreify(there, "measured_by", node_type="reading")
    assert to_canonical_json(back) == to_canonical_json(g)  # byte-identical round-trip


def test_reify_creates_one_node_per_edge_with_attributes_and_connectors():
    g = _reading_graph()
    r = reify(g, "measured_by", node_type="reading")
    readings = sorted(n.id for n in r.nodes_of_type("reading"))
    assert readings == ["measured_by:0", "measured_by:1"]            # parallel edges -> distinct nodes
    assert r.node("measured_by:0").attributes == {"actual": 4000, "period": "2026-Q1"}
    # the original measured_by edge type is gone; connector edge types appear
    assert list(r.edges_of_type("measured_by")) == []
    assert len(list(r.edges_of_type("measured_by_subject"))) == 2
    assert len(list(r.edges_of_type("measured_by_object"))) == 2
    # subject/object connectors point the right way
    subj = next(iter(r.edges_of_type("measured_by_subject")))
    assert subj.source == "output:op-1" and subj.target in readings


def test_evidence_rides_across_the_toggle():
    g = _reading_graph()
    r = reify(g, "measured_by", node_type="reading")
    assert "measured_by:0" in r.evidence          # edge evidence -> reified node (same id)
    back = unreify(r, "measured_by", node_type="reading")
    assert "measured_by:0" in back.evidence       # ... and back to the edge


def test_other_edge_types_untouched():
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "X"})
    g.add_node("p:1", types=("project",), attributes={"title": "Y"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds", attributes={"amount": 100})
    g.add_node("ind:1", types=("indicator",))
    g.add_edge("m:1", source="p:1", target="ind:1", type="measured_by", attributes={"actual": 5})
    r = reify(g, "measured_by", node_type="reading")
    # 'funds' is untouched; only 'measured_by' was reified
    assert len(list(r.edges_of_type("funds"))) == 1
    assert len(list(r.nodes_of_type("reading"))) == 1


def test_reify_refuses_preexisting_node_type():
    g = _reading_graph()
    g.add_node("reading:foreign", types=("reading",), attributes={})  # 'reading' already in use
    try:
        reify(g, "measured_by", node_type="reading")
        assert False, "expected a node_type-collision error"
    except ValueError as exc:
        assert "already" in str(exc)


def test_unreify_keeps_foreign_nodes_of_same_type():
    # A 'reading' node with no connector edges is not actually reified — unreify must
    # keep it as a node, not crash.
    g = Graph()
    g.add_node("reading:x", types=("reading",), attributes={"note": "hand-authored"})
    back = unreify(g, "measured_by", node_type="reading")
    assert back.has_node("reading:x")
    assert list(back.edges_of_type("measured_by")) == []


def test_reify_refuses_preexisting_connector_type():
    g = _reading_graph()
    g.add_edge("x", source="output:op-1", target="indicator:ind-1", type="measured_by_subject")
    try:
        reify(g, "measured_by", node_type="reading")
        assert False, "expected a connector-type-collision error"
    except ValueError as exc:
        assert "connector edge type" in str(exc)


def test_unreify_preserves_foreign_connector_type_edges():
    # A foreign edge that merely shares the connector type must survive unreify
    # (only the connectors of actually-collapsed reified nodes are removed).
    g = _reading_graph()
    r = reify(g, "measured_by", node_type="reading")
    r.add_edge("foreign", source="output:op-1", target="indicator:ind-1", type="measured_by_subject")
    back = unreify(r, "measured_by", node_type="reading")
    assert len(list(back.edges_of_type("measured_by"))) == 2  # readings collapsed back
    assert back.has_edge("foreign")                            # foreign edge untouched


def test_unreify_keeps_incomplete_reified_node_and_its_connector():
    g = Graph()
    g.add_node("a", types=("output",))
    g.add_node("r1", types=("reading",), attributes={"actual": 1})
    g.add_edge("c", source="a", target="r1", type="measured_by_subject")  # only one connector
    back = unreify(g, "measured_by", node_type="reading")
    assert back.has_node("r1")                            # incomplete node kept
    assert back.has_edge("c")                             # its lone connector NOT silently dropped
    assert list(back.edges_of_type("measured_by")) == []


def test_collision_raises_clearly():
    g = Graph()
    g.add_node("e:1", types=("thing",))           # a node already named 'e:1'
    g.add_node("a", types=("thing",))
    g.add_node("b", types=("thing",))
    g.add_edge("e:1", source="a", target="b", type="rel")  # edge id collides with the node id
    try:
        reify(g, "rel")
        assert False, "expected a collision error"
    except ValueError as exc:
        assert "collision" in str(exc)
