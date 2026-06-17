"""Shared, reusable transforms for extractors: slugging, casting, id templating.

These are used by more than one extractor strategy (pattern, query, …), so they
live here without an underscore prefix (cross-module reusable helpers) rather than
being duplicated privately in each strategy module.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_NUMERIC = ("int", "float", "number")


def slug(value: Any) -> str:
    """Lowercase, collapse non-alphanumerics to single dashes — for stable ids."""
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-") or "x"


def cast_value(value: Any, to: str | None) -> Any:
    """Cast ``value`` to ``to`` (``int``/``float``/``number``); else return unchanged.

    Numeric casts tolerate thousands separators and surrounding currency symbols and
    accept already-numeric inputs. Unparseable strings are returned unchanged.
    """
    if to not in _NUMERIC:
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
    else:
        cleaned = re.sub(r"[^0-9.\-]", "", str(value))
        if cleaned in ("", "-", ".", "-."):
            return value
        number = float(cleaned)
    if to == "int" or (to == "number" and number.is_integer()):
        return int(number)
    return number


def apply_casts(attrs: Mapping[str, Any], casts: Mapping[str, str]) -> dict[str, Any]:
    """Return ``attrs`` with each key listed in ``casts`` cast to its target type."""
    return {k: (cast_value(v, casts[k]) if k in casts else v) for k, v in attrs.items()}


def fill_template(template: str, record: Mapping[str, Any]) -> str:
    """Format ``template`` with **slugged** values of ``record`` (e.g. ``"donor:{name}"``)."""
    return template.format(**{k: slug(v) for k, v in record.items()})
