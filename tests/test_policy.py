"""Tests for ExtractionPolicy (#13/EPIC 11.4): self-consistency + review thresholds."""

import pytest

from creel import AttrSchema, ExtractionPolicy, GraphSpec, NodeType, extract
from creel.extract.llm import LLMExtractor
from creel.extract.protocol import ExtractionContext
from creel.sources import Source, SourceBundle

SPEC = GraphSpec(node_types=(
    NodeType("donor", attributes=(AttrSchema("name", required=True),)),
))
SOURCE = "Donor: Government of Norway."


class SequenceLLM:
    """Returns a fixed sequence of responses (one per call)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def complete_json(self, *, prompt, schema, system=None):
        self.calls += 1
        return self.responses.pop(0)


def _ctx(policy, llm):
    return ExtractionContext(
        element_id="donor", element_type=SPEC.node_type("donor"),
        sources=SourceBundle([Source("s", SOURCE)]), spec=SPEC,
        services={"llm": llm}, config={"policy": policy},
    )


def test_policy_resolution_chain():
    strict = ExtractionPolicy(self_consistency_samples=5)
    p = ExtractionPolicy(overrides={"donor": strict})
    assert p.for_element("donor", "donor") is strict
    assert p.for_element("project", "project") is p  # falls through to self


def test_self_consistency_majority_vote_and_confidence():
    # 3 samples: two agree on "Government of Norway", one differs -> modal wins, 2/3 agreement
    a = {"items": [{"name": "Government of Norway"}]}
    b = {"items": [{"name": "Govt of Norway"}]}
    llm = SequenceLLM([a, a, b])
    ext = LLMExtractor()
    out = ext(_ctx(ExtractionPolicy(self_consistency_samples=3), llm))
    assert llm.calls == 3                                   # one call per sample
    assert [n.attributes["name"] for n in out.nodes] == ["Government of Norway"]
    conf = out.nodes[0].evidence.confidence
    assert conf.method == "self_consistency"
    assert conf.score == pytest.approx(2 / 3)


def test_low_agreement_flags_needs_review():
    # all three disagree -> agreement 1/3 < review_below -> needs_review
    llm = SequenceLLM([
        {"items": [{"name": "A"}]}, {"items": [{"name": "B"}]}, {"items": [{"name": "C"}]},
    ])
    out = LLMExtractor()(_ctx(ExtractionPolicy(self_consistency_samples=3, review_below=0.5), llm))
    assert out.nodes[0].evidence.confidence.review_status == "needs_review"


def test_default_single_pass_uses_one_call():
    llm = SequenceLLM([{"items": [{"name": "Government of Norway"}]}])
    out = LLMExtractor()(_ctx(ExtractionPolicy(), llm))  # samples=1
    assert llm.calls == 1
    # grounded (name occurs in source) -> verbalized confidence, not flagged
    assert out.nodes[0].evidence.confidence.method == "verbalized"
    assert out.nodes[0].evidence.confidence.review_status == "auto"


def test_policy_via_services_through_facade():
    llm = SequenceLLM([{"items": [{"name": "Government of Norway"}]}] * 3)
    g = extract(SOURCE, SPEC, {"donor": ("llm", {})},
                services={"llm": llm, "policy": ExtractionPolicy(self_consistency_samples=3)},
                on_missing_binding="skip")
    assert llm.calls == 3  # the policy drove self-consistency through the facade
    assert g.node("donor:government-of-norway").attributes["name"] == "Government of Norway"
