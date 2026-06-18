"""End-to-end facade tests: sources + grammar + bindings -> graph + evidence."""

import pytest

from creel import (
    AttrSchema,
    EdgeType,
    EnumDef,
    GraphSpec,
    NodeType,
    extract,
    to_canonical_json,
    validate_graph,
)
from creel.graph.canonical import validate_canonical, to_canonical_dict

SOURCE = """\
Donor: Government X
Donor: Foundation Y
Project: Water programme
Project: Housing programme

Government X funds Water programme with USD 1000000.
Foundation Y funds Housing programme with EUR 500000.
Government X funds Housing programme with USD 250000.
"""


@pytest.fixture
def rbm_mini_spec() -> GraphSpec:
    return GraphSpec(
        id="rbm-mini",
        enums=(EnumDef("Currency", ("USD", "EUR", "CHF")),),
        node_types=(
            NodeType("donor", attributes=(AttrSchema("name", required=True),)),
            NodeType("project", attributes=(AttrSchema("title", required=True),)),
        ),
        edge_types=(
            EdgeType(
                "funds", subject_type="donor", object_type="project",
                attributes=(
                    AttrSchema("amount", range="integer", required=True, minimum=0),
                    AttrSchema("currency", range="Currency", required=True),
                ),
            ),
        ),
    )


@pytest.fixture
def bindings() -> dict:
    return {
        "donor": ("regex_node", {"pattern": r"Donor:\s*(?P<name>.+)", "id_attribute": "name"}),
        "project": ("regex_node", {"pattern": r"Project:\s*(?P<title>.+)", "id_attribute": "title"}),
        "funds": (
            "regex_edge",
            {
                "pattern": r"(?P<donor>[\w ]+?) funds (?P<project>[\w ]+?) with (?P<currency>[A-Z]{3}) (?P<amount>[\d,]+)",
                "source_id_template": "donor:{donor}",
                "target_id_template": "project:{project}",
                "casts": {"amount": "int"},
                "exclude_groups": ("donor", "project"),
            },
        ),
    }


def test_extract_builds_expected_graph(rbm_mini_spec, bindings):
    g = extract(SOURCE, rbm_mini_spec, bindings, on_missing_binding="skip")
    assert {n.id for n in g.nodes_of_type("donor")} == {"donor:government-x", "donor:foundation-y"}
    assert {n.id for n in g.nodes_of_type("project")} == {
        "project:water-programme",
        "project:housing-programme",
    }
    # three funding edges, one of them a parallel funding (Gov X -> Housing)
    funds = list(g.edges_of_type("funds"))
    assert len(funds) == 3
    amounts = sorted(e.attributes["amount"] for e in funds)
    assert amounts == [250000, 500000, 1000000]


def test_extracted_graph_conforms_to_grammar(rbm_mini_spec, bindings):
    g = extract(SOURCE, rbm_mini_spec, bindings, on_missing_binding="skip")
    assert validate_graph(g, rbm_mini_spec) == []


def test_extracted_graph_serialises_to_valid_canonical_json(rbm_mini_spec, bindings):
    g = extract(SOURCE, rbm_mini_spec, bindings, on_missing_binding="skip")
    validate_canonical(to_canonical_dict(g, spec=rbm_mini_spec))
    # deterministic round-trippable text
    assert to_canonical_json(g) == to_canonical_json(g)


def test_every_element_has_evidence(rbm_mini_spec, bindings):
    g = extract(SOURCE, rbm_mini_spec, bindings, on_missing_binding="skip")
    for node in g.nodes():
        assert node.id in g.evidence
    for edge in g.edges():
        assert edge.id in g.evidence
        assert g.evidence[edge.id].confidence.method == "deterministic"


def test_unbound_elements_reported_not_extracted(rbm_mini_spec):
    # Only bind 'donor'; 'project' and 'funds' are unbound and must be reported.
    g = extract(
        SOURCE,
        rbm_mini_spec,
        {"donor": ("regex_node", {"pattern": r"Donor:\s*(?P<name>.+)", "id_attribute": "name"})},
        on_missing_binding="skip",
    )
    assert set(g.report["unbound_elements"]) == {"project", "funds"}
    assert list(g.nodes_of_type("project")) == []


def test_missing_endpoint_edges_are_skipped_and_recorded(rbm_mini_spec):
    # Bind only 'funds' (no nodes extracted) -> every edge has missing endpoints.
    g = extract(
        SOURCE,
        rbm_mini_spec,
        {
            "funds": (
                "regex_edge",
                {
                    "pattern": r"(?P<donor>[\w ]+?) funds (?P<project>[\w ]+?) with (?P<currency>[A-Z]{3}) (?P<amount>[\d,]+)",
                    "source_id_template": "donor:{donor}",
                    "target_id_template": "project:{project}",
                    "exclude_groups": ("donor", "project"),
                },
            )
        },
        on_missing_binding="skip",
    )
    assert g.number_of_edges == 0
    assert len(g.report["skipped_edges"]) == 3
    assert all(s["reason"] == "missing-endpoint" for s in g.report["skipped_edges"])


def test_on_missing_binding_error_raises(rbm_mini_spec):
    with pytest.raises(ValueError):
        extract(SOURCE, rbm_mini_spec, {}, on_missing_binding="error")


def test_direct_callable_binding(rbm_mini_spec):
    from creel.extract.protocol import Extraction, ExtractedNode

    def donor_extractor(ctx):
        return Extraction(nodes=[ExtractedNode("donor:custom", "donor", {"name": "Custom"})])

    g = extract(SOURCE, rbm_mini_spec, {"donor": donor_extractor}, on_missing_binding="skip")
    assert g.node("donor:custom").attributes["name"] == "Custom"
