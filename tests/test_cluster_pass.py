"""Tests for the cluster-pass binding model (D-OP8, EPIC 11.1/11.2).

One binding can cover a *set* of grammar elements and be invoked ONCE — a single LLM
pass over several coupled types — instead of once per element.
"""

from creel import AttrSchema, EdgeType, GraphSpec, NodeType, extract
from creel.bindings import ExtractorBinding, ExtractorBindings
from creel.join import join

SPEC = GraphSpec(node_types=(
    NodeType("donor", attributes=(AttrSchema("name", required=True),)),
    NodeType("project", attributes=(AttrSchema("title", required=True),)),
), edge_types=(
    EdgeType("funds", subject_type="donor", object_type="project",
             attributes=(AttrSchema("amount", range="integer"),)),
))


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete_json(self, *, prompt, schema, system=None):
        self.calls.append(prompt)
        return self.response


def test_join_collapses_a_cluster_into_one_step():
    bindings = ExtractorBindings([
        ExtractorBinding("rbm", strategy="cluster_llm", elements=("donor", "project", "funds")),
    ])
    plan = join(SPEC, bindings)
    assert len(plan.steps) == 1                      # ONE step for the whole cluster
    step = plan.steps[0]
    assert {et.id for et in step.element_types} == {"donor", "project", "funds"}
    assert plan.unbound == ()                        # all three are covered


def test_cluster_llm_extracts_all_types_in_one_pass():
    llm = FakeLLM({
        "donor": [{"name": "Gov X"}],
        "project": [{"title": "WASH"}],
        "funds": [{"amount": 100, "_source": "donor:gov-x", "_target": "project:wash"}],
    })
    bindings = {"rbm": {"strategy": "cluster_llm", "elements": ("donor", "project", "funds")}}
    g = extract("Gov X funds WASH with 100.", SPEC, bindings,
                services={"llm": llm}, on_missing_binding="skip")
    assert len(llm.calls) == 1                        # exactly ONE LLM call for the cluster
    assert {n.id for n in g.nodes()} == {"donor:gov-x", "project:wash"}
    funds = list(g.edges_of_type("funds"))
    assert len(funds) == 1 and funds[0].attributes["amount"] == 100


def test_cluster_member_not_separately_unbound():
    # 'donor' is in the cluster; only 'project' is left to fall through.
    bindings = ExtractorBindings([
        ExtractorBinding("c", strategy="cluster_llm", elements=("donor", "funds")),
    ])
    plan = join(SPEC, bindings)
    assert set(plan.unbound) == {"project"}          # donor & funds covered by the cluster
