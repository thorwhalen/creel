"""Real-LLM integration tests via aix (run "from time to time", skipped without keys).

These exercise the LLM extractor, the ``llm_rubric`` verifier, and the LLM entity
resolver against a real model using aix's defaults. They are gated: skipped if aix
isn't installed or no provider API key is discoverable, so the default test run (and
CI without keys) stays fast and offline. Most of creel is tested with fakes; these
prove the seams actually connect to a real model.
"""

import pytest

aix = pytest.importorskip("aix")


def _has_key() -> bool:
    try:
        keys = aix.check_keys()
    except Exception:
        return False
    return any(isinstance(v, dict) and v.get("available") for v in keys.values())


pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not _has_key(), reason="no LLM API key discoverable (aix.check_keys)"),
]


def test_real_llm_extraction():
    from creel import AttrSchema, GraphSpec, NodeType, extract
    from creel.extract.llm import aix_client

    spec = GraphSpec(node_types=(
        NodeType("donor", description="An entity that provides funding.",
                 attributes=(AttrSchema("name", required=True, description="The donor's official name."),)),
    ))
    g = extract(
        "Donor: Government of Norway (DAC 301). Donor: European Commission (DAC 918).",
        spec,
        {"donor": ("llm", {})},
        services={"llm": aix_client()},
        on_missing_binding="skip",
    )
    names = " ".join(n.attributes.get("name", "") for n in g.nodes_of_type("donor"))
    assert "Norway" in names and ("Commission" in names or "European" in names)
    # every extracted donor carries an evidence record with a confidence method
    for node in g.nodes_of_type("donor"):
        assert node.id in g.evidence and g.evidence[node.id].confidence is not None


def test_real_llm_rubric_judges_semantic_equivalence():
    from creel.extract.llm import aix_judge
    from creel.verify.protocol import VerificationContext
    from creel.verify.rubric import LLMRubric

    ctx = VerificationContext(services={"judge": aix_judge()})
    rubric = LLMRubric(criterion="Both statements describe the same outcome about access to clean water.")
    same = rubric("Communities have sustained access to clean water",
                  "People enjoy lasting access to safe drinking water", context=ctx)
    diff = rubric("Communities have sustained access to clean water",
                  "Households received emergency cash assistance", context=ctx)
    assert same.score > diff.score          # semantically closer pair scores higher
    assert same.reason                       # a reason is always recorded


def test_real_llm_entity_resolution():
    from creel.extract.llm import aix_entity_judge
    from creel.graph.model import Graph
    from creel.resolve import LLMResolver, resolve_graph

    g = Graph()
    g.add_node("d:a", types=("donor",), attributes={"name": "Government of Norway"})
    g.add_node("d:b", types=("donor",), attributes={"name": "the Norwegian government"})
    g.add_node("d:c", types=("donor",), attributes={"name": "European Commission"})
    merged = resolve_graph(g, LLMResolver(judge=aix_entity_judge(), key="name"))
    # the two Norway variants merge; the EC stays separate
    assert len(list(merged.nodes_of_type("donor"))) == 2
