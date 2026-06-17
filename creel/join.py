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
    """One element of the plan: the element(s), the resolved extractor, and the source.

    ``element_types`` is the cluster this step covers (D-OP8); for an ordinary
    per-element step it is just ``(element_type,)``.
    """

    element_id: str
    element_type: ElementType
    extractor: Extractor
    binding_source: str  # "binding" | "schema_as_extractor"
    element_types: tuple = ()

    def __post_init__(self) -> None:
        if not self.element_types:
            object.__setattr__(self, "element_types", (self.element_type,))


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

    Cluster bindings (``binding.elements``) are resolved first into one multi-element
    step each (invoked once). Remaining elements resolve per-element. Node-types are
    produced before edge-types so the facade adds nodes before the edges that
    reference them.
    """
    steps: list[ResolvedStep] = []
    unbound: list[str] = []
    covered: set[str] = set()

    # 1) cluster bindings -> one step each, covering several element types
    for binding in (bindings or ()):
        if not getattr(binding, "elements", None):
            continue
        cluster = tuple(spec.element_type(eid) for eid in binding.elements if spec.element_type(eid))
        if not cluster:
            continue
        steps.append(ResolvedStep(cluster[0].id, cluster[0], binding.build(), "binding", cluster))
        covered.update(et.id for et in cluster)

    # 2) remaining elements -> per-element binding or schema-as-extractor fallback
    for element_type in spec.iter_element_types():
        if element_type.id in covered:
            continue
        binding = bindings.for_element(element_type.id) if bindings else None
        if binding is not None and not getattr(binding, "elements", None):
            steps.append(ResolvedStep(element_type.id, element_type, binding.build(), "binding"))
        elif schema_as_extractor is not None:
            steps.append(ResolvedStep(element_type.id, element_type,
                                      schema_as_extractor(element_type, spec), "schema_as_extractor"))
        else:
            unbound.append(element_type.id)
    return ResolvedPlan(tuple(steps), tuple(unbound))
