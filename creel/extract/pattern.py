"""Pattern / function extractors — the trivial, deterministic strategy family.

These are the strategies that bring the facade up before any LLM exists, and the
ones to prefer whenever a source is regular enough that an LLM would be overkill
(decision D5: route to the cheapest strategy that fits). They are fully
deterministic, so every extraction gets ``confidence=1.0`` and exact grounding.

- :class:`RegexNodeExtractor` — scan text sources; each regex match becomes a node
  whose attributes are the named capture groups.
- :class:`RegexEdgeExtractor` — likewise for first-class edges, with endpoint node
  ids built from templates over the captured groups.
- :func:`make_function_extractor` — adapt any ``(ctx) -> Extraction`` callable.

All three are registered (``"regex_node"``, ``"regex_edge"``, ``"function"``) so a
binding can name them and pass configuration as pure data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from creel.evidence import (
    TextPositionSelector,
    TextQuoteSelector,
    deterministic_evidence,
)
from creel.extract.protocol import (
    ExtractedEdge,
    ExtractedNode,
    Extraction,
    ExtractionContext,
)
from creel.extract.registry import register_extractor

_CONTEXT_CHARS = 24  # chars of prefix/suffix kept for a TextQuoteSelector


def _slug(value: str) -> str:
    """Lowercase, collapse non-alphanumerics to single dashes — for stable ids."""
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-") or "x"


def _cast(value: str, to: str) -> Any:
    """Cast a captured string to ``to`` (``int``/``float``/``number``/``string``).

    Numeric casts tolerate thousands separators and surrounding currency symbols.
    """
    if to in ("int", "float", "number"):
        cleaned = re.sub(r"[^0-9.\-]", "", value)
        if cleaned in ("", "-", ".", "-."):
            return value
        number = float(cleaned)
        if to == "int" or (to == "number" and number.is_integer()):
            return int(number)
        return number
    return value


def _apply_casts(attrs: dict[str, Any], casts: Mapping[str, str]) -> dict[str, Any]:
    return {k: (_cast(v, casts[k]) if k in casts and isinstance(v, str) else v) for k, v in attrs.items()}


def _grounding(text: str, match: "re.Match[str]", source_id: str):
    start, end = match.start(), match.end()
    return (
        TextQuoteSelector(
            exact=match.group(0),
            prefix=text[max(0, start - _CONTEXT_CHARS):start],
            suffix=text[end:end + _CONTEXT_CHARS],
        ),
        TextPositionSelector(start=start, end=end, source_id=source_id),
    )


@dataclass
class RegexNodeExtractor:
    """Produce nodes from regex matches over text sources.

    The named capture groups become the node's attributes; ``id_attribute`` (or a
    content hash) yields a stable node id; ``casts`` converts captured strings to
    numbers where the grammar expects them.
    """

    pattern: str
    node_type: Optional[str] = None  # defaults to ctx.element_id
    flags: int = 0
    id_attribute: Optional[str] = None
    casts: Mapping[str, str] = field(default_factory=dict)

    def __call__(self, ctx: ExtractionContext) -> Extraction:
        node_type = self.node_type or ctx.element_id
        regex = re.compile(self.pattern, self.flags)
        nodes: list[ExtractedNode] = []
        for src in ctx.sources.texts():
            text = src.content
            for match in regex.finditer(text):
                attrs = _apply_casts(
                    {k: v for k, v in match.groupdict().items() if v is not None}, self.casts
                )
                seed = attrs.get(self.id_attribute) if self.id_attribute else match.group(0)
                node_id = f"{node_type}:{_slug(seed)}"
                evidence = deterministic_evidence(
                    source_id=src.id,
                    generated_by=f"pattern:RegexNodeExtractor:{ctx.element_id}",
                    grounding=_grounding(text, match, src.id),
                )
                nodes.append(ExtractedNode(node_id, node_type, attrs, evidence))
        return Extraction(nodes=nodes)


@dataclass
class RegexEdgeExtractor:
    """Produce first-class edges from regex matches over text sources.

    ``source_id_template``/``target_id_template`` build the endpoint node ids from
    the captured groups (e.g. ``"donor:{donor}"``); remaining groups not consumed by
    the templates become edge attributes.
    """

    pattern: str
    source_id_template: str
    target_id_template: str
    edge_type: Optional[str] = None  # defaults to ctx.element_id
    flags: int = 0
    casts: Mapping[str, str] = field(default_factory=dict)
    exclude_groups: tuple = ()  # named groups used only as endpoint refs, not attributes

    def __call__(self, ctx: ExtractionContext) -> Extraction:
        edge_type = self.edge_type or ctx.element_id
        regex = re.compile(self.pattern, self.flags)
        edges: list[ExtractedEdge] = []
        for src in ctx.sources.texts():
            text = src.content
            for i, match in enumerate(regex.finditer(text)):
                groups = {k: v for k, v in match.groupdict().items() if v is not None}
                source_id = _format_template(self.source_id_template, groups)
                target_id = _format_template(self.target_id_template, groups)
                attr_groups = {k: v for k, v in groups.items() if k not in self.exclude_groups}
                attrs = _apply_casts(attr_groups, self.casts)
                edge_id = f"{edge_type}:{_slug(source_id)}->{_slug(target_id)}:{i}"
                evidence = deterministic_evidence(
                    source_id=src.id,
                    generated_by=f"pattern:RegexEdgeExtractor:{ctx.element_id}",
                    grounding=_grounding(text, match, src.id),
                )
                edges.append(
                    ExtractedEdge(edge_id, edge_type, source_id, target_id, attrs, evidence)
                )
        return Extraction(edges=edges)


def _format_template(template: str, groups: Mapping[str, Any]) -> str:
    slug_groups = {k: _slug(str(v)) for k, v in groups.items()}
    return template.format(**slug_groups)


def make_function_extractor(func: Callable[[ExtractionContext], Extraction]):
    """Adapt any ``(ctx) -> Extraction`` callable into an extractor (identity wrapper)."""
    return func


# --- registry factories (binding config is pure data) -------------------------
@register_extractor("regex_node")
def _regex_node_factory(**config: Any) -> RegexNodeExtractor:
    return RegexNodeExtractor(**config)


@register_extractor("regex_edge")
def _regex_edge_factory(**config: Any) -> RegexEdgeExtractor:
    return RegexEdgeExtractor(**config)


@register_extractor("function")
def _function_factory(*, func: Callable[[ExtractionContext], Extraction], **_: Any):
    return make_function_extractor(func)
