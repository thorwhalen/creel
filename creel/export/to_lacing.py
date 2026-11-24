"""creel → lacing: carry a creel annotation into lacing's envelope, source link intact.

A :class:`creel.annotate.Annotation` knows where a fact came from: its ``target`` can be
a :class:`~creel.annotate.Selection` (a source region plus a grounding selector) and its
``provenance`` says whether a model or a person made it. lacing's
:class:`lacing.Annotation` is what decks, videos and reports render, but lacing has no
source selector of its own (its ``Reference`` is media, node or annotation). This
adapter is the bridge thorwhalen/loomun#35 and its ADR-0012 call for: one function
that maps the envelope and the provenance, and keeps the whole creel record in the
body, so a rendered fact can always drill back to its source.

>>> from creel.annotate import Annotation, Selection
>>> from creel.evidence import Provenance, TextQuoteSelector, SOFTWARE_AGENT
>>> sel = Selection("s1", "report.pdf", TextQuoteSelector(exact="revenue grew 12%"))
>>> note = Annotation(
...     "a1", sel, "fact:revenue-growth", motivation="identifying",
...     provenance=Provenance("report.pdf", "llm:extract", attributed_to="model-x",
...                           attributed_kind=SOFTWARE_AGENT),
... )
>>> ann = to_lacing_annotation(note)  # doctest: +SKIP
>>> source_selection(ann)["source"]  # doctest: +SKIP
'report.pdf'

Needs lacing: ``pip install creel[lacing]``. Nothing here is imported until called.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from functools import cache
from typing import Any, Callable, Optional, Union

from creel.annotate import Annotation, Selection
from creel.evidence import DETERMINISTIC, PERSON, SOFTWARE_AGENT

#: The lacing ``body_schema_uri`` under which a creel annotation travels. The body is
#: :meth:`creel.annotate.Annotation.to_dict`, unchanged.
CREEL_BODY_SCHEMA_URI = "annot://schema/creel-annotation/v1"

#: Default lacing tier for exported creel annotations.
DEFAULT_TIER = "creel"

#: The ``uuid5`` namespace that turns a creel annotation id into a lacing UUID.
#: Fixed, so exporting the same annotation twice gives the same lacing id.
CREEL_ID_NAMESPACE = uuid.UUID("9d6c3f0e-5b6a-5c1e-9a4e-6372656c0001")

#: ``Provenance.activity`` by creel ``attributed_kind``: a model's output is
#: inferred, a person's coding is authored. Unknown kinds read as imported, and a
#: software agent whose confidence method is deterministic derived, not inferred.
ACTIVITY_BY_KIND = {SOFTWARE_AGENT: "infer", PERSON: "create"}

#: The path prefix of the ``NodeRef`` built for each kind of creel target.
SOURCE_PATH_PREFIX = "creel/source"
ELEMENT_PATH_PREFIX = "creel/element"

_INSTALL_HINT = "creel's lacing adapter needs lacing: pip install creel[lacing]"


def _lacing():
    try:
        import lacing
        from lacing import model, schema, time
    except ImportError as error:  # pragma: no cover - exercised only without lacing
        raise ImportError(_INSTALL_HINT) from error
    return lacing, model, schema, time


def lacing_id(creel_id: str, *, namespace: uuid.UUID = CREEL_ID_NAMESPACE) -> uuid.UUID:
    """The lacing UUID for a creel annotation id: stable across exports.

    >>> lacing_id("a1") == lacing_id("a1") != lacing_id("a2")
    True
    """
    return uuid.uuid5(namespace, creel_id)


def _path_part(part: Any) -> str:
    return str(part).replace("%", "%25").replace("/", "%2F")


def node_path(target: Any) -> str:
    """The ``NodeRef.scene_path`` that stands for a creel ``target``.

    A source selection points at its source, a graph element at the element, and an
    ``(element_id, attribute)`` pair at that attribute of the element. The precise
    region (the selector) is in the body: see :func:`source_selection`.

    A ``/`` or ``%`` inside an id is percent-escaped, so ``("a", "b")`` and
    ``"a/b"`` never share a path.

    >>> node_path("n1"), node_path(("n1", "name")), node_path("a/b")
    ('creel/element/n1', 'creel/element/n1/name', 'creel/element/a%2Fb')
    """
    if isinstance(target, Selection):
        return f"{SOURCE_PATH_PREFIX}/{_path_part(target.source_id)}"
    if isinstance(target, tuple) and target:
        return "/".join([ELEMENT_PATH_PREFIX, *map(_path_part, target)])
    if isinstance(target, str) and target:
        return f"{ELEMENT_PATH_PREFIX}/{_path_part(target)}"
    raise ValueError(
        f"Cannot place creel target {target!r} in lacing: expected a Selection, an "
        "element id or an (element_id, attribute) pair. Pass reference= to place it."
    )


def _default_reference(annotation: Annotation):
    _, model, _, time = _lacing()
    at = time.RationalTime.zero()  # a document region has no time: a point at 0
    return model.NodeRef(
        scene_path=node_path(annotation.target), interval=time.TimeInterval(at, at)
    )


def _generated_at(iso: Optional[str]):
    _, model, _, time = _lacing()
    if not iso:
        return model.UNKNOWN_GENERATED_AT
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"creel generated_at {iso!r} is not an ISO-8601 time this Python can read "
            "(use YYYY-MM-DDTHH:MM:SS[.ffffff]+HH:MM)"
        ) from error
    if moment.tzinfo is None:
        raise ValueError(
            f"creel generated_at {iso!r} has no time zone; lacing needs an absolute time"
        )
    seconds = moment.timestamp()
    return time.RationalTime.from_seconds_lossy(seconds)


@cache
def _creel_body_model():
    from pydantic import BaseModel, ConfigDict

    class CreelAnnotationBody(BaseModel):
        """A creel annotation as :meth:`creel.annotate.Annotation.to_dict` writes it."""

        model_config = ConfigDict(extra="forbid")

        id: str
        target: Any
        body: Any
        motivation: str
        provenance: Optional[dict] = None
        confidence: Optional[dict] = None

    return CreelAnnotationBody


def register_creel_body_schema() -> None:
    """Register :data:`CREEL_BODY_SCHEMA_URI` with lacing (idempotent).

    Called by :func:`to_lacing_annotation`, so lacing can validate the body.
    """
    _, _, schema, _ = _lacing()
    # One model class per process (cached), so registering it again, from any
    # thread, is the no-op lacing makes of re-registering an identical model.
    schema.register_body_schema(CREEL_BODY_SCHEMA_URI, _creel_body_model())


def _json_body(annotation: Annotation) -> dict:
    """The creel record as plain JSON, as lacing stores it (tuples become lists)."""
    try:
        return json.loads(json.dumps(annotation.to_dict()))
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"creel annotation {annotation.id!r} is not JSON-ready ({error}); lacing "
            "stores bodies as JSON, so give it string keys and JSON values"
        ) from error


def _lacing_confidence(confidence) -> Optional[float]:
    """creel's score when it is a probability-like value in [0, 1], else ``None``.

    lacing's ``confidence`` is one float in [0, 1]; creel scores are method-tagged and
    may be log-probabilities or percentages. The full record stays in the body.
    """
    if confidence is None:
        return None
    score = confidence.score
    if isinstance(score, (int, float)) and 0.0 <= score <= 1.0:
        return float(score)
    return None


def _activity(annotation: Annotation) -> str:
    prov, conf = annotation.provenance, annotation.confidence
    kind = prov.attributed_kind if prov else None
    if kind == SOFTWARE_AGENT and conf is not None and conf.method == DETERMINISTIC:
        return "derive"
    return ACTIVITY_BY_KIND.get(kind, "import")


def to_lacing_annotation(
    annotation: Annotation,
    *,
    tier: str = DEFAULT_TIER,
    reference: Union[Any, Callable[[Annotation], Any], None] = None,
    attributed_to: Optional[str] = None,
    generated_by: Optional[str] = None,
    namespace: uuid.UUID = CREEL_ID_NAMESPACE,
):
    """A :class:`lacing.Annotation` carrying *annotation*, source link intact.

    Args:
        annotation: The creel annotation.
        tier: The lacing tier it goes in.
        reference: What it annotates in lacing: a lacing ``Reference``, or a function
            of the creel annotation that returns one. Default: a ``NodeRef`` at
            :func:`node_path`, a point at time 0 (a document region has no time).
        attributed_to: Who is responsible, when the creel provenance does not say.
            Required in that case: lacing records a responsible party on everything.
        generated_by: lacing's ``was_generated_by``. Default:
            ``adapter:creel@<creel version>``, as lacing's own loaders stamp what they
            import; the creel extractor id stays in the body's provenance.
        namespace: The ``uuid5`` namespace of the lacing ids. creel ids are chosen
            per corpus, and lacing ids are unique across a whole store, so give each
            corpus its own namespace (``uuid.uuid5(CREEL_ID_NAMESPACE, corpus)``)
            when several share one lacing store.

    The lacing id is :func:`lacing_id` of the creel id in *namespace*, so
    re-exporting is idempotent. ``was_derived_from`` holds the lacing id of the record a creel
    revision supersedes (``was_revision_of``). The body is the full creel record.
    """
    _, model, _, _ = _lacing()
    register_creel_body_schema()
    prov = annotation.provenance
    responsible = (prov.attributed_to if prov else None) or attributed_to
    if not responsible:
        raise ValueError(
            f"creel annotation {annotation.id!r} names no responsible party: give it "
            "provenance.attributed_to, or pass attributed_to="
        )
    if generated_by is None:
        from creel import __version__

        generated_by = f"adapter:creel@{__version__}"
    revision_of = prov.was_revision_of if prov else None
    if reference is None:
        reference = _default_reference(annotation)
    elif callable(reference):
        reference = reference(annotation)
    provenance = model.Provenance(
        was_generated_by=generated_by,
        was_attributed_to=responsible,
        was_derived_from=(
            [lacing_id(revision_of, namespace=namespace)] if revision_of else []
        ),
        generated_at_time=_generated_at(prov.generated_at if prov else None),
        activity=_activity(annotation),
    )
    return model.Annotation(
        id=lacing_id(annotation.id, namespace=namespace),
        tier=tier,
        reference=reference,
        body=_json_body(annotation),
        body_schema_uri=CREEL_BODY_SCHEMA_URI,
        provenance=provenance,
        confidence=_lacing_confidence(annotation.confidence),
    )


def source_selection(lacing_annotation) -> Optional[dict]:
    """The source region a lacing annotation made by this adapter points at, if any.

    The drill-in: ``{"id", "source", "selector"}`` as
    :meth:`creel.annotate.Selection.to_dict` wrote it, or ``None`` when the creel
    target was a graph element rather than a source region.
    """
    if lacing_annotation.body_schema_uri != CREEL_BODY_SCHEMA_URI:
        raise ValueError(
            f"{lacing_annotation.body_schema_uri!r} is not a creel annotation body"
        )
    target = lacing_annotation.body.get("target")
    if isinstance(target, dict) and "source" in target and "selector" in target:
        return target
    return None
