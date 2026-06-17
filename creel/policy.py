"""ExtractionPolicy — the operational policy layer for LLM extraction (decision #13).

This turns a recorded confidence into *action*: how hard to try (validate-retry), when
to spend more for reliability (self-consistency voting on high-value/low-confidence
fields), and when to flag an element for human review (``needs_review``). It is kept
**separate** from the grammar and the bindings (the same separation-of-concerns as
verifiers), and resolved by a chain: per-element → per-type → global default.

The deterministic extractor families ignore it (they are always
``deterministic, score=1.0``); it only bites for the probabilistic LLM extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class ExtractionPolicy:
    """How the LLM extractor should try, escalate, and flag for review.

    Args:
        max_retries: validate-retry attempts for shape/constraint failures.
        self_consistency_samples: if >1, draw N samples and keep the modal result;
            confidence becomes the agreement fraction (``self_consistency`` method).
        review_below: any element whose confidence score is below this is marked
            ``needs_review`` (human-in-the-loop gate).
        overrides: per element-id or per type-id policies (most specific wins).
    """

    max_retries: int = 2
    self_consistency_samples: int = 1
    review_below: float = 0.5
    overrides: Mapping[str, "ExtractionPolicy"] = field(default_factory=dict)

    def for_element(
        self, element_id: str, type_id: Optional[str] = None
    ) -> "ExtractionPolicy":
        """Resolve the effective policy for an element (element-id → type-id → self)."""
        return (
            self.overrides.get(element_id)
            or (self.overrides.get(type_id) if type_id else None)
            or self
        )
