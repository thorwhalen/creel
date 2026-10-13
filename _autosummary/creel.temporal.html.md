# creel.temporal

Reserved temporal vocabulary (decision #15 / D-OP9 — reserved, not yet enforced).

Temporal modeling is deferred for v1, but the attribute names are **reserved now** so
adding it later (validity intervals, ingestion timestamps, invalidate-don’t-delete)
is purely additive — no schema migration. Extractors/consumers that want to stamp
time should use exactly these keys.

A time-series of indicator readings can be carried today as \*\*parallel `measured_by`
edges\*\* distinguished by `period` (creel’s LPG supports parallel edges natively);
when readings need shared Period/Source/dimension nodes or cross-period merging,
promote them with `creel.reify.reify()` (decision #12).

### Module Attributes

| [`VALID_FROM`](#creel.temporal.VALID_FROM)   | Start of the validity interval for a fact (valid-time, ISO-8601 string).         |
|---------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`VALID_TO`](#creel.temporal.VALID_TO)     | End of the validity interval (open-ended if absent).                             |
| [`OBSERVED_AT`](#creel.temporal.OBSERVED_AT)  | When the fact was observed/measured (e.g. an indicator reading's period anchor). |
| [`RECORDED_AT`](#creel.temporal.RECORDED_AT)  | When creel ingested/recorded the fact (transaction-time).                        |
| [`RESERVED`](#creel.temporal.RESERVED)     | The reserved temporal attribute names.                                           |

### Functions

| [`is_temporal_attribute`](#creel.temporal.is_temporal_attribute)(name)   | True if `name` is one of the reserved temporal attribute keys.   |
|--------------------------------------------------------------------------------|------------------------------------------------------------------|

### creel.temporal.OBSERVED_AT *= 'observed_at'*

When the fact was observed/measured (e.g. an indicator reading’s period anchor).

### creel.temporal.RECORDED_AT *= 'recorded_at'*

When creel ingested/recorded the fact (transaction-time).

### creel.temporal.RESERVED *= ('valid_from', 'valid_to', 'observed_at', 'recorded_at')*

The reserved temporal attribute names. Use these keys for any temporal stamping.

### creel.temporal.VALID_FROM *= 'valid_from'*

Start of the validity interval for a fact (valid-time, ISO-8601 string).

### creel.temporal.VALID_TO *= 'valid_to'*

End of the validity interval (open-ended if absent).

### creel.temporal.is_temporal_attribute(name)

True if `name` is one of the reserved temporal attribute keys.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
