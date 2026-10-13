# creel.evidence

Evidence — the separable per-element audit record (provenance + grounding + confidence).

Per decision D8, auditability is structural: every extracted node, edge, and value
can carry a small [`Evidence`](#creel.evidence.Evidence) record answering three orthogonal questions —
*where from* (provenance), *where exactly* (grounding selectors), and *how sure*
(method-tagged confidence). The record is kept physically separable from the graph
definition (a sidecar keyed by element id) but joinable on demand.

The vocabulary deliberately uses the lightweight cores of W3C PROV / PAV and the
W3C Web Annotation Model as plain JSON (progressive disclosure), so a full
RDF/PROV-O export remains possible later without imposing it now.

### Module Attributes

| [`SOFTWARE_AGENT`](#creel.evidence.SOFTWARE_AGENT)   | agent kinds for `Provenance.attributed_kind` (A5) — derive machine vs manual.   |
|-------------------------------------------------------------------|---------------------------------------------------------------------------------|

### Functions

| [`deterministic_evidence`](#creel.evidence.deterministic_evidence)(\*, source_id, ...[, ...])   | Build an [`Evidence`](#creel.evidence.Evidence) record for a deterministic extraction (confidence 1.0).   |
|------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|

### Classes

| [`BoundingBoxSelector`](#creel.evidence.BoundingBoxSelector)(source_id, page, bbox[, ...])   | Anchor a value to a bounding box on a page (visual grounding for PDF/images).   |
|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`CellSelector`](#creel.evidence.CellSelector)(source_id, row, column)                | Anchor a value to a table cell (row index + column key).                        |
| [`Confidence`](#creel.evidence.Confidence)(method, score[, verified, ...])          | How sure we are, tagged with the *method* (scores are not cross-comparable).    |
| [`Evidence`](#creel.evidence.Evidence)(provenance[, grounding, confidence])       | The full audit record for one element: provenance + grounding + confidence.     |
| [`JsonPathSelector`](#creel.evidence.JsonPathSelector)(expression[, source_id])           | Anchor a value to a JSON location via a JMESPath/JSONPath-style expression.     |
| [`PageSelector`](#creel.evidence.PageSelector)(source_id, page)                       | Anchor a value to a page (coarsest locator for PDF/scanned sources).            |
| [`Provenance`](#creel.evidence.Provenance)(derived_from, generated_by[, ...])       | Where an element came from (PROV-lite + PAV as plain JSON keys).                |
| [`TextPositionSelector`](#creel.evidence.TextPositionSelector)(start, end[, source_id])       | Anchor by character offsets `[start, end)` within a source.                     |
| [`TextQuoteSelector`](#creel.evidence.TextQuoteSelector)(exact[, prefix, suffix])          | Anchor by quoting the exact source text plus a little surrounding context.      |

### *class* creel.evidence.BoundingBoxSelector(source_id, page, bbox, normalized=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor a value to a bounding box on a page (visual grounding for PDF/images).

Coordinates are `[x0, y0, x1, y1]`; `normalized` indicates 0..1 fractions of
the page (recommended, since rasterisation DPI varies) vs absolute pixels.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.CellSelector(source_id, row, column)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor a value to a table cell (row index + column key).

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.Confidence(method, score, verified=None, review_status='auto')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How sure we are, tagged with the *method* (scores are not cross-comparable).

#### to_dict()

Serialise to a plain dict, omitting an unset `verified` flag.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.Evidence(provenance, grounding=(), confidence=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The full audit record for one element: provenance + grounding + confidence.

#### to_dict()

Serialise the whole record to plain, JSON-ready dicts.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.JsonPathSelector(expression, source_id=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor a value to a JSON location via a JMESPath/JSONPath-style expression.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.PageSelector(source_id, page)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor a value to a page (coarsest locator for PDF/scanned sources).

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.Provenance(derived_from, generated_by, attributed_to=None, attributed_kind=None, coded_by=None, was_revision_of=None, generated_at=None, version=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where an element came from (PROV-lite + PAV as plain JSON keys).

`attributed_kind` (`software_agent` | `person`) + `was_revision_of` make
the machine-extracted / manually-coded / human-corrected distinction *derivable*
(decision A5): non-destructive correction records a new provenance pointing at the
superseded one, rather than overwriting.

#### *property* is_corrected *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if this is a person’s revision of an earlier (machine or human) record.

#### *property* is_machine *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if attributed to a software agent and not a human correction.

#### *property* is_manual *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True if attributed to a person with no machine antecedent (manual coding).

#### to_dict()

Serialise to a plain dict, omitting unset optional keys.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.evidence.SOFTWARE_AGENT *= 'software_agent'*

agent kinds for `Provenance.attributed_kind` (A5) — derive machine vs manual.

### *class* creel.evidence.TextPositionSelector(start, end, source_id=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor by character offsets `[start, end)` within a source.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### *class* creel.evidence.TextQuoteSelector(exact, prefix='', suffix='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Anchor by quoting the exact source text plus a little surrounding context.

#### to_dict()

Serialise to a plain dict with a `type` discriminator.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### creel.evidence.deterministic_evidence(, source_id, generated_by, grounding=())

Build an [`Evidence`](#creel.evidence.Evidence) record for a deterministic extraction (confidence 1.0).

* **Return type:**
  [`Evidence`](#creel.evidence.Evidence)
