"""Tests for the verifier-kind taxonomy: each kind, known-good and known-bad."""

from creel.verify.kinds import (
    Composite,
    ExactMatch,
    NormalizedMatch,
    NumericTolerance,
    SchemaConstraint,
    SemanticSimilarity,
    SetMatch,
)
from creel.verify.protocol import VerificationContext
from creel.verify.registry import available_verifiers, build_verifier


def test_exact():
    assert ExactMatch()("a", "a").passed
    assert not ExactMatch()("a", "b").passed
    assert ExactMatch()("a", "b").score == 0.0


def test_normalized():
    v = NormalizedMatch()
    assert v(" Government  X ", "government x").passed
    assert not v("Gov X", "Government X").passed


def test_numeric_tolerance():
    assert NumericTolerance()(1_000_000, 1_000_000.0).passed  # int vs float
    assert NumericTolerance(rel_tol=0.01)(101, 100).passed
    assert not NumericTolerance(rel_tol=0.01)(120, 100).passed
    assert not NumericTolerance()("lots", 100).passed  # non-numeric


def test_set_match_partial_credit():
    v = SetMatch()
    full = v({"a", "b", "c"}, {"a", "b", "c"})
    assert full.passed and full.score == 1.0
    partial = v({"a", "b"}, {"a", "b", "c"})  # missing 'c'
    assert 0 < partial.score < 1
    assert partial.details["missing"] == ["c"]


def test_set_match_with_key():
    v = SetMatch(key=lambda d: d["id"])
    a = [{"id": 1, "x": 9}, {"id": 2, "x": 8}]
    e = [{"id": 1, "x": 0}, {"id": 2, "x": 0}]
    assert v(a, e).score == 1.0  # keyed on id only


def test_schema_constraint_predicate():
    v = SchemaConstraint(predicate=lambda x: x > 0, description="positive")
    assert v(5).passed
    assert not v(-1).passed


def test_schema_constraint_against_grammar(sample_spec, sample_graph):
    v = SchemaConstraint(spec=sample_spec)
    good = v(sample_graph)
    assert good.passed and good.score == 1.0


def test_semantic_similarity_lexical_fallback():
    v = SemanticSimilarity(threshold=0.9)
    assert v("clean water delivered", "clean water delivered").passed
    low = v("clean water", "armed conflict in the region")
    assert not low.passed
    assert "fallback" in low.details["method"]


def test_semantic_similarity_with_injected_embedder():
    # tiny fake embedder: bag-of-words vector over a fixed vocab
    vocab = ["clean", "water", "housing"]
    def embed(text):
        words = text.lower().split()
        return [float(words.count(w)) for w in vocab]
    ctx = VerificationContext(services={"embedder": embed})
    v = SemanticSimilarity(threshold=0.99)
    assert v("clean water", "water clean", context=ctx).passed  # same bag → cosine 1
    assert not v("clean water", "housing housing", context=ctx).passed


def test_composite_weighted():
    v = Composite(components=(
        ("amount", NumericTolerance(rel_tol=0.0), 2.0),
        ("currency", ExactMatch(), 1.0),
    ))
    good = v({"x": 1}, {"x": 1})  # both sub-verifiers compare the same objects here
    # amount: NumericTolerance on dicts -> non-numeric -> 0; currency: ExactMatch dict==dict ->1
    # weighted = (2*0 + 1*1)/3
    assert abs(good.score - (1 / 3)) < 1e-9
    assert "components" in good.details


def test_registry_builds_kinds():
    assert {"exact", "normalized", "numeric_tolerance", "set_match", "schema_constraint",
            "semantic_similarity", "composite", "llm_rubric"} <= set(available_verifiers())
    v = build_verifier("numeric_tolerance", rel_tol=0.05)
    assert isinstance(v, NumericTolerance)
