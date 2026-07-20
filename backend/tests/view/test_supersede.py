"""Supersede-vs-contradict resolution over the **production key path** (master §4.3, EVAL RCA §2.1).

The pre-fix suite hand-injected a slot-shaped ``edge_instance`` onto each claim's ``resolved_ref``, so it
tested ``build_instance_edges`` in isolation while the real key builder (``base_ref`` / the ``view.pipeline``
fallback) embedded the object and made supersede *unreachable in production*. These tests instead leave
``resolved_ref=None`` and let ``rebuild()`` construct the key, so they exercise the config-driven
``instance_key`` mechanism end to end: a ``based-at`` edge declared functional keys on the subject alone, so
a unit's before/after basing sites collapse to ONE instance and supersede/contradiction can fire.
"""

from __future__ import annotations

import pytest

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DocRef,
    EntityDescriptor,
    ExactDate,
    LabelDate,
    OntologyConfig,
    ResolvedRef,
    SourcesConfig,
    Triple,
    TypeDef,
)
from chanakya.store import EvidenceLog
from chanakya.view import rebuild
from tests.credibility.builders import cred_config, source

FLOOR = {
    "min_band": "probable",
    "min_independent_looks": 1,
    "newer_status_allow": ["probable", "confirmed"],
    "blocking_gate_flags": ["adversary-denial", "decoy-risk", "contradiction"],
}


def _cfg(*, functional: bool, floor: bool = True) -> ConfigBundle:
    """A minimal ontology declaring only ``based-at``; ``functional`` toggles the subject-only instance key
    so the same fixtures show both the revived beat and the defect it cures.

    ``floor`` toggles the *second* half of the rule (D-P4.4 iv): ordering only nominates a pair, and the
    post-status floor decides whether it is actually retired. Two source classes are registered — a
    ``strong`` one (``s``) that clears the floor and a ``weak`` one (``adv``) that cannot.
    """
    based_at: dict[str, object] = {"name": "based-at", "from": "unit", "to": "basing_site", "extractor": True}
    if functional:
        based_at["instance_key"] = ["from"]
    cred = cred_config(half_lives_days={"based-at": 365}, **({"supersede_floor": FLOOR} if floor else {}))
    return ConfigBundle(
        ontology=OntologyConfig(edge_types=[TypeDef.model_validate(based_at)]),
        credibility=cred,
        sources=SourcesConfig(sources=[source("s", "strong"), source("adv", "weak")]),
    )


def _entity(eid: str, etype: str) -> ClaimRecord:
    # Declared entities give the endpoints stable ids (a unit + its candidate sites) so the assertions can
    # name edges; the RELATIONSHIP claims below still carry no resolved_ref, so the instance key is built
    # by the production path, not injected.
    return ClaimRecord(
        claim_id=f"ent-{eid}", source_id="s", doc_ref=DocRef(file=eid),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(entity_type=etype, name=eid),
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def _based_at(
    cid: str, target: str, iso: str | None, *, sid: str = "s", attributes: dict | None = None
) -> ClaimRecord:
    # resolved_ref is deliberately None → the PRODUCTION key builder (resolve.entities.base_ref) mints the
    # edge_instance, so this test fails if the object ever creeps back into a functional edge's key.
    return ClaimRecord(
        claim_id=cid, source_id=sid, doc_ref=DocRef(file=cid),
        kind="observation", asserts="relationship",
        payload=Triple(subject="unit_x", predicate="based-at", object=target),
        event_time=ExactDate(iso_date=iso) if iso else None,
        attributes=attributes,
    )


def _vague(cid: str, target: str, year: int) -> ClaimRecord:
    """A claim dated only to a YEAR — the shape that used to win an ordering it had no right to."""
    c = _based_at(cid, target, "2000-01-01")
    return c.model_copy(update={"event_time": LabelDate(raw=str(year), granularity="year", year=year)})


def _view(cfg: ConfigBundle, *claims: ClaimRecord):
    log = EvidenceLog()
    targets = sorted({str(c.payload.object) for c in claims if c.payload.form == "triple"})
    log.append_many([_entity("unit_x", "unit"), *(_entity(t, "basing_site") for t in targets), *claims])
    return rebuild(log, [], cfg)


def _edges(cfg: ConfigBundle, *claims: ClaimRecord) -> dict[str, object]:
    return {e.id: e for e in _view(cfg, *claims).edges}


def test_newer_supersedes_older_via_production_key() -> None:
    view = _view(_cfg(functional=True), _based_at("c21", "site_a", "2021-01-01"),
                 _based_at("c25", "site_b", "2025-01-01"))
    edges = {e.id: e for e in view.edges}
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    # Both targets share ONE instance because the functional key excludes the object — the whole fix.
    assert old.edge_instance == new.edge_instance == "edge:unit_x:based-at"
    assert old.superseded_by == new.id
    assert new.supersedes == old.id
    assert not old.attrs.get("contradiction")
    # The floor cleared, so the pair is adjudicated by the machine — no longer a question for HITL.
    assert not old.attrs.get("candidate_supersede") and not new.attrs.get("candidate_supersede")
    assert old.attrs["supersede_gate"] == new.attrs["supersede_gate"] == "promoted"
    # ...and the consequence: the retired position reads STALE (history), never `insufficient`.
    assert old.status == "stale"
    assert "superseded" in (old.confidence.integrity_flags if old.confidence else [])


def test_promotion_draws_the_site_to_site_supersedes_edge() -> None:
    """D-P4.11 — the relocation is also a node→node edge an analyst can see and click.

    The internal ``superseded_by``/``supersedes`` fields link *edges*; the oracle (and the way a relocation
    is actually narrated) models it as one fact about two sites. The drawn edge carries the UNION of both
    basing edges' claims, so it is one-click traceable to the documents on either side of the move (G4).
    """
    view = _view(_cfg(functional=True), _based_at("c21", "site_a", "2021-01-01"),
                 _based_at("c25", "site_b", "2025-01-01"))
    drawn = [e for e in view.edges if e.type == "supersedes"]
    assert len(drawn) == 1
    edge = drawn[0]
    assert (edge.source, edge.target) == ("site_b", "site_a")  # newer site supersedes the older one
    assert set(edge.claim_ids) == {"c21", "c25"}
    assert edge.attrs["derived_via"] == "supersede"
    assert edge.status is None  # a rendering of a version link, never a second truth score (G5)


def test_low_grade_decoy_newer_claim_cannot_retire_a_well_evidenced_position() -> None:
    """The floor (D-P4.4 iv) — the planted-spoof defence, as a *gate* rather than as luck.

    ``d20_supersede_spoof`` (grade E, ``bias_vector: adversary``, ``decoy_risk_flag``) exists in the corpus
    to retire the confirmed Rahwali position off one low-grade look. Here the same attack: the OLDER
    position is well-evidenced by two independent looks; the NEWER one is a single decoy-flagged look from
    a weak source. It is newer — and it still must not retire anything.
    """
    cfg = _cfg(functional=True)
    view = _view(
        cfg,
        _based_at("c21a", "site_a", "2021-01-01"),
        _based_at("c21b", "site_a", "2021-02-01"),
        _based_at("spoof", "site_b", "2025-01-01", sid="adv", attributes={"decoy_risk_flag": True}),
    )
    edges = {e.id: e for e in view.edges}
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert old.superseded_by is None and new.supersedes is None   # nothing retired
    assert old.status != "stale"                                   # the older position stands
    assert old.attrs["candidate_supersede"] and new.attrs["candidate_supersede"]  # → HITL, the default
    assert old.attrs["supersede_gate"] == "held"
    reasons = old.attrs["supersede_hold_reason"]
    assert "newer-deception-gate:decoy-risk" in reasons and any(r.startswith("newer-below-") for r in reasons)
    assert not [e for e in view.edges if e.type == "supersedes"]   # and nothing is drawn


def test_no_floor_configured_retires_nothing() -> None:
    """A missing safety gate must read as CLOSED, never as open (config/credibility.yaml `supersede_floor`)."""
    edges = _edges(_cfg(functional=True, floor=False), _based_at("c21", "site_a", "2021-01-01"),
                   _based_at("c25", "site_b", "2025-01-01"))
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert old.superseded_by is None and new.supersedes is None
    assert old.attrs["supersede_hold_reason"] == ["supersede-floor-not-configured"]


def test_same_time_different_target_is_a_contradiction() -> None:
    edges = _edges(_cfg(functional=True), _based_at("cA", "site_a", "2023-06-01"),
                   _based_at("cB", "site_b", "2023-06-01"))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.attrs.get("contradiction") and b.attrs.get("contradiction")
    assert "cB" in a.opposing_claims and "cA" in b.opposing_claims
    assert a.superseded_by is None and b.superseded_by is None


def test_missing_time_yields_candidate_supersede() -> None:
    edges = _edges(_cfg(functional=True), _based_at("c1", "site_a", "2021-01-01"),
                   _based_at("c2", "site_b", None))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.attrs.get("candidate_supersede") and b.attrs.get("candidate_supersede")
    # can't order → do NOT overwrite either position
    assert a.superseded_by is None and b.superseded_by is None


def test_vague_year_cannot_outrank_a_precise_date_it_contains() -> None:
    """D-P4.4 (iii), R-5: a claim dated only "2025" has an upper bound of 2025-12-31, which under a
    bare upper-bound comparison made it *newer* than a precise 2025-03-27 — a vague restatement could
    retire a precisely-dated confirmation. Their intervals overlap, so the honest answer is a
    contradiction for the analyst, never an arrow either way."""
    edges = _edges(_cfg(functional=True), _vague("cVague", "site_a", 2025),
                   _based_at("cPrecise", "site_b", "2025-03-27"))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.superseded_by is None and b.superseded_by is None
    assert a.supersedes is None and b.supersedes is None
    assert a.attrs.get("contradiction") and b.attrs.get("contradiction")
    assert "cPrecise" in a.opposing_claims and "cVague" in b.opposing_claims


def test_equally_vague_targets_are_unorderable_not_contradictory() -> None:
    """Two claims that both say only "2025" share an upper bound. String equality read that as "same
    instant → contradiction"; the truth is that there is no ordering signal at all → candidate → HITL."""
    edges = _edges(_cfg(functional=True), _vague("c1", "site_a", 2025), _vague("c2", "site_b", 2025))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.attrs.get("candidate_supersede") and b.attrs.get("candidate_supersede")
    assert not a.attrs.get("contradiction") and not b.attrs.get("contradiction")
    assert a.superseded_by is None and b.superseded_by is None


def test_a_late_restatement_of_an_old_fact_does_not_reverse_the_arrow() -> None:
    """R-5: ordering took ``max`` over a target's claims, so a 2026 document *restating* the 2021
    position made the OLD site the "newest" one and retired the 2025 relocation. Taking the union
    interval instead widens the old fact into overlap — contradiction, not a reversed supersession."""
    edges = _edges(
        _cfg(functional=True),
        _based_at("c21", "site_a", "2021-01-01"),
        _based_at("c26restate", "site_a", "2026-01-01"),   # a late restatement of the OLD position
        _based_at("c25", "site_b", "2025-01-01"),
    )
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert new.superseded_by is None                 # the 2025 relocation is NOT retired by a restatement
    assert old.superseded_by is None                 # and no arrow is drawn the other way either
    assert old.attrs.get("contradiction") and new.attrs.get("contradiction")
    assert not [e for e in _view(_cfg(functional=True),
                                 _based_at("c21", "site_a", "2021-01-01"),
                                 _based_at("c26restate", "site_a", "2026-01-01"),
                                 _based_at("c25", "site_b", "2025-01-01")).edges if e.type == "supersedes"]


def test_disjoint_intervals_still_order_even_when_one_is_vague() -> None:
    """The flagship shape: the retired position is precisely dated (2021), the current one is a vague
    "2025" plus a precise confirmation. The intervals do not overlap, so the supersession still fires —
    the fix tightens ordering without disarming the demo beat."""
    view = _view(_cfg(functional=True), _based_at("c21", "site_a", "2021-10-09"),
                 _vague("c25vague", "site_b", 2025), _based_at("c25exact", "site_b", "2025-03-29"))
    edges = {e.id: e for e in view.edges}
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert old.superseded_by == new.id and new.supersedes == old.id
    assert old.status == "stale"


def test_same_target_is_plain_corroboration() -> None:
    edges = _edges(_cfg(functional=True), _based_at("c1", "site_a", "2021-01-01"),
                   _based_at("c2", "site_a", "2023-01-01"))
    assert len(edges) == 1
    edge = edges["e:unit_x:based-at:site_a"]
    assert set(edge.claim_ids) == {"c1", "c2"}  # one edge, two corroborating claims
    assert edge.superseded_by is None and not edge.attrs.get("contradiction")


def test_non_functional_edge_keeps_object_in_key_and_never_supersedes() -> None:
    """The defect this fix cures: with the default (multi-valued) key the object stays in the instance id,
    so a unit's two sites are DIFFERENT instances and ``build_instance_edges`` early-returns — supersede is
    structurally unreachable. This is exactly what production did for EVERY edge before the ``instance_key``
    declaration existed."""
    edges = _edges(_cfg(functional=False), _based_at("c21", "site_a", "2021-01-01"),
                   _based_at("c25", "site_b", "2025-01-01"))
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert old.edge_instance == "edge:unit_x:based-at:site_a"
    assert new.edge_instance == "edge:unit_x:based-at:site_b"
    assert old.superseded_by is None and new.supersedes is None


@pytest.mark.xfail(
    strict=True,
    reason="KNOWN REFINEMENT (D-P4.4, Tier-4): based-at is single-valued per (unit, site_TYPE), not per "
    "unit. A unit at its garrison AND a forward field site at once is TWO valid instances, but today's "
    "subject-only key collapses them into a false supersede. The fix is to sub-scope the instance key by "
    "site_type once the derivation stamps it; no such simultaneous pair exists in the corpus yet, so this "
    "is inert today. When site_type sub-scoping lands, this xfail will XPASS and must be removed.",
)
def test_garrison_and_field_are_not_a_false_supersede() -> None:
    # unit_x is simultaneously at its garrison (site_g) and a forward field deployment (site_f): different
    # site_types, both live. The CORRECT outcome is two independent edges, no supersede/contradiction.
    edges = _edges(_cfg(functional=True), _based_at("cg", "site_g", "2025-01-01"),
                   _based_at("cf", "site_f", "2025-06-01"))
    g, f = edges["e:unit_x:based-at:site_g"], edges["e:unit_x:based-at:site_f"]
    assert g.superseded_by is None and f.supersedes is None
    assert not g.attrs.get("contradiction") and not f.attrs.get("contradiction")
