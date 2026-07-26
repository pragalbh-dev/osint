"""RK-COREF (S3) test toolkit — abstract fixtures + config **discovery** (never a hand-copied knob).

Why discovery rather than a copy: S2 lost a round because a hand-written copy of ``supersede_floor``
omitted a knob the implementation later added, so the guard short-circuited and no fixture could turn the
feature on (see ``tests/_rk_layer._shipped_supersede_floor``). Everything here **reads the shipped
config** and, where the spec does not fix a name, *searches* for it and reports what it searched for — so
a test can neither pass nor fail on a mis-guessed key.

Every fixture is abstract (corpus-independent, like G1/G2): §7 RK-COREF's gate note — "All fixtures must
be abstract — the corpus holds essentially one numbered formation, one stated basing and zero serials, so
it cannot exercise them."

**Correction to the quoted count:** the corpus holds **five** ``based-at`` claims over **three** subjects,
not one. The rest of the note (one numbered formation, zero serials, and therefore abstract fixtures) is
accurate, and the reason for abstract fixtures is unchanged — the one multi-basing subject carries a dated
succession rather than the conflict G18 would need. See ``artifacts/plan/PROGRESS.md``.
"""

from __future__ import annotations

from typing import Any

# ── the coref lane, read from production rather than re-typed (re-exported for the test files) ────
from chanakya.ingest.coref import (
    CLUSTER_ATTR as CLUSTER_ATTR,
)
from chanakya.ingest.coref import (
    COREF_PREDICATE as COREF_PREDICATE,
)
from chanakya.ingest.coref import (
    EVIDENCE_ATTR as EVIDENCE_ATTR,
)
from chanakya.ingest.coref import (
    EXPLICIT_EQUIVALENCE as EXPLICIT_EQUIVALENCE,
)
from chanakya.ingest.coref import (
    NAME_VARIANT as NAME_VARIANT,
)
from chanakya.ingest.coref import (
    QUOTE_ATTR as QUOTE_ATTR,
)
from chanakya.ingest.coref import (
    UNAMBIGUOUS_ANAPHOR as UNAMBIGUOUS_ANAPHOR,
)
from chanakya.ingest.coref import (
    UNKNOWN_TYPE as UNKNOWN_TYPE,
)
from chanakya.resolve import resolve
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DocRef,
    EntityDescriptor,
    ExactDate,
    ResolutionConfig,
    ResolvedRef,
    SourceRegistryEntry,
    SourcesConfig,
    Triple,
    pair_key,
)
from tests import _rk_layer as rk
from tests.credibility.builders import cred_config

#: The four declared values of C6's re-specified ``time_role`` (REVIEW-VERDICT "C6 re-specified" table).
TIME_ROLES = ("durable", "perishable", "constitutive", "identifying")

#: The boolean key C6 replaces. "No backward compatibility … a bare ``perishable:`` key becomes a **loud
#: validation error**, exactly as S1 did for ``attrs``."
LEGACY_PERISHABLE_KEY = "perishable"

#: The contrastive channel (b) introduces — "its own ``coref-distinct-from`` lane … **never** the stated
#: ``distinct-from`` rail, which is hard, transitive and ungraded".
CONTRAST_PREDICATE = "coref-distinct-from"


# ── graded sources (the grade floor axis) ────────────────────────────────────────────────────────

#: STANAG letters are ordinal A (most reliable) → F. ``hi`` clears any sane floor, ``lo`` clears none.
GRADES = {"hi": "A", "mid": "C", "lo": "E"}
_CLASS_OF = {"hi": "strong", "mid": "text", "lo": "weak"}


def graded_source(sid: str, grade: str, stype: str = "text") -> SourceRegistryEntry:
    return SourceRegistryEntry(source_id=sid, source_type=stype, reliability_grade=grade)


def graded_sources() -> SourcesConfig:
    return SourcesConfig(
        sources=[graded_source(sid, grade, _CLASS_OF[sid]) for sid, grade in GRADES.items()]
    )


SHIPPED = "<shipped>"
#: The stage block's key in ``config/resolution.yaml`` — where S3's own knobs live.
_EARNED_BLOCK = "earned_identity"

def bundle(
    *,
    resolution: ResolutionConfig | str | None = SHIPPED,
    sources: SourcesConfig | None = None,
    **credibility: Any,
) -> ConfigBundle:
    """A bundle over the **shipped ontology + shipped resolution config**, with graded sources.

    Passing the shipped ``resolution`` wholesale is the point: nearly every knob this stage adds lives in
    ``config/resolution.yaml`` (§7 RK-COREF owned paths), so a fixture that re-typed the block could not
    see a knob S3 declares. Pass an explicit :class:`ResolutionConfig` only where a test needs to *vary*
    one dial.

    Raises :class:`~tests._rk_layer.DeadStageKwarg` for a retired staging-flag keyword — one registry, in
    ``_rk_layer.DEAD_STAGE_KWARGS``, because both fixture builders have the same ``extra="allow"`` hole and a
    second copy of the refusal list is how one of them ends up not refusing. Everything else in
    ``**credibility`` is a credibility knob, as before.
    """
    rk.reject_dead_stage_kwargs("bundle", credibility)
    shipped = rk.shipped_bundle()
    proposer = getattr(shipped.credibility, "basing_proposer", None)
    cred = cred_config(
        half_lives_days={"based-at": 365, "observed-at": 180, "inducted-into": 900},
        **({"basing_proposer": dict(proposer)} if isinstance(proposer, dict) else {}),
        **credibility,
    )
    out = ConfigBundle(
        ontology=shipped.ontology,
        credibility=cred,
        sources=sources or graded_sources(),
        places=shipped.places,
        resolution=shipped.resolution if resolution == SHIPPED else (resolution or ResolutionConfig()),
    )
    return out


def with_resolution(base: ConfigBundle, **overrides: Any) -> ConfigBundle:
    """The same bundle with named resolution knobs overridden — extras included (``extra="allow"``)."""
    data = base.resolution.model_dump()
    data.update(overrides)
    return base.model_copy(update={"resolution": ResolutionConfig.model_validate(data)})


# ── claim builders (document-aware: (b)/C9 need a real doc axis) ─────────────────────────────────

def ent(
    eid: str,
    etype: str,
    name: str,
    *,
    doc: str = "d1",
    sid: str = "hi",
    attrs: dict[str, Any] | None = None,
    cid: str | None = None,
    iso: str | None = None,
) -> ClaimRecord:
    """A declared entity pinned to a stable node id, carrying an explicit **document**."""
    return ClaimRecord(
        claim_id=cid or f"c-{doc}-{eid}",
        source_id=sid,
        doc_ref=DocRef(file=f"{doc}.txt", line=1),
        kind="observation",
        polarity="positive",
        asserts="entity",
        payload=EntityDescriptor(form="entity", entity_type=etype, name=name, attrs=attrs or {}),
        resolved_ref=ResolvedRef(entity_id=eid),
        event_time=ExactDate(iso_date=iso) if iso else None,
        report_time=ExactDate(iso_date=iso) if iso else None,
    )


def rel(
    cid: str,
    subject: str,
    predicate: str,
    obj: str,
    *,
    doc: str = "d1",
    sid: str = "hi",
    iso: str | None = "2025-01-01",
    attributes: dict[str, Any] | None = None,
    kind: str = "observation",
    premises: list[str] | None = None,
) -> ClaimRecord:
    """A relationship claim with ``resolved_ref=None`` so the PRODUCTION key builder mints the instance."""
    return ClaimRecord(
        claim_id=cid,
        source_id=sid,
        doc_ref=DocRef(file=f"{doc}.txt", line=1),
        kind=kind,
        polarity="positive",
        asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=iso) if iso else None,
        report_time=ExactDate(iso_date=iso) if iso else None,
        attributes=attributes,
        premises=premises or [],
    )


def coref(
    anchor: str,
    member: str,
    *,
    evidence: str = EXPLICIT_EQUIVALENCE,
    quote: str = "the Alpha Air Defence Regiment (AADR)",
    doc: str = "d1",
    sid: str = "hi",
    cluster: str = "c1",
    cid: str | None = None,
    extra: dict[str, Any] | None = None,
) -> ClaimRecord:
    """One ``coref-same-as`` link (anchor→member) exactly as ``ingest/coref.coref_claims`` emits it.

    A cluster is a **star** from the anchor, so an n-member cluster is n-1 of these sharing one
    ``_coref_cluster`` — which is what makes C5's per-*link* quantifier expressible in a fixture.
    """
    return rel(
        cid or f"coref-{doc}-{anchor}-{member}",
        anchor,
        COREF_PREDICATE,
        member,
        doc=doc,
        sid=sid,
        attributes={
            CLUSTER_ATTR: cluster,
            EVIDENCE_ATTR: evidence,
            QUOTE_ATTR: quote,
            **(extra or {}),
        },
    )


def coref_spans(
    anchor: str,
    member: str,
    *,
    quotes: list[str],
    docs: list[str] | None = None,
    evidence: str = EXPLICIT_EQUIVALENCE,
    sid: str = "hi",
    cluster: str = "c1",
    cid: str | None = None,
) -> ClaimRecord:
    """One coref link whose licensing evidence is a **set** of verbatim spans (ruling M2).

    "licensing evidence is a set of verbatim spans from the same document, which together must contain both
    surface forms and the marker."

    The *carrier* shape is not fixed by the ruling, so the fixture supplies the span list under the shipped
    quote key **and** under a plural sibling, plus one ``DocRef`` per span — any reasonable reading finds it.
    ``docs`` defaults to one document for every span; passing two names is the cross-document negative.
    """
    files = docs or ["d1"] * len(quotes)
    return ClaimRecord(
        claim_id=cid or f"coref-spans-{anchor}-{member}",
        source_id=sid,
        doc_ref=[DocRef(file=f"{f}.txt", line=i + 1) for i, f in enumerate(files)],
        kind="observation",
        polarity="positive",
        asserts="relationship",
        payload=Triple(subject=anchor, predicate=COREF_PREDICATE, object=member),
        attributes={
            CLUSTER_ATTR: cluster,
            EVIDENCE_ATTR: evidence,
            QUOTE_ATTR: list(quotes),
            f"{QUOTE_ATTR}s": list(quotes),
        },
    )


def descriptor_min_len() -> int:
    """The shipped mark-vs-word threshold — "the length of the first token the longer name adds".

    Read from config, never re-typed: ruling M1 says "Reuse the shipped knob; do **not** introduce a second
    threshold for the same idea (G6)."
    """
    value = resolution_keys().get("containment_min_descriptor_len")
    assert isinstance(value, int) and value > 0, (
        f"config/resolution.yaml declares containment_min_descriptor_len={value!r}; M1's fourth conjunct "
        "has no threshold to reuse"
    )
    return value


def contrast(a: str, b: str, *, doc: str = "d1", sid: str = "hi", quote: str = "", cid: str | None = None):
    """A same-document stated **contrast** on coref's own lane (decision (b))."""
    return rel(
        cid or f"contrast-{doc}-{a}-{b}",
        a,
        CONTRAST_PREDICATE,
        b,
        doc=doc,
        sid=sid,
        attributes={QUOTE_ATTR: quote} if quote else None,
    )


# ── reading a partition ─────────────────────────────────────────────────────────────────────────

def part_of(claims: list[ClaimRecord], cfg: ConfigBundle):
    return resolve(claims, cfg)


def endpoint_id(etype: str, name: str) -> str:
    """The id production mints for a bare relation endpoint the document never declared.

    ``resolve.entities.build`` keys an entity as ``ent:{type}:{name}`` when no ``resolved_ref`` pins it, and
    ``_link_endpoints`` types an undeclared endpoint from the edge's declared domain/range. The elliptical
    reference ("the export agency") is exactly this shape on the real corpus, so an anaphor fixture has to
    use it rather than a declared entity.
    """
    return f"ent:{etype}:{name}"


def shared_neighbours(
    a: str, b: str, *, design: str = "d", operator: str = "op", doc_a: str = "d1", doc_b: str = "d2",
    sid_b: str = "mid",
) -> list[ClaimRecord]:
    """Two shared graph neighbours for ``a``/``b`` — the co-location evidence class, and nothing else.

    A design (``inducted-into``) and an operator (``operated-by``) shared by two instances is precisely
    D-13.14's "shared design + site + operator" minus the site. Two shared neighbours is also what
    ``relational_support_k`` requires before the relational term counts in full, so the pair is a genuine
    would-be merge rather than an incidental low score.
    """
    return [
        ent(design, "variant", "HQ-X", doc=doc_a),
        ent(operator, "operator", "Air Force", doc=doc_a),
        rel(f"r-ind-{a}", design, "inducted-into", a, doc=doc_a, iso="2020-01-01"),
        rel(f"r-ind-{b}", design, "inducted-into", b, doc=doc_b, iso="2020-02-01", sid=sid_b),
        rel(f"r-op-{a}", a, "operated-by", operator, doc=doc_a),
        rel(f"r-op-{b}", b, "operated-by", operator, doc=doc_b, sid=sid_b),
    ]


def site(eid: str, name: str, *, site_class: str | None = "garrison", lat: float = 33.6,
         lon: float = 73.1, doc: str = "d1", sid: str = "hi") -> ClaimRecord:
    attrs = rk.coords(lat, lon, eid) | ({"site_type": site_class} if site_class else {})
    return ent(eid, "basing_site", name, attrs=attrs, doc=doc, sid=sid)


def cluster_of(part: Any, eid: str) -> set[str]:
    """Every id fused with ``eid`` — same_as stars plus the canonical map (the suite's own idiom)."""
    members = {eid}
    grew = True
    while grew:
        grew = False
        for a, b in list(part.same_as) + list(part.entity_canonical.items()):
            if (a in members or b in members) and not {a, b} <= members:
                members |= {a, b}
                grew = True
    return members


def fused(part: Any, a: str, b: str) -> bool:
    """Did the resolver **fuse** the pair (the only verdict that collapses two nodes into one)?

    Read through the cluster, not the raw pair: ``finalise`` re-stars merges onto a cluster canonical, so
    the literal ``(a, b)`` tuple may not survive even when the two are one node (defect register D8: the
    verdict names are "a derived read of set membership … where **only ``same_as`` fuses**").
    """
    return b in cluster_of(part, a)


def status(part: Any, a: str, b: str) -> str | None:
    return part.identity_status(a, b)


def walled(part: Any, a: str, b: str) -> bool:
    """Is the pair in the **transitive** wall channel — the one ``finalise``/``distinct_from`` can see?

    §5a G18: membership in ``veto`` "is hard **and transitive** and re-applied in ``finalise``", whereas
    consultation inside ``vetoed()`` only "is hard, **pairwise and invisible** … The gate must name the
    channel". A pair surfaced in ``Partition.distinct_from`` is in the visible channel.
    """
    return any({x, y} == {a, b} for x, y in part.distinct_from)


def reason(part: Any, a: str, b: str) -> str:
    return part.candidate_reasons.get(pair_key(a, b), "")


def signals(part: Any, a: str, b: str) -> dict[str, float]:
    return dict(part.merge_breakdown.get(pair_key(a, b), {}))


def visible_rationale(part: Any, a: str, b: str) -> str:
    """Everything analyst-facing the partition carries about this pair (reason ∪ wall membership)."""
    bits = [reason(part, a, b)]
    if walled(part, a, b):
        bits.append(f"distinct_from:{a}|{b}")
    return " ".join(b for b in bits if b)


# ── discovery: names the spec does not fix ──────────────────────────────────────────────────────

def resolution_keys(cfg: ConfigBundle | None = None) -> dict[str, Any]:
    """Every key the shipped resolution block declares — declared fields **and** ``extra="allow"`` ones."""
    return dict((cfg or rk.shipped_bundle()).resolution.model_dump())


def keys_matching(*tokens: str, cfg: ConfigBundle | None = None) -> list[str]:
    """Shipped resolution keys whose name contains **all** ``tokens`` (case-insensitive)."""
    return sorted(k for k in resolution_keys(cfg) if all(t in k.lower() for t in tokens))


def accessors_matching(*tokens: str) -> list[str]:
    """``ResolveConfig`` public members whose name contains all ``tokens`` — the consumer side."""
    return sorted(
        n for n in dir(ResolveConfig)
        if not n.startswith("_") and all(t in n.lower() for t in tokens)
    )


def attribute_role_entries(cfg: ConfigBundle | None = None) -> list[tuple[str, str, dict[str, Any]]]:
    """``(entity_type, attribute, declaration)`` for every shipped ``attribute_roles`` entry."""
    roles = resolution_keys(cfg).get("attribute_roles") or {}
    out: list[tuple[str, str, dict[str, Any]]] = []
    for etype, attrs in roles.items():
        for attr, entry in (attrs or {}).items():
            out.append((etype, attr, dict(entry) if isinstance(entry, dict) else {"role": entry}))
    return sorted(out)


def time_role_of(entry: dict[str, Any]) -> Any:
    """The declared time-role of one ``attribute_roles`` entry, whatever key S3 spelled it with.

    Searched for, not assumed: any key containing ``time_role``/``time-role``/``temporal_role``, else any
    key whose *value* is one of C6's four declared values.
    """
    for key, value in entry.items():
        if any(t in key.lower() for t in ("time_role", "time-role", "temporal_role", "timerole")):
            return value
    for key, value in entry.items():
        if key != "role" and isinstance(value, str) and value in TIME_ROLES:
            return value
    return None


def coref_authoritative(cfg: ConfigBundle | None = None) -> list[str]:
    """Which coref categories the shipped config authorises.

    Read through the typed accessor rather than off the raw top-level key, because the opt-in sits in the
    stage block (``earned_identity.authoritative_categories``) while the pre-existing top-level key stays
    ``[]``; the accessor is the union, which is what the resolver reads.
    """
    return sorted(ResolveConfig.from_bundle(cfg or rk.shipped_bundle()).coref_authoritative_evidence)


def earned_identity_block(cfg: ConfigBundle | None = None) -> dict[str, Any]:
    """``resolution.earned_identity`` as declared — the identity tunables.

    A separate accessor from :func:`resolution_keys` because the block is where every S3 threshold, cap,
    floor and vocabulary lives; a config assertion that searches only the top level cannot see them, and
    that blind spot is how three ceilings ended up declared twice under two names.
    """
    block = getattr((cfg or rk.shipped_bundle()).resolution, _EARNED_BLOCK, None)
    return dict(block) if isinstance(block, dict) else {}


def coref_producer_block(cfg: ConfigBundle | None = None) -> dict[str, Any]:
    """``credibility.coreference`` — the *producer* switch (``{}`` ⇒ the pass returns ``[]``)."""
    block = getattr((cfg or rk.shipped_bundle()).credibility, "coreference", None)
    return dict(block) if isinstance(block, dict) else {}


def hard_id_unique(cfg: ConfigBundle | None = None) -> dict[str, Any]:
    return dict((resolution_keys(cfg).get("hard_id_fields") or {}).get("unique") or {})


def raises_loudly(fn: Any) -> bool:
    """Did ``fn()`` fail loudly (any exception) rather than silently tolerating its input?"""
    try:
        fn()
    except Exception:
        return True
    return False


__all__ = [n for n in dir() if not n.startswith("_")]
