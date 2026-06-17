"""Annotations — the standoff overlay for machine insight AND human coding (D-OP9 / A2).

A single :class:`Annotation` record serves both directions of authorship: an LLM/
analysis laying an insight over the graph (decision D15) and a human highlighting a
source passage and linking it to a node/edge/category (the manual-"coding" workflow).
They differ only by ``motivation`` + the provenance agent ``kind`` — never two
schemas. The overlay is standoff (kept separate from the graph; joined by target).

A :class:`Selection` reifies a region of a source (id + selector) so several
annotations can share one highlighted span. Targets may be a graph element id, an
``(element_id, attribute)`` pair (per-attribute, A1), or a :class:`Selection`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from creel.evidence import Confidence, Provenance

# W3C Web Annotation motivations creel uses.
CLASSIFYING = "classifying"
IDENTIFYING = "identifying"
TAGGING = "tagging"
LINKING = "linking"
COMMENTING = "commenting"
EDITING = "editing"
HIGHLIGHTING = "highlighting"


@dataclass(frozen=True)
class Selection:
    """A reified, shareable selection of a source region (id + a grounding selector)."""

    id: str
    source_id: str
    selector: Any  # any creel.evidence selector (TextQuote/TextPosition/Cell/Page/...)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        return {"id": self.id, "source": self.source_id, "selector": self.selector.to_dict()}


@dataclass(frozen=True)
class Annotation:
    """A standoff annotation linking a ``target`` to a ``body`` with a ``motivation``.

    ``target``: an element id (str), an ``(element_id, attribute)`` tuple, or a
    :class:`Selection` (a source span). ``body``: a graph-element/category ref (str),
    a free-text comment, or any structured insight. ``provenance``/``confidence`` reuse
    the evidence vocabulary; ``provenance.attributed_kind`` distinguishes a
    ``software_agent`` annotation (machine insight) from a ``person`` one (human coding).
    """

    id: str
    target: Any
    body: Any
    motivation: str = COMMENTING
    provenance: Optional[Provenance] = None
    confidence: Optional[Confidence] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain, JSON-ready dict."""
        target = self.target.to_dict() if isinstance(self.target, Selection) else (
            list(self.target) if isinstance(self.target, tuple) else self.target
        )
        out: dict[str, Any] = {"id": self.id, "target": target, "body": self.body,
                               "motivation": self.motivation}
        if self.provenance is not None:
            out["provenance"] = self.provenance.to_dict()
        if self.confidence is not None:
            out["confidence"] = self.confidence.to_dict()
        return out

    def target_element_id(self) -> Optional[str]:
        """The graph element id this annotation targets, if any (else ``None``)."""
        if isinstance(self.target, str):
            return self.target
        if isinstance(self.target, tuple) and self.target:
            return self.target[0]
        return None
