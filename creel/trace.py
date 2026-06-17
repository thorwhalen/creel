"""Bidirectional source↔graph traceability (ADR D-OP9 — A1, A3, A4).

Three additive capabilities that make the extracted graph clickable both ways and
robust to re-ingestion, without changing the canonical graph:

- **A1 — per-attribute grounding.** Attach/read evidence keyed by ``(element_id,
  attribute)`` (the evidence sidecar already accepts arbitrary keys), so a single
  *property* — not just the node/edge — traces to its source span.
- **A3 — reverse-trace index.** :class:`TraceIndex` is a rebuildable index over the
  evidence grounding selectors answering "which elements did this source span/cell/
  page produce?" (the inverse of element→source).
- **A4 — anchor robustness.** :func:`reanchor` re-locates a ``TextQuoteSelector`` after
  the source text changes or is re-OCR'd (quote = system of record; position = hint),
  falling back from exact+context to a bounded fuzzy match.
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from typing import Any, Optional

from creel.evidence import Evidence
from creel.graph.model import Graph


# --- A1: per-attribute grounding ----------------------------------------------
def set_attribute_evidence(
    graph: Graph, element_id: str, attribute: str, evidence: Evidence
) -> None:
    """Attach an evidence record to a specific attribute value (key ``(id, attribute)``)."""
    graph.evidence[(element_id, attribute)] = evidence


def attribute_evidence(
    graph: Graph, element_id: str, attribute: str
) -> Optional[Evidence]:
    """Return the per-attribute evidence for ``(element_id, attribute)``, or the
    element-level evidence as a fallback, or ``None``."""
    return graph.evidence.get((element_id, attribute)) or graph.evidence.get(element_id)


# --- A3: reverse-trace index (source span/cell/page -> elements) --------------
class TraceIndex:
    """A rebuildable index from source locations to the elements grounded there.

    Built from a graph's evidence sidecar. Keys returned are the evidence keys, i.e.
    an element id or an ``(element_id, attribute)`` pair (per-attribute grounding).
    """

    def __init__(self, graph: Graph) -> None:
        self._spans: dict[str, list[tuple[int, int, Any]]] = defaultdict(list)
        self._cells: dict[str, list[tuple[int, str, Any]]] = defaultdict(list)
        self._pages: dict[str, list[tuple[int, Any]]] = defaultdict(list)
        for key, ev in graph.evidence.items():
            for selector in getattr(ev, "grounding", ()):
                kind = getattr(selector, "kind", None)
                if kind == "TextPositionSelector":
                    src = selector.source_id or "?"
                    self._spans[src].append((selector.start, selector.end, key))
                elif kind == "CellSelector":
                    self._cells[selector.source_id].append(
                        (selector.row, selector.column, key)
                    )
                elif kind == "PageSelector":
                    self._pages[selector.source_id].append((selector.page, key))

    def elements_at(self, source_id: str, offset: int) -> list[Any]:
        """Evidence keys whose text span contains ``offset`` (stabbing query)."""
        return [k for (s, e, k) in self._spans.get(source_id, []) if s <= offset < e]

    def elements_overlapping(self, source_id: str, start: int, end: int) -> list[Any]:
        """Evidence keys whose text span overlaps ``[start, end)`` (range query)."""
        return [
            k for (s, e, k) in self._spans.get(source_id, []) if s < end and start < e
        ]

    def elements_in_cell(self, source_id: str, row: int, column: str) -> list[Any]:
        """Evidence keys grounded in table cell ``(row, column)``."""
        return [
            k
            for (r, c, k) in self._cells.get(source_id, [])
            if r == row and c == column
        ]

    def elements_on_page(self, source_id: str, page: int) -> list[Any]:
        """Evidence keys grounded on ``page``."""
        return [k for (p, k) in self._pages.get(source_id, []) if p == page]


# --- A4: anchor robustness (re-anchoring) -------------------------------------
def verify_anchor(selector: Any, text: str) -> bool:
    """True if the selector's ``exact`` quote still occurs verbatim in ``text``."""
    exact = getattr(selector, "exact", None)
    return bool(exact) and exact in text


def reanchor(
    selector: Any, text: str, *, hint: Optional[int] = None, fuzzy: bool = True
) -> Optional[tuple[int, int]]:
    """Re-locate a ``TextQuoteSelector`` in (possibly changed) ``text``.

    Strategy (Hypothes.is-style): exact match → disambiguate multiple hits by
    prefix/suffix context (and ``hint`` position) → bounded fuzzy fallback. Returns the
    ``(start, end)`` of the relocated quote, or ``None`` if it can't be found. A caller
    that resolves only via the fuzzy path should downgrade the element to needs-review.
    """
    exact = getattr(selector, "exact", None)
    if not exact:
        return None
    positions = [m.start() for m in re.finditer(re.escape(exact), text)]
    if len(positions) == 1:
        return positions[0], positions[0] + len(exact)
    if positions:
        # raw prefix/suffix (not stripped) so the immediately-adjacent chars match
        prefix = getattr(selector, "prefix", "") or ""
        suffix = getattr(selector, "suffix", "") or ""
        best, best_score = positions[0], float("-inf")
        for p in positions:
            score = 0.0
            if prefix and text[max(0, p - len(prefix)) : p].endswith(prefix):
                score += 1
            if suffix and text[
                p + len(exact) : p + len(exact) + len(suffix)
            ].startswith(suffix):
                score += 1
            if hint is not None:
                score -= abs(p - hint) * 1e-6
            if score > best_score:
                best, best_score = p, score
        return best, best + len(exact)
    if not fuzzy:
        return None
    matcher = difflib.SequenceMatcher(None, text, exact)
    match = matcher.find_longest_match(0, len(text), 0, len(exact))
    if match.size >= max(3, int(0.6 * len(exact))):
        return match.a, match.a + len(exact)
    return None
