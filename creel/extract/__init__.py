"""creel extraction layer: the pluggable strategies that populate the graph.

Re-exports the extractor contract (:mod:`creel.extract.protocol`), the built-in
pattern/function family (:mod:`creel.extract.pattern`), the strategy registry
(:mod:`creel.extract.registry`), and the cache seam (:mod:`creel.extract.cache`).
Importing this package registers the built-in ``regex_node`` / ``regex_edge`` /
``function`` strategies.
"""

from creel.extract.cache import Cache, DictCache, NullCache, cache_key
from creel.extract.pattern import (
    RegexEdgeExtractor,
    RegexNodeExtractor,
    make_function_extractor,
)
from creel.extract.protocol import (
    ExtractedEdge,
    ExtractedNode,
    Extraction,
    ExtractionContext,
    Extractor,
)
from creel.extract.registry import (
    available_extractors,
    build_extractor,
    register_extractor,
)

__all__ = [
    "Cache",
    "DictCache",
    "NullCache",
    "cache_key",
    "RegexNodeExtractor",
    "RegexEdgeExtractor",
    "make_function_extractor",
    "ExtractedNode",
    "ExtractedEdge",
    "Extraction",
    "ExtractionContext",
    "Extractor",
    "available_extractors",
    "build_extractor",
    "register_extractor",
]
