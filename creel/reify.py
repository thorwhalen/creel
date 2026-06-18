"""Reification — promote an attributed edge-type to relation-instance nodes (decision #12 / D1).

D1's normalization toggle: an **attributed edge** and a **reified relation-node** are
interchangeable renderings of one fact. :func:`reify` promotes every edge of a given
type into a node carrying the edge's attributes, linked to its original endpoints by
two connector edges; :func:`unreify` inverts it. The pair is **lossless** — a
round-trip reproduces the original graph (a tested invariant).

Use it per-edge-type, on demand, when a relation becomes genuinely n-ary — e.g. an
indicator reading that needs shared ``Period``/``Source``/disaggregation-dimension nodes, or that
will be merged across reporting periods (the node-based resolver then dedups it; see
:mod:`creel.resolve`). Until then, keep the simpler attributed edge (decision #12).

``measured_by`` example::

    reified = reify(graph, "measured_by", node_type="reading")     # edge -> Reading node
    original = unreify(reified, "measured_by", node_type="reading") # back, losslessly
"""

from __future__ import annotations

from typing import Optional

from creel.graph.model import Graph


def _names(edge_type, node_type, subject_edge_type, object_edge_type):
    node_type = node_type or f"{edge_type}_node"
    return (
        node_type,
        subject_edge_type or f"{edge_type}_subject",
        object_edge_type or f"{edge_type}_object",
    )


def reify(
    graph: Graph,
    edge_type: str,
    *,
    node_type: Optional[str] = None,
    subject_edge_type: Optional[str] = None,
    object_edge_type: Optional[str] = None,
) -> Graph:
    """Return a new graph with every ``edge_type`` edge promoted to a node.

    Each promoted edge becomes a node (id = the edge's id, type ``node_type``,
    carrying the edge's attributes), with ``source ──subject──▶ node ──object──▶ target``
    connector edges. All other nodes/edges (and the evidence sidecar) pass through
    unchanged. Other edge-types are untouched, so this is a per-edge-type toggle.
    """
    node_type, subject_edge_type, object_edge_type = _names(
        edge_type, node_type, subject_edge_type, object_edge_type
    )
    # The toggle identifies reified structure by these type names, so they must be
    # fresh: refuse to reuse a node-type or connector edge-type already in the graph
    # (otherwise unreify could not tell reified structure from pre-existing data).
    existing_node_types = {t for node in graph.nodes() for t in node.types}
    if node_type in existing_node_types:
        raise ValueError(
            f"cannot reify to node_type {node_type!r}: nodes of that type already "
            "exist; pass a distinct node_type=..."
        )
    existing_edge_types = {edge.type for edge in graph.edges()}
    for connector in (subject_edge_type, object_edge_type):
        if connector in existing_edge_types:
            raise ValueError(
                f"cannot reify: connector edge type {connector!r} already exists in the "
                "graph; pass a distinct subject_edge_type=/object_edge_type="
            )
    out = Graph()
    for node in graph.nodes():
        out.add_node(node.id, types=node.types, attributes=node.attributes)
        _carry_evidence(graph, out, node.id)

    for edge in graph.edges():
        if edge.type != edge_type:
            out.add_edge(
                edge.id,
                source=edge.source,
                target=edge.target,
                type=edge.type,
                attributes=edge.attributes,
            )
            _carry_evidence(graph, out, edge.id)
            continue
        if out.has_node(edge.id):
            raise ValueError(
                f"cannot reify edge {edge.id!r}: a node already uses that id "
                "(node/edge id collision)"
            )
        out.add_node(edge.id, types=(node_type,), attributes=edge.attributes)
        _carry_evidence(
            graph, out, edge.id
        )  # the edge's evidence rides to the node (same id)
        for cid, csrc, ctgt, ctype in (
            (f"{subject_edge_type}:{edge.id}", edge.source, edge.id, subject_edge_type),
            (f"{object_edge_type}:{edge.id}", edge.id, edge.target, object_edge_type),
        ):
            if out.has_edge(cid):
                raise ValueError(
                    f"cannot reify edge {edge.id!r}: connector id {cid!r} already in use"
                )
            out.add_edge(cid, source=csrc, target=ctgt, type=ctype)
    out.report["reified"] = {"edge_type": edge_type, "node_type": node_type}
    return out


def unreify(
    graph: Graph,
    edge_type: str,
    *,
    node_type: Optional[str] = None,
    subject_edge_type: Optional[str] = None,
    object_edge_type: Optional[str] = None,
) -> Graph:
    """Invert :func:`reify`: collapse well-formed relation-nodes back into edges.

    Only nodes of ``node_type`` that carry **both** a subject and object connector are
    collapsed, and only *their* connector edges are removed — so foreign edges that
    merely share the connector type, and incomplete/hand-authored nodes of the same
    type, are preserved (the toggle is safe on partial/foreign input).
    """
    node_type, subject_edge_type, object_edge_type = _names(
        edge_type, node_type, subject_edge_type, object_edge_type
    )
    reified_ids = {n.id for n in graph.nodes_of_type(node_type)}
    subject_conn: dict[
        str, tuple[str, str]
    ] = {}  # reified id -> (connector edge id, source)
    object_conn: dict[
        str, tuple[str, str]
    ] = {}  # reified id -> (connector edge id, target)
    for edge in graph.edges():
        if edge.type == subject_edge_type and edge.target in reified_ids:
            subject_conn[edge.target] = (edge.id, edge.source)
        elif edge.type == object_edge_type and edge.source in reified_ids:
            object_conn[edge.source] = (edge.id, edge.target)

    collapse = {
        rid for rid in reified_ids if rid in subject_conn and rid in object_conn
    }
    connectors_to_drop = {subject_conn[rid][0] for rid in collapse} | {
        object_conn[rid][0] for rid in collapse
    }

    out = Graph()
    for node in graph.nodes():
        if node.id in collapse:
            continue  # becomes an edge below
        out.add_node(node.id, types=node.types, attributes=node.attributes)
        _carry_evidence(graph, out, node.id)

    for edge in graph.edges():
        if edge.id in connectors_to_drop:
            continue  # only the connectors of collapsed nodes are removed
        out.add_edge(
            edge.id,
            source=edge.source,
            target=edge.target,
            type=edge.type,
            attributes=edge.attributes,
        )
        _carry_evidence(graph, out, edge.id)

    for reified_id in collapse:
        node = graph.node(reified_id)
        if out.has_edge(reified_id):
            raise ValueError(
                f"cannot unreify {reified_id!r}: an edge with that id already exists"
            )
        out.add_edge(
            reified_id,
            source=subject_conn[reified_id][1],
            target=object_conn[reified_id][1],
            type=edge_type,
            attributes=node.attributes,
        )
        _carry_evidence(
            graph, out, reified_id
        )  # node evidence rides back to the edge (same id)
    return out


def _carry_evidence(src: Graph, dst: Graph, element_id: str) -> None:
    """Carry an element's evidence across the reify/unreify boundary — both the
    element-level record AND every per-attribute ``(element_id, attr)`` record (A1),
    so value-level provenance survives the lossless round-trip (D8)."""
    if element_id in src.evidence:
        dst.evidence[element_id] = src.evidence[element_id]
    for key, ev in src.evidence.items():
        if isinstance(key, tuple) and len(key) == 2 and key[0] == element_id:
            dst.evidence[key] = ev
