"""creel ingestion layer: turn raw files into Sources (decision D-OP7, report R13).

Public entry points:
- :func:`ingest` — load one file into a :class:`~creel.sources.Source`, routing by
  file extension (or with an explicit ``loader``).
- :func:`ingest_paths` — load several files into a :class:`~creel.sources.SourceBundle`.

See the ``creel-ingestion`` skill for the route-by-format + quality-gate strategy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, Union

from creel.ingest.loaders import (
    loader_for,
    register_loader,
    supported_extensions,
)
from creel.ingest.protocol import Loader
from creel.sources import Source, SourceBundle


def ingest(
    path: Union[str, Path],
    *,
    source_id: Optional[str] = None,
    loader: Optional[Callable[..., Source]] = None,
) -> Source:
    """Load the file at ``path`` into a :class:`~creel.sources.Source`.

    The loader is chosen by file extension unless one is passed explicitly. The
    ``source_id`` defaults to the file stem (so a binding can reference it by name).
    """
    path = Path(path)
    source_id = source_id or path.stem
    loader = loader or loader_for(path)
    return loader(path, source_id=source_id)


def ingest_paths(paths: Iterable[Union[str, Path]]) -> SourceBundle:
    """Load several files into one :class:`~creel.sources.SourceBundle`."""
    return SourceBundle([ingest(p) for p in paths])


__all__ = [
    "ingest",
    "ingest_paths",
    "Loader",
    "register_loader",
    "loader_for",
    "supported_extensions",
]
