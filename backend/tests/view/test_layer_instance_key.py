"""The ``site_type`` re-key, and the relocation mitigation it must not silently drop (R1.3 / C1 / L1 / C7).

``based-at`` is FUNCTIONAL and keyed on the unit alone, which is what makes a relocation legible: one
subject, two site targets, one instance, so the supersede can compare them. Tagging that key by *kind of
place* is a real refinement — a unit at its garrison and concurrently at a forward site is **two valid
basings, not a relocation** — but it changes the shape of an identifier three other mechanisms read. This
file pins the two things that could go wrong, and one that could go wrong later.

**1. The mitigation that must survive: ``resolve.scoring.co_instances``.** Two sites that are co-objects of
*one* edge instance are a relocation's before/after, and the scorer excludes that neighbour so a confirmed
relocation cannot manufacture relational evidence that origin ≡ destination. It reads ``Edge.edge_instance``
on the **resolve** side. A naive re-key that changed the shape there would silently drop the mitigation, and
the failure would be invisible — the scorer would just quietly find one more "shared neighbour". So this
asserts both halves: the resolve-side key stays untagged, *and* the detector still fires.

**2. The per-subject rule (ruling L1).** The tag may only de-conflict a subject's basings when **every** one
of them has a known class. If even one does not, tagging the rest *separates* the unknown one from them —
and separation is de-confliction, which C7's third state forbids, because a real relocation then quietly
stops firing while the code still looks deterministic. Absent and stated-but-unmappable are the **same**
condition: we do not know the class.

**3. And the third state is all three parts or none.** No de-confliction, no fusion, *and* a named gap. A
suppression with no gap is the silent kill this whole mechanism exists to prevent.
"""

from __future__ import annotations

from chanakya.credibility.supersession import (
    ADJUDICATION_HELD,
    CANDIDATE,
    GATE,
    PENDING_NEWER,
    PENDING_OLDER,
    identity_is_unearned,
    promote_supersessions,
    protects_an_honest_refusal,
)
from chanakya.ontology import EdgeLaneIndex, LayerRouting, build_edge_instance_key
from chanakya.resolve.entities import base_ref
from chanakya.resolve.scoring import co_instances
from chanakya.schemas import (
    ClaimRecord,
    ConfidenceBreakdown,
    ConfigBundle,
    CredibilityConfig,
    EdgeView,
    GraphView,
    IndependenceGroup,
    NodeView,
    OntologyConfig,
)
from chanakya.schemas.claim import DocRef, EntityDescriptor, Triple
from chanakya.schemas.values import ExactDate
from chanakya.schemas.view import SufficiencyEval
from chanakya.view.layers import SUPERSEDE_SUPPRESSED
from chanakya.view.pipeline import rebuild

_UNIT = "ent:unit:1st Bn"
_OLD = "ent:basing_site:Old Site"
_NEW = "ent:basing_site:New Site"


def _ontology(*, routing: bool = True, vocabulary: list[str] | None = None) -> OntologyConfig:
    return OntologyConfig.model_validate(
        {
            "node_types": [
                {
                    "name": "unit",
                    "layer": "instance",
                    "attrs": [{"name": "designator", "layer": "instance"}],
                },
                {
                    "name": "basing_site",
                    "layer": "design",
                    "attrs": [{"name": "site_type", "layer": "design"}],
                },
            ],
            "edge_types": [
                {
                    "name": "based-at",
                    "from": "unit",
                    "to": "basing_site",
                    "extractor": True,
                    "freshness_class": "perishable",
                    "instance_key": ["from"],
                    "instance_key_tag": "site_type",
                },
            ],
            "layer_routing": {
                "enabled": routing,
                "presence_type": "presence",
                "design_link_edge": "instance-of",
                "site_type_vocabulary": (
                    ["garrison", "forward_site"] if vocabulary is None else vocabulary
                ),
                "absent_bucket": "unknown",
            },
        }
    )


def _config(**kwargs: object) -> ConfigBundle:
    return ConfigBundle(
        ontology=_ontology(**kwargs),  # type: ignore[arg-type]
        credibility=CredibilityConfig(
            thresholds={"confirmed": 0.8, "probable": 0.5},
            half_life_defaults={"perishable": 540, "durable": None},
            supersede_floor={
                "min_band": "probable",
                "min_independent_looks": 1,
                "newer_status_allow": ["probable", "confirmed"],
                "blocking_gate_flags": ["adversary-denial", "decoy-risk", "contradiction"],
            },
        ),
    )


def _site(claim_id: str, name: str, site_type: str | None) -> ClaimRecord:
    attrs = {"site_type": site_type} if site_type is not None else {}
    return ClaimRecord(
        claim_id=claim_id,
        source_id="s1",
        doc_ref=[DocRef(file="d.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="entity",
        payload=EntityDescriptor(form="entity", entity_type="basing_site", name=name, attrs=attrs),
        report_time=ExactDate(iso_date="2025-01-01"),
    )


def _basing(claim_id: str, obj: str, when: str, source: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id=source,
        doc_ref=[DocRef(file=f"{source}.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="relationship",
        payload=Triple(subject=_UNIT, predicate="based-at", object=obj),
        event_time=ExactDate(iso_date=when),
        report_time=ExactDate(iso_date=when),
    )


def _relocation(old_type: str | None, new_type: str | None) -> list[ClaimRecord]:
    """One unit, two sites, two dates — the relocation shape, with each site's class parameterised."""
    return [
        ClaimRecord(
            claim_id="c-unit",
            source_id="s1",
            doc_ref=[DocRef(file="d.txt", line=1)],
            kind="observation",
            polarity="positive",
            asserts="entity",
            payload=EntityDescriptor(
                form="entity", entity_type="unit", name="1st Bn", attrs={"designator": "1st Bn"}
            ),
            report_time=ExactDate(iso_date="2025-01-01"),
        ),
        _site("c-old", "Old Site", old_type),
        _site("c-new", "New Site", new_type),
        _basing("c-b-old", _OLD, "2021-10-09", "s1"),
        _basing("c-b-new", _NEW, "2025-04-04", "s2"),
    ]


def _basings(view: GraphView) -> dict[str, str | None]:
    return {e.target: e.edge_instance for e in view.edges if e.type == "based-at"}


# ── 1. the co_instances mitigation survives ────────────────────────────────────────────────────────

def test_the_resolve_side_instance_key_stays_untagged() -> None:
    """``base_ref`` must keep producing the untagged key, whatever the ontology declares.

    The tag is a **view** post-pass, so the identifier ``co_instances`` reads is structurally unchanged by
    this stage. Asserted rather than assumed: if a later stage tags the resolve side too, it inherits the
    obligation to carry the relocation exclusion forward, and this is where that shows up as a red test
    rather than as a scorer quietly finding one more shared neighbour.
    """
    lane = EdgeLaneIndex(_ontology().edge_types and _ontology())
    claim = _basing("c-b-old", _OLD, "2021-10-09", "s1")
    ref = base_ref(claim, lane)
    assert ref.edge_instance == build_edge_instance_key(_UNIT, "based-at", _OLD, ("from",))
    assert ref.edge_instance == "edge:ent:unit:1st Bn:based-at"
    assert lane.instance_key_tag("based-at") == "site_type"  # the declaration IS there…
    assert ":garrison" not in (ref.edge_instance or "")      # …and the resolve side still ignores it


def test_co_instances_still_detects_a_relocation_pair() -> None:
    """The two sites of one relocation are co-objects of one instance ⇒ the exclusion still fires."""
    from chanakya.resolve import entities as ent

    lane = EdgeLaneIndex(_ontology())
    graph = ent.build(_relocation("garrison", "forward_site"), lane)
    shared = co_instances(graph, _OLD, _NEW)
    assert shared == {"edge:ent:unit:1st Bn:based-at"}, (
        "a dated relationship to the same neighbour at two different times is NOT the same relationship: "
        "if this set is empty, a confirmed relocation manufactures relational evidence that origin is the "
        "destination"
    )


# ── 2 + 3. the per-subject rule, and the third state ───────────────────────────────────────────────

def test_two_known_classes_de_conflict_into_two_valid_basings() -> None:
    """A garrison *and* a forward site at overlapping times: two basings, not a manufactured relocation."""
    view = rebuild(_relocation("garrison", "forward_site"), [], _config())
    instances = _basings(view)
    assert instances == {
        _OLD: "edge:ent:unit:1st Bn:based-at:garrison",
        _NEW: "edge:ent:unit:1st Bn:based-at:forward_site",
    }
    # Asserted on the NOMINATION, not on a drawn edge. Promotion additionally requires the newer
    # assertion to clear the credibility floor, which is a different gate and would pass this test
    # vacuously in an abstract fixture with no source registry — the thing the re-key controls is whether
    # the pair is ever *ordered against each other* at all, and across two instances it must not be.
    assert not any(
        PENDING_NEWER in e.attrs or PENDING_OLDER in e.attrs
        for e in view.edges if e.type == "based-at"
    ), "two concurrently valid basings at different kinds of site are not a before/after pair"
    assert not [e for e in view.edges if e.type == "supersedes"]


def test_one_unknown_class_does_not_de_conflict_and_does_not_fuse() -> None:
    """The third state, all three parts (ruling L1 / C7).

    The old site's class is stated but unmappable; the new site's is known. Tagging only the known one would
    **separate** them — and then the relocation just stops firing, with nothing anywhere to say so. That is
    the measured failure this rule exists to prevent, so: one shared untagged instance (no de-confliction),
    no supersede nomination (no fusion), and a named gap (visible refusal).
    """
    view = rebuild(_relocation("prepared revetment complex", "forward_site"), [], _config())
    instances = _basings(view)
    assert set(instances.values()) == {"edge:ent:unit:1st Bn:based-at"}, (
        f"an unknown class must not be separated from a known one — got {instances}"
    )
    basings = [e for e in view.edges if e.type == "based-at"]
    assert all(e.attrs.get(SUPERSEDE_SUPPRESSED) for e in basings), "no fusion: the nomination is withdrawn"
    assert not [e for e in view.edges if e.type == "supersedes"], "and no relocation is drawn"
    assert all(e.status != "stale" for e in basings), "nothing is retired, so nothing goes stale"
    gaps = [g for g in view.known_gaps if "site_type" in (g.missing_slots or [])]
    assert len(gaps) == 1, (
        "a suppressed supersede MUST be named — an unreported non-event is indistinguishable from the "
        f"mechanism working. Gaps: {[g.id for g in view.known_gaps]}"
    )
    assert "prepared revetment complex" in gaps[0].what_missing, "the gap quotes what the source stated"


def test_an_absent_class_is_the_same_condition_as_an_unmappable_one() -> None:
    """"Not stated" and "stated but unmappable" are identical for keying: we do not know the class."""
    view = rebuild(_relocation(None, "forward_site"), [], _config())
    assert set(_basings(view).values()) == {"edge:ent:unit:1st Bn:based-at"}
    assert all(
        e.attrs.get(SUPERSEDE_SUPPRESSED) for e in view.edges if e.type == "based-at"
    )
    gaps = [g for g in view.known_gaps if "site_type" in (g.missing_slots or [])]
    assert len(gaps) == 1
    assert "not stated by any source" in gaps[0].what_missing


def test_a_same_class_change_of_site_is_still_nominated_as_a_relocation() -> None:
    """Same kind of site, two dates ⇒ still one instance, still an ordered before/after pair.

    The counterpart the other tests need: the third state must be a refusal *on a specific ground*, not a
    blanket refusal. If this case stopped being nominated, the re-key would have disabled the relocation beat
    rather than made it precise.

    Stops at the **nomination**, deliberately. Whether the pair is then *promoted* and drawn is the
    credibility floor's call (D-P4.4 iv) — a separate gate, which in an abstract fixture with no source
    registry holds the pair for the analyst, and rightly so. Asserting a drawn edge here would be asserting
    someone else's mechanism through a fixture that cannot honestly satisfy it.
    """
    view = rebuild(_relocation("garrison", "garrison"), [], _config())
    assert set(_basings(view).values()) == {"edge:ent:unit:1st Bn:based-at:garrison"}
    basings = {e.target: e for e in view.edges if e.type == "based-at"}
    assert basings[_OLD].attrs.get(PENDING_NEWER) == basings[_NEW].id, (
        "the older basing must nominate the newer one as its successor"
    )
    assert basings[_OLD].id in basings[_NEW].attrs.get(PENDING_OLDER, [])
    assert not any(e.attrs.get(SUPERSEDE_SUPPRESSED) for e in basings.values()), (
        "a known, shared site class licenses the ordering — nothing here is suppressed"
    )


def test_flag_off_keys_are_untagged_everywhere() -> None:
    """With routing off the view keys exactly as it did before this stage — the safety property, locally."""
    view = rebuild(_relocation("garrison", "forward_site"), [], _config(routing=False))
    assert set(_basings(view).values()) == {"edge:ent:unit:1st Bn:based-at"}


def test_the_vocabulary_is_config_declared_not_a_code_literal() -> None:
    """Gate G6: change the config and the classification changes; nothing about it lives in code."""
    routing = LayerRouting.from_ontology(_ontology(vocabulary=["depot"]))
    assert routing.normalise_tag("Depot") == ("depot", True)
    assert routing.normalise_tag("garrison") == ("unknown", False)  # no longer in the vocabulary


# ── R1.4, in BOTH directions — the mirror the first implementation lacked ───────────────────────────
#
# The first version of R1.4's guard returned a *hold*, which quietly disabled the legitimate relocation
# beat. Every test I had written rewarded caution, so nothing caught it; an independently-authored mirror
# did. These are the mirror I should have written: each prohibition is paired with the thing that must
# still work, so timidity fails as loudly as over-promotion.

def _promotable() -> ConfigBundle:
    """Config whose supersede floor a single well-graded look can actually clear.

    The floor is a real gate and an abstract fixture cannot satisfy it by accident, so the promotion-side
    tests would pass vacuously (nothing promoted, nothing to check) unless it is reachable. Lowered here
    *for the fixture only* — the shipped floor is untouched.
    """
    config = _config()
    return config.model_copy(
        update={
            "credibility": config.credibility.model_copy(
                update={
                    "thresholds": {"confirmed": 0.8, "probable": 0.0},
                    "supersede_floor": {
                        "min_band": "probable",
                        "min_independent_looks": 1,
                        "newer_status_allow": ["possible", "probable", "confirmed"],
                        "blocking_gate_flags": ["adversary-denial", "decoy-risk", "contradiction"],
                        "require_earned_identity": True,
                    },
                }
            )
        }
    )


def test_an_earned_relocation_is_still_promoted_retired_and_drawn() -> None:
    """R1.4 must NOT disable supersession. The subject here rests on no open identity question at all."""
    view = rebuild(_relocation("garrison", "garrison"), [], _promotable())
    basings = {e.target: e for e in view.edges if e.type == "based-at"}
    assert basings[_OLD].superseded_by == basings[_NEW].id, "the earned relocation must be promoted"
    assert basings[_NEW].supersedes == basings[_OLD].id
    drawn = [e for e in view.edges if e.type == "supersedes"]
    assert drawn and (drawn[0].source, drawn[0].target) == (_NEW, _OLD), "and drawn, so it is clickable"
    # …and the machine really did adjudicate it: the pair is off the analyst's desk.
    assert CANDIDATE not in basings[_OLD].attrs and CANDIDATE not in basings[_NEW].attrs
    assert not any(ADJUDICATION_HELD in e.attrs for e in basings.values())


def test_a_well_evidenced_retirement_still_reads_stale() -> None:
    """R1.4(b) protects an honest ``insufficient``; it does not stop a retirement from being *stale*.

    The counterpart to the test below. Both must hold, and an implementation that made *every* retirement
    keep its label would satisfy the other one while quietly disabling retirement.
    """
    view = rebuild(_relocation("garrison", "garrison"), [], _promotable())
    older = next(e for e in view.edges if e.type == "based-at" and e.target == _OLD)
    assert older.sufficiency is not None and older.sufficiency.satisfied, (
        "this fixture's older basing must be ASSESSABLE, or the test measures the protected path instead"
    )
    assert older.status == "stale", "a retired, assessable position is history — that is `stale`"
    assert not any(g.related_ref == older.id for g in view.known_gaps)


def test_an_honest_insufficient_over_an_unearned_identity_keeps_its_label_and_gap() -> None:
    """R1.4(b), the prohibition itself: an ``insufficient`` is a refusal, not a weak assessment.

    Calling it ``stale`` would say "we knew this and it has been overtaken" about something we never knew,
    and deleting its Known Gap would remove the only record that we still cannot assess it. The supersede
    link is still written — the newer fact stands — so nothing is hidden; only the honest refusal is intact.

    **Conditioned on the identity**, and the test says so by supplying a provisional subject. D-13.14 names
    the gap deletion as a consequence *of the over-merge*, not as a general wrong. Unconditioned, this rule
    stops a legitimate relocation's retired end from ever reading ``stale`` — measured on the real corpus —
    which disables the beat rather than protecting anything. The test below pins that other direction.
    """
    older = EdgeView(
        id="e:old", type="based-at", source=_UNIT, target=_OLD, status="insufficient",
        sufficiency=SufficiencyEval(satisfied=False, missing_slots=["official_announcement"]),
        attrs={CANDIDATE: True, PENDING_NEWER: "e:new", GATE: "pending"},
    )
    newer = EdgeView(
        id="e:new", type="based-at", source=_UNIT, target=_NEW, status="probable",
        sufficiency=SufficiencyEval(satisfied=True),
        confidence=ConfidenceBreakdown(assertion_confidence=0.9),
        supporting_claims=[IndependenceGroup(group_id="g1", claim_ids=["c1"], weight=1.0)],
        attrs={CANDIDATE: True, PENDING_OLDER: ["e:old"], GATE: "pending"},
    )
    subject = {_UNIT: NodeView(id=_UNIT, type="unit", attrs={"provisional": True})}
    assert protects_an_honest_refusal(older, identity_unearned=True)
    assert not protects_an_honest_refusal(older, identity_unearned=False), (
        "an under-evidenced retirement over an EARNED identity is retired normally — the protection is not "
        "a blanket one (this is the assertion that keeps the real relocation working)"
    )
    assert not protects_an_honest_refusal(newer, identity_unearned=True)
    outcome = promote_supersessions([older, newer], _promotable(), subject, set())
    assert older.superseded_by == "e:new", "the supersede link IS written — the newer fact stands"
    assert older.status == "insufficient", "…but the honest refusal is not overwritten with `stale`"
    assert outcome.protected_refusals == ["e:old"]
    assert older.id not in outcome.retired_element_ids, (
        "and because it is not listed as retired, the pipeline leaves its Known Gap in place"
    )


def test_an_unearned_identity_is_promoted_but_stays_in_the_analysts_queue() -> None:
    """R1.4(a) — the narrow prohibition: no *machine adjudication*, not "no promotion".

    The subject is a provisional instance, so there is no earned identity under the movement at all. The
    relocation still stands (it cleared the credibility floor) and is still drawn — but the pair keeps
    `candidate_supersede`, with the reason recorded, because with the identity in question the analyst is
    exactly who should decide.
    """
    claims = _relocation("garrison", "garrison")
    # Build the pre-promotion pair shape (the `_config()` floor holds, so the nominations survive), then
    # stand the subject in as a provisional instance — exactly how the routing marks a materialized one.
    fresh = rebuild(claims, [], _config())
    pair = {e.target: e for e in fresh.edges if e.type == "based-at"}
    for e in pair.values():
        e.attrs.pop(GATE, None)
        e.attrs.pop("supersede_hold_reason", None)
    nodes = {n.id: n for n in fresh.nodes}
    nodes[_UNIT].attrs["provisional"] = True
    outcome = promote_supersessions(list(pair.values()), _promotable(), nodes, set())
    assert pair[_OLD].superseded_by == pair[_NEW].id, "promotion is NOT withheld — only adjudication is"
    assert outcome.identity_unearned_pairs == [(pair[_OLD].id, pair[_NEW].id)]
    assert pair[_OLD].attrs.get(CANDIDATE) is True, "the pair must stay in the analyst's queue"
    assert pair[_NEW].attrs.get(CANDIDATE) is True
    assert pair[_OLD].attrs[ADJUDICATION_HELD] == "subject-identity-provisional"


def test_an_open_candidate_merge_on_the_subject_also_holds_adjudication() -> None:
    """The second unearned shape: the subject is an endpoint of a same-as nobody has adjudicated."""
    claims = _relocation("garrison", "garrison")
    fresh = rebuild(claims, [], _config())
    pair = {e.target: e for e in fresh.edges if e.type == "based-at"}
    for e in pair.values():
        e.attrs.pop(GATE, None)
        e.attrs.pop("supersede_hold_reason", None)
    outcome = promote_supersessions(
        list(pair.values()), _promotable(), {n.id: n for n in fresh.nodes}, {_UNIT}
    )
    assert outcome.identity_unearned_pairs, "an open candidate merge on the subject is an open question"
    assert pair[_OLD].attrs[ADJUDICATION_HELD] == "subject-identity-open-candidate-merge"
    assert pair[_OLD].superseded_by == pair[_NEW].id, "still promoted, still drawn — only not adjudicated"


def test_a_same_target_refresh_is_never_treated_as_unearned() -> None:
    """The guard is scoped to promotions that would DRAW a relocation. A refresh asserts no movement."""
    floor = {"require_earned_identity": True}
    older = EdgeView(id="e:old", type="based-at", source=_UNIT, target=_NEW)
    newer = EdgeView(id="e:new", type="based-at", source=_UNIT, target=_NEW)
    assert identity_is_unearned(older, newer, {_UNIT: NodeView(
        id=_UNIT, type="unit", attrs={"provisional": True})}, {_UNIT}, floor) is None


def test_the_guard_is_config_gated_and_the_gap_register_never_repeats_itself() -> None:
    """Two small properties worth pinning: the switch is real, and a gap is stated once."""
    floor_off: dict[str, object] = {"require_earned_identity": False}
    older = EdgeView(id="e:old", type="based-at", source=_UNIT, target=_OLD)
    newer = EdgeView(id="e:new", type="based-at", source=_UNIT, target=_NEW)
    provisional = {_UNIT: NodeView(id=_UNIT, type="unit", attrs={"provisional": True})}
    assert identity_is_unearned(older, newer, provisional, {_UNIT}, floor_off) is None
    assert identity_is_unearned(older, newer, provisional, {_UNIT}, {"require_earned_identity": True})
    # And no view repeats a gap id — several mechanisms can notice the same absence.
    view = rebuild(_relocation("prepared revetment complex", "forward_site"), [], _config())
    ids = [g.id for g in view.known_gaps]
    assert len(ids) == len(set(ids)), f"the gap register must not repeat itself: {ids}"
