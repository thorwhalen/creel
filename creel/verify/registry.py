"""Verifier discovery: a decorator registry + entry points (group ``creel.verifiers``).

Mirrors :mod:`creel.extract.registry` (decision D12). A registered factory is
``(**config) -> Verifier``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from creel.verify.protocol import Verifier

#: name -> factory(**config) -> Verifier
_REGISTRY: Dict[str, Callable[..., Verifier]] = {}

_ENTRY_POINT_GROUP = "creel.verifiers"
_entry_points_loaded = False


def register_verifier(
    name: str,
) -> Callable[[Callable[..., Verifier]], Callable[..., Verifier]]:
    """Decorator registering a verifier *factory* under ``name``."""

    def deco(factory: Callable[..., Verifier]) -> Callable[..., Verifier]:
        if name in _REGISTRY:
            raise ValueError(f"verifier {name!r} already registered")
        _REGISTRY[name] = factory
        return factory

    return deco


def get_verifier_factory(name: str) -> Callable[..., Verifier]:
    """Return the registered factory for ``name`` (loading entry points on first miss)."""
    if name not in _REGISTRY:
        _load_entry_points()
    if name not in _REGISTRY:
        raise KeyError(
            f"no verifier registered as {name!r}; known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def build_verifier(name: str, **config: Any) -> Verifier:
    """Instantiate the named verifier with its ``config``."""
    return get_verifier_factory(name)(**config)


def available_verifiers() -> list[str]:
    """Return the sorted names of all registered verifiers (incl. entry points)."""
    _load_entry_points()
    return sorted(_REGISTRY)


def _load_entry_points() -> None:
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    _entry_points_loaded = True
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return
    try:
        eps = entry_points(group=_ENTRY_POINT_GROUP)
    except TypeError:  # pragma: no cover
        eps = entry_points().get(_ENTRY_POINT_GROUP, [])
    for ep in eps:
        if ep.name not in _REGISTRY:
            _REGISTRY[ep.name] = ep.load()
