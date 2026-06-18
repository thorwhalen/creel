"""``llm_rubric`` — a verifier defined purely by natural-language instructions.

This is the capability the user emphasised: a verifier that is *fully specified by
instructions to an LLM*, which judges robustly where a hardcoded comparison cannot
(decision D9). It follows the G-Eval shape — a criterion (optionally expanded into
chain-of-thought eval steps) form-filled into a normalised ``[0, 1]`` score with a
mandatory ``reason``.

The judge model is **injected** via ``context.services["judge"]`` so the core never
pins a provider SDK, the call is testable with a fake judge, and the **judge can be
held distinct from the extractor model** (self-preference-bias mitigation). The
default rubric is *seeded from the element's own schema ``description``* — the dual
of schema-as-extractor (schema-as-verifier).

A judge is any callable ``(prompt: str) -> {"score": float, "reason": str}`` (a raw
JSON string with those keys is also accepted).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from creel.verify.protocol import Verdict, VerificationContext, passed_at
from creel.verify.registry import register_verifier


@register_verifier("llm_rubric")
@dataclass
class LLMRubric:
    """Grade ``actual`` (optionally against ``expected``) by a natural-language criterion.

    Set ``reference_free=True`` to grade ``actual`` against the criterion alone (no
    gold value). ``threshold`` sets the pass bar.
    """

    criterion: str
    threshold: float = 0.5
    reference_free: bool = False
    instructions: Optional[str] = None  # extra eval steps; auto-built if None

    def __call__(
        self, actual, expected=None, *, context: Optional[VerificationContext] = None
    ) -> Verdict:
        judge = (
            context.services.get("judge") if (context and context.services) else None
        )
        if judge is None:
            raise ValueError(
                "llm_rubric needs a judge: pass context.services={'judge': callable}. "
                "The judge must differ from the extractor model (D9)."
            )
        prompt = self._build_prompt(actual, expected)
        raw = judge(prompt)
        score, reason = _parse_judge(raw)
        return Verdict(
            score,
            passed_at(score, self.threshold),
            reason or "(no reason returned)",
            {
                "criterion": self.criterion,
                "judge_raw": raw if isinstance(raw, str) else dict(raw),
            },
        )

    def _build_prompt(self, actual: Any, expected: Any) -> str:
        steps = self.instructions or _default_steps(self.criterion)
        ref = (
            ""
            if self.reference_free or expected is None
            else (f"\nReference (expected) answer:\n{_fmt(expected)}\n")
        )
        return (
            "You are a careful evaluator. Apply the criterion below and return ONLY a JSON "
            'object: {"score": <float 0..1>, "reason": "<one sentence>"}.\n\n'
            f"Criterion:\n{self.criterion}\n\n"
            f"Evaluation steps:\n{steps}\n"
            f"{ref}\n"
            f"Candidate answer to grade:\n{_fmt(actual)}\n\n"
            "Score 1.0 means fully satisfies the criterion; 0.0 means not at all. "
            "Return only the JSON object."
        )


def schema_description_verifier(
    element_type: Any, *, threshold: float = 0.5
) -> LLMRubric:
    """Build the default ``llm_rubric`` for an element, seeded from its ``description``.

    This is the schema-as-verifier default: the same ``description`` that drives the
    schema-as-extractor also becomes the grading criterion.
    """
    desc = getattr(element_type, "description", None) or (
        f"The extracted value correctly represents a {getattr(element_type, 'id', 'value')}."
    )
    return LLMRubric(criterion=desc, threshold=threshold, reference_free=False)


def _default_steps(criterion: str) -> str:
    return (
        "1. Read the criterion and the candidate (and reference, if given).\n"
        "2. Identify whether the candidate satisfies the criterion in meaning, not just wording.\n"
        "3. Note any factual or semantic mismatch.\n"
        "4. Assign a calibrated score in [0,1] and justify it in one sentence."
    )


def _fmt(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _parse_judge(raw: Any) -> tuple[float, str]:
    """Coerce a judge response into ``(score, reason)``."""
    data: Mapping[str, Any]
    if isinstance(raw, Mapping):
        data = raw
    elif isinstance(raw, str):
        try:
            data = json.loads(_extract_json(raw))
        except (ValueError, json.JSONDecodeError):
            raise ValueError(f"judge returned unparseable response: {raw!r}")
    else:
        raise TypeError(f"judge must return a mapping or JSON string, got {type(raw)}")
    try:
        score = float(data["score"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"judge response missing a numeric 'score': {data!r}")
    return max(0.0, min(1.0, score)), str(data.get("reason", ""))


def _extract_json(text: str) -> str:
    """Extract the first **balanced** ``{...}`` object from judge text.

    Uses brace-counting (string-aware) rather than ``rfind("}")`` so a judge that
    appends prose containing a ``}`` after a valid object doesn't break parsing.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]  # unbalanced; let json.loads raise a clear error
