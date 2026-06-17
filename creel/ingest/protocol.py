"""The ingestion contract: a Loader turns a file into a :class:`~creel.sources.Source`.

Per decision D-OP7 (report R13), ingestion is *upstream* of extraction: files →
Sources. A :class:`Loader` is a callable ``(path, *, source_id) -> Source`` that
emits LLM-friendly content (Markdown/text for prose, row dicts for tables, parsed
objects for JSON) and records enough metadata that downstream extractors can ground
each value back to a page/cell/char-span.

Loaders are callables behind a Protocol (composition over inheritance), mirroring
the Extractor/Verifier strategy pattern. Route-by-format lives in
:mod:`creel.ingest.loaders`; the public entry point is :func:`creel.ingest.ingest`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from creel.sources import Source


@runtime_checkable
class Loader(Protocol):
    """Turn a file at ``path`` into a :class:`~creel.sources.Source`."""

    def __call__(self, path: Path, *, source_id: str) -> Source:
        """Load ``path`` and return a Source with id ``source_id``."""
        ...
