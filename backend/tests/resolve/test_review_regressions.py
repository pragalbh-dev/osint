"""Regressions for the bugs the adversarial review caught — each must stay fixed (spine/03 discipline)."""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import DecisionRecord, PlaceEntry
from tests.resolve._helpers import entity, mk_config, triple

RADII = {"pad": 500.0, "site": 1500.0, "terminal": 3000.0, "district": 5000.0, "city": 15000.0}


def _cluster_of(part, eid: str) -> set[str]:
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


# ── (crit) resolve() must not crash when a triple endpoint has no entity claim ──────────────────

def test_no_crash_on_undeclared_triple_endpoint() -> None:
    cfg = mk_config()
    claims = [
        entity("unit_a", "unit", "Alpha Regiment"),
        entity("unit_b", "unit", "Bravo Regiment"),
        triple("unit_a", "based-at", "ghost_site"),  # ghost_site has NO entity claim
        triple("unit_b", "based-at", "ghost_site"),
    ]
    part = resolve(claims, cfg)  # must not raise KeyError
    # they share a mention-only neighbour ⇒ at least surfaced, never dropped/crashed
    assert isinstance(part.candidates, list)


# ── (crit) distinct-from is a HARD veto even transitively through a bridge node ─────────────────

def test_veto_not_bypassed_by_bridge_node() -> None:
    cfg = mk_config(distinct_from={"HQ-9/P": ["HQ-9BE"]})
    shared = [entity(f"comp_{i}", "component", f"C{i}") for i in range(8)]
    claims = [
        entity("var_hq9p", "variant", "HQ-9/P", family="HQ-9"),
        entity("var_hq9be", "variant", "HQ-9BE", family="HQ-9"),
        entity("var_mid", "variant", "HQ-9", family="HQ-9"),  # un-vetoed bridge
        *shared,
        *[triple("var_hq9p", "equips", f"comp_{i}") for i in range(8)],
        *[triple("var_hq9be", "equips", f"comp_{i}") for i in range(8)],
        *[triple("var_mid", "equips", f"comp_{i}") for i in range(8)],
        triple("var_mid", "same-as", "var_hq9p"),
        triple("var_mid", "same-as", "var_hq9be"),
    ]
    part = resolve(claims, cfg)
    # the flagship non-negotiable: HQ-9/P and HQ-9BE must NEVER end up in one cluster, even via a bridge
    assert not ({"var_hq9p", "var_hq9be"} <= _cluster_of(part, "var_hq9p"))
    # and the partition is not self-contradictory (the pair is not simultaneously same_as + distinct_from)
    same = {frozenset(p) for p in part.same_as}
    assert frozenset({"var_hq9p", "var_hq9be"}) not in same


# ── (high) identical names in different namespaces (countries) must NOT hard-merge ──────────────

def test_same_name_different_country_not_merged() -> None:
    cfg = mk_config()
    claims = [
        entity("site_cn", "basing_site", "Air Defence Base", country="China"),
        entity("site_pk", "basing_site", "Air Defence Base", country="Pakistan"),
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []  # same name, different namespace ⇒ not fused


# ── (high) blank / unsupported-script names must never be treated as alias-equivalent ───────────

def test_empty_or_arabic_names_do_not_merge() -> None:
    cfg = mk_config()
    claims = [
        entity("u_a", "unit", "فوج", service_branch="PA"),   # Arabic/Urdu 'army'
        entity("u_b", "unit", "دفاع", service_branch="PA"),  # Arabic/Urdu 'defence' — distinct
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []  # both once normalised to '' under the old bug → confident false merge


# ── (crit/high) places must NOT fuse a unit with its co-located base (co-location ≠ identity) ────

def test_places_do_not_merge_unit_with_its_base() -> None:
    base = PlaceEntry(
        place_id="pl_nurkhan", canonical_name="PAF Base Nur Khan", kind="airbase",
        precision_class="site", canonical_dd=(33.61639, 73.09972), aliases=["Nur Khan"],
    )
    cfg = mk_config(places=[base], proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0)
    claims = [
        entity("unit_bty", "unit", "3 Bn launcher section", coordinates=[33.6164, 73.0997]),
        entity("comp_radar", "component", "HT-233 radar", coordinates=[33.6170, 73.1000]),
        entity("site_base", "basing_site", "Nur Khan", coordinates=[33.6164, 73.0997]),
    ]
    part = resolve(claims, cfg)
    # a launcher unit and a radar co-located at the base must NOT be fused with each other or the base
    assert part.same_as == []


# ── (high) a learned merge_adjudication(reject) must survive place resolution (HITL propagation) ─

def test_place_resolution_honours_learned_reject() -> None:
    p1 = PlaceEntry(place_id="pl_x", canonical_name="Site X", precision_class="site",
                    canonical_dd=(33.0, 73.0), aliases=["Site X"])
    cfg = mk_config(places=[p1], proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0)
    claims = [
        entity("site_a", "basing_site", "Site X north pad", coordinates=[33.0001, 73.0001]),
        entity("site_b", "basing_site", "Site X south pad", coordinates=[33.0002, 73.0002]),
    ]
    reject = DecisionRecord(
        event_id="ma-r", ts="t", actor="analyst", stage="resolution", type="merge_adjudication",
        decision={"pair": ["Site X north pad", "Site X south pad"], "verdict": "reject"},
    )
    part = resolve(claims, cfg, decisions=[reject])
    assert frozenset({"site_a", "site_b"}) not in {frozenset(p) for p in part.same_as}  # reject not overridden


# ── (crit) a place-merge bridge must NOT transitively fuse a config-vetoed pair (finalise guard) ─

def test_place_bridge_cannot_transitively_fuse_vetoed_pair() -> None:
    p1 = PlaceEntry(place_id="pl_x", canonical_name="Combined Site", precision_class="site",
                    canonical_dd=(33.0, 73.0), aliases=["Combined Site"])
    cfg = mk_config(distinct_from={"Site A": ["Site B"]}, places=[p1],
                    proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0)
    # A, B (vetoed apart) and a Bridge site, all co-located at pl_x — place-merges A~Bridge and B~Bridge
    # would transitively fuse the vetoed A,B if finalise didn't guard the union.
    claims = [
        entity("site_a", "basing_site", "Site A", coordinates=[33.0001, 73.0001]),
        entity("site_b", "basing_site", "Site B", coordinates=[33.0002, 73.0002]),
        entity("site_bridge", "basing_site", "Bridge", coordinates=[33.0000, 73.0000]),
    ]
    part = resolve(claims, cfg)
    assert not ({"site_a", "site_b"} <= _cluster_of(part, "site_a"))  # veto holds through the place bridge
