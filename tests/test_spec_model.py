"""Tests for the grammar model: taxonomy, inheritance, lookups."""

from creel.spec.model import (
    AttrSchema,
    EdgeType,
    GraphSpec,
    NodeType,
    effective_attributes,
)


def test_lookups(sample_spec):
    assert sample_spec.node_type("donor").id == "donor"
    assert sample_spec.edge_type("funds").subject_type == "donor"
    assert sample_spec.element_type("delivers").id == "delivers"
    assert sample_spec.node_type("nope") is None
    assert sample_spec.enum("Currency").permissible_values == ("USD", "EUR", "CHF")


def test_inheritance_effective_attributes(sample_spec):
    # 'outcome' is_a 'result' which declares the required 'statement' attribute.
    eff = effective_attributes(sample_spec, "outcome")
    assert "statement" in eff
    assert eff["statement"].required is True
    # 'donor' has no parents, only its own attributes.
    assert set(effective_attributes(sample_spec, "donor")) == {"name", "dac_code"}


def test_is_subtype(sample_spec):
    assert sample_spec.is_subtype("outcome", "result") is True
    assert sample_spec.is_subtype("outcome", "outcome") is True
    assert sample_spec.is_subtype("outcome", "donor") is False
    assert sample_spec.is_subtype("unknown", "result") is False


def test_mixins_multiple_inheritance():
    spec = GraphSpec(
        node_types=(
            NodeType("timestamped", attributes=(AttrSchema("created_at", range="datetime"),)),
            NodeType("named", attributes=(AttrSchema("name", required=True),)),
            NodeType("person", is_a="named", mixins=("timestamped",),
                     attributes=(AttrSchema("age", range="integer"),)),
        )
    )
    eff = effective_attributes(spec, "person")
    assert set(eff) == {"name", "created_at", "age"}
    assert spec.is_subtype("person", "named") is True
    assert spec.is_subtype("person", "timestamped") is True


def test_own_attribute_overrides_inherited():
    spec = GraphSpec(
        node_types=(
            NodeType("base", attributes=(AttrSchema("x", required=False),)),
            NodeType("child", is_a="base", attributes=(AttrSchema("x", required=True),)),
        )
    )
    assert effective_attributes(spec, "child")["x"].required is True


def test_attrschema_enum_normalised_to_tuple():
    a = AttrSchema("status", enum=["open", "closed"])
    assert a.enum == ("open", "closed")


def test_edge_is_first_class_with_own_attributes(sample_spec):
    funds = sample_spec.edge_type("funds")
    assert isinstance(funds, EdgeType)
    assert {a.name for a in funds.attributes} == {"amount", "currency"}
    assert funds.attribute("amount").minimum == 0
