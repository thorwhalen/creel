"""``graph_match`` — compare a whole extracted graph to an expected one.

Per decision D9 this is **decomposable partial credit**, not all-or-nothing: it
scores nodes and edges with set-based precision/recall/F1 (after canonicalisation)
*and* scores the attributes of matched elements with per-attribute sub-verifiers
(``numeric_tolerance`` for amounts, ``normalized`` for strings, …). The overall
score is a weighted blend, and ``details`` carries a full breakdown for audit.

Nodes are matched by id (creel's ids are deterministic, so a correct extraction and
the expected graph share them). Edges are matched by their canonical key
``(type, source, target)`` with greedy best-attribute alignment for parallel edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from creel.graph.model import Edge, Graph, Node
from creel.spec.model import GraphSpec, effective_attributes
from creel.verify.kinds import NormalizedMatch, NumericTolerance
from creel.verify.protocol import Verdict, VerificationContext, Verifier, passed_at
from creel.verify.registry import register_verifier

_NUMERIC_RANGES = {"decimal", "float", "integer"}


@register_verifier("graph_match")
@dataclass
class GraphMatch:
    """Score an ``actual`` :class:`Graph` against an ``expected`` one (partial credit)."""

    spec: Optional[GraphSpec] = None
    attribute_verifiers: Mapping[tuple, Verifier] = field(default_factory=dict)
    node_weight: float = 1.0
    edge_weight: float = 1.0
    attr_weight: float = 1.0
    threshold: float = 0.8

    def __call__(self, actual: Graph, expected: Graph, *, context=None) -> Verdict:
        spec = self.spec or (context.spec if context else None)

        node_pr = _set_prf(
            {n.id for n in actual.nodes()}, {n.id for n in expected.nodes()}
        )
        edge_pr = _edge_prf(actual, expected)
        attr = self._attribute_score(actual, expected, spec, context)

        components = [
            (self.node_weight, node_pr["f1"]),
            (self.edge_weight, edge_pr["f1"]),
            (self.attr_weight, attr["score"]),
        ]
        total_w = sum(w for w, _ in components) or 1.0
        score = sum(w * s for w, s in components) / total_w
        return Verdict(
            score,
            passed_at(score, self.threshold),
            f"graph_match={score:.3f} (nodeF1={node_pr['f1']:.3f} edgeF1={edge_pr['f1']:.3f} attr={attr['score']:.3f})",
            {"nodes": node_pr, "edges": edge_pr, "attributes": attr},
        )

    def _attribute_score(self, actual, expected, spec, context) -> dict[str, Any]:
        scores: list[float] = []
        mismatches: list[dict[str, Any]] = []
        for exp_node in expected.nodes():
            if not actual.has_node(exp_node.id):
                continue
            self._score_element(
                actual.node(exp_node.id),
                exp_node,
                exp_node.types[0] if exp_node.types else None,
                spec,
                context,
                scores,
                mismatches,
                "node",
            )
        for exp_edge in expected.edges():
            act = _find_matching_edge(actual, exp_edge)
            if act is None:
                continue
            self._score_element(
                act, exp_edge, exp_edge.type, spec, context, scores, mismatches, "edge"
            )
        score = sum(scores) / len(scores) if scores else 1.0
        return {"score": score, "compared": len(scores), "mismatches": mismatches}

    def _score_element(
        self, act, exp, type_id, spec, context, scores, mismatches, kind
    ) -> None:
        exp_attrs = exp.attributes
        if not exp_attrs:
            return
        schema = effective_attributes(spec, type_id) if (spec and type_id) else {}
        for name, exp_val in exp_attrs.items():
            verifier = self._verifier_for(type_id, name, schema.get(name))
            act_val = act.attributes.get(name)
            verdict = verifier(act_val, exp_val, context=context)
            scores.append(verdict.score)
            if not verdict.passed:
                mismatches.append(
                    {
                        "kind": kind,
                        "id": exp.id,
                        "attr": name,
                        "expected": exp_val,
                        "actual": act_val,
                        "reason": verdict.reason,
                    }
                )

    def _verifier_for(self, type_id, name, attr_schema) -> Verifier:
        override = self.attribute_verifiers.get(
            (type_id, name)
        ) or self.attribute_verifiers.get(name)
        if override is not None:
            return override
        if attr_schema is not None and attr_schema.range in _NUMERIC_RANGES:
            return NumericTolerance()
        return NormalizedMatch()


def _set_prf(actual: set, expected: set) -> dict[str, Any]:
    tp = len(actual & expected)
    precision = tp / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = tp / len(expected) if expected else (1.0 if not actual else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
    }


def _edge_key(edge: Edge) -> tuple:
    return (edge.type, edge.source, edge.target)


def _edge_prf(actual: Graph, expected: Graph) -> dict[str, Any]:
    from collections import Counter

    a = Counter(_edge_key(e) for e in actual.edges())
    e = Counter(_edge_key(x) for x in expected.edges())
    tp = sum((a & e).values())
    a_total, e_total = sum(a.values()), sum(e.values())
    precision = tp / a_total if a_total else (1.0 if not e_total else 0.0)
    recall = tp / e_total if e_total else (1.0 if not a_total else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched": tp,
        "expected_total": e_total,
        "actual_total": a_total,
    }


def _find_matching_edge(actual: Graph, expected_edge: Edge) -> Optional[Edge]:
    """Find an actual edge with the same (type, source, target); for parallels, the
    one whose attributes best match (most equal values)."""
    candidates = [
        e
        for e in actual.edges_between(expected_edge.source, expected_edge.target)
        if e.type == expected_edge.type
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def overlap(edge: Edge) -> int:
        return sum(
            1
            for k, v in expected_edge.attributes.items()
            if edge.attributes.get(k) == v
        )

    return max(candidates, key=overlap)
