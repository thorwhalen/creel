"""The renderer contract — the three-layer annotated-graph renderers consume (D15).

creel ships the *contract*, not concrete renderers (those live in consumer packages).
An :class:`AnnotatedGraph` is the three layers: the graph (the SSOT), a standoff
:class:`~creel.annotate.Annotation` overlay (insights/comments/codings keyed by
target), and optional presentation hints. A :class:`GraphRenderer` turns one into a
:class:`RenderArtifact` (bytes/text + media type).

Use :mod:`creel.view` for the dependency-free projections (DOT/Mermaid/Cytoscape/
tables) that concrete renderers build on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Sequence, runtime_checkable

from creel.annotate import Annotation
from creel.graph.model import Graph


@dataclass
class AnnotatedGraph:
    """The render contract: graph + standoff annotation overlay + presentation hints."""

    graph: Graph
    annotations: Sequence[Annotation] = ()
    presentation: Mapping[str, Any] = field(default_factory=dict)

    def annotations_for(self, element_id: str) -> list[Annotation]:
        """Return the annotations whose target is (or starts at) ``element_id``."""
        return [a for a in self.annotations if a.target_element_id() == element_id]


@dataclass(frozen=True)
class RenderArtifact:
    """The output of a renderer: content (str/bytes/dict) + its media type."""

    content: Any
    media_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class GraphRenderer(Protocol):
    """Render an :class:`AnnotatedGraph` into a :class:`RenderArtifact`."""

    name: str
    output_media_type: str

    def render(self, graph: AnnotatedGraph, *, options: Optional[Mapping[str, Any]] = None) -> RenderArtifact:
        """Produce the rendered artifact."""
        ...
