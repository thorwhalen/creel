"""Caching for expensive (e.g. LLM) extraction calls.

Per decision D11 caching is exact-match and deterministic — a stable key derived
from everything that affects the result — never semantic/approximate (which would
break reproducibility and auditability). The :class:`Cache` Protocol lets a
persistent backend be injected via the extraction context; the default is a no-op.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    """A minimal get/set cache. Implementations must be exact-match."""

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for ``key``, or ``None`` if absent."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key``."""
        ...


class NullCache:
    """The default cache: stores nothing, always misses."""

    def get(self, key: str) -> Optional[Any]:
        """Always a miss (returns ``None``)."""
        return None

    def set(self, key: str, value: Any) -> None:
        """No-op."""
        return None


class DictCache:
    """A simple in-memory cache backed by a dict (handy for tests and single runs)."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for ``key``, or ``None``."""
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key``."""
        self._store[key] = value


def cache_key(*parts: Any) -> str:
    """Build a deterministic cache key from arbitrary JSON-serialisable parts.

    Used by LLM extractors as ``cache_key(prompt, model, params, element_id,
    source_fingerprint)`` so identical inputs reuse the identical result.
    """
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
