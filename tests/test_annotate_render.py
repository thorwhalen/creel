"""Tests for the annotation overlay, render contract, and RAG-readiness (EPIC 8 / D-OP9)."""

from creel.annotate import IDENTIFYING, TAGGING, Annotation, Selection
from creel.evidence import TextQuoteSelector, Provenance
from creel.graph.model import Graph
from creel.render import AnnotatedGraph, GraphRenderer, RenderArtifact
from creel.view import to_embedding_records


def _graph():
    g = Graph()
    g.add_node("d:1", types=("donor",), attributes={"name": "Gov X"})
    g.add_node("p:1", types=("project",), attributes={"title": "Water"})
    g.add_edge("f:1", source="d:1", target="p:1", type="funds", attributes={"amount": 100})
    return g


def test_machine_and_human_annotations_share_one_schema():
    # machine insight: software_agent classifies a node
    machine = Annotation("a1", target="d:1", body="major bilateral donor", motivation=IDENTIFYING,
                         provenance=Provenance(derived_from="analysis", generated_by="llm:insight",
                                               attributed_kind="software_agent"))
    # human coding: a person highlights a passage and links it to a node
    sel = Selection("sel1", "donor_agreement", TextQuoteSelector(exact="Government X"))
    human = Annotation("a2", target=sel, body="d:1", motivation=TAGGING,
                       provenance=Provenance(derived_from="donor_agreement", generated_by="manual",
                                             attributed_kind="person", attributed_to="thor"))
    assert machine.provenance.attributed_kind == "software_agent"
    assert human.provenance.attributed_kind == "person"
    # same record type; only motivation + agent kind differ
    assert machine.to_dict()["motivation"] == "identifying"
    assert human.to_dict()["target"]["selector"]["exact"] == "Government X"
    assert human.target_element_id() is None  # targets a span, not an element


def test_per_attribute_annotation_target():
    a = Annotation("a3", target=("f:1", "amount"), body="verified against bank record")
    assert a.target_element_id() == "f:1"
    assert a.to_dict()["target"] == ["f:1", "amount"]


def test_annotated_graph_overlay_lookup():
    g = _graph()
    anns = (Annotation("a1", target="d:1", body="note A"),
            Annotation("a2", target="p:1", body="note B"))
    ag = AnnotatedGraph(g, annotations=anns)
    assert [a.id for a in ag.annotations_for("d:1")] == ["a1"]
    assert ag.graph is g


def test_render_contract_is_satisfiable_by_a_simple_renderer():
    class CountRenderer:
        name = "count"
        output_media_type = "text/plain"

        def render(self, graph, *, options=None):
            return RenderArtifact(content=f"{graph.graph.number_of_nodes} nodes", media_type=self.output_media_type)

    r = CountRenderer()
    assert isinstance(r, GraphRenderer)  # structural check (runtime_checkable Protocol)
    art = r.render(AnnotatedGraph(_graph()))
    assert art.content == "2 nodes" and art.media_type == "text/plain"


def test_embedding_records_for_rag():
    recs = {r["id"]: r for r in to_embedding_records(_graph())}
    assert recs["d:1"]["kind"] == "node" and "Gov X" in recs["d:1"]["text"]
    assert recs["f:1"]["kind"] == "edge"
    assert recs["f:1"]["text"] == "d:1 funds p:1 (amount=100)"
