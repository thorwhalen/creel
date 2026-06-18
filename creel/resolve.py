"""Entity resolution — merge nodes that name the same real entity (decision #14 / D-OP8).

Messy multi-source documents (field-written, non-native English, OCR'd) name the
same entity in different ways — "Foundation Alpha" / "Alpha Fnd. (MFA)" /
"the Alpha foundation". Per the changed decision #14 (report R14 §5), resolution is a
**required**, pluggable cascade — *blocking → matching → merging* — defaulting to
cheap deterministic strategies (exact id → normalize-before-merge → registry) with
hooks for embedding/LLM adjudication.

A :class:`Resolver` decides whether two nodes are the same entity. :func:`resolve_graph`
applies one as a post-extraction pass: it blocks by node type, clusters by transitive
sameness (union-find), merges each cluster into one canonical node, and remaps every
edge — non-destructively returning a new graph with a ``merges`` report.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

from creel.extract.transforms import slug
from creel.graph.model import Graph, Node

# Tokens stripped during entity normalization (legal forms + honorifics).
_LEGAL = {
    "inc",
    "ltd",
    "llc",
    "corp",
    "co",
    "company",
    "gmbh",
    "plc",
    "sa",
    "ag",
    "srl",
    "bv",
}
_HONORIFIC = {"dr", "mr", "mrs", "ms", "prof", "mme", "m", "the"}


def normalize_entity(text: str) -> str:
    """Normalize an entity mention for matching: casefold, strip punctuation/legal/honorific."""
    cleaned = re.sub(r"[^\w\s]", " ", str(text).lower())
    tokens = [t for t in cleaned.split() if t not in _LEGAL and t not in _HONORIFIC]
    return " ".join(tokens)


@runtime_checkable
class Resolver(Protocol):
    """Decide whether two nodes denote the same real entity."""

    def same(self, a: Node, b: Node, *, context: Any = None) -> bool:
        """Return ``True`` if ``a`` and ``b`` are the same entity."""
        ...


@dataclass
class NormalizeResolver:
    """Match by a normalized key attribute (+ an optional alias table). The cheap default."""

    key: str = "name"
    aliases: Mapping[str, str] = field(default_factory=dict)

    def _key(self, node: Node) -> Optional[str]:
        value = node.attributes.get(self.key)
        if value is None:
            return None
        norm = normalize_entity(str(value))
        return self.aliases.get(str(value), self.aliases.get(norm, norm))

    def same(self, a: Node, b: Node, *, context: Any = None) -> bool:
        ka = self._key(a)
        return ka is not None and ka == self._key(b)

    def canonical_id(self, cluster: Sequence[Node]) -> str:
        """A stable id from the normalized key + type."""
        rep = cluster[0]
        type_label = rep.types[0] if rep.types else "node"
        return f"{type_label}:{slug(self._key(rep) or rep.id)}"


@dataclass
class RegistryResolver:
    """Resolve mentions to canonical ids via an authoritative lookup table (an org registry)."""

    registry: Mapping[str, str]
    key: str = "name"

    def _canon(self, node: Node) -> Optional[str]:
        value = node.attributes.get(self.key)
        if value is None:
            return None
        return self.registry.get(str(value)) or self.registry.get(
            normalize_entity(str(value))
        )

    def same(self, a: Node, b: Node, *, context: Any = None) -> bool:
        ca = self._canon(a)
        return ca is not None and ca == self._canon(b)

    def canonical_id(self, cluster: Sequence[Node]) -> str:
        """The registry's canonical id for the cluster."""
        return self._canon(cluster[0]) or cluster[0].id


@dataclass
class LLMResolver:
    """Adjudicate hard pairs with an injected judge ``(name_a, name_b) -> bool``.

    The judge is injected (testable with a fake; an LLM in production via ``creel[llm]``).
    Reserve this for pairs the cheap resolvers leave ambiguous — it is the costly tail.
    """

    judge: Callable[[str, str], bool]
    key: str = "name"

    def same(self, a: Node, b: Node, *, context: Any = None) -> bool:
        return bool(
            self.judge(
                str(a.attributes.get(self.key, "")), str(b.attributes.get(self.key, ""))
            )
        )


@dataclass
class CascadeResolver:
    """Try resolvers in order (cheapest first); two nodes match if ANY resolver matches."""

    resolvers: Sequence[Resolver]

    def same(self, a: Node, b: Node, *, context: Any = None) -> bool:
        return any(r.same(a, b, context=context) for r in self.resolvers)

    def canonical_id(self, cluster: Sequence[Node]) -> str:
        """Use the first resolver that can name a canonical id; else the smallest id."""
        for r in self.resolvers:
            namer = getattr(r, "canonical_id", None)
            if namer is not None:
                cid = namer(cluster)
                if cid:
                    return cid
        return min(n.id for n in cluster)


def resolve_graph(graph: Graph, resolver: Resolver, *, context: Any = None) -> Graph:
    """Return a new graph with same-entity nodes merged and edges remapped.

    Blocking (by node type-tuple) → matching (``resolver.same``) → merging (union-find;
    one canonical node per cluster, attributes first-wins) → edge remap. The original
    graph is untouched; the result's ``report["merges"]`` lists each merge.
    """
    canonical_of: dict[str, str] = {}
    merged: Graph = Graph()
    merges: list[dict[str, Any]] = []

    # index per-attribute evidence (keys shaped ``(element_id, attr)``, A1) by id so
    # it can be remapped onto the canonical node — otherwise value-level provenance
    # is silently lost on every merge (D8).
    attr_evidence: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    for key, ev in graph.evidence.items():
        if isinstance(key, tuple) and len(key) == 2:
            attr_evidence[key[0]].append((key[1], ev))

    blocks: dict[tuple, list[Node]] = defaultdict(list)
    for node in graph.nodes():
        blocks[node.types].append(node)

    for block_nodes in blocks.values():
        for cluster in _cluster(block_nodes, resolver, context):
            cid = _canonical_id(cluster, resolver)
            attributes: dict[str, Any] = {}
            for node in cluster:  # first-wins merge of attributes
                attributes = {**node.attributes, **attributes}
                canonical_of[node.id] = cid
            merged.add_node(cid, types=cluster[0].types, attributes=attributes)
            # carry evidence for EVERY cluster member onto cid (first-wins, matching
            # the attribute merge): element-level + per-attribute (A1).
            if cid in graph.evidence:
                merged.evidence[cid] = graph.evidence[cid]
            for member in cluster:
                if member.id in graph.evidence:
                    merged.evidence.setdefault(cid, graph.evidence[member.id])
                for attr, ev in attr_evidence.get(member.id, ()):
                    merged.evidence.setdefault((cid, attr), ev)
            if len(cluster) > 1:
                merges.append(
                    {"canonical": cid, "merged": sorted(n.id for n in cluster)}
                )

    for edge in graph.edges():
        source = canonical_of.get(edge.source, edge.source)
        target = canonical_of.get(edge.target, edge.target)
        if not (merged.has_node(source) and merged.has_node(target)):
            continue
        merged.add_edge(
            edge.id,
            source=source,
            target=target,
            type=edge.type,
            attributes=edge.attributes,
        )
        if edge.id in graph.evidence:
            merged.evidence[edge.id] = graph.evidence[edge.id]
        for attr, ev in attr_evidence.get(
            edge.id, ()
        ):  # per-attribute edge evidence (A1)
            merged.evidence[(edge.id, attr)] = ev

    merged.report["merges"] = merges
    return merged


def _cluster(
    nodes: Sequence[Node], resolver: Resolver, context: Any
) -> list[list[Node]]:
    parent = {n.id: n.id for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if resolver.same(nodes[i], nodes[j], context=context):
                union(nodes[i].id, nodes[j].id)

    groups: dict[str, list[Node]] = defaultdict(list)
    for node in nodes:
        groups[find(node.id)].append(node)
    return list(groups.values())


def _canonical_id(cluster: Sequence[Node], resolver: Resolver) -> str:
    namer = getattr(resolver, "canonical_id", None)
    if namer is not None:
        cid = namer(cluster)
        if cid:
            return cid
    return min(n.id for n in cluster)
