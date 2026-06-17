"""Validate an instance :class:`~creel.graph.model.Graph` against a :class:`GraphSpec`.

This is *structural/shape* validation of an extracted graph against its grammar
(decision D6: the grammar enforces shape; deeper semantic faithfulness is the job
of the verifier subsystem). It checks that node/edge types are declared, that edge
endpoints have conformant node-types, that required attributes are present, and
that attribute values respect their declared range / enum / bounds / pattern.

Use :func:`validate_graph` to collect issues, or pass ``raise_on_error=True`` to
raise a :class:`GraphValidationError` summarising them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from creel.graph.model import Edge, Graph, Node
from creel.spec.model import (
    AttrSchema,
    EdgeType,
    GraphSpec,
    PRIMITIVE_RANGES,
    effective_attributes,
)


@dataclass(frozen=True)
class ValidationIssue:
    """A single grammar-conformance problem found in an instance graph."""

    element: str  # "node" | "edge"
    element_id: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.element} {self.element_id!r}: {self.message}"


class GraphValidationError(ValueError):
    """Raised by :func:`validate_graph` when ``raise_on_error`` and issues exist."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        joined = "\n  ".join(str(i) for i in issues)
        super().__init__(f"{len(issues)} graph validation issue(s):\n  {joined}")


def validate_graph(
    graph: Graph, spec: GraphSpec, *, raise_on_error: bool = False
) -> list[ValidationIssue]:
    """Return the list of grammar-conformance issues for ``graph`` under ``spec``.

    With ``raise_on_error=True``, raises :class:`GraphValidationError` if any issue
    is found instead of returning the list.
    """
    issues: list[ValidationIssue] = []
    for node in graph.nodes():
        issues.extend(_check_node(node, spec))
    for edge in graph.edges():
        issues.extend(_check_edge(edge, graph, spec))
    if raise_on_error and issues:
        raise GraphValidationError(issues)
    return issues


def _check_node(node: Node, spec: GraphSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not node.types:
        issues.append(
            ValidationIssue("node", node.id, "untyped", "node has no type label")
        )
        return issues
    for t in node.types:
        if spec.node_type(t) is None:
            issues.append(
                ValidationIssue(
                    "node", node.id, "unknown-type", f"unknown node-type {t!r}"
                )
            )
    # Validate attributes against the (most specific) declared type's effective schema.
    for t in node.types:
        if spec.node_type(t) is not None:
            issues.extend(_check_attributes("node", node.id, node.attributes, spec, t))
    return issues


def _check_edge(edge: Edge, graph: Graph, spec: GraphSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    et = spec.edge_type(edge.type)
    if et is None:
        issues.append(
            ValidationIssue(
                "edge", edge.id, "unknown-type", f"unknown edge-type {edge.type!r}"
            )
        )
        return issues
    issues.extend(_check_endpoint(edge, graph, spec, et, "subject"))
    issues.extend(_check_endpoint(edge, graph, spec, et, "object"))
    issues.extend(_check_attributes("edge", edge.id, edge.attributes, spec, edge.type))
    return issues


def _check_endpoint(
    edge: Edge, graph: Graph, spec: GraphSpec, et: EdgeType, role: str
) -> list[ValidationIssue]:
    expected = et.subject_type if role == "subject" else et.object_type
    endpoint_id = edge.source if role == "subject" else edge.target
    if expected is None:
        return []
    if not graph.has_node(endpoint_id):
        return [
            ValidationIssue(
                "edge", edge.id, "missing-endpoint", f"{role} {endpoint_id!r} absent"
            )
        ]
    node = graph.node(endpoint_id)
    if not any(spec.is_subtype(t, expected) for t in node.types):
        return [
            ValidationIssue(
                "edge",
                edge.id,
                "endpoint-type",
                f"{role} {endpoint_id!r} types {node.types} not a subtype of {expected!r}",
            )
        ]
    return []


def _check_attributes(
    element: str, element_id: str, attributes: Any, spec: GraphSpec, type_id: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    schema = effective_attributes(spec, type_id)
    for name, attr in schema.items():
        if attr.required and name not in attributes:
            issues.append(
                ValidationIssue(
                    element, element_id, "missing-required", f"missing {name!r}"
                )
            )
    for name, value in attributes.items():
        attr = schema.get(name)
        if attr is None:
            continue  # extra attributes are tolerated (open-world for instances)
        issues.extend(_check_value(element, element_id, attr, value, spec))
    return issues


def _check_value(
    element: str, element_id: str, attr: AttrSchema, value: Any, spec: GraphSpec
) -> list[ValidationIssue]:
    if value is None:
        return []
    if attr.multivalued:
        if not isinstance(value, (list, tuple)):
            return [
                ValidationIssue(
                    element,
                    element_id,
                    "not-multivalued",
                    f"{attr.name!r} must be a list",
                )
            ]
        issues: list[ValidationIssue] = []
        for item in value:
            issues.extend(_check_scalar(element, element_id, attr, item, spec))
        return issues
    return _check_scalar(element, element_id, attr, value, spec)


def _check_scalar(
    element: str, element_id: str, attr: AttrSchema, value: Any, spec: GraphSpec
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    permissible = _permissible_values(attr, spec)
    if permissible is not None:
        if value not in permissible:
            issues.append(
                ValidationIssue(
                    element,
                    element_id,
                    "enum",
                    f"{attr.name!r}={value!r} not in {permissible}",
                )
            )
        return issues  # enum value need not also pass a primitive type check
    if attr.range in PRIMITIVE_RANGES and not _is_range(value, attr.range):
        issues.append(
            ValidationIssue(
                element,
                element_id,
                "range-type",
                f"{attr.name!r}={value!r} is not a {attr.range}",
            )
        )
    if (
        attr.minimum is not None
        and isinstance(value, (int, float))
        and value < attr.minimum
    ):
        issues.append(
            ValidationIssue(
                element,
                element_id,
                "minimum",
                f"{attr.name!r}={value} < {attr.minimum}",
            )
        )
    if (
        attr.maximum is not None
        and isinstance(value, (int, float))
        and value > attr.maximum
    ):
        issues.append(
            ValidationIssue(
                element,
                element_id,
                "maximum",
                f"{attr.name!r}={value} > {attr.maximum}",
            )
        )
    if (
        attr.pattern is not None
        and isinstance(value, str)
        and re.search(attr.pattern, value) is None
    ):
        issues.append(
            ValidationIssue(
                element,
                element_id,
                "pattern",
                f"{attr.name!r}={value!r} !~ /{attr.pattern}/",
            )
        )
    return issues


def _permissible_values(attr: AttrSchema, spec: GraphSpec) -> Optional[tuple[str, ...]]:
    """Inline enum, or a named enum referenced by ``range``; else ``None``."""
    if attr.enum is not None:
        return tuple(attr.enum)
    enum_def = spec.enum(attr.range)
    if enum_def is not None:
        return tuple(enum_def.permissible_values)
    return None


def _is_range(value: Any, range_name: str) -> bool:
    """True if ``value``'s Python type matches the primitive ``range_name``."""
    if range_name == "string":
        return isinstance(value, str)
    if range_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if range_name in ("decimal", "float"):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if range_name == "boolean":
        return isinstance(value, bool)
    if range_name in ("date", "datetime"):
        return isinstance(
            value, str
        )  # ISO-8601 string; deeper parsing is a verifier's job
    return True
