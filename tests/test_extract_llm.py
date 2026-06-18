"""Tests for the LLM extractor — schema-as-extractor, validate-retry, grounding.

The LLM client is injected and faked, so these are deterministic and need no network
(the same posture that keeps LLM-defined verifiers testable).
"""

import pytest

from creel import AttrSchema, EnumDef, GraphSpec, NodeType, extract
from creel.extract.llm import LLMExtractor, build_instruction, compile_output_schema
from creel.extract.protocol import ExtractionContext
from creel.sources import Source, SourceBundle


class FakeLLM:
    """A fake LLM client. Routes by element id found in the prompt, or replays a sequence."""

    def __init__(self, by_element=None, sequence=None):
        self.by_element = by_element or {}
        self.sequence = list(sequence or [])
        self.calls = []

    def complete_json(self, *, prompt, schema, system=None):
        self.calls.append(prompt)
        if self.sequence:
            return self.sequence.pop(0)
        for element_id, items in self.by_element.items():
            if f"every {element_id} (" in prompt:
                return {"items": items}
        return {"items": []}


DONOR_SPEC = GraphSpec(
    enums=(EnumDef("Currency", ("USD", "EUR")),),
    node_types=(
        NodeType("donor", description="An entity that provides funding.", attributes=(
            AttrSchema("name", required=True, description="The donor's official name."),
            AttrSchema("org_code", pattern=r"^\d{3,5}$"),
            AttrSchema("preferred_currency", range="Currency"),
        )),
    ),
)
SOURCE = "Donor: Foundation Alpha (ref 301), prefers USD."


def _ctx(element_id, spec, source, services):
    return ExtractionContext(
        element_id=element_id, element_type=spec.element_type(element_id),
        sources=SourceBundle([Source("s1", source)]), spec=spec, services=services,
    )


def test_compile_output_schema_has_enum_and_omits_numeric_bounds():
    spec = GraphSpec(node_types=(NodeType("x", attributes=(
        AttrSchema("amount", range="decimal", minimum=0, maximum=10),
        AttrSchema("currency", enum=("USD", "EUR")),
    )),))
    schema = compile_output_schema(spec.node_type("x"), spec)
    item = schema["properties"]["items"]["items"]
    assert item["properties"]["currency"]["enum"] == ["USD", "EUR"]
    # D6: numeric bounds are NOT in the decoder schema (checked post-decode)
    assert "minimum" not in item["properties"]["amount"]
    assert item["properties"]["amount"]["type"] == "number"


def test_build_instruction_mentions_descriptions_and_constraints():
    instr = build_instruction(DONOR_SPEC.node_type("donor"), DONOR_SPEC)
    assert "official name" in instr
    assert "one of ['USD', 'EUR']" in instr
    assert "required" in instr


def test_llm_extractor_schema_as_extractor():
    llm = FakeLLM(by_element={"donor": [
        {"name": "Foundation Alpha", "org_code": "301", "preferred_currency": "USD"}]})
    out = LLMExtractor()(_ctx("donor", DONOR_SPEC, SOURCE, {"llm": llm}))
    assert len(out.nodes) == 1
    node = out.nodes[0]
    assert node.id == "donor:foundation-alpha"
    assert node.attributes["org_code"] == "301"
    # grounded: the name appears verbatim in the source -> verified, confidence recorded
    assert node.evidence.confidence.verified is True
    assert node.evidence.grounding[0].kind == "TextQuoteSelector"


def test_validate_retry_reasks_then_succeeds():
    bad = {"items": [{"name": "Foundation Alpha", "preferred_currency": "GBP"}]}   # GBP not in Currency
    good = {"items": [{"name": "Foundation Alpha", "preferred_currency": "USD"}]}
    llm = FakeLLM(sequence=[bad, good])
    out = LLMExtractor(max_retries=2)(_ctx("donor", DONOR_SPEC, "Foundation Alpha prefers USD.", {"llm": llm}))
    assert out.nodes[0].attributes["preferred_currency"] == "USD"
    assert len(llm.calls) == 2  # retried once
    assert "fix them" in llm.calls[1]  # feedback included the validation problem


def test_faithfulness_gate_flags_ungrounded_value():
    # 'Atlantis' does not occur in the source -> not grounded -> needs_review
    llm = FakeLLM(by_element={"donor": [{"name": "Atlantis"}]})
    out = LLMExtractor()(_ctx("donor", DONOR_SPEC, SOURCE, {"llm": llm}))
    ev = out.nodes[0].evidence
    assert ev.confidence.verified is False
    assert ev.confidence.review_status == "needs_review"


def test_missing_llm_client_raises():
    with pytest.raises(ValueError, match="services\\['llm'\\]"):
        LLMExtractor()(_ctx("donor", DONOR_SPEC, SOURCE, {}))


def test_facade_uses_schema_as_extractor_fallback_with_injected_llm():
    spec = GraphSpec(node_types=(
        NodeType("donor", attributes=(AttrSchema("name", required=True),)),
        NodeType("project", attributes=(AttrSchema("title", required=True),)),
    ))
    llm = FakeLLM(by_element={
        "donor": [{"name": "Gov X"}],
        "project": [{"title": "Water"}],
    })
    # No bindings: every element falls back to the schema-as-extractor LLM strategy.
    g = extract("Gov X funds Water.", spec, None, services={"llm": llm},
                on_missing_binding="schema_as_extractor")
    assert {n.id for n in g.nodes()} == {"donor:gov-x", "project:water"}
