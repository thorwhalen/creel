"""Tests for the natural-language ``llm_rubric`` verifier (G-Eval) with a fake judge.

The judge model is injected, so these tests are fully deterministic and need no
network — exactly how creel keeps LLM-defined verifiers testable.
"""

import json

import pytest

from creel.spec.model import NodeType
from creel.verify.protocol import VerificationContext
from creel.verify.rubric import LLMRubric, schema_description_verifier


def _judge_returning(score, reason="because"):
    """A fake judge: ignores the prompt, returns a fixed verdict."""
    return lambda prompt: {"score": score, "reason": reason}


def test_llm_rubric_uses_injected_judge():
    ctx = VerificationContext(services={"judge": _judge_returning(1.0, "matches intent")})
    v = LLMRubric(criterion="The statement expresses an outcome about protection.")
    verdict = v("Refugees access protection services", "...", context=ctx)
    assert verdict.passed and verdict.score == 1.0
    assert verdict.reason == "matches intent"  # reason is mandatory and retained


def test_llm_rubric_fails_below_threshold():
    ctx = VerificationContext(services={"judge": _judge_returning(0.2)})
    v = LLMRubric(criterion="x", threshold=0.5)
    assert not v("a", "b", context=ctx).passed


def test_llm_rubric_parses_json_string_response():
    judge = lambda prompt: 'Here is my verdict: {"score": 0.9, "reason": "close enough"} done.'
    ctx = VerificationContext(services={"judge": judge})
    verdict = LLMRubric(criterion="x")("a", "b", context=ctx)
    assert verdict.score == 0.9 and verdict.reason == "close enough"


def test_llm_rubric_requires_a_judge():
    with pytest.raises(ValueError, match="needs a judge"):
        LLMRubric(criterion="x")("a", "b", context=VerificationContext())


def test_llm_rubric_prompt_contains_criterion_and_candidate():
    captured = {}
    def judge(prompt):
        captured["prompt"] = prompt
        return {"score": 1.0, "reason": "ok"}
    ctx = VerificationContext(services={"judge": judge})
    LLMRubric(criterion="MUST mention water")("clean water", "potable water", context=ctx)
    assert "MUST mention water" in captured["prompt"]
    assert "clean water" in captured["prompt"]       # candidate
    assert "potable water" in captured["prompt"]      # reference


def test_schema_as_verifier_default_seeds_from_description():
    et = NodeType("outcome", description="A measurable change in the lives of people of concern.")
    v = schema_description_verifier(et)
    assert isinstance(v, LLMRubric)
    assert "measurable change" in v.criterion


def test_reference_free_grading_omits_reference():
    captured = {}
    def judge(prompt):
        captured["prompt"] = prompt
        return {"score": 0.7, "reason": "plausible"}
    ctx = VerificationContext(services={"judge": judge})
    LLMRubric(criterion="Is a valid donor name", reference_free=True)("Government X", None, context=ctx)
    assert "Reference" not in captured["prompt"]
