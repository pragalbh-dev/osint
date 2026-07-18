"""The fixture is test input, so guard its invariants — a broken fixture would silently weaken every
downstream agent test. Mirrors the spirit of gate G4 (traceability) on the hand-authored data."""

from __future__ import annotations

from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView


def test_every_view_claim_id_resolves(view: GraphView, claims: dict[str, ClaimRecord]) -> None:
    """G4-style: every claim_id on a node/edge resolves to a real ClaimRecord → doc_ref."""
    for n in view.nodes:
        for cid in n.claim_ids:
            assert cid in claims, f"node {n.id} cites missing claim {cid}"
    for e in view.edges:
        assert e.claim_ids, f"edge {e.id} has no claim (naked assertion)"
        for cid in e.claim_ids:
            assert cid in claims, f"edge {e.id} cites missing claim {cid}"


def test_hero_chain_present(view: GraphView) -> None:
    """The DATA-C answer_key chain, stored origin-ward."""
    want = {
        ("unit_paad", "based-at", "site_karachi"),
        ("var_hq9p", "inducted-into", "unit_paad"),
        ("comp_ht233", "equips", "var_hq9p"),
        ("mfr_casic", "manufactures", "comp_ht233"),
    }
    have = {(e.source, e.type, e.target) for e in view.edges}
    assert want <= have


def test_ht233_is_candidate_not_confirmed(view: GraphView) -> None:
    """The disqualifying line: HT-233 is a CANDIDATE chokepoint with UNKNOWN substitutability."""
    ht = next(n for n in view.nodes if n.id == "comp_ht233")
    assert ht.materiality is not None
    assert ht.materiality.chokepoint_status == "candidate"
    assert ht.materiality.substitutability_state == "UNKNOWN"


def test_planted_gap_is_first_class(view: GraphView) -> None:
    gap = next(g for g in view.known_gaps if g.id == "gap:comp_ht233:sole_source")
    assert gap.missing_slots
    assert gap.next_coverage_due
    assert gap.observability_ceiling == "confirmable"


def test_inference_claims_carry_premises(claims: dict[str, ClaimRecord]) -> None:
    for c in claims.values():
        if c.kind == "inference":
            assert c.premises, f"inference claim {c.claim_id} must cite premises"


def test_config_has_hero_lens_and_aliases(config: ConfigBundle) -> None:
    assert "lens-hq9p-pk" in config.subjects.as_map()
    assert "HQ-9/P" in config.resolution.alias_table
    assert config.sources.as_map()  # get_evidence needs source metadata
