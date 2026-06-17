"""Built-in loaders + the route-by-format registry (decision D-OP7, report R13).

The default set is **local, structure-preserving, permissively-licensed, and
pure-stdlib** (text/Markdown/CSV/TSV/JSON). Richer formats (PDF/DOCX/XLSX/HTML) are
handled by optional backends behind the ``[ingest]`` extra — lazily imported, with a
clear error if the extra is missing. License discipline: no AGPL/GPL parsers
(PyMuPDF4LLM, Marker) in the defaults.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
from pathlib import Path
from typing import Callable, Dict

from creel.sources import JSON, TABLE, TEXT, Source

#: file extension (lowercased, incl. dot) -> Loader
_LOADERS: Dict[str, Callable[..., Source]] = {}


def register_loader(*extensions: str):
    """Decorator registering a loader for one or more file extensions."""

    def deco(fn: Callable[..., Source]) -> Callable[..., Source]:
        for ext in extensions:
            _LOADERS[ext.lower()] = fn
        return fn

    return deco


def loader_for(path: Path) -> Callable[..., Source]:
    """Return the loader registered for ``path``'s extension, or raise ``ValueError``."""
    ext = path.suffix.lower()
    if ext not in _LOADERS:
        raise ValueError(
            f"no loader for {ext!r} (known: {sorted(_LOADERS)}); pass loader=... explicitly"
        )
    return _LOADERS[ext]


def supported_extensions() -> list[str]:
    """Return the sorted list of registered file extensions."""
    return sorted(_LOADERS)


# --- pure-stdlib default loaders ---------------------------------------------
@register_loader(".txt", ".text")
def load_text(path: Path, *, source_id: str) -> Source:
    """Load plain text as a ``text`` source."""
    return Source(
        source_id,
        path.read_text(encoding="utf-8"),
        kind=TEXT,
        metadata={"filename": path.name, "format": "text"},
    )


@register_loader(".md", ".markdown")
def load_markdown(path: Path, *, source_id: str) -> Source:
    """Load Markdown as-is (it is already LLM-native and structure-preserving)."""
    return Source(
        source_id,
        path.read_text(encoding="utf-8"),
        kind=TEXT,
        metadata={"filename": path.name, "format": "markdown"},
    )


@register_loader(".csv")
def load_csv(path: Path, *, source_id: str) -> Source:
    """Load CSV into a ``table`` source (``list[dict]`` rows; cell-addressable)."""
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    return Source(
        source_id, rows, kind=TABLE, metadata={"filename": path.name, "format": "csv"}
    )


@register_loader(".tsv")
def load_tsv(path: Path, *, source_id: str) -> Source:
    """Load TSV into a ``table`` source."""
    rows = list(
        csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")), delimiter="\t")
    )
    return Source(
        source_id, rows, kind=TABLE, metadata={"filename": path.name, "format": "tsv"}
    )


@register_loader(".json")
def load_json(path: Path, *, source_id: str) -> Source:
    """Load JSON into a ``json`` source (parsed object)."""
    return Source(
        source_id,
        json.loads(path.read_text(encoding="utf-8")),
        kind=JSON,
        metadata={"filename": path.name, "format": "json"},
    )


# --- optional-backend loaders ([ingest] extra) -------------------------------
@register_loader(".xlsx", ".xls")
def load_xlsx(path: Path, *, source_id: str) -> Source:
    """Load the first worksheet into a ``table`` source (openpyxl, ``data_only``).

    Basic header-row mapping. Merged cells / multi-row headers / hidden rows are a
    known limitation (R13) — escalate to a richer backend when needed.
    """
    openpyxl = _require("openpyxl", "[ingest]")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = [
        str(c) if c is not None else f"col{i}"
        for i, c in enumerate(next(rows_iter, ()))
    ]
    rows = [dict(zip(header, row)) for row in rows_iter]
    return Source(
        source_id,
        rows,
        kind=TABLE,
        metadata={"filename": path.name, "format": "xlsx", "sheet": ws.title},
    )


@register_loader(".html", ".htm")
def load_html(path: Path, *, source_id: str) -> Source:
    """Extract main content from HTML to Markdown (trafilatura; strips boilerplate)."""
    trafilatura = _require("trafilatura", "[ingest]")
    text = (
        trafilatura.extract(path.read_text(encoding="utf-8"), output_format="markdown")
        or ""
    )
    return Source(
        source_id, text, kind=TEXT, metadata={"filename": path.name, "format": "html"}
    )


@register_loader(".pdf", ".docx", ".pptx")
def load_docling(path: Path, *, source_id: str) -> Source:
    """Convert PDF/DOCX/PPTX to Markdown via Docling (structure + page provenance).

    Docling is the structure-preserving default for rich formats; its
    ``DoclingDocument`` carries page/bbox provenance that a later pass can attach to
    grounding selectors.
    """
    dc = _require("docling.document_converter", "[ingest]")
    result = dc.DocumentConverter().convert(str(path))
    markdown = result.document.export_to_markdown()
    return Source(
        source_id,
        markdown,
        kind=TEXT,
        metadata={"filename": path.name, "format": path.suffix.lower().lstrip(".")},
    )


def _require(module: str, extra: str):
    """Import ``module`` or raise a clear error pointing at the ``creel[extra]`` install."""
    try:
        return importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            f"loading this format needs the {extra} extra (missing {module!r}). "
            f"Install with: pip install 'creel{extra}'"
        ) from exc
