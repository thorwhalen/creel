"""Tests for the LinkML bridge + schema codegen (EPIC 2.4) — all dependency-free."""

import pytest

from creel.spec.linkml import (
    generate_json_schema,
    generate_pydantic,
    load_linkml,
    to_linkml,
)


def test_linkml_roundtrip(sample_spec):
    spec2 = load_linkml(to_linkml(sample_spec))
    assert {n.id for n in spec2.node_types} == {n.id for n in sample_spec.node_types}
    assert {e.id for e in spec2.edge_types} == {e.id for e in sample_spec.edge_types}
    assert spec2.enum("Currency").permissible_values == ("USD", "EUR", "CHF")
    # ranged + required edge attribute survives the round-trip
    amount = spec2.edge_type("funds").attribute("amount")
    assert amount.range == "decimal" and amount.minimum == 0 and amount.required
    # first-class edges + endpoints
    assert spec2.edge_type("funds").subject_type == "donor"
    # inheritance preserved
    assert spec2.node_type("outcome").is_a == "result"
    assert spec2.node_type("result").abstract is True


def test_edges_are_linkml_relationships(sample_spec):
    schema = to_linkml(sample_spec)
    assert schema["classes"]["funds"]["represents_relationship"] is True
    assert "represents_relationship" not in schema["classes"]["donor"]


def test_generate_json_schema_carries_constraints(sample_spec):
    js = generate_json_schema(sample_spec)
    funds = js["$defs"]["funds"]
    assert funds["properties"]["amount"]["minimum"] == 0      # validation schema HAS bounds
    assert funds["properties"]["currency"]["enum"] == ["USD", "EUR", "CHF"]
    assert "amount" in funds["required"] and "currency" in funds["required"]


def test_generate_pydantic_models_validate(sample_spec):
    from pydantic import ValidationError

    models = generate_pydantic(sample_spec)
    donor = models["donor"](name="Government X")        # required name present
    assert donor.name == "Government X"
    with pytest.raises(ValidationError):
        models["donor"]()                                # missing required name
    with pytest.raises(ValidationError):
        models["funds"](amount=-5, currency="USD")       # amount ge=0 violated


def test_load_linkml_from_yaml_path(sample_spec, tmp_path):
    import yaml

    path = tmp_path / "grammar.yaml"
    path.write_text(yaml.safe_dump(to_linkml(sample_spec)))
    spec2 = load_linkml(path)
    assert {n.id for n in spec2.node_types} == {n.id for n in sample_spec.node_types}
