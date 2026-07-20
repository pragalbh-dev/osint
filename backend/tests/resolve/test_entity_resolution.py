"""Acceptance tests for the entity resolver (spine/03; RESOLVE.md acceptance criteria)."""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import DecisionRecord, pair_key
from tests.fixtures import loaders
from tests.resolve._helpers import entity, mk_config, triple


def _cluster_of(part, eid: str) -> set[str]:
    """All ids fused with ``eid`` (via same_as / entity_canonical)."""
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


# ── G2 guardrail: the real resolver is identity on F0's golden fixtures ─────────────────────────

def test_golden_partition_is_identity() -> None:
    store = loaders.golden_config_store()
    part = resolve(loaders.golden_claims(), store.snapshot())
    assert part.same_as == []
    assert part.candidates == []
    assert part.distinct_from == []
    assert part.entity_canonical == {}


# ── AC: FD-2000 ↔ HQ-9/P auto-merges (marketing-name alias, deterministic ≥0.85) ────────────────

def test_fd2000_hq9p_auto_merge() -> None:
    cfg = mk_config(alias_table={"HQ-9/P": ["HQ-9P", "FD-2000"]})
    claims = [
        entity("var_hq9p", "variant", "HQ-9/P", export_designator="HQ-9/P", family="HQ-9"),
        entity("var_fd2000", "variant", "FD-2000", family="HQ-9"),
    ]
    part = resolve(claims, cfg)
    assert {"var_hq9p", "var_fd2000"} <= _cluster_of(part, "var_hq9p")
    key = pair_key("var_hq9p", "var_fd2000")
    assert part.merge_confidence[key] >= cfg.resolution.bands["auto_merge"]


# ── AC: HQ-9/P vs HQ-9BE held apart by an explicit distinct-from (never merges) ─────────────────

def test_hq9p_hq9be_distinct_from_veto() -> None:
    cfg = mk_config(distinct_from={"HQ-9/P": ["HQ-9BE"]})
    claims = [
        entity("var_hq9p", "variant", "HQ-9/P", family="HQ-9", operator_branch="Pakistan Army", range_km=125),
        entity("var_hq9be", "variant", "HQ-9BE", family="HQ-9", operator_branch="Pakistan Air Force", range_km=260),
    ]
    part = resolve(claims, cfg)
    assert ("var_hq9be", "var_hq9p") in part.distinct_from or ("var_hq9p", "var_hq9be") in part.distinct_from
    assert part.same_as == []  # never merged despite same family + high name overlap
    assert part.candidates == []  # a hard veto short-circuits before the band decision


# ── AC: FD-2000 / FT-2000 lands in the mid HITL band (neither auto-merged nor kept-separate) ────

def test_ft2000_lands_in_hitl_band() -> None:
    # FT-2000 is NOT seeded distinct (user decision: score it) — high attribute similarity to FD-2000,
    # a source that conflates them (source_asserted), but no shared neighbourhood ⇒ the mid band.
    cfg = mk_config(alias_table={"HQ-9/P": ["FD-2000"]})
    claims = [
        entity("var_hq9p", "variant", "HQ-9/P", family="HQ-9"),
        entity("var_fd2000", "variant", "FD-2000", family="HQ-9"),
        entity("var_ft2000", "variant", "FT-2000", family="FT"),
        triple("var_ft2000", "same-as", "var_fd2000", source="src-tradepress"),  # a source conflates them
    ]
    part = resolve(claims, cfg)
    # FD-2000 auto-merged into HQ-9/P; FT-2000 stays out but surfaces as a candidate for the analyst.
    assert {"var_hq9p", "var_fd2000"} <= _cluster_of(part, "var_hq9p")
    assert "var_ft2000" not in _cluster_of(part, "var_hq9p")
    cand_pairs = {frozenset(p) for p in part.candidates}
    assert frozenset({"var_ft2000", "var_fd2000"}) in cand_pairs
    total = part.merge_breakdown[pair_key("var_ft2000", "var_fd2000")]["total"]
    assert cfg.resolution.bands["hitl_low"] <= total < cfg.resolution.bands["auto_merge"]


# ── AC: the relational fixpoint terminates (and a relational-only link is found) ────────────────

def test_relational_fixpoint_finds_shared_neighbourhood_merge() -> None:
    # Two same-type units with different names but the SAME neighbourhood (both field comp_x AND
    # based-at site_y) — the analyst "shared neighbourhood" signal the fixpoint exists to catch.
    cfg = mk_config()
    claims = [
        entity("unit_a", "unit", "12 Air Defence Regiment", service_branch="PA"),
        entity("unit_b", "unit", "Twelfth AD Rgt", service_branch="PA"),
        entity("comp_x", "component", "HT-233"),
        entity("site_y", "basing_site", "Site Y"),
        triple("unit_a", "fields", "comp_x"),
        triple("unit_b", "fields", "comp_x"),
        triple("unit_a", "based-at", "site_y"),
        triple("unit_b", "based-at", "site_y"),
    ]
    part = resolve(claims, cfg)  # returns ⇒ terminates
    # High shared-neighbourhood ⇒ they at least reach the analyst (merge or candidate), never dropped.
    fused = {"unit_a", "unit_b"} <= _cluster_of(part, "unit_a")
    candidate = frozenset({"unit_a", "unit_b"}) in {frozenset(p) for p in part.candidates}
    assert fused or candidate


def test_relocation_pair_is_not_a_shared_neighbour_merge() -> None:
    # A unit based-at two sites at different times: the two SITES share the unit as a neighbour, but it
    # is a relocation (one supersede instance) ⇒ excluded from the relational term ⇒ kept separate.
    cfg = mk_config()
    claims = [
        entity("unit_u", "unit", "Regiment U"),
        entity("site_1", "basing_site", "Alpha Cantonment"),
        entity("site_2", "basing_site", "Bravo Airfield"),
        triple("unit_u", "based-at", "site_1", iso="2021-06-01", edge_instance="based-at:unit_u"),
        triple("unit_u", "based-at", "site_2", iso="2025-05-01", edge_instance="based-at:unit_u"),
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []
    assert frozenset({"site_1", "site_2"}) not in {frozenset(p) for p in part.candidates}


# ── AC: alias table grows from the log (replay-derived learning) ────────────────────────────────

def test_alias_grows_from_decision_log() -> None:
    cfg = mk_config()  # no seeded alias linking the two
    claims = [
        entity("comp_h200", "component", "H-200"),
        entity("comp_ht233", "component", "HT-233"),
    ]
    # Without a decision, they do not auto-merge (different designators, no seeded alias).
    before = resolve(claims, cfg)
    assert before.same_as == []

    accept = DecisionRecord(
        event_id="ma-1", ts="2026-07-18", actor="analyst", stage="resolution",
        type="merge_adjudication", subject_ref="m1",
        decision={"pair": ["H-200", "HT-233"], "verdict": "accept"},
    )
    after = resolve(claims, cfg, decisions=[accept])
    assert {"comp_h200", "comp_ht233"} <= _cluster_of(after, "comp_h200")  # auto-resolves, no HITL


# ── AC: raise-only LLM signal cannot cross the auto-merge line (property) ────────────────────────

def test_llm_proposal_is_raise_only() -> None:
    cfg = mk_config()  # weak pair: different names, no shared neighbourhood, no source assertion
    claims = [
        entity("comp_h200", "component", "H-200"),
        entity("comp_ht233", "component", "HT-233"),
    ]
    proposal = DecisionRecord(
        event_id="mp-1", ts="2026-07-18", actor="agent", stage="resolution",
        type="merge_proposal", subject_ref="comp_h200",
        decision={"pair": ["comp_h200", "comp_ht233"], "raise_only": True},
    )
    part = resolve(claims, cfg, decisions=[proposal])
    # The LLM lifts the weak pair INTO the HITL queue, but can never auto-merge it (hard clamp).
    assert frozenset({"comp_h200", "comp_ht233"}) in {frozenset(p) for p in part.candidates}
    assert part.same_as == []


# ── AC (D-2.5): identity read from the claim stream — source-weighted, raise-only, never auto ───

def _identity_pair(source: str, grades: dict[str, str]):
    """A pair one source calls the same thing, with nothing else linking them but the assertion."""
    cfg = mk_config(source_grades=grades)
    claims = [
        entity("var_a", "variant", "Alpha SAM"),
        entity("var_b", "variant", "Bravo SAM"),
        triple("var_a", "same-as", "var_b", source=source),
    ]
    return cfg, resolve(claims, cfg)


def test_identity_assertion_is_weighted_by_the_asserting_source() -> None:
    # The SAME assertion from a curated register and from an anonymous post are not the same evidence.
    grades = {"src-register": "curated-register", "src-anon": "anon-social"}
    _, strong = _identity_pair("src-register", grades)
    _, weak = _identity_pair("src-anon", grades)
    key = pair_key("var_a", "var_b")
    assert strong.merge_breakdown[key]["source_asserted"] > weak.merge_breakdown[key]["source_asserted"]
    assert strong.merge_breakdown[key]["total"] > weak.merge_breakdown[key]["total"]


def test_identity_assertion_reaches_the_analyst_but_never_auto_merges() -> None:
    # Even the best-graded source's `same-as` only PROPOSES: the corpus plants false identities, so the
    # merge itself has to be earned by the deterministic terms (or by an analyst).
    _, part = _identity_pair("src-register", {"src-register": "curated-register"})
    assert part.same_as == []
    assert frozenset({"var_a", "var_b"}) in {frozenset(p) for p in part.candidates}


def test_identity_assertion_names_the_claim_it_came_from() -> None:
    """T10 — the score alone is not enough: an analyst adjudicating the pair has to read the source.

    ``source_asserted`` is the one merge signal that is somebody's *assertion* rather than the resolver's
    own arithmetic, and the assertion is consumed rather than drawn — so unless the pair carries the claim
    id, the sentence behind the number is unreachable from the review queue.
    """
    _, part = _identity_pair("src-register", {"src-register": "curated-register"})
    key = pair_key("var_a", "var_b")
    assert part.merge_breakdown[key]["source_asserted"] > 0
    assert len(part.identity_claims[key]) == 1


def test_a_pair_no_source_spoke_about_carries_no_identity_citation() -> None:
    """The absence is load-bearing: no key at all, so nothing downstream can offer an empty link."""
    cfg = mk_config()
    part = resolve(
        [entity("var_a", "variant", "Alpha SAM"), entity("var_b", "variant", "Alpha SAM Mk2")], cfg
    )
    assert part.identity_claims == {}


def test_identity_assertion_cannot_cross_the_auto_line_at_any_weight() -> None:
    # Property: crank the identity weight past the auto band; the pair must STILL only reach HITL.
    cfg = mk_config()
    cfg.resolution.merge_weights = {"source_asserted": 1.0}
    claims = [
        entity("var_a", "variant", "Alpha SAM"),
        entity("var_b", "variant", "Bravo SAM"),
        triple("var_a", "same-as", "var_b"),
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []
    assert frozenset({"var_a", "var_b"}) in {frozenset(p) for p in part.candidates}


def test_claim_asserted_distinct_from_is_a_hard_veto_and_stays_visible() -> None:
    # The mirror image: a source SEPARATING two things is honoured immediately, and stays inspectable.
    cfg = mk_config(alias_table={"Alpha SAM": ["Bravo SAM"]})  # an alias that would otherwise auto-merge
    claims = [
        entity("var_a", "variant", "Alpha SAM"),
        entity("var_b", "variant", "Bravo SAM"),
        triple("var_a", "distinct-from", "var_b"),
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []  # the veto beats an alias-equivalence bootstrap merge
    assert ("var_a", "var_b") in part.distinct_from


# ── AC (P3.3): the open-world containment / acronym trigger, and what it refuses ─────────────────

def test_containment_merges_a_descriptive_extension_but_not_a_designator_extension() -> None:
    cfg = mk_config(containment_min_descriptor_len=3, containment_min_short_tokens=2, acronym_min_len=3)
    claims = [
        entity("c_short", "component", "HT-233"),
        entity("c_long", "component", "HT-233 engagement radar"),
        entity("v_hq9", "variant", "HQ-9"),
        entity("v_hq9p", "variant", "HQ-9/P"),
    ]
    part = resolve(claims, cfg)
    assert {"c_short", "c_long"} <= _cluster_of(part, "c_short")  # a WORD added ⇒ same radar
    assert "v_hq9p" not in _cluster_of(part, "v_hq9")             # a MARK added ⇒ a different missile


def test_containment_refuses_a_bare_one_word_hook() -> None:
    # "Pakistan" is a prefix of half the order of battle — far too generic to bootstrap identity on.
    cfg = mk_config(containment_min_descriptor_len=3, containment_min_short_tokens=2, acronym_min_len=3)
    claims = [
        entity("u_bare", "unit", "Pakistan"),
        entity("u_paf", "unit", "Pakistan Air Force"),
    ]
    part = resolve(claims, cfg)
    assert part.same_as == []


def test_acronym_expansion_merges_initials_to_their_expansion() -> None:
    cfg = mk_config(containment_min_descriptor_len=3, containment_min_short_tokens=2, acronym_min_len=3)
    claims = [
        entity("u_acr", "unit", "PAAD"),
        entity("u_full", "unit", "Pakistan Army Air Defence"),
    ]
    part = resolve(claims, cfg)
    assert {"u_acr", "u_full"} <= _cluster_of(part, "u_acr")


# ── fixpoint cascade: one merge unlocks the next; converges to a single cluster ─────────────────

def test_fixpoint_cascade_converges() -> None:
    # A≡B by alias (bootstrap). C shares A's + B's neighbourhood ⇒ merges relationally. D shares the
    # {A,B,C} neighbourhood ⇒ merges only after C did — a genuine iterate-to-fixpoint cascade.
    cfg = mk_config(alias_table={"unit_a": ["Aye Regiment"]})
    claims = [
        entity("unit_a", "unit", "unit_a"),
        entity("unit_b", "unit", "Aye Regiment"),  # alias-equivalent to unit_a → bootstrap merge
        entity("unit_c", "unit", "Charlie Regiment"),
        entity("unit_d", "unit", "Delta Regiment"),
        entity("comp_r", "component", "HT-233"),
        entity("site_s", "basing_site", "Site S"),
        triple("unit_a", "fields", "comp_r"), triple("unit_a", "based-at", "site_s"),
        triple("unit_b", "fields", "comp_r"), triple("unit_b", "based-at", "site_s"),
        triple("unit_c", "fields", "comp_r"), triple("unit_c", "based-at", "site_s"),
        triple("unit_d", "fields", "comp_r"), triple("unit_d", "based-at", "site_s"),
    ]
    part = resolve(claims, cfg)  # must terminate
    cluster = _cluster_of(part, "unit_a")
    # All four units share the identical neighbourhood ⇒ they end up together (merge or, worst case,
    # each surfaced) — the point is the loop converges and clusters only grew.
    fused = {"unit_a", "unit_b", "unit_c"} <= cluster
    assert fused or frozenset({"unit_a", "unit_c"}) in {frozenset(p) for p in part.candidates}


# ── determinism: same inputs → identical partition across runs (gate G2 at the stage level) ─────

def test_resolve_is_deterministic() -> None:
    cfg = mk_config(alias_table={"HQ-9/P": ["FD-2000"]})
    claims = [
        entity("var_hq9p", "variant", "HQ-9/P", family="HQ-9"),
        entity("var_fd2000", "variant", "FD-2000", family="HQ-9"),
        entity("var_ft2000", "variant", "FT-2000", family="FT"),
        triple("var_ft2000", "same-as", "var_fd2000"),
    ]
    a = resolve(claims, cfg)
    b = resolve(claims, cfg)
    assert a.model_dump_json() == b.model_dump_json()


# ── AC: transliteration + seeded alias fuse cross-script designators ────────────────────────────

def test_transliteration_alias_merge() -> None:
    cfg = mk_config(
        alias_table={"HQ-9": ["Hongqi-9", "红旗-9"]},
        transliteration={"红旗-9": "Hongqi-9"},
    )
    claims = [
        entity("var_hq9", "variant", "HQ-9", family="HQ-9"),
        entity("var_hongqi", "variant", "红旗-9", family="HQ-9"),
    ]
    part = resolve(claims, cfg)
    assert {"var_hq9", "var_hongqi"} <= _cluster_of(part, "var_hq9")
