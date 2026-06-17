"""The evaluation runner — score an extraction corpus with pluggable verifiers.

A corpus case is ``{sources, spec, bindings, expected_graph, verifier_overrides?}``
(decision D9). The runner extracts the actual graph and scores it against the
expected one — by default with :class:`~creel.verify.graph_match.GraphMatch`
(decomposable partial credit), or with a caller-supplied verifier. Per-attribute
verifiers attach by ``(type, attribute)`` so most cases need zero per-item config.

This is deliberately thin (decision D11): a function over cases, not a framework.
Roll-ups (per-graph node/edge/attribute scores) come straight from the verdict
``details``; a richer per-type breakdown can be layered on without changing the
contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from creel.facade import extract
from creel.graph.model import Graph
from creel.spec.model import GraphSpec
from creel.verify.graph_match import GraphMatch
from creel.verify.protocol import Verdict, VerificationContext, Verifier


@dataclass
class CorpusCase:
    """One evaluation item: inputs + how to extract + the expected graph."""

    name: str
    sources: Any
    spec: GraphSpec
    bindings: Any  # the `extractors` argument to extract()
    expected_graph: Graph
    verifier: Optional[Verifier] = None
    attribute_verifiers: Mapping[tuple, Verifier] = field(default_factory=dict)
    services: Mapping[str, Any] = field(default_factory=dict)
    on_missing_binding: str = "skip"


@dataclass
class CaseResult:
    """The outcome of evaluating one case: the verdict + the produced graph."""

    name: str
    verdict: Verdict
    actual_graph: Graph

    @property
    def score(self) -> float:
        """The case's normalised score in ``[0, 1]``."""
        return self.verdict.score

    @property
    def passed(self) -> bool:
        """Whether the case met its verifier's threshold."""
        return self.verdict.passed


@dataclass
class CorpusResult:
    """Aggregate outcome over a corpus."""

    cases: Sequence[CaseResult]

    @property
    def mean_score(self) -> float:
        """Mean case score (``1.0`` for an empty corpus)."""
        return sum(c.score for c in self.cases) / len(self.cases) if self.cases else 1.0

    @property
    def pass_rate(self) -> float:
        """Fraction of cases that passed."""
        return (
            sum(1 for c in self.cases if c.passed) / len(self.cases)
            if self.cases
            else 1.0
        )

    def summary(self) -> dict[str, Any]:
        """A compact, JSON-ready summary (mean score, pass rate, per-case scores)."""
        return {
            "mean_score": self.mean_score,
            "pass_rate": self.pass_rate,
            "cases": {
                c.name: {"score": c.score, "passed": c.passed} for c in self.cases
            },
        }


def evaluate_case(case: CorpusCase) -> CaseResult:
    """Extract ``case.sources`` and score the result against ``case.expected_graph``."""
    actual = extract(
        case.sources,
        case.spec,
        case.bindings,
        services=case.services,
        on_missing_binding=case.on_missing_binding,
    )
    verifier = case.verifier or GraphMatch(
        spec=case.spec, attribute_verifiers=dict(case.attribute_verifiers)
    )
    context = VerificationContext(spec=case.spec, services=case.services)
    verdict = verifier(actual, case.expected_graph, context=context)
    return CaseResult(case.name, verdict, actual)


def evaluate_corpus(cases: Sequence[CorpusCase]) -> CorpusResult:
    """Evaluate every case and aggregate the results."""
    return CorpusResult([evaluate_case(c) for c in cases])
