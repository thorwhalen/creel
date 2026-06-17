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
from creel.extract.llm import (
    ClusterLLMExtractor,
    LLMClient,
    LLMExtractor,
    anthropic_client,
    build_instruction,
    compile_output_schema,
    make_cluster_llm_extractor,
    make_llm_extractor,
)
from creel.extract.query import (
    make_json_extractor,
    make_sql_extractor,
    make_table_map_extractor,
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
    "make_table_map_extractor",
    "make_sql_extractor",
    "make_json_extractor",
    "LLMClient",
    "LLMExtractor",
    "ClusterLLMExtractor",
    "make_llm_extractor",
    "make_cluster_llm_extractor",
    "anthropic_client",
    "compile_output_schema",
    "build_instruction",
    "ExtractedNode",
    "ExtractedEdge",
    "Extraction",
    "ExtractionContext",
    "Extractor",
    "available_extractors",
    "build_extractor",
    "register_extractor",
]
