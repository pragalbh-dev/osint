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
    OntologyConfig,
    ResolvedRef,
    Triple,
    TypeDef,
)
from chanakya.store import EvidenceLog
from chanakya.view import rebuild


def _cfg(*, functional: bool) -> ConfigBundle:
    """A minimal ontology declaring only ``based-at``; ``functional`` toggles the subject-only instance key
    so the same fixtures show both the revived beat and the defect it cures."""
    based_at: dict[str, object] = {"name": "based-at", "from": "unit", "to": "basing_site", "extractor": True}
    if functional:
        based_at["instance_key"] = ["from"]
    return ConfigBundle(ontology=OntologyConfig(edge_types=[TypeDef.model_validate(based_at)]))


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


def _based_at(cid: str, target: str, iso: str | None) -> ClaimRecord:
    # resolved_ref is deliberately None → the PRODUCTION key builder (resolve.entities.base_ref) mints the
    # edge_instance, so this test fails if the object ever creeps back into a functional edge's key.
    return ClaimRecord(
        claim_id=cid, source_id="s", doc_ref=DocRef(file=cid),
        kind="observation", asserts="relationship",
        payload=Triple(subject="unit_x", predicate="based-at", object=target),
        event_time=ExactDate(iso_date=iso) if iso else None,
    )


def _edges(cfg: ConfigBundle, *claims: ClaimRecord) -> dict[str, object]:
    log = EvidenceLog()
    targets = sorted({str(c.payload.object) for c in claims if c.payload.form == "triple"})
    log.append_many([_entity("unit_x", "unit"), *(_entity(t, "basing_site") for t in targets), *claims])
    view = rebuild(log, [], cfg)
    return {e.id: e for e in view.edges}


def test_newer_supersedes_older_via_production_key() -> None:
    edges = _edges(_cfg(functional=True), _based_at("c21", "site_a", "2021-01-01"),
                   _based_at("c25", "site_b", "2025-01-01"))
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    # Both targets share ONE instance because the functional key excludes the object — the whole fix.
    assert old.edge_instance == new.edge_instance == "edge:unit_x:based-at"
    assert old.superseded_by == new.id
    assert new.supersedes == old.id
    assert not old.attrs.get("contradiction")


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
