"""Per-type auto-merge floor (P3.5) on the REAL corpus — outcome pinned end to end.

``tests/resolve/test_per_type_automerge.py`` pins the mechanism on hand-built graphs. These pin what the
floor actually does to the frozen ``hq9p_primary`` view: it unifies the organisation / trading-org
spelling variants (which the strict global bar left fragmented), and it touches nothing else — every
same-type trap and every identity-sensitive type stays exactly as split as before.

Stated as invariants, not counts (a data improvement must not turn a test red). Without the per-type floor
each org "family" below fragments into ≥2 nodes (the fuzzy fixpoint auto-merges nothing at the global bar),
so a `== 1` family size genuinely guards the feature.
"""

from __future__ import annotations

from chanakya.schemas import GraphView


def _family(view: GraphView, etype: str, *needles: str) -> list[str]:
    """Node ids of ``etype`` whose id or name contains any of ``needles`` (case-insensitive)."""
    out = []
    for n in view.nodes:
        if n.type != etype:
            continue
        hay = (n.id + " " + (n.name or "")).lower()
        if any(x.lower() in hay for x in needles):
            out.append(n.id)
    return out


def _claim_count(view: GraphView, node_id: str) -> int:
    return next((len(n.claim_ids) for n in view.nodes if n.id == node_id), 0)


# ── the floor unifies the org / trading-org spelling variants ───────────────────────────────────

def test_cpmiec_spelling_variants_collapse_to_one_manufacturer(view: GraphView) -> None:
    """CPMIEC ≡ "China (National) Precision Machinery Import[-/&] Export Corporation" — one importer node."""
    fam = _family(view, "manufacturer", "cpmiec", "precision machinery")
    assert len(fam) == 1, f"the CPMIEC importer is fragmented across {fam}"
    assert _claim_count(view, fam[0]) >= 2, "the CPMIEC node pooled no corroboration — the merge did not land"


def test_sino_galaxy_spelling_variants_collapse_to_one_trading_org(view: GraphView) -> None:
    """The SINO-GALAXY IMP/EXP · IMPEX · IMP.&EXP. spellings are one consignor."""
    fam = _family(view, "trading_org", "sino", "galaxy")
    assert len(fam) == 1, f"SINO-GALAXY is fragmented across {fam}"
    assert _claim_count(view, fam[0]) >= 2, "the SINO-GALAXY node pooled no corroboration — the merge did not land"


def test_taian_wanshan_variants_collapse_to_one_manufacturer(view: GraphView) -> None:
    """'Taian' and 'Taian (Wanshan) special-vehicle works' are the one TEL-chassis maker."""
    fam = _family(view, "manufacturer", "taian")
    assert len(fam) == 1, f"the Taian chassis maker is fragmented across {fam}"


# ── …and touches nothing else: every same-type trap stays split ─────────────────────────────────

def test_casic_is_not_merged_with_its_own_sub_institutes(view: GraphView) -> None:
    """A parent design house is not identical to its 23rd Institute / 4th Academy (a lower score, not identity)."""
    ids = {n.id for n in view.nodes}
    assert "mfr_casic" in ids, "fixture drift: CASIC node gone"
    assert "mfr_23rd_ri" in ids and "mfr_4th_academy" in ids, "fixture drift: a CASIC sub-institute node gone"
    # distinct node ids ⇒ never fused
    assert len({"mfr_casic", "mfr_23rd_ri", "mfr_4th_academy"} & ids) == 3


def test_orient_and_sino_galaxy_are_two_distinct_trading_orgs(view: GraphView) -> None:
    """Two different consignors that happen to share the generic trading-house descriptor tokens."""
    orient = _family(view, "trading_org", "orient")
    sino = _family(view, "trading_org", "sino", "galaxy")
    assert orient and sino, f"fixture drift: orient={orient} sino={sino}"
    assert set(orient).isdisjoint(sino), "ORIENT and SINO-GALAXY were fused — a same-type trap slipped the floor"


def test_the_floor_did_not_leak_into_identity_sensitive_types(view: GraphView) -> None:
    """variant / unit keep the strict global bar: the HQ-9 family and the two commands stay separate nodes."""
    ids = {n.id for n in view.nodes}
    # the HQ-9 variant family: Pakistan HQ-9/P, the export HQ-9BE and the Chinese parent are three nodes
    for nid in ("var_hq9p", "var_hq9be", "ent:variant:HQ-9"):
        assert nid in ids, f"fixture drift: variant node {nid} gone"
    assert len({"var_hq9p", "var_hq9be", "ent:variant:HQ-9"}) == 3
    # the two commands (the relocation subject vs the Army regiment) stay distinct
    assert "unit_hq9b" in ids and "unit_paad" in ids
    # and no accepted merge / candidate same-as edge fuses any two of the variant-family nodes
    fam = {"var_hq9p", "var_hq9be", "ent:variant:HQ-9", "ent:variant:HQ-9A"}
    for e in view.edges:
        if e.type == "same-as":
            assert not ({e.source, e.target} <= fam), f"a variant-family pair became a merge: {e.source}/{e.target}"
