"""Shared, reusable transforms for extractors: slugging, casting, id templating.

These are used by more than one extractor strategy (pattern, query, …), so they
live here without an underscore prefix (cross-module reusable helpers) rather than
being duplicated privately in each strategy module.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

_NUMERIC = ("int", "float", "number")
# a single run of leading sign + digits + at most one decimal point (post-cleaning)
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$|^-?\.\d+$")


def slug(value: Any) -> str:
    """Casefold, keep Unicode alphanumerics, collapse the rest to single dashes.

    Unicode-aware so distinct non-Latin names (e.g. ``"日本"`` vs ``"中国"``) get
    distinct ids instead of all collapsing to the ASCII fallback — silent node
    merges were a real data-loss risk for international corpora. ASCII inputs slug
    exactly as before (e.g. ``"Government of Norway" -> "government-of-norway"``).
    """
    normalized = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    out: list[str] = []
    prev_dash = False
    for ch in normalized:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or "x"


def cast_value(value: Any, to: str | None) -> Any:
    """Cast ``value`` to ``to`` (``int``/``float``/``number``); else return unchanged.

    Numeric casts tolerate thousands separators and surrounding currency symbols and
    accept already-numeric inputs. **Non-scalar** values are handled structurally
    (lists/tuples cast element-wise; mappings returned unchanged) and **any string
    that doesn't denote a single number** (dates like ``"2020-01-01"``, codes like
    ``"12-34"``) is returned unchanged rather than crashing.
    """
    if to not in _NUMERIC:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, (list, tuple)):
        return type(value)(cast_value(v, to) for v in value)
    elif isinstance(value, Mapping):
        return value
    else:
        cleaned = re.sub(r"[^0-9.\-]", "", str(value))
        if not _NUMBER_RE.match(cleaned):
            return value
        number = float(cleaned)
    if to == "int" or (to == "number" and number.is_integer()):
        return int(number)
    return number


def apply_casts(attrs: Mapping[str, Any], casts: Mapping[str, str]) -> dict[str, Any]:
    """Return ``attrs`` with each key listed in ``casts`` cast to its target type."""
    return {k: (cast_value(v, casts[k]) if k in casts else v) for k, v in attrs.items()}


def fill_template(template: str, record: Mapping[str, Any]) -> str:
    """Format ``template`` with **slugged** values of ``record`` (e.g. ``"donor:{name}"``).

    Raises an informative :class:`KeyError` (naming the missing field and the
    available ones) instead of a bare ``KeyError`` when ``template`` references a
    field absent from ``record``.
    """
    slugged = {k: slug(v) for k, v in record.items()}
    try:
        return template.format(**slugged)
    except KeyError as exc:
        missing = exc.args[0]
        raise KeyError(
            f"template {template!r} references field {missing!r}, "
            f"not found in record; available fields: {sorted(record)}"
        ) from None
