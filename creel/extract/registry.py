"""Strategy discovery: a decorator registry for built-ins + entry points for plugins.

Per decision D12 creel uses a simple decorator/dict registry for in-tree strategies
and ``importlib.metadata`` entry points (group ``creel.extractors``) for
third-party packages, lazily loaded. pluggy is intentionally deferred — extractor
binding is 1:1 (one chosen strategy per element), not a 1:N hook loop.

A registered factory is ``(**config) -> Extractor`` — i.e. it takes binding config
and returns a callable extractor.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from creel.extract.protocol import Extractor

#: name -> factory(**config) -> Extractor
_REGISTRY: Dict[str, Callable[..., Extractor]] = {}

_ENTRY_POINT_GROUP = "creel.extractors"
_entry_points_loaded = False


def register_extractor(
    name: str,
) -> Callable[[Callable[..., Extractor]], Callable[..., Extractor]]:
    """Decorator registering an extractor *factory* under ``name``.

    The decorated object is a factory ``(**config) -> Extractor``. A plain extractor
    callable can be registered by wrapping it in a factory that ignores config.
    """

    def deco(factory: Callable[..., Extractor]) -> Callable[..., Extractor]:
        if name in _REGISTRY:
            raise ValueError(f"extractor {name!r} already registered")
        _REGISTRY[name] = factory
        return factory

    return deco


def get_extractor_factory(name: str) -> Callable[..., Extractor]:
    """Return the registered factory for ``name`` (loading entry points on first miss)."""
    if name not in _REGISTRY:
        _load_entry_points()
    if name not in _REGISTRY:
        raise KeyError(
            f"no extractor registered as {name!r}; known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def build_extractor(name: str, **config: Any) -> Extractor:
    """Instantiate the named extractor with ``config`` (its binding configuration)."""
    return get_extractor_factory(name)(**config)


def available_extractors() -> list[str]:
    """Return the sorted names of all registered extractors (incl. entry points)."""
    _load_entry_points()
    return sorted(_REGISTRY)


def _load_entry_points() -> None:
    """Discover third-party extractors advertised under the ``creel.extractors`` group."""
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    _entry_points_loaded = True
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover - py<3.8 never targeted
        return
    try:
        eps = entry_points(group=_ENTRY_POINT_GROUP)
    except TypeError:  # pragma: no cover - older selectable-EP API
        eps = entry_points().get(_ENTRY_POINT_GROUP, [])
    for ep in eps:
        if ep.name not in _REGISTRY:
            _REGISTRY[ep.name] = ep.load()
