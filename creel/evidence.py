"""Evidence — the separable per-element audit record (provenance + grounding + confidence).

Per decision D8, auditability is structural: every extracted node, edge, and value
can carry a small :class:`Evidence` record answering three orthogonal questions —
*where from* (provenance), *where exactly* (grounding selectors), and *how sure*
(method-tagged confidence). The record is kept physically separable from the graph
definition (a sidecar keyed by element id) but joinable on demand.

The vocabulary deliberately uses the lightweight cores of W3C PROV / PAV and the
W3C Web Annotation Model as plain JSON (progressive disclosure), so a full
RDF/PROV-O export remains possible later without imposing it now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, Optional, Sequence

# --- confidence methods (never compare scores across methods) ------------------
DETERMINISTIC = "deterministic"
LOGPROB = "logprob"
VERBALIZED = "verbalized"
SELF_CONSISTENCY = "self_consistency"

# --- review states -------------------------------------------------------------
AUTO = "auto"
NEEDS_REVIEW = "needs_review"
CONFIRMED = "confirmed"
REJECTED = "rejected"
CORRECTED = "corrected"


# --- grounding selectors (W3C Web Annotation shapes) ---------------------------
@dataclass(frozen=True)
class TextQuoteSelector:
    """Anchor by quoting the exact source text plus a little surrounding context."""

    exact: str
    prefix: str = ""
    suffix: str = ""
    kind: ClassVar[str] = "TextQuoteSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        return {"type": self.kind, "exact": self.exact, "prefix": self.prefix, "suffix": self.suffix}


@dataclass(frozen=True)
class TextPositionSelector:
    """Anchor by character offsets ``[start, end)`` within a source."""

    start: int
    end: int
    source_id: Optional[str] = None
    kind: ClassVar[str] = "TextPositionSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        d: dict[str, Any] = {"type": self.kind, "start": self.start, "end": self.end}
        if self.source_id is not None:
            d["source"] = self.source_id
        return d


@dataclass(frozen=True)
class CellSelector:
    """Anchor a value to a table cell (row index + column key)."""

    source_id: str
    row: int
    column: str
    kind: ClassVar[str] = "CellSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        return {"type": self.kind, "source": self.source_id, "row": self.row, "column": self.column}


@dataclass(frozen=True)
class JsonPathSelector:
    """Anchor a value to a JSON location via a JMESPath/JSONPath-style expression."""

    expression: str
    source_id: Optional[str] = None
    kind: ClassVar[str] = "JsonPathSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        d: dict[str, Any] = {"type": self.kind, "expression": self.expression}
        if self.source_id is not None:
            d["source"] = self.source_id
        return d


@dataclass(frozen=True)
class PageSelector:
    """Anchor a value to a page (coarsest locator for PDF/scanned sources)."""

    source_id: str
    page: int
    kind: ClassVar[str] = "PageSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        return {"type": self.kind, "source": self.source_id, "page": self.page}


@dataclass(frozen=True)
class BoundingBoxSelector:
    """Anchor a value to a bounding box on a page (visual grounding for PDF/images).

    Coordinates are ``[x0, y0, x1, y1]``; ``normalized`` indicates 0..1 fractions of
    the page (recommended, since rasterisation DPI varies) vs absolute pixels.
    """

    source_id: str
    page: int
    bbox: tuple
    normalized: bool = True
    kind: ClassVar[str] = "BoundingBoxSelector"

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict with a ``type`` discriminator."""
        return {
            "type": self.kind,
            "source": self.source_id,
            "page": self.page,
            "bbox": list(self.bbox),
            "normalized": self.normalized,
        }


# --- provenance & confidence ---------------------------------------------------
@dataclass(frozen=True)
class Provenance:
    """Where an element came from (PROV-lite + PAV as plain JSON keys)."""

    derived_from: str  # source id (optionally with a span suffix)
    generated_by: str  # strategy + extractor id, e.g. "pattern:RegexNodeExtractor"
    attributed_to: Optional[str] = None  # model id+version or human id
    generated_at: Optional[str] = None  # ISO-8601; omitted by default for determinism
    version: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict, omitting unset optional keys."""
        d = {"derived_from": self.derived_from, "generated_by": self.generated_by}
        for k in ("attributed_to", "generated_at", "version"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d


@dataclass(frozen=True)
class Confidence:
    """How sure we are, tagged with the *method* (scores are not cross-comparable)."""

    method: str
    score: float
    verified: Optional[bool] = None
    review_status: str = AUTO

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict, omitting an unset ``verified`` flag."""
        d: dict[str, Any] = {
            "method": self.method,
            "score": self.score,
            "review_status": self.review_status,
        }
        if self.verified is not None:
            d["verified"] = self.verified
        return d


@dataclass(frozen=True)
class Evidence:
    """The full audit record for one element: provenance + grounding + confidence."""

    provenance: Provenance
    grounding: Sequence[Any] = ()  # selector objects (each exposes .to_dict())
    confidence: Optional[Confidence] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the whole record to plain, JSON-ready dicts."""
        d: dict[str, Any] = {
            "provenance": self.provenance.to_dict(),
            "grounding": [g.to_dict() for g in self.grounding],
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence.to_dict()
        return d


def deterministic_evidence(
    *, source_id: str, generated_by: str, grounding: Sequence[Any] = ()
) -> Evidence:
    """Build an :class:`Evidence` record for a deterministic extraction (confidence 1.0)."""
    return Evidence(
        provenance=Provenance(derived_from=source_id, generated_by=generated_by),
        grounding=tuple(grounding),
        confidence=Confidence(method=DETERMINISTIC, score=1.0, verified=True),
    )
