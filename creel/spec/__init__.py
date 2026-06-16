"""creel grammar layer: declare *what* graph to extract, and validate instances.

Re-exports the grammar model (:mod:`creel.spec.model`) and instance validation
(:mod:`creel.spec.validate`).
"""

from creel.spec.model import (
    PRIMITIVE_RANGES,
    AttrSchema,
    EdgeType,
    ElementType,
    EnumDef,
    GraphSpec,
    NodeType,
    effective_attributes,
)
from creel.spec.validate import (
    GraphValidationError,
    ValidationIssue,
    validate_graph,
)

__all__ = [
    "PRIMITIVE_RANGES",
    "AttrSchema",
    "EdgeType",
    "ElementType",
    "EnumDef",
    "GraphSpec",
    "NodeType",
    "effective_attributes",
    "GraphValidationError",
    "ValidationIssue",
    "validate_graph",
]
