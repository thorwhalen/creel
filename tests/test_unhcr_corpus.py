"""End-to-end UNHCR RBM corpus test (EPIC 7): extract -> verify against expected.

Exercises all available deterministic extractor families against ONE shared grammar
and scores the result with the verifier subsystem (not hardcoded equality). This is
the integration test that catches schema-join regressions across the whole engine.
"""

import sys
from pathlib import Path

import pytest

_UNHCR_DIR = Path(__file__).resolve().parent / "data" / "unhcr"
sys.path.insert(0, str(_UNHCR_DIR))

import corpus  # noqa: E402  (loaded from the corpus dir)

from creel.evaluation import evaluate_case, evaluate_corpus  # noqa: E402
from creel.graph.canonical import from_canonical_dict, to_canonical_dict  # noqa: E402
from creel.spec.validate import validate_graph  # noqa: E402
from creel.verify.graph_match import GraphMatch  # noqa: E402
from creel.verify.protocol import VerificationContext  # noqa: E402
from creel.verify.rubric import LLMRubric  # noqa: E402


@pytest.fixture(scope="module")
def case():
    return corpus.build_case()


def test_extraction_matches_expected_graph(case):
    result = evaluate_case(case)
    assert result.passed
    assert result.score == pytest.approx(1.0)


def test_extracted_graph_conforms_to_grammar(case):
    result = evaluate_case(case)
    assert validate_graph(result.actual_graph, case.spec) == []


def test_all_node_and_edge_families_present(case):
    g = evaluate_case(case).actual_graph
    counts = {t: len(list(g.nodes_of_type(t)))
              for t in ("donor", "project", "cross_cutting_area", "output", "outcome", "indicator")}
    assert counts == {"donor": 2, "project": 2, "cross_cutting_area": 2,
                      "output": 2, "outcome": 2, "indicator": 2}
    edge_counts = {t: len(list(g.edges_of_type(t)))
                   for t in ("funds", "addresses", "delivers", "contributes_to", "measured_by")}
    assert edge_counts == {"funds": 3, "addresses": 2, "delivers": 2,
                           "contributes_to": 2, "measured_by": 2}


def test_values_live_on_edges(case):
    g = evaluate_case(case).actual_graph
    # funding amount on a funds edge
    funds = next(e for e in g.edges_of_type("funds") if e.source == "donor:government-of-norway"
                 and e.target == "project:prj-001")
    assert funds.attributes == {"amount": 3_000_000, "currency": "USD", "transaction_type": "commitment"}
    # indicator value on a measured_by edge
    measured = next(e for e in g.edges_of_type("measured_by") if e.target == "indicator:ind-1")
    assert measured.attributes["baseline"] == 1000 and measured.attributes["actual"] == 4200


def test_every_element_has_evidence(case):
    g = evaluate_case(case).actual_graph
    for node in g.nodes():
        assert node.id in g.evidence
    for edge in g.edges():
        assert edge.id in g.evidence


def test_verifier_catches_a_wrong_funding_amount(case):
    # Perturb the expected graph: a single wrong funding amount must lower the score
    # AND surface as a structured mismatch (decomposable partial credit, not all-or-nothing).
    doc = to_canonical_dict(case.expected_graph)
    for edge in doc["edges"]:
        if edge["type"] == "funds" and edge["source"] == "donor:government-of-norway" \
                and edge["target"] == "project:prj-001":
            edge["attributes"]["amount"] = 9_999_999  # wrong
    perturbed = from_canonical_dict(doc)

    actual = evaluate_case(case).actual_graph
    verifier = GraphMatch(spec=case.spec, attribute_verifiers=corpus.attribute_verifiers())
    verdict = verifier(actual, perturbed, context=VerificationContext(spec=case.spec))
    assert verdict.score < 1.0
    mismatches = verdict.details["attributes"]["mismatches"]
    assert any(m["attr"] == "amount" and m["expected"] == 9_999_999 for m in mismatches)


def test_normalized_verifier_tolerates_statement_representation(case):
    # Same meaning, different surface form: NormalizedMatch (the configured verifier
    # for statements) must still score it correct where a raw == would fail.
    doc = to_canonical_dict(case.expected_graph)
    doc["nodes"]["outcome:oc-1"]["attributes"]["statement"] = \
        "  COMMUNITIES   HAVE   sustained access to CLEAN water  "
    perturbed = from_canonical_dict(doc)

    actual = evaluate_case(case).actual_graph
    verifier = GraphMatch(spec=case.spec, attribute_verifiers=corpus.attribute_verifiers())
    verdict = verifier(actual, perturbed, context=VerificationContext(spec=case.spec))
    assert verdict.score == pytest.approx(1.0)  # normalization absorbs the difference


def test_llm_rubric_can_grade_statements_in_graph_match(case):
    # Demonstrate an LLM-defined verifier wired into graph_match for a prose field,
    # using an injected fake judge (deterministic, no network).
    judge = lambda prompt: {"score": 1.0, "reason": "semantically equivalent outcome statement"}
    actual = evaluate_case(case).actual_graph
    verifier = GraphMatch(
        spec=case.spec,
        attribute_verifiers={("outcome", "statement"): LLMRubric(criterion="Same outcome meaning.")},
    )
    ctx = VerificationContext(spec=case.spec, services={"judge": judge})
    verdict = verifier(actual, case.expected_graph, context=ctx)
    assert verdict.passed


def test_corpus_runner_summary(case):
    summary = evaluate_corpus([case]).summary()
    assert summary["pass_rate"] == 1.0
    assert summary["mean_score"] == pytest.approx(1.0)
    assert "unhcr-rbm" in summary["cases"]
