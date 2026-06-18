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

        node_a = {n.id for n in actual.nodes()}
        node_e = {n.id for n in expected.nodes()}
        node_pr = _set_prf(node_a, node_e)
        edge_pr = _edge_prf(actual, expected)
        attr = self._attribute_score(actual, expected, spec, context)

        # Only blend components that actually MEASURED something. A vacuously-true
        # 1.0 (no expected edges, or no attributes compared) must not inflate the
        # score — an empty extraction should score 0, not 0.667.
        components = []
        if node_a or node_e:
            components.append((self.node_weight, node_pr["f1"]))
        if edge_pr["expected_total"] or edge_pr["actual_total"]:
            components.append((self.edge_weight, edge_pr["f1"]))
        if attr["compared"]:
            components.append((self.attr_weight, attr["score"]))

        if not components:  # both graphs empty -> trivially perfect
            score = 1.0
        else:
            total_w = sum(w for w, _ in components) or 1.0
            score = sum(w * s for w, s in components) / total_w
        return Verdict(
            score,
            passed_at(score, self.threshold),
            f"graph_match={score:.3f} (nodeF1={node_pr['f1']:.3f} edgeF1={edge_pr['f1']:.3f} attr={attr['score']:.3f})",
            {"nodes": node_pr, "edges": edge_pr, "attributes": attr},
        )

    def _attribute_score(self, actual, expected, spec, context) -> dict[str, Any]:
        from collections import defaultdict

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
        # Assign each expected edge to a DISTINCT actual edge within its
        # (type, source, target) group, greedily by attribute overlap, so no single
        # actual edge backs two expected parallel edges (which inflated credit).
        exp_by_key: dict[tuple, list[Edge]] = defaultdict(list)
        for exp_edge in expected.edges():
            exp_by_key[_edge_key(exp_edge)].append(exp_edge)
        for (type_id, src, tgt), exp_edges in exp_by_key.items():
            cands = [e for e in actual.edges_between(src, tgt) if e.type == type_id]
            pairs = sorted(
                (
                    (_overlap(exp_edges[ei], cands[ai]), ei, ai)
                    for ei in range(len(exp_edges))
                    for ai in range(len(cands))
                ),
                key=lambda t: -t[0],
            )
            used_exp: set[int] = set()
            used_act: set[int] = set()
            for _, ei, ai in pairs:
                if ei in used_exp or ai in used_act:
                    continue
                used_exp.add(ei)
                used_act.add(ai)
                self._score_element(
                    cands[ai], exp_edges[ei], type_id, spec, context,
                    scores, mismatches, "edge",
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


def _overlap(expected_edge: Edge, edge: Edge) -> int:
    """Count attribute values an actual edge shares with an expected one (for greedy
    alignment of parallel edges)."""
    return sum(
        1 for k, v in expected_edge.attributes.items() if edge.attributes.get(k) == v
    )
