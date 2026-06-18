"""Quickstart: extract a typed graph from prose + a table, then project & export it.

Run: ``python examples/quickstart.py`` (no API key needed — uses deterministic
pattern/query extractors). See the README for the LLM variant via ``aix``.
"""

from creel import (
    AttrSchema,
    EdgeType,
    EnumDef,
    GraphSpec,
    NodeType,
    Source,
    SourceBundle,
    extract,
    to_canonical_json,
    to_mermaid,
    to_turtle,
    validate_graph,
)

# 1) A small grammar: donors fund projects (amount on the edge); projects have outputs.
spec = GraphSpec(
    enums=(EnumDef("Currency", ("USD", "EUR")),),
    node_types=(
        NodeType("donor", attributes=(AttrSchema("name", required=True),)),
        NodeType("project", attributes=(AttrSchema("title", required=True),)),
        NodeType("output", attributes=(AttrSchema("statement", required=True),)),
    ),
    edge_types=(
        EdgeType("funds", subject_type="donor", object_type="project",
                 attributes=(AttrSchema("amount", range="integer", required=True, minimum=0),
                             AttrSchema("currency", range="Currency", required=True))),
        EdgeType("delivers", subject_type="project", object_type="output"),
    ),
)

# 2) Heterogeneous sources: prose (regex) + a table (declarative query).
prose = Source("agreement", "Donor: Gov X\nProject: Water\nGov X funds Water with USD 1000000")
table = Source("outputs", [{"project": "Water", "code": "OP-1", "statement": "Water delivered"}],
               kind="table")

bindings = {
    "donor": ("regex_node", {"pattern": r"Donor:\s*(?P<name>.+)", "id_attribute": "name"}),
    "project": ("regex_node", {"pattern": r"Project:\s*(?P<title>.+)", "id_attribute": "title"}),
    "funds": ("regex_edge", {
        "pattern": r"(?P<donor>[\w ]+?) funds (?P<project>[\w ]+?) with (?P<currency>[A-Z]{3}) (?P<amount>\d+)",
        "source_id_template": "donor:{donor}", "target_id_template": "project:{project}",
        "casts": {"amount": "int"}, "exclude_groups": ("donor", "project")}),
    "output": ("table_map", {"records_source": "outputs", "type": "output",
                             "id_template": "output:{code}", "attributes": {"statement": "statement"}}),
    "delivers": ("table_map", {"records_source": "outputs", "kind": "edge", "type": "delivers",
                               "source_template": "project:{project}", "target_template": "output:{code}"}),
}

graph = extract(SourceBundle([prose, table]), spec, bindings, on_missing_binding="skip")

assert validate_graph(graph, spec) == []
print("== canonical JSON ==")
print(to_canonical_json(graph))
print("\n== Mermaid ==")
# label_attr picks an attribute for node labels; nodes lacking it fall back to their id
print(to_mermaid(graph, label_attr="name"))
print("\n== RDF-star Turtle (amount annotates the funds edge) ==")
print(to_turtle(graph))
print("\n== evidence for the funds edge (traced to the source span) ==")
edge = next(iter(graph.edges_of_type("funds")))
print(graph.evidence[edge.id].to_dict())
