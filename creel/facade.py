"""The facade: ``extract(sources, graph_spec, extractors) -> graph``.

This is creel's single public entry point and the embodiment of the whole package
(decisions D5/D7/D11). It:

1. normalises the flexible ``sources`` and ``extractors`` arguments;
2. equijoins the grammar with the extractor bindings into a runnable plan;
3. maps each resolved extractor over the sources (embarrassingly parallel in
   principle; run sequentially here for determinism and simplicity);
4. assembles the results into a Labeled Property Graph — nodes first, then the
   edges that reference them — attaching each element's evidence to the separable
   audit sidecar;
5. returns the graph (the single source of truth), with ``graph.evidence`` and
   ``graph.report`` carrying the joinable audit/diagnostic layers.

Value-level constraint checking and faithfulness verification are the job of the
verifier subsystem (decision D6), not of the facade.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from creel.bindings import ExtractorBindings, coerce_bindings
from creel.extract.cache import Cache, NullCache
from creel.extract.protocol import ExtractionContext
from creel.graph.model import Graph
from creel.join import ResolvedPlan, SchemaAsExtractor, join
from creel.sources import SourcesArg, coerce_sources
from creel.spec.model import GraphSpec

# on_missing_binding policies
SCHEMA_AS_EXTRACTOR = "schema_as_extractor"
SKIP = "skip"
ERROR = "error"


def extract(
    sources: SourcesArg,
    graph_spec: GraphSpec,
    extractors: Union[ExtractorBindings, Mapping, None] = None,
    *,
    cache: Optional[Cache] = None,
    services: Optional[Mapping[str, Any]] = None,
    on_missing_binding: str = SCHEMA_AS_EXTRACTOR,
    schema_as_extractor: Optional[SchemaAsExtractor] = None,
) -> Graph:
    """Read ``sources``, populate the graph described by ``graph_spec``, return it.

    Args (beyond the 3rd, keyword-only):
        cache: a :class:`~creel.extract.cache.Cache` for expensive extractor calls.
        services: injected dependencies (e.g. an LLM client under key ``"llm"``).
        on_missing_binding: what to do for grammar elements with no extractor —
            ``"schema_as_extractor"`` (use the ``schema_as_extractor`` factory if
            available, else skip), ``"skip"``, or ``"error"``.
        schema_as_extractor: factory ``(element_type, spec) -> Extractor`` used for
            unbound elements (provided by the LLM strategy layer; ``None`` here).

    Returns:
        A :class:`~creel.graph.model.Graph` (the SSOT). ``graph.evidence`` maps
        element id → evidence record; ``graph.report`` holds run diagnostics.
    """
    bundle = coerce_sources(sources)
    bindings = coerce_bindings(extractors)
    cache = cache or NullCache()
    services = dict(services or {})

    fallback = (
        schema_as_extractor if on_missing_binding == SCHEMA_AS_EXTRACTOR else None
    )
    plan = join(graph_spec, bindings, schema_as_extractor=fallback)

    if plan.unbound and on_missing_binding == ERROR:
        raise ValueError(f"no extractor bound for elements: {list(plan.unbound)}")

    graph = Graph()
    graph.report["unbound_elements"] = list(plan.unbound)
    _run_plan(plan, bundle, graph_spec, cache, services, graph)
    return graph


def _run_plan(
    plan: ResolvedPlan,
    bundle,
    graph_spec: GraphSpec,
    cache: Cache,
    services: Mapping[str, Any],
    graph: Graph,
) -> None:
    """Execute every step, then assemble nodes-before-edges into ``graph``."""
    all_nodes = []
    all_edges = []
    for step in plan.steps:
        ctx = ExtractionContext(
            element_id=step.element_id,
            element_type=step.element_type,
            sources=bundle,
            spec=graph_spec,
            cache=cache,
            services=services,
        )
        extraction = step.extractor(ctx)
        all_nodes.extend(extraction.nodes)
        all_edges.extend(extraction.edges)

    for node in all_nodes:
        graph.add_node(node.id, types=(node.type,), attributes=node.attributes)
        if node.evidence is not None:
            graph.evidence[node.id] = node.evidence

    skipped: list[dict[str, str]] = []
    for edge in all_edges:
        if not (graph.has_node(edge.source) and graph.has_node(edge.target)):
            skipped.append(
                {
                    "edge_id": edge.id,
                    "reason": "missing-endpoint",
                    "source": edge.source,
                    "target": edge.target,
                }
            )
            continue
        graph.add_edge(
            edge.id,
            source=edge.source,
            target=edge.target,
            type=edge.type,
            attributes=edge.attributes,
        )
        if edge.evidence is not None:
            graph.evidence[edge.id] = edge.evidence

    graph.report["skipped_edges"] = skipped
