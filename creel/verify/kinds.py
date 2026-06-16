"""The verifier-kind taxonomy — pick the comparison that matches the field's nature.

These parallel the node/edge/attribute taxonomy (decision D9). The rule: use the
*cheapest verifier that is right* — ``exact`` only where exactness is correct,
``numeric_tolerance`` for amounts/indicator values, ``set_match`` for unordered
collections, ``schema_constraint`` for no-gold property checks, ``semantic_similarity``
or ``llm_rubric`` (see :mod:`creel.verify.rubric`) for free text, and ``composite``
to weight several together.

Each kind is a callable verifier; each is registered so a binding can name it.
``graph_match`` (whole-graph comparison) lives in :mod:`creel.verify.graph_match`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Mapping, Optional, Sequence

from creel.verify.protocol import Verdict, VerificationContext, Verifier, passed_at
from creel.verify.registry import register_verifier


# --- exact / normalized --------------------------------------------------------
@register_verifier("exact")
@dataclass
class ExactMatch:
    """``score=1.0`` iff ``actual == expected``; else ``0.0``. The auditable default."""

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        ok = actual == expected
        return Verdict(1.0 if ok else 0.0, ok, "exact match" if ok else f"{actual!r} != {expected!r}")


@register_verifier("normalized")
@dataclass
class NormalizedMatch:
    """Equality after normalising strings (casefold / strip / collapse whitespace)."""

    casefold: bool = True
    strip: bool = True
    collapse_ws: bool = True

    def _norm(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if self.strip:
            value = value.strip()
        if self.collapse_ws:
            value = re.sub(r"\s+", " ", value)
        if self.casefold:
            value = value.casefold()
        return value

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        ok = self._norm(actual) == self._norm(expected)
        return Verdict(
            1.0 if ok else 0.0, ok,
            "normalized match" if ok else f"normalized {actual!r} != {expected!r}",
        )


# --- numeric tolerance ---------------------------------------------------------
@register_verifier("numeric_tolerance")
@dataclass
class NumericTolerance:
    """Compare numbers within an absolute and/or relative tolerance.

    For funding amounts and indicator values on edges — a brittle ``==`` would
    spuriously fail on ``1000000`` vs ``1000000.0`` or rounding.
    """

    abs_tol: float = 0.0
    rel_tol: float = 0.0

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        try:
            a, e = float(actual), float(expected)
        except (TypeError, ValueError):
            return Verdict(0.0, False, f"non-numeric: {actual!r} vs {expected!r}")
        diff = abs(a - e)
        allowed = max(self.abs_tol, self.rel_tol * abs(e))
        ok = diff <= allowed
        return Verdict(
            1.0 if ok else 0.0, ok,
            f"|{a} - {e}| = {diff} {'<=' if ok else '>'} {allowed}",
            {"diff": diff, "allowed": allowed},
        )


# --- set match (P/R/F1 over collections) --------------------------------------
@register_verifier("set_match")
@dataclass
class SetMatch:
    """Set-based precision/recall/F1 over (canonicalised) collections.

    ``key`` maps each item to a hashable canonical form before comparing (so dicts
    or fuzzy items can be aligned). ``score`` is the F1.
    """

    key: Optional[Callable[[Any], Any]] = None
    threshold: float = 1.0

    def _key(self, item: Any) -> Any:
        if self.key is not None:
            return self.key(item)
        try:
            hash(item)
            return item
        except TypeError:
            return json.dumps(item, sort_keys=True, default=str)

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        a = {self._key(x) for x in actual}
        e = {self._key(x) for x in expected}
        tp = len(a & e)
        precision = tp / len(a) if a else (1.0 if not e else 0.0)
        recall = tp / len(e) if e else (1.0 if not a else 0.0)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        return Verdict(
            f1, passed_at(f1, self.threshold),
            f"set F1={f1:.3f} (P={precision:.3f} R={recall:.3f})",
            {
                "precision": precision, "recall": recall, "f1": f1,
                "missing": sorted(map(str, e - a)), "extra": sorted(map(str, a - e)),
            },
        )


# --- schema constraint (no gold value) ----------------------------------------
@register_verifier("schema_constraint")
@dataclass
class SchemaConstraint:
    """Property-based check with **no expected value** — validates ``actual`` itself.

    Pass either a :class:`~creel.spec.model.GraphSpec` (validates a graph against the
    grammar) or a ``predicate(actual) -> bool`` with a ``description``.
    """

    spec: Any = None
    predicate: Optional[Callable[[Any], bool]] = None
    description: str = "schema constraint"

    def __call__(self, actual, expected=None, *, context=None) -> Verdict:
        if self.predicate is not None:
            ok = bool(self.predicate(actual))
            return Verdict(1.0 if ok else 0.0, ok, self.description)
        spec = self.spec or (context.spec if context else None)
        if spec is None:
            raise ValueError("SchemaConstraint needs a spec or a predicate")
        from creel.spec.validate import validate_graph

        issues = validate_graph(actual, spec)
        n = max(1, actual.number_of_nodes + actual.number_of_edges)
        score = max(0.0, 1.0 - len(issues) / n)
        return Verdict(
            score, not issues,
            "conforms to grammar" if not issues else f"{len(issues)} grammar issue(s)",
            {"issues": [str(i) for i in issues]},
        )


# --- semantic similarity ------------------------------------------------------
@register_verifier("semantic_similarity")
@dataclass
class SemanticSimilarity:
    """Similarity of free text. Uses an injected ``embedder`` if available, else a
    deterministic lexical fallback (``difflib`` ratio) — which is flagged, because
    similarity is not equivalence.
    """

    threshold: float = 0.8

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        embedder = (context.services.get("embedder") if context else None)
        if embedder is not None:
            sim = _cosine(embedder(str(actual)), embedder(str(expected)))
            method = "embedding cosine"
        else:
            sim = SequenceMatcher(None, str(actual), str(expected)).ratio()
            method = "lexical (difflib) fallback — not semantic"
        ok = passed_at(sim, self.threshold)
        return Verdict(sim, ok, f"{method} similarity={sim:.3f}", {"method": method})


def _cosine(u: Sequence[float], v: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = sum(a * a for a in u) ** 0.5
    nv = sum(b * b for b in v) ** 0.5
    return dot / (nu * nv) if nu and nv else 0.0


# --- composite ----------------------------------------------------------------
@register_verifier("composite")
@dataclass
class Composite:
    """Weighted combination of named sub-verifiers (promptfoo-style)."""

    components: Sequence[tuple] = field(default_factory=tuple)  # (name, verifier, weight)
    threshold: float = 0.5

    def __call__(self, actual, expected, *, context=None) -> Verdict:
        total_w = sum(w for _, _, w in self.components) or 1.0
        sub: dict[str, Any] = {}
        score = 0.0
        for name, verifier, weight in self.components:
            v = verifier(actual, expected, context=context)
            sub[name] = v.to_dict()
            score += weight * v.score
        score /= total_w
        return Verdict(score, passed_at(score, self.threshold), f"composite={score:.3f}", {"components": sub})


# --- registry factories -------------------------------------------------------
@register_verifier("predicate")
def _predicate_factory(*, predicate: Callable[[Any], bool], description: str = "predicate") -> Verifier:
    return SchemaConstraint(predicate=predicate, description=description)
