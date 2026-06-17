"""Tests for the query extractor family: table_map, sql (DuckDB), json_query."""

import pytest

from creel.extract.registry import build_extractor
from creel.extract.protocol import ExtractionContext
from creel.sources import JSON, TABLE, Source, SourceBundle
from creel.spec.model import GraphSpec, NodeType

ROWS = [
    {"code": "D1", "name": "Alpha", "amt": "1,000"},
    {"code": "D2", "name": "Beta", "amt": "2,000"},
]


def _ctx(element_id, source):
    spec = GraphSpec(node_types=(NodeType(element_id),))
    return ExtractionContext(
        element_id=element_id,
        element_type=spec.element_type(element_id) or NodeType(element_id),
        sources=SourceBundle([source]),
        spec=spec,
    )


def test_table_map_nodes_with_casts_and_grounding():
    src = Source("t", ROWS, kind=TABLE)
    ex = build_extractor(
        "table_map", records_source="t", type="donor", id_template="donor:{code}",
        attributes={"name": "name", "amount": "amt"}, casts={"amount": "int"},
    )
    out = ex(_ctx("donor", src))
    assert [n.id for n in out.nodes] == ["donor:d1", "donor:d2"]
    assert out.nodes[0].attributes == {"name": "Alpha", "amount": 1000}
    assert out.nodes[0].evidence.grounding[0].kind == "CellSelector"


def test_table_map_edges():
    rows = [{"a": "X", "b": "Y"}, {"a": "P", "b": "Q"}]
    src = Source("t", rows, kind=TABLE)
    ex = build_extractor(
        "table_map", records_source="t", kind="edge", type="rel",
        source_template="n:{a}", target_template="n:{b}",
    )
    out = ex(_ctx("rel", src))
    assert [(e.source, e.target) for e in out.edges] == [("n:x", "n:y"), ("n:p", "n:q")]


def test_table_map_edge_requires_templates():
    src = Source("t", ROWS, kind=TABLE)
    ex = build_extractor("table_map", records_source="t", kind="edge", type="rel")
    with pytest.raises(ValueError, match="source_template"):
        ex(_ctx("rel", src))


def test_sql_extractor_filters_with_parameters():
    pytest.importorskip("duckdb")  # optional [query] extra
    src = Source("t", ROWS, kind=TABLE)
    ex = build_extractor(
        "sql", records_source="t", sql="SELECT * FROM t WHERE name = ?", params=["Beta"],
        type="donor", id_template="donor:{code}", attributes={"name": "name"},
    )
    out = ex(_ctx("donor", src))
    assert [n.id for n in out.nodes] == ["donor:d2"]
    assert out.nodes[0].attributes == {"name": "Beta"}


def test_json_query_select_and_filter():
    pytest.importorskip("jmespath")  # optional [query] extra
    content = {"items": [{"id": "x", "v": 5}, {"id": "y", "v": 1}]}
    src = Source("j", content, kind=JSON)
    ex = build_extractor(
        "json_query", records_source="j", select="items", where={"v": {"$gt": 2}},
        type="thing", id_template="thing:{id}", attributes={"value": "v"},
    )
    out = ex(_ctx("thing", src))
    assert [n.id for n in out.nodes] == ["thing:x"]
    assert out.nodes[0].attributes == {"value": 5}
    assert out.nodes[0].evidence.grounding[0].kind == "JsonPathSelector"


def test_query_strategies_registered():
    from creel.extract.registry import available_extractors

    assert {"table_map", "sql", "json_query"} <= set(available_extractors())
