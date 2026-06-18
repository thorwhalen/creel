"""Query extractors — pull graph elements from STRUCTURED sources (tables, JSON).

Per decision D5, when a source is structured, querying it is cheaper, faster, and
more auditable than asking an LLM to transcribe values. Three strategies, all driven
by **pure-data** specs (a record→element *mapping*, plus an optional query), never by
raw engine strings interpolated from untrusted input:

- ``table_map`` — declarative: map each row of a table source (``list[dict]``) to a
  node or edge. Zero extra dependencies.
- ``sql`` (extra ``[query]``) — run a **parameterized** DuckDB SQL query over a table
  source, then map the result rows. For filtering/joins/aggregation.
- ``json_query`` (extra ``[query]``) — select records from a JSON source via a
  JMESPath expression (+ optional equality filter), then map them.

The shared **mapping** spec keys (all optional unless noted):
  kind: "node" | "edge" (default "node");  type: element-type id (default = element id);
  id_template: e.g. "output:{output_code}"  (node id; values are slugged);
  id_from: column whose slugged value becomes the id (alt. to id_template);
  source_template / target_template: endpoint node ids for an edge (required for edges);
  attributes: { attr_name: column_name };  casts: { attr_name: "int"|"float"|"number" }.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence

from creel.evidence import CellSelector, JsonPathSelector, deterministic_evidence
from creel.extract.protocol import (
    ExtractedEdge,
    ExtractedNode,
    Extraction,
    ExtractionContext,
)
from creel.extract.registry import register_extractor
from creel.extract.transforms import apply_casts, fill_template, slug

Grounder = Callable[[int, Mapping[str, Any]], Sequence[Any]]


def _attrs(record: Mapping[str, Any], mapping: Mapping[str, Any]) -> dict[str, Any]:
    picked = {
        a: record[col]
        for a, col in mapping.get("attributes", {}).items()
        if col in record
    }
    return apply_casts(picked, mapping.get("casts", {}))


def _record_to_node(
    record, i, mapping, *, source_id, element_id, grounder
) -> ExtractedNode:
    el_type = mapping.get("type") or element_id
    if mapping.get("id_template"):
        node_id = fill_template(mapping["id_template"], record)
    elif mapping.get("id_from"):
        col = mapping["id_from"]
        if col not in record:
            raise KeyError(
                f"query node mapping for {element_id!r}: id_from column {col!r} "
                f"not in record; available columns: {sorted(record)}"
            )
        node_id = f"{el_type}:{slug(record[col])}"
    else:
        node_id = f"{el_type}:{i}"
    evidence = deterministic_evidence(
        source_id=source_id,
        generated_by=f"query:{element_id}",
        grounding=grounder(i, record),
    )
    return ExtractedNode(node_id, el_type, _attrs(record, mapping), evidence)


def _record_to_edge(
    record, i, mapping, *, source_id, element_id, grounder
) -> ExtractedEdge:
    el_type = mapping.get("type") or element_id
    for key in ("source_template", "target_template"):
        if not mapping.get(key):
            raise ValueError(f"query edge mapping for {element_id!r} needs {key!r}")
    edge_id = (
        fill_template(mapping["id_template"], {**record, "index": i})
        if mapping.get("id_template")
        else f"{el_type}:{i}"
    )
    evidence = deterministic_evidence(
        source_id=source_id,
        generated_by=f"query:{element_id}",
        grounding=grounder(i, record),
    )
    return ExtractedEdge(
        edge_id,
        el_type,
        fill_template(mapping["source_template"], record),
        fill_template(mapping["target_template"], record),
        _attrs(record, mapping),
        evidence,
    )


def _map_records(
    records, mapping, *, source_id, element_id, grounder: Optional[Grounder] = None
) -> Extraction:
    """Map an iterable of record dicts to an :class:`Extraction` per the mapping spec."""
    grounder = grounder or _cell_grounder(source_id, mapping)
    kind = mapping.get("kind", "node")
    nodes, edges = [], []
    for i, record in enumerate(records):
        if kind == "edge":
            edges.append(
                _record_to_edge(
                    record,
                    i,
                    mapping,
                    source_id=source_id,
                    element_id=element_id,
                    grounder=grounder,
                )
            )
        else:
            nodes.append(
                _record_to_node(
                    record,
                    i,
                    mapping,
                    source_id=source_id,
                    element_id=element_id,
                    grounder=grounder,
                )
            )
    return Extraction(nodes=nodes, edges=edges)


def _cell_grounder(source_id: str, mapping: Mapping[str, Any]) -> Grounder:
    primary = mapping.get("id_from") or next(
        iter(mapping.get("attributes", {}).values()), "row"
    )
    return lambda i, record: (CellSelector(source_id, i, str(primary)),)


# --- table_map: declarative, no extra deps -----------------------------------
@register_extractor("table_map")
def make_table_map_extractor(*, records_source: str, **mapping: Any):
    """Build an extractor that maps rows of the table source ``records_source``."""

    def extractor(ctx: ExtractionContext) -> Extraction:
        src = ctx.sources.get(records_source)
        records = list(src.content) if src is not None else []
        return _map_records(
            records, mapping, source_id=records_source, element_id=ctx.element_id
        )

    return extractor


# --- sql: parameterized DuckDB over a table source (extra [query]) ------------
@register_extractor("sql")
def make_sql_extractor(
    *, records_source: str, sql: str, params: Sequence[Any] = (), **mapping: Any
):
    """Build an extractor that runs parameterized DuckDB ``sql`` over the table, then maps."""

    def extractor(ctx: ExtractionContext) -> Extraction:
        src = ctx.sources.get(records_source)
        rows = list(src.content) if src is not None else []
        result = _duckdb_query(rows, sql, list(params))
        return _map_records(
            result, mapping, source_id=records_source, element_id=ctx.element_id
        )

    return extractor


def _duckdb_query(rows: list[dict], sql: str, params: list) -> list[dict]:
    """Run ``sql`` against ``rows`` registered as table ``t`` (all columns VARCHAR).

    Uses only DuckDB (no pandas/pyarrow). The query is parameterized — never
    string-interpolate untrusted values; bind them as ``params`` and reference ``?``.
    """
    import duckdb  # local import: optional [query] extra

    con = duckdb.connect()
    try:
        if rows:
            cols = list(rows[0].keys())
            quoted = ", ".join(_qident(c) for c in cols)
            con.execute(
                f'CREATE TABLE t ({", ".join(f"{_qident(c)} VARCHAR" for c in cols)})'
            )
            con.executemany(
                f"INSERT INTO t ({quoted}) VALUES ({', '.join('?' for _ in cols)})",
                [[_as_str(r.get(c)) for c in cols] for r in rows],
            )
        cur = con.execute(sql, params)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]
    finally:
        con.close()


def _qident(name: str) -> str:
    """Quote a SQL identifier safely (double any internal quote), so a column name
    from an untrusted header can't break out of the DDL."""
    return '"' + str(name).replace('"', '""') + '"'


def _as_str(value: Any) -> Any:
    return value if value is None else str(value)


# --- json_query: JMESPath select + optional equality filter (extra [query]) --
@register_extractor("json_query")
def make_json_extractor(
    *,
    records_source: str,
    select: Optional[str] = None,
    where: Optional[Mapping] = None,
    **mapping: Any,
):
    """Build an extractor that selects records from a JSON source, then maps them."""

    def extractor(ctx: ExtractionContext) -> Extraction:
        src = ctx.sources.get(records_source)
        records = _json_select(src.content if src is not None else [], select, where)
        grounder = _jsonpath_grounder(records_source, select)
        return _map_records(
            records,
            mapping,
            source_id=records_source,
            element_id=ctx.element_id,
            grounder=grounder,
        )

    return extractor


def _json_select(content: Any, select: Optional[str], where: Optional[Mapping]) -> list:
    records = content
    if select:
        import jmespath  # local import: optional [query] extra

        found = jmespath.search(select, content)
        records = (
            found if isinstance(found, list) else ([] if found is None else [found])
        )
    if not isinstance(records, list):
        records = [records]
    if where:
        records = [r for r in records if _matches(r, where)]
    return records


def _matches(record: Mapping[str, Any], where: Mapping[str, Any]) -> bool:
    for field, cond in where.items():
        value = record.get(field)
        if isinstance(cond, Mapping):
            for op, operand in cond.items():
                if op in ("$gt", "$lt"):
                    if value is None or not _ordered(value, operand, op):
                        return False
                elif op == "$in":
                    if not isinstance(operand, (list, tuple, set)):
                        raise ValueError(
                            f"$in operand must be a list/tuple/set, "
                            f"got {type(operand).__name__}: {operand!r}"
                        )
                    if value not in operand:
                        return False
                elif op == "$ne" and value == operand:
                    return False
        elif value != cond:
            return False
    return True


def _as_number(x: Any) -> Optional[float]:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def _ordered(value: Any, operand: Any, op: str) -> bool:
    """Compare for ``$gt``/``$lt``, coercing numeric-looking strings (CSV/JSON values
    are often strings) and treating an incomparable pair as non-matching, not a crash."""
    a, b = _as_number(value), _as_number(operand)
    if a is None or b is None:  # not both numeric -> compare as-is, tolerate mismatch
        a, b = value, operand
    try:
        return a > b if op == "$gt" else a < b
    except TypeError:
        return False


def _jsonpath_grounder(source_id: str, select: Optional[str]) -> Grounder:
    base = select or "$"
    return lambda i, record: (JsonPathSelector(f"{base}[{i}]", source_id),)
