"""Reserved temporal vocabulary (decision #15 / D-OP9 — reserved, not yet enforced).

Temporal modeling is deferred for v1, but the attribute names are **reserved now** so
adding it later (validity intervals, ingestion timestamps, invalidate-don't-delete)
is purely additive — no schema migration. Extractors/consumers that want to stamp
time should use exactly these keys.

A time-series of indicator readings can be carried today as **parallel `measured_by`
edges** distinguished by ``period`` (creel's LPG supports parallel edges natively);
when readings need shared Period/Source/dimension nodes or cross-period merging,
promote them with :func:`creel.reify.reify` (decision #12).
"""

from __future__ import annotations

#: Start of the validity interval for a fact (valid-time, ISO-8601 string).
VALID_FROM = "valid_from"
#: End of the validity interval (open-ended if absent).
VALID_TO = "valid_to"
#: When the fact was observed/measured (e.g. an indicator reading's period anchor).
OBSERVED_AT = "observed_at"
#: When creel ingested/recorded the fact (transaction-time).
RECORDED_AT = "recorded_at"

#: The reserved temporal attribute names. Use these keys for any temporal stamping.
RESERVED = (VALID_FROM, VALID_TO, OBSERVED_AT, RECORDED_AT)


def is_temporal_attribute(name: str) -> bool:
    """True if ``name`` is one of the reserved temporal attribute keys."""
    return name in RESERVED
