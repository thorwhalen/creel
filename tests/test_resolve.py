"""Tests for entity resolution (#14): normalize/registry/LLM/cascade + merge pass."""

from creel import AttrSchema, GraphSpec, NodeType, extract
from creel.graph.model import Graph
from creel.resolve import (
    CascadeResolver,
    LLMResolver,
    NormalizeResolver,
    RegistryResolver,
    normalize_entity,
    resolve_graph,
)


def test_normalize_entity_strips_case_punctuation_legal_honorific():
    assert normalize_entity("Foundation Alpha") == "foundation alpha"
    assert normalize_entity("FOUNDATION,  Alpha.") == "foundation alpha"  # case/punct/space
    assert normalize_entity("Acme Corp") == "acme"  # legal form stripped
    assert normalize_entity("Dr. Smith") == "smith"  # honorific stripped


def _two_donor_graph(name_a, name_b):
    g = Graph()
    g.add_node("donor:a", types=("donor",), attributes={"name": name_a})
    g.add_node("donor:b", types=("donor",), attributes={"name": name_b})
    g.add_node("p:1", types=("project",), attributes={"title": "Water"})
    g.add_edge("f1", source="donor:a", target="p:1", type="funds", attributes={"amount": 100})
    g.add_edge("f2", source="donor:b", target="p:1", type="funds", attributes={"amount": 200})
    return g


def test_normalize_resolver_merges_variants_and_remaps_edges():
    g = _two_donor_graph("Foundation Alpha", "FOUNDATION ALPHA,")
    merged = resolve_graph(g, NormalizeResolver(key="name"))
    donors = list(merged.nodes_of_type("donor"))
    assert len(donors) == 1
    canon = donors[0].id
    assert canon == "donor:foundation-alpha"
    # both fundings remapped onto the one canonical donor (parallel edges preserved)
    funds = list(merged.edges_of_type("funds"))
    assert len(funds) == 2 and all(e.source == canon for e in funds)
    assert merged.report["merges"][0]["merged"] == ["donor:a", "donor:b"]


def test_distinct_entities_are_not_merged():
    g = _two_donor_graph("Foundation Alpha", "Agency Beta")
    merged = resolve_graph(g, NormalizeResolver(key="name"))
    assert len(list(merged.nodes_of_type("donor"))) == 2
    assert merged.report["merges"] == []


def test_alias_table_merges_known_synonyms():
    g = _two_donor_graph("Foundation Alpha", "Alpha MFA")
    r = NormalizeResolver(key="name", aliases={"alpha mfa": "foundation alpha"})
    merged = resolve_graph(g, r)
    assert len(list(merged.nodes_of_type("donor"))) == 1


def test_registry_resolver_uses_canonical_ids():
    g = _two_donor_graph("Foundation Alpha", "Alpha Fund (MFA)")
    registry = {"foundation alpha": "org:ALPHA-301", "alpha fund mfa": "org:ALPHA-301"}
    merged = resolve_graph(g, RegistryResolver(registry, key="name"))
    donors = list(merged.nodes_of_type("donor"))
    assert len(donors) == 1 and donors[0].id == "org:ALPHA-301"


def test_llm_resolver_with_fake_judge():
    g = _two_donor_graph("Foundation Alpha", "the Alpha foundation")
    # cheap normalize can't match these; the (fake) LLM judge says they're the same
    judge = lambda a, b: "alpha" in a.lower() and "alpha" in b.lower()
    merged = resolve_graph(g, LLMResolver(judge=judge, key="name"))
    assert len(list(merged.nodes_of_type("donor"))) == 1


def test_cascade_tries_cheap_then_llm():
    g = _two_donor_graph("Foundation Alpha", "the Alpha foundation")
    judge = lambda a, b: "alpha" in a.lower() and "alpha" in b.lower()
    cascade = CascadeResolver([NormalizeResolver(key="name"), LLMResolver(judge=judge, key="name")])
    merged = resolve_graph(g, cascade)
    assert len(list(merged.nodes_of_type("donor"))) == 1


def test_facade_resolve_pass_merges_messy_extractions():
    spec = GraphSpec(node_types=(NodeType("donor", attributes=(AttrSchema("name", required=True),)),))
    g = extract(
        "Donor: Foundation Alpha\nDonor: Foundation Alpha Inc",
        spec,
        {"donor": ("regex_node", {"pattern": r"Donor:\s*(?P<name>.+)", "id_attribute": "name"})},
        on_missing_binding="skip",
        resolve=NormalizeResolver(key="name"),
    )
    assert len(list(g.nodes_of_type("donor"))) == 1  # 'Inc' suffix variant merged
    assert g.report["merges"]
