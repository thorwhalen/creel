"""Sources — the heterogeneous inputs creel reads.

A :class:`Source` is one unit of input with a stable ``id``, a ``kind`` (so the
right extractor strategy can be routed to it — prose to an LLM, a table to a query
extractor), its ``content``, and optionally its own ``schema`` (when a structured
source carries one, extraction can be made more robust).

A :class:`SourceBundle` is an addressable collection of sources. :func:`coerce_sources`
makes the common cases simple: a bare string becomes one text source, a list of
sources becomes a bundle, etc. (progressive disclosure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Optional, Union

#: Known source kinds. Extra kinds are allowed; these are the ones built-in
#: strategies recognise for routing.
TEXT = "text"
TABLE = "table"
JSON = "json"


@dataclass(frozen=True)
class Source:
    """One input unit: prose, a table, a JSON document, etc."""

    id: str
    content: Any
    kind: str = TEXT
    schema: Optional[Any] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SourceBundle:
    """An addressable, iterable collection of :class:`Source` objects."""

    def __init__(self, sources: Iterable[Source] = ()) -> None:
        self._by_id: dict[str, Source] = {}
        for s in sources:
            if s.id in self._by_id:
                raise ValueError(f"duplicate source id: {s.id!r}")
            self._by_id[s.id] = s

    def __iter__(self) -> Iterator[Source]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, source_id: str) -> Optional[Source]:
        """Return the source with this id, or ``None``."""
        return self._by_id.get(source_id)

    def of_kind(self, kind: str) -> Iterator[Source]:
        """Iterate over sources whose ``kind`` equals ``kind``."""
        return (s for s in self if s.kind == kind)

    def texts(self) -> Iterator[Source]:
        """Iterate over text (prose) sources."""
        return self.of_kind(TEXT)

    def __repr__(self) -> str:
        kinds = sorted({s.kind for s in self})
        return f"SourceBundle({len(self)} sources, kinds={kinds})"


SourcesArg = Union[str, Source, SourceBundle, Iterable[Source], Mapping[str, Any]]


def coerce_sources(sources: SourcesArg) -> SourceBundle:
    """Normalise a flexible ``sources`` argument into a :class:`SourceBundle`.

    Accepts a bare string (→ one ``text`` source with id ``"source"``), a single
    :class:`Source`, an existing :class:`SourceBundle`, an iterable of sources, or a
    ``{id: content_or_source}`` mapping.
    """
    if isinstance(sources, SourceBundle):
        return sources
    if isinstance(sources, str):
        return SourceBundle([Source("source", sources, kind=TEXT)])
    if isinstance(sources, Source):
        return SourceBundle([sources])
    if isinstance(sources, Mapping):
        out = []
        for sid, val in sources.items():
            out.append(val if isinstance(val, Source) else Source(str(sid), val))
        return SourceBundle(out)
    # any other iterable of Source
    return SourceBundle(list(sources))
