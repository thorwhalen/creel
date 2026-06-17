"""LinkML bridge + schema codegen for the grammar (EPIC 2.4, decision D3).

LinkML is creel's optional **build-time authoring front-end**, not the runtime SSOT
(the Python :class:`~creel.spec.model.GraphSpec` is). This module bridges the two and
generates validation artifacts — all **dependency-free** for the common subset (a
LinkML schema is YAML with ``classes`` / ``attributes`` / ``enums``), so it is fully
testable without the heavy ``linkml`` package:

- :func:`to_linkml` — ``GraphSpec`` → a LinkML schema dict (YAML-able).
- :func:`load_linkml` — a LinkML schema (dict or YAML path) → ``GraphSpec``.
- :func:`generate_json_schema` — ``GraphSpec`` → JSON Schema (a ``$def`` per type,
  with enums/ranges/cardinality) for external validators.
- :func:`generate_pydantic` — a Pydantic model per node/edge type for typed access.

Edges are LinkML classes flagged ``represents_relationship: true`` (the LinkML idiom
for first-class, attribute-bearing relations).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Union

from creel.spec.model import (
    AttrSchema,
    EdgeType,
    EnumDef,
    GraphSpec,
    NodeType,
    effective_attributes,
)

_JSON_TYPE = {
    "string": "string",
    "integer": "integer",
    "decimal": "number",
    "float": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
}
_PY_TYPE = {
    "string": str,
    "integer": int,
    "decimal": float,
    "float": float,
    "boolean": bool,
    "date": str,
    "datetime": str,
}


# --- GraphSpec -> LinkML ------------------------------------------------------
def to_linkml(spec: GraphSpec) -> dict[str, Any]:
    """Emit a LinkML schema dict (pass to ``yaml.safe_dump`` to write a ``.yaml``)."""
    classes: dict[str, Any] = {}
    for nt in spec.node_types:
        classes[nt.id] = _linkml_class(nt)
    for et in spec.edge_types:
        cls = _linkml_class(et)
        cls["represents_relationship"] = True
        if et.subject_type:
            cls["subject_type"] = et.subject_type
        if et.object_type:
            cls["object_type"] = et.object_type
        classes[et.id] = cls
    return {
        "id": spec.id or "https://creel.dev/schema/grammar",
        "name": (spec.id or "creel_grammar").replace("-", "_"),
        "enums": {
            e.name: {"permissible_values": {v: {} for v in e.permissible_values}}
            for e in spec.enums
        },
        "classes": classes,
    }


def _linkml_class(element) -> dict[str, Any]:
    cls: dict[str, Any] = {
        "attributes": {a.name: _linkml_slot(a) for a in element.attributes}
    }
    if element.description:
        cls["description"] = element.description
    if element.is_a:
        cls["is_a"] = element.is_a
    if element.mixins:
        cls["mixins"] = list(element.mixins)
    if element.abstract:
        cls["abstract"] = True
    return cls


def _linkml_slot(attr: AttrSchema) -> dict[str, Any]:
    slot: dict[str, Any] = {"range": attr.range}
    if attr.required:
        slot["required"] = True
    if attr.multivalued:
        slot["multivalued"] = True
    if attr.enum is not None:
        slot["permissible_values"] = list(attr.enum)
    if attr.minimum is not None:
        slot["minimum_value"] = attr.minimum
    if attr.maximum is not None:
        slot["maximum_value"] = attr.maximum
    if attr.pattern is not None:
        slot["pattern"] = attr.pattern
    if attr.description:
        slot["description"] = attr.description
    return slot


# --- LinkML -> GraphSpec ------------------------------------------------------
def load_linkml(schema: Union[dict, str, Path]) -> GraphSpec:
    """Parse a LinkML schema (dict, or a path to a ``.yaml``) into a :class:`GraphSpec`."""
    if isinstance(schema, (str, Path)):
        import yaml  # PyYAML; only needed for path loading

        schema = yaml.safe_load(Path(schema).read_text())
    enums = tuple(
        EnumDef(name, tuple((body or {}).get("permissible_values", {}).keys()))
        for name, body in (schema.get("enums") or {}).items()
    )
    node_types: list[NodeType] = []
    edge_types: list[EdgeType] = []
    for cname, cbody in (schema.get("classes") or {}).items():
        cbody = cbody or {}
        attrs = tuple(
            _attr_from_slot(n, s or {})
            for n, s in (cbody.get("attributes") or {}).items()
        )
        common = dict(
            description=cbody.get("description"),
            is_a=cbody.get("is_a"),
            mixins=tuple(cbody.get("mixins", ())),
            attributes=attrs,
            abstract=bool(cbody.get("abstract", False)),
        )
        if cbody.get("represents_relationship"):
            edge_types.append(
                EdgeType(
                    cname,
                    subject_type=cbody.get("subject_type"),
                    object_type=cbody.get("object_type"),
                    **common,
                )
            )
        else:
            node_types.append(NodeType(cname, **common))
    return GraphSpec(
        id=schema.get("id"),
        node_types=tuple(node_types),
        edge_types=tuple(edge_types),
        enums=enums,
    )


def _attr_from_slot(name: str, slot: dict[str, Any]) -> AttrSchema:
    return AttrSchema(
        name=name,
        range=slot.get("range", "string"),
        required=bool(slot.get("required", False)),
        multivalued=bool(slot.get("multivalued", False)),
        enum=tuple(slot["permissible_values"])
        if slot.get("permissible_values")
        else None,
        minimum=slot.get("minimum_value"),
        maximum=slot.get("maximum_value"),
        pattern=slot.get("pattern"),
        description=slot.get("description"),
    )


# --- GraphSpec -> JSON Schema -------------------------------------------------
def generate_json_schema(spec: GraphSpec) -> dict[str, Any]:
    """Generate a JSON Schema with a ``$def`` per node/edge type (for external validators)."""
    defs: dict[str, Any] = {}
    for et in spec.iter_element_types():
        props, required = {}, []
        for name, attr in effective_attributes(spec, et.id).items():
            props[name] = _json_attr(attr, spec)
            if attr.required:
                required.append(name)
        schema: dict[str, Any] = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        defs[et.id] = schema
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": defs}


def _json_attr(attr: AttrSchema, spec: GraphSpec) -> dict[str, Any]:
    permissible = attr.enum or (
        spec.enum(attr.range).permissible_values if spec.enum(attr.range) else None
    )
    base: dict[str, Any] = (
        {"enum": list(permissible)}
        if permissible
        else {"type": _JSON_TYPE.get(attr.range, "string")}
    )
    # Unlike the LLM decode schema, a *validation* schema DOES carry value bounds.
    if attr.minimum is not None:
        base["minimum"] = attr.minimum
    if attr.maximum is not None:
        base["maximum"] = attr.maximum
    if attr.pattern is not None:
        base["pattern"] = attr.pattern
    if attr.description:
        base["description"] = attr.description
    return {"type": "array", "items": base} if attr.multivalued else base


# --- GraphSpec -> Pydantic ----------------------------------------------------
def generate_pydantic(spec: GraphSpec) -> dict[str, type]:
    """Generate one Pydantic v2 model per node/edge type (typed access at the IO boundary)."""
    from pydantic import Field, create_model

    models: dict[str, type] = {}
    for et in spec.iter_element_types():
        fields: dict[str, Any] = {}
        for name, attr in effective_attributes(spec, et.id).items():
            annotation = _py_type(attr, spec)
            constraints: dict[str, Any] = {}
            if attr.minimum is not None:
                constraints["ge"] = attr.minimum
            if attr.maximum is not None:
                constraints["le"] = attr.maximum
            if attr.pattern is not None:
                constraints["pattern"] = attr.pattern
            default = ... if attr.required else None
            fields[name] = (
                annotation if attr.required else Optional[annotation],
                Field(default, **constraints),
            )
        models[et.id] = create_model(
            et.id.replace(".", "_").title().replace("_", ""), **fields
        )
    return models


def _py_type(attr: AttrSchema, spec: GraphSpec):
    base = _PY_TYPE.get(attr.range, str)
    return List[base] if attr.multivalued else base


__all__ = ["to_linkml", "load_linkml", "generate_json_schema", "generate_pydantic"]
