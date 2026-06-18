"""The extraction-metadata layer: which strategy populates each grammar element.

Per decision D7 this is physically separate from the grammar (:class:`GraphSpec`)
and joined to it on demand (:func:`creel.join.join`). A binding pairs a taxonomy
element id with either a registered strategy name + pure-data config, or a direct
extractor callable. Keeping this separate means the same grammar can be paired with
different extraction strategies for different source sets — reuse by join, not by
duplication.

Resolution is by a default chain (element-specific → type-default → global
default); unresolved elements fall back to schema-as-extractor at join time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Union

from creel.extract.protocol import Extraction, ExtractionContext, Extractor
from creel.extract.registry import build_extractor


@dataclass(frozen=True)
class ExtractorBinding:
    """Bind one grammar element (or a cluster) to a strategy or a direct callable.

    When ``elements`` is set, this is a **cluster binding** (D-OP8): the extractor is
    invoked **once** for the whole set of element ids (one pass over several coupled
    types), rather than once per element. ``element_id`` is then just a label.
    """

    element_id: str
    strategy: Optional[str] = None
    config: Mapping[str, Any] = field(default_factory=dict)
    extractor: Optional[Callable[[ExtractionContext], Extraction]] = None
    elements: Optional[tuple] = None

    def __post_init__(self) -> None:
        if self.elements is not None and not isinstance(self.elements, tuple):
            object.__setattr__(self, "elements", tuple(self.elements))

    def build(self) -> Extractor:
        """Instantiate the bound extractor (direct callable wins over a named strategy).

        Raises a binding-level :class:`ValueError` (naming the element and strategy)
        for a malformed config or missing required params, instead of leaking a
        ``dict``-internals or ``__init__`` traceback to the caller.
        """
        if self.extractor is not None:
            return self.extractor
        if self.strategy is not None:
            if not isinstance(self.config, Mapping):
                raise ValueError(
                    f"binding for {self.element_id!r} ({self.strategy!r}): config must be "
                    f"a mapping of params, got {type(self.config).__name__}: {self.config!r}"
                )
            try:
                return build_extractor(self.strategy, **dict(self.config))
            except TypeError as exc:
                raise ValueError(
                    f"binding for {self.element_id!r} ({self.strategy!r}) has invalid "
                    f"params {dict(self.config)!r}: {exc}"
                ) from None
        raise ValueError(
            f"binding for {self.element_id!r} has neither a strategy nor an extractor"
        )


class ExtractorBindings:
    """A collection of :class:`ExtractorBinding`, looked up by element id."""

    #: element id used for the catch-all / global default binding.
    DEFAULT = "*"

    def __init__(self, bindings: Iterable[ExtractorBinding] = ()) -> None:
        self._by_id: dict[str, ExtractorBinding] = {}
        for b in bindings:
            self._by_id[b.element_id] = b

    def for_element(self, element_id: str) -> Optional[ExtractorBinding]:
        """Return the binding for ``element_id``, else the global default, else ``None``."""
        return self._by_id.get(element_id) or self._by_id.get(self.DEFAULT)

    def __iter__(self):
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    @classmethod
    def from_mapping(
        cls, mapping: Mapping[str, Union["ExtractorBinding", tuple, dict, Callable]]
    ) -> "ExtractorBindings":
        """Build bindings from ``{element_id: spec}`` where ``spec`` is flexible.

        ``spec`` may be an :class:`ExtractorBinding`, a ``(strategy, config)`` tuple,
        a ``{"strategy": ..., "config": ...}`` dict, or a bare extractor callable.
        """
        out = []
        for element_id, spec in mapping.items():
            out.append(_coerce_binding(element_id, spec))
        return cls(out)


def _coerce_binding(element_id: str, spec: Any) -> ExtractorBinding:
    if isinstance(spec, ExtractorBinding):
        return spec
    if callable(spec):
        return ExtractorBinding(element_id, extractor=spec)
    if isinstance(spec, tuple):
        strategy = spec[0]
        config = spec[1] if len(spec) > 1 else {}
        return ExtractorBinding(element_id, strategy=strategy, config=config)
    if isinstance(spec, Mapping):
        return ExtractorBinding(
            element_id,
            strategy=spec.get("strategy"),
            config=spec.get("config", {}),
            extractor=spec.get("extractor"),
            elements=spec.get("elements"),
        )
    raise TypeError(f"cannot interpret binding spec for {element_id!r}: {spec!r}")


def coerce_bindings(
    extractors: Union[ExtractorBindings, Mapping, Iterable[ExtractorBinding], None],
) -> Optional[ExtractorBindings]:
    """Normalise the facade's ``extractors`` argument into :class:`ExtractorBindings`."""
    if extractors is None:
        return None
    if isinstance(extractors, ExtractorBindings):
        return extractors
    if isinstance(extractors, Mapping):
        return ExtractorBindings.from_mapping(extractors)
    return ExtractorBindings(list(extractors))
