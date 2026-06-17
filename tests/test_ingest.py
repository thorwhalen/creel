"""Tests for the ingestion layer: route-by-format + the stdlib loaders."""

import json

import pytest

from creel.ingest import ingest, ingest_paths, loader_for, supported_extensions
from creel.sources import JSON, TABLE, TEXT


def test_text_and_markdown_load_as_text(tmp_path):
    md = tmp_path / "note.md"
    md.write_text("# Title\n\nbody")
    src = ingest(md)
    assert src.kind == TEXT
    assert src.id == "note"  # default source_id = file stem
    assert src.content.startswith("# Title")
    assert src.metadata["format"] == "markdown"


def test_csv_loads_as_table_rows(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a,b\n1,x\n2,y\n")
    src = ingest(csv_path)
    assert src.kind == TABLE
    assert src.content == [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]


def test_json_loads_as_parsed_object(tmp_path):
    j = tmp_path / "doc.json"
    j.write_text(json.dumps({"k": [1, 2, 3]}))
    src = ingest(j)
    assert src.kind == JSON
    assert src.content == {"k": [1, 2, 3]}


def test_explicit_source_id_and_routing(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hello")
    src = ingest(p, source_id="custom")
    assert src.id == "custom" and src.kind == TEXT


def test_unknown_extension_raises(tmp_path):
    p = tmp_path / "x.parquet"
    p.write_text("")
    with pytest.raises(ValueError, match="no loader"):
        ingest(p)


def test_ingest_paths_returns_bundle(tmp_path):
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "b.csv").write_text("h\n1\n")
    bundle = ingest_paths([tmp_path / "a.txt", tmp_path / "b.csv"])
    assert {s.id for s in bundle} == {"a", "b"}
    assert bundle.get("b").kind == TABLE


def test_supported_extensions_includes_stdlib_set():
    exts = set(supported_extensions())
    assert {".txt", ".md", ".csv", ".tsv", ".json"} <= exts
    # heavy formats are registered too (backends are lazy)
    assert {".pdf", ".docx", ".xlsx", ".html"} <= exts


def test_loader_for_returns_callable(tmp_path):
    from pathlib import Path

    assert callable(loader_for(Path("x.csv")))
