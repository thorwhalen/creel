"""LLM extractor — schema-as-extractor via a provider-agnostic, injected client.

This is the default strategy for prose (decision D5). It compiles a grammar
element's attribute schema into a JSON schema, turns the element/attribute
``description``s into the extraction instruction (**schema-as-extractor**), asks an
LLM for structured output, and validates the result — re-asking on failure
(**validate-retry**, decision D6: the decoder guarantees shape, value-level
constraints are checked here). Every extracted value is run through a deterministic
**faithfulness gate** (does it occur in the source?) which grounds it and sets
confidence/review-state (decision D8, EPIC 6.6).

Per decision D10 the LLM client is **injected** via ``ctx.services["llm"]`` — the
core pins no provider SDK and the extractor is fully testable with a fake client.
A default Anthropic adapter lives behind the ``[anthropic]`` extra (:func:`anthropic_client`).
"""

from __future__ import annotations

import importlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol, runtime_checkable

from creel.evidence import (
    AUTO,
    NEEDS_REVIEW,
    SELF_CONSISTENCY,
    VERBALIZED,
    Confidence,
    Evidence,
    Provenance,
    TextPositionSelector,
    TextQuoteSelector,
)
from creel.policy import ExtractionPolicy
from creel.extract.protocol import (
    ExtractedEdge,
    ExtractedNode,
    Extraction,
    ExtractionContext,
)
from creel.extract.registry import register_extractor
from creel.extract.transforms import slug
from creel.spec.model import EdgeType, ElementType, GraphSpec, effective_attributes
from creel.spec.validate import validate_attributes

_SYSTEM = (
    "You are a careful information-extraction engine. Extract only what the source "
    "explicitly supports; never invent values. Return valid JSON only."
)
_CONTEXT_CHARS = 24
_JSON_TYPE = {
    "string": "string",
    "integer": "integer",
    "decimal": "number",
    "float": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
}


@runtime_checkable
class LLMClient(Protocol):
    """The thin LLM seam: return a JSON object conforming to ``schema``."""

    def complete_json(
        self, *, prompt: str, schema: Mapping[str, Any], system: Optional[str] = None
    ) -> Mapping[str, Any]:
        """Return a parsed JSON object for ``prompt`` shaped like ``schema``."""
        ...


def _attr_json_schema(attr, spec: GraphSpec) -> dict[str, Any]:
    # NB: numeric minimum/maximum are intentionally NOT emitted (D6 — the decoder
    # does not enforce ranges; they are checked post-decode in validate-retry).
    schema: dict[str, Any] = {}
    permissible = attr.enum or (
        spec.enum(attr.range).permissible_values if spec.enum(attr.range) else None
    )
    if permissible is not None:
        schema["enum"] = list(permissible)
    else:
        schema["type"] = _JSON_TYPE.get(attr.range, "string")
    if attr.description:
        schema["description"] = attr.description
    if attr.multivalued:
        return {"type": "array", "items": schema}
    return schema


def compile_output_schema(element_type: ElementType, spec: GraphSpec) -> dict[str, Any]:
    """JSON schema for the LLM's output: ``{"items": [ {attributes…} ]}``."""
    attrs = effective_attributes(spec, element_type.id)
    item: dict[str, Any] = {
        "type": "object",
        "properties": {n: _attr_json_schema(a, spec) for n, a in attrs.items()},
    }
    required = [n for n, a in attrs.items() if a.required]
    if isinstance(element_type, EdgeType):
        item["properties"]["_source"] = {
            "type": "string",
            "description": "source node name/id",
        }
        item["properties"]["_target"] = {
            "type": "string",
            "description": "target node name/id",
        }
    if required:
        item["required"] = required
    return {
        "type": "object",
        "properties": {"items": {"type": "array", "items": item}},
        "required": ["items"],
    }


def build_instruction(element_type: ElementType, spec: GraphSpec) -> str:
    """Turn the element + attribute descriptions into the extraction instruction."""
    desc = element_type.description or f"a {element_type.id}"
    lines = [
        f"From the SOURCE, extract every {element_type.id} ({desc}).",
        "For each, provide these attributes:",
    ]
    for name, attr in effective_attributes(spec, element_type.id).items():
        extra = []
        permissible = attr.enum or (
            spec.enum(attr.range).permissible_values if spec.enum(attr.range) else None
        )
        if permissible is not None:
            extra.append(f"one of {list(permissible)}")
        if attr.minimum is not None:
            extra.append(f">= {attr.minimum}")
        if attr.maximum is not None:
            extra.append(f"<= {attr.maximum}")
        if attr.required:
            extra.append("required")
        suffix = f" ({'; '.join(extra)})" if extra else ""
        lines.append(f"- {name}: {attr.description or name}{suffix}")
    if isinstance(element_type, EdgeType):
        lines.append(
            "- _source / _target: the names/ids of the two nodes this relation connects."
        )
    lines.append(
        "Only extract values explicitly supported by the source; do not invent."
    )
    return "\n".join(lines)


@dataclass
class LLMExtractor:
    """Extract instances of one grammar element from prose via an injected LLM client."""

    node_type: Optional[str] = None  # unused override; element comes from ctx
    max_retries: int = 2
    instruction: Optional[str] = None
    model: Optional[str] = None
    id_attribute: Optional[str] = None
    policy: Optional[ExtractionPolicy] = None

    def __call__(self, ctx: ExtractionContext) -> Extraction:
        client = ctx.services.get("llm")
        if client is None:
            raise ValueError(
                "LLMExtractor needs an LLM client at ctx.services['llm']. Install a "
                "provider extra and pass its factory, e.g. `pip install creel[aix]` then "
                "`services={'llm': aix_client()}` (or creel[anthropic] / anthropic_client), "
                "or inject any object with a `complete_json(prompt, schema, system=None)` method."
            )
        et = ctx.element_type
        policy = self._policy(ctx, et)
        out_schema = compile_output_schema(et, ctx.spec)
        instruction = self.instruction or build_instruction(et, ctx.spec)
        text = "\n\n".join(s.content for s in ctx.sources.texts())
        items, confidence = self._extract(
            client, instruction, text, out_schema, et, ctx, policy
        )
        return items_to_extraction(
            items,
            et,
            ctx,
            text,
            model=self.model,
            id_attribute=self.id_attribute,
            base_confidence=confidence,
            review_below=policy.review_below,
        )

    def _policy(self, ctx, et) -> ExtractionPolicy:
        policy = (
            self.policy
            or ctx.config.get("policy")
            or ctx.services.get("policy")
            or ExtractionPolicy(max_retries=self.max_retries)
        )
        return policy.for_element(ctx.element_id, et.id)

    def _extract(self, client, instruction, text, out_schema, et, ctx, policy):
        """Run extraction, with self-consistency voting if the policy asks for it."""
        n = max(1, policy.self_consistency_samples)
        if n == 1:
            return self._extract_items(
                client, instruction, text, out_schema, et, ctx, policy.max_retries
            ), None
        samples = [
            self._extract_items(
                client, instruction, text, out_schema, et, ctx, policy.max_retries
            )
            for _ in range(n)
        ]
        keyed = [json.dumps(s, sort_keys=True, default=str) for s in samples]
        top, count = Counter(keyed).most_common(1)[0]
        agreement = count / n
        confidence = Confidence(
            method=SELF_CONSISTENCY,
            score=agreement,
            review_status=NEEDS_REVIEW if agreement < policy.review_below else AUTO,
        )
        return json.loads(top), confidence

    def _extract_items(
        self, client, instruction, text, out_schema, et, ctx, max_retries
    ) -> list:
        base = f'{instruction}\n\nReturn a JSON object {{"items": [...]}}.\n\nSOURCE:\n{text}'
        feedback, best = "", []
        for _ in range(max_retries + 1):
            response = client.complete_json(
                prompt=base + feedback, schema=out_schema, system=_SYSTEM
            )
            items = list((response or {}).get("items", []))
            issues = []
            for item in items:
                payload = {k: v for k, v in item.items() if not str(k).startswith("_")}
                issues.extend(validate_attributes(payload, et.id, ctx.spec))
            if not issues:
                return items
            best = items
            feedback = (
                "\n\nThe previous response had these problems — fix them:\n"
                + "\n".join(f"- {i}" for i in issues[:20])
            )
        return best  # best-effort after retries; the verify pass is the final gate


def items_to_extraction(
    items,
    element_type,
    ctx,
    text,
    *,
    model=None,
    id_attribute=None,
    base_confidence: Optional[Confidence] = None,
    review_below: float = 0.5,
) -> Extraction:
    """Turn raw LLM ``items`` for one element type into an :class:`Extraction`.

    Each item is grounded (faithfulness gate) and gets an evidence record. Shared by
    the single-element :class:`LLMExtractor` and the :class:`ClusterLLMExtractor`.
    """
    nodes, edges = [], []
    source_id = next((s.id for s in ctx.sources.texts()), "source")
    derived = ",".join(s.id for s in ctx.sources.texts()) or "source"
    for i, item in enumerate(items):
        attrs = {k: v for k, v in item.items() if not str(k).startswith("_")}
        grounding, verified = _ground(attrs, text, source_id)
        evidence = Evidence(
            provenance=Provenance(
                derived_from=derived,
                generated_by=f"llm:{element_type.id}",
                attributed_to=model,
            ),
            grounding=grounding,
            confidence=_confidence(verified, base_confidence, review_below),
        )
        if isinstance(element_type, EdgeType):
            edges.append(
                ExtractedEdge(
                    f"{element_type.id}:{i}",
                    element_type.id,
                    str(item.get("_source", "")),
                    str(item.get("_target", "")),
                    attrs,
                    evidence,
                )
            )
        else:
            seed = (
                attrs.get(id_attribute)
                if id_attribute
                else next(iter(attrs.values()), i)
            )
            nodes.append(
                ExtractedNode(
                    f"{element_type.id}:{slug(seed)}", element_type.id, attrs, evidence
                )
            )
    return Extraction(nodes=nodes, edges=edges)


def _confidence(
    verified: bool, base: Optional[Confidence], review_below: float
) -> Confidence:
    """Confidence for one extracted item, applying the policy's review threshold.

    With a ``base`` (e.g. a self-consistency agreement score) keep its method/score and
    escalate to ``needs_review`` if ungrounded or below threshold; otherwise default to
    verbalized confidence derived from the faithfulness gate.
    """
    if base is not None:
        review = base.review_status
        if not verified or base.score < review_below:
            review = NEEDS_REVIEW
        return Confidence(
            method=base.method,
            score=base.score,
            verified=verified,
            review_status=review,
        )
    score = 1.0 if verified else 0.5
    review = AUTO if (verified and score >= review_below) else NEEDS_REVIEW
    return Confidence(
        method=VERBALIZED, score=score, verified=verified, review_status=review
    )


def _ground(attrs: Mapping[str, Any], text: str, source_id: str):
    """Faithfulness gate: ground the first string value that occurs verbatim in ``text``."""
    for value in attrs.values():
        if isinstance(value, str) and value and value in text:
            start = text.find(value)
            end = start + len(value)
            return (
                TextQuoteSelector(
                    exact=value,
                    prefix=text[max(0, start - _CONTEXT_CHARS) : start],
                    suffix=text[end : end + _CONTEXT_CHARS],
                ),
                TextPositionSelector(start=start, end=end, source_id=source_id),
            ), True
    return (), False


@dataclass
class ClusterLLMExtractor:
    """Extract a CLUSTER of coupled element types in ONE LLM pass (D-OP8).

    Reads ``ctx.element_types`` (set by a cluster binding), asks for a JSON object
    with one array per type, and emits instances of each. Grouping coupled types
    (e.g. donor + project + funds) in one pass preserves cross-type consistency that
    separate passes would break, while the document stays a single cacheable prefix.
    """

    max_retries: int = 2
    model: Optional[str] = None

    def __call__(self, ctx: ExtractionContext) -> Extraction:
        client = ctx.services.get("llm")
        if client is None:
            raise ValueError(
                "ClusterLLMExtractor needs an LLM client at ctx.services['llm']."
            )
        types = tuple(ctx.element_types)
        out_schema = {
            "type": "object",
            "properties": {
                et.id: compile_output_schema(et, ctx.spec)["properties"]["items"]
                for et in types
            },
            "required": [et.id for et in types],
        }
        instruction = self._instruction(types, ctx.spec)
        text = "\n\n".join(s.content for s in ctx.sources.texts())
        response = self._extract(client, instruction, text, out_schema, types, ctx)
        nodes, edges = [], []
        for et in types:
            extraction = items_to_extraction(
                list(response.get(et.id, [])), et, ctx, text, model=self.model
            )
            nodes.extend(extraction.nodes)
            edges.extend(extraction.edges)
        return Extraction(nodes=nodes, edges=edges)

    def _instruction(self, types, spec) -> str:
        parts = [
            "Extract a graph from the SOURCE. Return a JSON object with one array per type below."
        ]
        for et in types:
            parts.append(f"\n### {et.id}\n{build_instruction(et, spec)}")
        parts.append(
            "\nReturn JSON: {" + ", ".join(f'"{et.id}": [...]' for et in types) + "}."
        )
        return "\n".join(parts)

    def _extract(
        self, client, instruction, text, out_schema, types, ctx
    ) -> Mapping[str, Any]:
        base = f"{instruction}\n\nSOURCE:\n{text}"
        feedback, best = "", {}
        for _ in range(self.max_retries + 1):
            response = (
                client.complete_json(
                    prompt=base + feedback, schema=out_schema, system=_SYSTEM
                )
                or {}
            )
            issues = []
            for et in types:
                for item in response.get(et.id, []):
                    payload = {
                        k: v for k, v in item.items() if not str(k).startswith("_")
                    }
                    issues.extend(
                        f"[{et.id}] {i}"
                        for i in validate_attributes(payload, et.id, ctx.spec)
                    )
            if not issues:
                return response
            best = response
            feedback = (
                "\n\nThe previous response had these problems — fix them:\n"
                + "\n".join(f"- {i}" for i in issues[:20])
            )
        return best


def schema_as_extractor(element_type: ElementType, spec: GraphSpec) -> LLMExtractor:
    """Factory for the facade's ``on_missing_binding="schema_as_extractor"`` fallback."""
    return LLMExtractor()


@register_extractor("llm")
def make_llm_extractor(**config: Any) -> LLMExtractor:
    """Registry factory for the ``"llm"`` strategy."""
    return LLMExtractor(**config)


@register_extractor("cluster_llm")
def make_cluster_llm_extractor(**config: Any) -> ClusterLLMExtractor:
    """Registry factory for the ``"cluster_llm"`` strategy (one pass over a cluster)."""
    return ClusterLLMExtractor(**config)


# --- default Anthropic adapter (extra [anthropic]; lazy; provider-agnostic seam) --
def anthropic_client(
    *, model: str = "claude-sonnet-4-6", max_tokens: int = 4096
) -> LLMClient:
    """A default :class:`LLMClient` backed by Anthropic Claude. Requires ``creel[anthropic]``.

    Kept deliberately thin — it requests JSON for the given schema and parses it. For
    hardened structured output, wrap Instructor/Outlines behind the same seam.
    """
    anthropic = importlib.import_module("anthropic")  # creel[anthropic]
    client = anthropic.Anthropic()

    def complete_json(*, prompt, schema, system=None):
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=(system or _SYSTEM),
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nReturn JSON conforming to this schema:\n{json.dumps(schema)}",
                }
            ],
        )
        text = "".join(
            b.text for b in message.content if getattr(b, "type", None) == "text"
        )
        return json.loads(_first_json_object(text))

    return _FuncClient(complete_json)


@dataclass
class _FuncClient:
    """Adapt a ``complete_json`` callable into an :class:`LLMClient`."""

    _fn: Callable[..., Mapping[str, Any]]

    def complete_json(self, *, prompt, schema, system=None):
        """Delegate to the wrapped function."""
        return self._fn(prompt=prompt, schema=schema, system=system)


def _first_json_object(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


# --- aix integration (extra [aix]; the user's provider-agnostic AI package) -------
def aix_client(*, model: Optional[str] = None) -> LLMClient:
    """An :class:`LLMClient` backed by ``aix`` (uses aix's configured defaults).

    aix returns text; creel's prompt already asks for the JSON shape and validate-retry
    enforces value-level constraints, so the JSON is parsed out of the reply.
    Requires ``creel[aix]``. Pass ``model=`` to override aix's default model.
    """
    aix = importlib.import_module("aix")

    def complete_json(*, prompt, schema, system=None):
        full = prompt if system is None else f"{system}\n\n{prompt}"
        text = aix.ask(full, model=model)
        return json.loads(_first_json_object(text))

    return _FuncClient(complete_json)


def aix_judge(*, model: Optional[str] = None) -> Callable[[str], str]:
    """A judge callable for ``llm_rubric`` (returns the model's raw reply text).

    The rubric prompt already instructs the judge to return ``{"score","reason"}``;
    :class:`~creel.verify.rubric.LLMRubric` parses that out. Requires ``creel[aix]``.
    Use a *different* model from the extractor to mitigate self-preference bias (D9).
    """
    aix = importlib.import_module("aix")
    return lambda prompt: aix.ask(prompt, model=model)


def aix_embedder(*, model: Optional[str] = None) -> Callable[[str], Any]:
    """An embedder callable ``text -> vector`` (for ``semantic_similarity``). ``creel[aix]``."""
    aix = importlib.import_module("aix")
    return lambda text: aix.embed(text, model=model)


def aix_entity_judge(*, model: Optional[str] = None) -> Callable[[str, str], bool]:
    """An entity-resolution judge ``(a, b) -> bool`` for :class:`~creel.resolve.LLMResolver`."""
    aix = importlib.import_module("aix")

    def judge(a: str, b: str) -> bool:
        reply = aix.ask(
            f"Do '{a}' and '{b}' refer to the SAME real-world entity? Answer only yes or no.",
            model=model,
        )
        return reply.strip().lower().startswith("y")

    return judge
