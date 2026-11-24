"""creel → lacing adapter (thorwhalen/loomun#35): envelope, provenance, drill-in."""

import uuid

import pytest

lacing = pytest.importorskip("lacing")

from lacing import schema as lacing_schema  # noqa: E402
from lacing.model import UNKNOWN_GENERATED_AT, AnnotationRef, NodeRef  # noqa: E402
from lacing.time import RationalTime, TimeInterval  # noqa: E402

from creel.annotate import Annotation, Selection  # noqa: E402
from creel.evidence import (  # noqa: E402
    PERSON,
    SOFTWARE_AGENT,
    Confidence,
    Provenance,
    TextQuoteSelector,
)
from creel.export.to_lacing import (  # noqa: E402
    CREEL_BODY_SCHEMA_URI,
    lacing_id,
    node_path,
    source_selection,
    to_lacing_annotation,
)

QUOTE = TextQuoteSelector(exact="revenue grew 12%")


def _machine(**prov_kw):
    prov = dict(attributed_to="model-x", attributed_kind=SOFTWARE_AGENT)
    prov.update(prov_kw)
    return Annotation(
        "a1",
        Selection("s1", "report.pdf", QUOTE),
        "fact:revenue-growth",
        motivation="identifying",
        provenance=Provenance("report.pdf", "llm:extract", **prov),
        confidence=Confidence(method="llm", score=0.8),
    )


def test_a_source_selection_survives_as_a_drill_in_link():
    ann = to_lacing_annotation(_machine())
    sel = source_selection(ann)
    assert sel["source"] == "report.pdf"
    assert sel["selector"] == QUOTE.to_dict()
    assert ann.body == _machine().to_dict()  # the whole creel record, unchanged
    assert ann.body_schema_uri == CREEL_BODY_SCHEMA_URI
    lacing_schema.validate(ann.body, ann.body_schema_uri)  # registered and valid


def test_envelope_and_provenance_mapping():
    ann = to_lacing_annotation(_machine(generated_at="2026-11-23T10:00:00Z"))
    assert ann.id == lacing_id("a1") and isinstance(ann.id, uuid.UUID)
    assert ann.tier == "creel"
    assert ann.confidence == 0.8
    assert ann.reference == NodeRef(
        scene_path="creel/source/report.pdf",
        interval=TimeInterval(RationalTime.zero(), RationalTime.zero()),
    )
    p = ann.provenance
    assert p.was_attributed_to == "model-x"
    assert p.activity == "infer"
    assert p.was_generated_by.startswith("adapter:creel@")
    assert p.generated_at_is_known
    assert p.was_derived_from == []


def test_a_person_revision_is_created_and_derives_from_what_it_supersedes():
    note = Annotation(
        "a2",
        ("n1", "amount"),
        "corrected: 12.5%",
        motivation="editing",
        provenance=Provenance(
            "report.pdf",
            "ui:review",
            attributed_to="thor",
            attributed_kind=PERSON,
            was_revision_of="a1",
        ),
    )
    ann = to_lacing_annotation(note)
    assert ann.provenance.activity == "create"
    assert ann.provenance.was_derived_from == [lacing_id("a1")]
    assert ann.reference.scene_path == "creel/element/n1/amount"
    assert source_selection(ann) is None  # an element target, not a source region


def test_unknown_time_stays_unknown_and_a_naive_time_is_refused():
    assert to_lacing_annotation(_machine()).provenance.generated_at_time == (
        UNKNOWN_GENERATED_AT
    )
    with pytest.raises(ValueError, match="time zone"):
        to_lacing_annotation(_machine(generated_at="2026-11-23T10:00:00"))


def test_no_responsible_party_is_refused_unless_given():
    bare = Annotation("a3", "n1", "a note")
    with pytest.raises(ValueError, match="responsible party"):
        to_lacing_annotation(bare)
    ann = to_lacing_annotation(bare, attributed_to="thor")
    assert ann.provenance.was_attributed_to == "thor"
    assert ann.provenance.activity == "import"


def test_reference_and_tier_are_seams():
    target = uuid.uuid4()
    ann = to_lacing_annotation(
        _machine(), tier="facts", reference=lambda a: AnnotationRef(target_id=target)
    )
    assert ann.tier == "facts" and ann.reference.target_id == target


def test_re_export_is_idempotent_and_misuse_is_refused():
    assert to_lacing_annotation(_machine()).id == to_lacing_annotation(_machine()).id
    with pytest.raises(ValueError, match="Cannot place"):
        node_path(None)
    with pytest.raises(ValueError, match="not a creel annotation"):
        source_selection(
            to_lacing_annotation(_machine()).model_copy(
                update={"body_schema_uri": "annot://schema/other/v1"}
            )
        )


# --- review findings (each would have slipped through the tests above) -----------


def test_the_converted_time_is_the_creel_time():
    from datetime import datetime, timezone

    ann = to_lacing_annotation(_machine(generated_at="2026-11-23T10:00:00+01:00"))
    expected = datetime(2026, 11, 23, 9, tzinfo=timezone.utc).timestamp()
    assert abs(float(ann.provenance.generated_at_time.to_seconds()) - expected) < 1e-3


def test_an_unreadable_time_says_so():
    with pytest.raises(ValueError, match="ISO-8601"):
        to_lacing_annotation(_machine(generated_at="last tuesday"))


@pytest.mark.parametrize("score", [-0.3, 85, 1.5])
def test_a_score_outside_0_1_is_not_passed_as_lacing_confidence(score):
    note = Annotation(
        "a1", "n1", "x", confidence=Confidence(method="logprob", score=score)
    )
    ann = to_lacing_annotation(note, attributed_to="thor")
    assert ann.confidence is None
    assert ann.body["confidence"]["score"] == score  # the record keeps it


def test_a_deterministic_software_agent_derives_rather_than_infers():
    note = Annotation(
        "a1",
        "n1",
        "x",
        provenance=Provenance(
            "s", "pattern:re", attributed_to="creel", attributed_kind=SOFTWARE_AGENT
        ),
        confidence=Confidence(method="deterministic", score=1.0),
    )
    assert to_lacing_annotation(note).provenance.activity == "derive"


def test_a_namespace_keeps_two_corpora_apart():
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "corpus-b")
    a = to_lacing_annotation(_machine())
    b = to_lacing_annotation(_machine(was_revision_of="a0"), namespace=ns)
    assert a.id != b.id == lacing_id("a1", namespace=ns)
    assert b.provenance.was_derived_from == [lacing_id("a0", namespace=ns)]


def test_bodies_are_plain_json_and_non_json_bodies_are_refused_clearly():
    ann = to_lacing_annotation(Annotation("a1", "n1", {"x": (1, 2)}), attributed_to="t")
    assert ann.body["body"] == {"x": [1, 2]}
    with pytest.raises(ValueError, match="not JSON-ready"):
        to_lacing_annotation(
            Annotation("a1", "n1", {("n", "a"): "x"}), attributed_to="t"
        )


def test_element_paths_do_not_collide():
    assert node_path(("a", "b")) != node_path("a/b")


def test_first_registration_from_several_threads_does_not_conflict():
    from concurrent.futures import ThreadPoolExecutor

    from creel.export.to_lacing import register_creel_body_schema

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _: register_creel_body_schema(), range(16)))
