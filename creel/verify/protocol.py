"""The verifier contract — the evaluation-time dual of the extractor contract.

The user-emphasized principle (decision D9): comparing an *actual* extraction to an
*expected* one is **not** a hardcoded equality check, but a pluggable
:class:`Verifier` — and many verifiers are fully defined by natural-language
instructions to an LLM (see :mod:`creel.verify.rubric`).

A :class:`Verifier` is any callable ``(actual, expected, *, context) -> Verdict``,
mirroring the callable :class:`~creel.extract.protocol.Extractor`. Every verdict is
a normalised ``score`` in ``[0, 1]`` plus a boolean ``passed``, an auditable
``reason`` (mandatory for LLM judges), and structured ``details`` (per-component
scores, matched pairs) — the exact shape the whole eval ecosystem converged on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class Verdict:
    """The result of a verification: a normalised score plus an audit trail."""

    score: float
    passed: bool
    reason: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Clamp defensively so downstream roll-ups never see out-of-range scores.
        if not 0.0 <= self.score <= 1.0:
            object.__setattr__(self, "score", max(0.0, min(1.0, self.score)))

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (reasons retained for audit)."""
        return {
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class VerificationContext:
    """Optional context a verifier may consult (element schema, services, config).

    ``services`` carries injected dependencies such as an LLM ``"judge"`` (which
    must differ from the extractor model — D9) or an ``"embedder"`` for semantic
    similarity. ``element_type``/``spec`` let a verifier read the schema (e.g. to
    seed an ``llm_rubric`` from a ``description``).
    """

    element_type: Optional[Any] = None
    spec: Optional[Any] = None
    services: Mapping[str, Any] = field(default_factory=dict)
    config: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class Verifier(Protocol):
    """A strategy that scores an ``actual`` value against an ``expected`` one."""

    def __call__(
        self, actual: Any, expected: Any, *, context: Optional[VerificationContext] = None
    ) -> Verdict:
        """Return a :class:`Verdict` scoring ``actual`` against ``expected``."""
        ...


def passed_at(score: float, threshold: float) -> bool:
    """Helper: ``True`` iff ``score >= threshold`` (used uniformly by all kinds)."""
    return score >= threshold
