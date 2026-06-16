"""Join the grammar and the extraction-metadata layers into a runnable plan.

Per decision D7 this is a pure equijoin by element id: for every node-type and
edge-type in the :class:`GraphSpec`, find its :class:`ExtractorBinding` (if any) and
resolve the concrete :class:`Extractor`. Elements with no binding fall back to a
``schema_as_extractor`` factory when one is supplied (the progressive-disclosure
default), otherwise they are reported as ``unbound``.

The result, a :class:`ResolvedPlan`, is what the facade maps over.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from creel.bindings import ExtractorBindings
from creel.extract.protocol import Extractor
from creel.spec.model import ElementType, GraphSpec

#: A factory ``(element_type, spec) -> Extractor`` used when an element has no binding.
SchemaAsExtractor = Callable[[ElementType, GraphSpec], Extractor]


@dataclass(frozen=True)
class ResolvedStep:
    """One element of the plan: the element, its resolved extractor, and the source."""

    element_id: str
    element_type: ElementType
    extractor: Extractor
    binding_source: str  # "binding" | "schema_as_extractor"


@dataclass(frozen=True)
class ResolvedPlan:
    """The full set of resolved extraction steps plus any unbound element ids."""

    steps: tuple[ResolvedStep, ...]
    unbound: tuple[str, ...]


def join(
    spec: GraphSpec,
    bindings: Optional[ExtractorBindings],
    *,
    schema_as_extractor: Optional[SchemaAsExtractor] = None,
) -> ResolvedPlan:
    """Equijoin ``spec`` with ``bindings`` by element id into a :class:`ResolvedPlan`.

    Node-types are resolved before edge-types so that, when the facade runs the plan,
    nodes are produced before the edges that reference them.
    """
    steps: list[ResolvedStep] = []
    unbound: list[str] = []
    for element_type in spec.iter_element_types():
        binding = bindings.for_element(element_type.id) if bindings else None
        if binding is not None:
            steps.append(
                ResolvedStep(element_type.id, element_type, binding.build(), "binding")
            )
        elif schema_as_extractor is not None:
            steps.append(
                ResolvedStep(
                    element_type.id,
                    element_type,
                    schema_as_extractor(element_type, spec),
                    "schema_as_extractor",
                )
            )
        else:
            unbound.append(element_type.id)
    return ResolvedPlan(tuple(steps), tuple(unbound))
