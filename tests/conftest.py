"""Shared pytest fixtures: a small grammar + a conforming instance graph.

The fixture grammar is a miniature of the UNHCR results model — donors fund
projects, projects deliver outputs, and ``result`` is an abstract supertype of
``outcome``/``output`` — so it exercises inheritance, enums, ranges, edge
endpoints, and parallel edges without the full ``unhcr-rbm`` grammar.
"""

import pytest

from creel.graph.model import Graph
from creel.spec.model import (
    AttrSchema,
    EdgeType,
    EnumDef,
    GraphSpec,
    NodeType,
)


@pytest.fixture
def sample_spec() -> GraphSpec:
    """A small grammar with inheritance, an enum, a ranged edge attribute."""
    return GraphSpec(
        id="sample",
        version="0.1.0",
        enums=(EnumDef("Currency", ("USD", "EUR", "CHF")),),
        node_types=(
            NodeType(
                "result",
                abstract=True,
                attributes=(AttrSchema("statement", required=True, description="The result statement."),),
            ),
            NodeType("outcome", is_a="result"),
            NodeType("output", is_a="result"),
            NodeType(
                "donor",
                attributes=(
                    AttrSchema("name", required=True),
                    AttrSchema("dac_code", pattern=r"^\d{3,5}$"),
                ),
            ),
            NodeType("project", attributes=(AttrSchema("title", required=True),)),
        ),
        edge_types=(
            EdgeType(
                "funds",
                subject_type="donor",
                object_type="project",
                attributes=(
                    AttrSchema("amount", range="decimal", required=True, minimum=0),
                    AttrSchema("currency", range="Currency", required=True),
                ),
            ),
            EdgeType("delivers", subject_type="project", object_type="output"),
        ),
    )


@pytest.fixture
def sample_graph() -> Graph:
    """A conforming instance with two parallel ``funds`` edges (distinct fundings)."""
    g = Graph()
    g.add_node("d:gov-x", types=("donor",), attributes={"name": "Government X", "dac_code": "302"})
    g.add_node("p:wash", types=("project",), attributes={"title": "WASH programme"})
    g.add_node("o:clean-water", types=("output",), attributes={"statement": "Clean water delivered"})
    g.add_edge("f:1", source="d:gov-x", target="p:wash", type="funds",
               attributes={"amount": 1_000_000, "currency": "USD"})
    g.add_edge("f:2", source="d:gov-x", target="p:wash", type="funds",
               attributes={"amount": 500_000, "currency": "EUR"})
    g.add_edge("e:delivers-1", source="p:wash", target="o:clean-water", type="delivers")
    return g
