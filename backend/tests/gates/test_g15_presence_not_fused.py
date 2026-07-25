"""G15 — **a presence is not a formation**, and an ambiguous attribution must produce a **named gap**.

Two clauses, and they are not the same kind of assertion.

**Clause 1 (regression guard) — kit photographed here ≠ a formation stationed here.** An ``observed-at``
sighting never becomes a ``based-at`` formation basing without *organizational evidence*: a stated
formation, or an ``inducted-into`` membership tying the sighted equipment to a named unit. The corpus
carries a recycled-image trap and a grade-E relocation spoof built to punish a system that collapses those
two into one confident basing.

*This clause is stated honestly as what it is: it passes today, and it passed before this stage too.* The
old offline pass already skipped when no formation link existed, so the asserted behaviour was current
behaviour — the plan's word for that is **vacuous**. It is kept because a regression guard over a live
mechanism is worth having (the derivation moved house this stage, so "it still refuses" is a real thing to
pin), but it is not where the gate earns its keep.

**Clause 2 (the clause that bites) — never a silent pick.** Where the observed equipment is associated with
**more than one** candidate formation, the attribution is *ambiguous*, and the fan-out cap makes the build
choose. The old pass took ``formations[:max_units]`` and recorded **nothing** about the ones it dropped —
while every other rejection path in the same function appended a skip record. That is an order-of-battle
**undercount with no merge involved**, which is exactly why neither the presence/formation gate nor the
co-location cap could see it: both watch merges, and no merge happens here. An adversary needs no lie; two
plausible unit references at one site are enough to make a battery disappear.

So: **two candidate formations ⇒ two attributions, or one plus an explicitly named gap. Never a silent
pick.** Which of the two you get is a config dial (``max_units_per_site``) and either answer is honest;
the third option — keep one, say nothing — is the one this gate exists to forbid.

The fixtures are abstract (a hand-built ontology + claims), so the gate is immune to the re-key's data
churn, and each clause asserts on the **observable outcome** of ``rebuild()`` rather than on an internal.
"""

from __future__ import annotations

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    CredibilityConfig,
    GraphView,
    OntologyConfig,
)
from chanakya.schemas.claim import DocRef, EntityDescriptor, Triple
from chanakya.schemas.values import ExactDate
from chanakya.view.pipeline import rebuild

_ROUTING = {
    "presence_type": "presence",
    "design_link_edge": "instance-of",
    "provisional_prefix": "presence",
    "count_attrs": ["count"],
    "site_type_vocabulary": ["garrison", "airfield"],
    "absent_bucket": "unknown",
    "superseded_derived_layers": ["unit-attribution"],
}


def _ontology() -> OntologyConfig:
    return OntologyConfig.model_validate(
        {
            "node_types": [
                {"name": "variant", "layer": "design", "attrs": [{"name": "family", "layer": "design"}]},
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
                {
                    "name": "presence",
                    "layer": "instance",
                    "attrs": [{"name": "count", "layer": "instance"}],
                },
            ],
            "edge_types": [
                {
                    "name": "observed-at",
                    "from": "variant",
                    "to": "basing_site",
                    "extractor": True,
                    "freshness_class": "perishable",
                    "materializes": {"end": "from", "node_type": "presence", "link": "instance-of"},
                },
                {
                    "name": "inducted-into",
                    "from": "variant",
                    "to": "unit",
                    "extractor": True,
                    "freshness_class": "semi-durable",
                },
                {
                    "name": "based-at",
                    "from": "unit",
                    "to": "basing_site",
                    "extractor": True,
                    "freshness_class": "perishable",
                    "instance_key": ["from"],
                    "instance_key_tag": "site_type",
                },
                {
                    "name": "instance-of",
                    "from": "presence",
                    "to": "variant",
                    "freshness_class": "durable",
                },
            ],
            "layer_routing": dict(_ROUTING),
        }
    )


def _config(max_units: int = 1) -> ConfigBundle:
    return ConfigBundle(
        ontology=_ontology(),
        credibility=CredibilityConfig(
            thresholds={"confirmed": 0.8, "probable": 0.5},
            half_life_defaults={"perishable": 540, "semi-durable": 540, "durable": None},
            basing_proposer={
                "occupancy_edge_types": ["observed-at"],
                "formation_edge_types": ["inducted-into"],
                "equipment_hop_edges": [],
                "derived_edge": "based-at",
                "require_located_site": False,
                "max_units_per_site": max_units,
                "occupied_tokens": ["occupied"],
            },
        ),
    )


def _entity(claim_id: str, etype: str, name: str, **attrs: object) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="s1",
        doc_ref=[DocRef(file="doc1.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="entity",
        payload=EntityDescriptor(form="entity", entity_type=etype, name=name, attrs=dict(attrs)),
        report_time=ExactDate(iso_date="2025-01-01"),
    )


def _triple(claim_id: str, subject: str, predicate: str, obj: str, when: str, source: str = "s1") -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id=source,
        doc_ref=[DocRef(file=f"{source}.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=when),
        report_time=ExactDate(iso_date=when),
    )


_VAR = "ent:variant:HQ-X"
_SITE = "ent:basing_site:Site A"
_U1 = "ent:unit:1st Bn"
_U2 = "ent:unit:2nd Bn"


def _sighting_only() -> list[ClaimRecord]:
    """A bare sighting: equipment seen at a site, and **no organizational evidence anywhere**."""
    return [
        _entity("c-var", "variant", "HQ-X"),
        _entity("c-site", "basing_site", "Site A", site_type="garrison"),
        _triple("c-obs", _VAR, "observed-at", _SITE, "2025-03-01"),
    ]


def _two_candidate_formations() -> list[ClaimRecord]:
    """One sighting, **two** named formations the sighted equipment is inducted into — ambiguous."""
    return [
        _entity("c-var", "variant", "HQ-X"),
        _entity("c-site", "basing_site", "Site A", site_type="garrison"),
        _entity("c-u1", "unit", "1st Bn", designator="1st Bn"),
        _entity("c-u2", "unit", "2nd Bn", designator="2nd Bn"),
        _triple("c-obs", _VAR, "observed-at", _SITE, "2025-03-01"),
        _triple("c-ind1", _VAR, "inducted-into", _U1, "2025-02-01"),
        _triple("c-ind2", _VAR, "inducted-into", _U2, "2025-02-02", source="s2"),
    ]


def _basings(view: GraphView) -> list[str]:
    return sorted(e.id for e in view.edges if e.type == "based-at")


# ── clause 1: the regression guard (passes today, and said so) ─────────────────────────────────────

def test_a_bare_sighting_never_becomes_a_formation_basing() -> None:
    """No ``inducted-into`` and no stated basing ⇒ no ``based-at`` edge, at any confidence."""
    view = rebuild(_sighting_only(), [], _config())
    assert _basings(view) == [], (
        "a sighting is not a basing: equipment photographed at a site says nothing about which formation "
        "is stationed there (G15 clause 1)"
    )


def test_a_bare_sighting_still_materializes_a_presence() -> None:
    """…but it *does* produce the other citizen. Presence is the workhorse; formation is earned.

    Asserted together with the clause above on purpose: "no basing" would also be satisfied by a build that
    simply dropped the sighting, which would be a *loss* dressed as caution. The honest outcome is a
    presence — the strongest thing the evidence supports — and nothing more.
    """
    view = rebuild(_sighting_only(), [], _config())
    presences = [n for n in view.nodes if n.type == "presence"]
    assert len(presences) == 1, f"expected one presence, got {[n.id for n in presences]}"
    assert presences[0].attrs["provisional"] is True
    assert presences[0].attrs["instance_of_design"] == _VAR
    assert [e.id for e in view.edges if e.type == "instance-of"], "the presence must link to its design"
    # `count` is a SOURCED attribute: no source stated one, so it is ABSENT — never inferred from the fact
    # that a report landed here (k reports of one battery is not k launchers).
    assert "count" not in presences[0].attrs


def test_organizational_evidence_is_what_earns_the_basing() -> None:
    """The same sighting plus an ``inducted-into`` *does* derive a basing — the guard is not a blanket no."""
    claims = [
        *_sighting_only(),
        _entity("c-u1", "unit", "1st Bn", designator="1st Bn"),
        _triple("c-ind1", _VAR, "inducted-into", _U1, "2025-02-01"),
    ]
    view = rebuild(claims, [], _config())
    assert _basings(view) == [f"e:{_U1}:based-at:{_SITE}"]


# ── clause 2: the clause that bites — never a silent pick ──────────────────────────────────────────

def _attribution_gaps(view: GraphView) -> list[str]:
    return [g.what_missing for g in view.known_gaps if g.id.endswith(":formation-attribution")]


def test_two_candidate_formations_are_never_a_silent_pick() -> None:
    """With the fan-out capped at one: **one attribution plus an explicitly named gap.**

    The gap must *name the discarded candidate*. "Ambiguity exists somewhere" is not a finding an analyst
    can task collection against; "2nd Bn is not attributed, designation coverage needed" is.
    """
    view = rebuild(_two_candidate_formations(), [], _config(max_units=1))
    drawn = _basings(view)
    assert len(drawn) == 1, f"the cap should have limited the fan-out to one, got {drawn}"
    gaps = _attribution_gaps(view)
    assert len(gaps) == 1, (
        "a truncated formation attribution MUST produce a named gap — the old pass recorded nothing, an "
        "order-of-battle undercount with no merge involved and therefore invisible to every merge-watching "
        f"gate (G15 clause 2). Gaps seen: {[g.id for g in view.known_gaps]}"
    )
    attributed = drawn[0].split(":based-at:")[0].removeprefix("e:")
    discarded = _U2 if attributed == _U1 else _U1
    assert discarded in gaps[0], f"the gap must name the discarded candidate {discarded!r}: {gaps[0]!r}"


def test_raising_the_cap_yields_two_attributions_instead() -> None:
    """The other honest answer to the same ambiguity — and it is a **config** dial, not a code path."""
    view = rebuild(_two_candidate_formations(), [], _config(max_units=2))
    assert _basings(view) == sorted([f"e:{_U1}:based-at:{_SITE}", f"e:{_U2}:based-at:{_SITE}"])
    assert _attribution_gaps(view) == [], "nothing was discarded, so there is nothing to name"


def test_one_candidate_formation_raises_no_attribution_gap() -> None:
    """No ambiguity ⇒ no gap. A gap against every attribution is how a gap register stops being read."""
    claims = [
        *_sighting_only(),
        _entity("c-u1", "unit", "1st Bn", designator="1st Bn"),
        _triple("c-ind1", _VAR, "inducted-into", _U1, "2025-02-01"),
    ]
    assert _attribution_gaps(rebuild(claims, [], _config())) == []


def test_the_gate_can_fail() -> None:
    """Non-vacuity for clause 2: the *ambiguous* fixture and the *unambiguous* one must differ.

    A gate that reports the same thing on both inputs is measuring nothing. This pins that the fixture
    really is ambiguous — two distinct candidate formations reach the derivation — so the gap assertion
    above is about a discarded candidate rather than about an empty branch.
    """
    ambiguous = rebuild(_two_candidate_formations(), [], _config(max_units=1))
    unambiguous = rebuild(
        [
            *_sighting_only(),
            _entity("c-u1", "unit", "1st Bn", designator="1st Bn"),
            _triple("c-ind1", _VAR, "inducted-into", _U1, "2025-02-01"),
        ],
        [],
        _config(max_units=1),
    )
    assert len(_basings(ambiguous)) == len(_basings(unambiguous)) == 1
    assert _attribution_gaps(ambiguous) and not _attribution_gaps(unambiguous)
