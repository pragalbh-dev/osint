"""RK-COREF (S3) — what it takes to EARN an identity from a coreference cluster.

An "authoritative" coref pair is a **Phase-1 bootstrap trigger**: it merges at hardcoded confidence 1.0 and
**bypasses banding entirely**, so no cap restrains it — not the name cap, not the perishable cap, not a band
ceiling. Two consequences drive the whole policy, and both are asserted here:

1. authorising a category authorises an **uncapped, unbanded fusion on a model-chosen label**, so a category
   may only be authoritative behind a **deterministic, code-verified precondition**;
2. it must **also** clear a source-grade floor — because a coref bind acted *harder* than the assertion it most
   resembles: a source-stated ``same-as`` is grade-floored **and** structurally raise-only, while a coref bind
   fused at 1.0 with no grade check anywhere. The weaker-evidenced channel acting harder is an inversion.

Plus the two things that make the *policy* honest rather than merely strict: the rebuild may **decline** a
grouping (D-13.18), and every link that does not bind reaches the analyst **with its licensing evidence** —
which an audit found was written and read nowhere, making every justification of raise-only fictional.
"""

from __future__ import annotations

from chanakya.resolve import ResolveConfig, resolve
from tests.resolve._helpers import coref, entity, mk_config, triple

MARKER_QUOTE = 'China Precision Machinery Import-Export Corporation, also known as CPMIEC, shipped it.'
MARK_QUOTE = 'the HQ-9 (HQ-9/P) was delivered'

EARNED = {
    "enabled": True,
    "name_ceiling": "possible",
    "authoritative_categories": ["EXPLICIT_EQUIVALENCE", "UNAMBIGUOUS_ANAPHOR"],
    "bind_min_grade": "C",
    "equivalence_markers": ["also known as", "aka", "formerly"],
    "contrast_ceiling": "probable",
}


def _cfg(**over):
    earned = {**EARNED, **over.pop("earned", {})}
    over.setdefault("source_reliability_grades", {"src-t": "B", "src-low": "E"})
    over.setdefault("containment_min_descriptor_len", 3)
    over.setdefault("containment_min_short_tokens", 2)
    return mk_config(earned_identity=earned, name_alone_caps_at_possible=True, **over)


def _pair(*, gate="PASS", evidence="EXPLICIT_EQUIVALENCE", source="src-t", quote=MARKER_QUOTE,
          referent="ref:d01-c1"):
    """Two differently-named manufacturers plus the coref link the producer would emit for them."""
    return [
        entity("m_long", "manufacturer", "China Precision Machinery Import-Export Corporation"),
        entity("m_short", "manufacturer", "CPMIEC"),
        coref("China Precision Machinery Import-Export Corporation", "CPMIEC",
              evidence=evidence, quote=quote, source=source, referent=referent, gate=gate,
              forms=("China Precision Machinery Import-Export Corporation", "CPMIEC")),
    ]


def _same_cluster(part, a: str, b: str) -> bool:
    """Did these two profiles end up as ONE node? — the observable outcome, not a raw pair form.

    Asserting on ``same_as`` membership by id would be fragile and, worse, misleading: ``_link_endpoints``
    mints a typed twin for a triple endpoint that matched no entity *id*, so a coreference bind legitimately
    lands on ``ent:<type>:<form>`` and the claim-backed profile joins the same cluster through its exact name.
    Both are "these two are one thing"; only the cluster says so unambiguously.
    """
    canon = part.entity_canonical
    return canon.get(a, a) == canon.get(b, b)


def _merged(part) -> bool:
    return _same_cluster(part, "m_long", "m_short")


# ── the bind: a passing gate AND a passing grade, both required ───────────────────────────────────

def test_a_gated_and_graded_explicit_equivalence_binds() -> None:
    """The positive case, first — a policy that binds nothing is not a policy.

    Two names that share no token and are in no alias table: nothing but the document's own sentence connects
    them, which is exactly the leak coreference exists to close. With the structural gate passed and the
    source above the floor, the bind is earned.
    """
    part = resolve(_pair(), _cfg())

    assert _merged(part), (
        "a gated, graded, uncontradicted EXPLICIT_EQUIVALENCE did not bind — if nothing can bind, coreference "
        "is not a required tier, it is a decoration"
    )


def test_a_failing_per_link_gate_falls_back_to_raise_only() -> None:
    """C5: the gate is per LINK, and a failing link becomes an injected candidate — never a silent drop."""
    part = resolve(_pair(gate="FAIL"), _cfg())

    assert not _merged(part), "a link whose deterministic gate FAILED still bound (D-13.17)"
    assert any({a, b} & {"m_long", "m_short"} for a, b in part.candidates), (
        "the failing link vanished instead of becoming a Tier-1 candidate pair — a partial bind means the link "
        "still reaches the analyst (C5)"
    )


def test_a_below_floor_source_cannot_bind_however_good_the_gate() -> None:
    """The inversion, closed. A grade-E repost's reading of its own prose does not fuse two nodes at 1.0.

    This is the gap the spike called the sharpest in the substrate: a source-stated ``same-as`` was
    grade-floored *and* raise-only, while a coref bind — weaker evidence — fused uncapped with no grade check.
    """
    part = resolve(_pair(source="src-low"), _cfg())

    assert not _merged(part), (
        "a below-floor source's coreference bound at full confidence — the weaker-evidenced channel acting "
        "harder than a stated same-as is the inversion D-13.17 exists to remove"
    )


def test_name_variant_is_raise_only_permanently() -> None:
    """Not caution — mechanics. An authoritative NAME_VARIANT *is* the exact-name auto-merge lane, rebuilt.

    Because a bind bypasses banding, authorising this category would reinstate the very lane D-13.1 deletes,
    on a different predicate, immune to the name cap that replaced it.
    """
    part = resolve(_pair(evidence="NAME_VARIANT"), _cfg())

    assert not _merged(part), "NAME_VARIANT bound — the name verdict has been rebuilt on another predicate"


def test_a_category_the_operator_did_not_authorise_never_binds() -> None:
    """The operator's list still governs: a gate verdict is a precondition, not a licence."""
    part = resolve(_pair(), _cfg(earned={"authoritative_categories": []}))

    assert not _merged(part), "a category absent from the authorised list bound anyway"


# ── ruling M1: the mark-vs-word conjunct ──────────────────────────────────────────────────────────

def test_a_mark_extension_is_refused_even_though_it_reads_like_an_alias_declaration() -> None:
    """M1. ``"<Design> (<Design>/X)"`` passes every other conjunct while DISTINGUISHING two variants.

    Verbatim span, both surface forms present, parenthetical marker present — and the equivalence is wrong.
    The grade floor cannot catch it (a good source writes exactly that sentence) and the decline only fires if
    the two members happen to conflict on a critical discriminator, which two marks of one design often do not.
    A marker vocabulary built as a token list can *never* catch it, because the marker really is there. What
    catches it is the distinction the containment bootstrap already encodes: a name extended by a WORD is the
    same thing described more fully; a name extended by a MARK is a different model.
    """
    claims = [
        entity("v_base", "variant", "HQ-9"),
        entity("v_mark", "variant", "HQ-9/P"),
        coref("HQ-9", "HQ-9/P", quote=MARK_QUOTE, referent="ref:d01-c1", gate="FAIL",
              forms=("HQ-9", "HQ-9/P")),
    ]
    part = resolve(claims, _cfg())

    assert not _same_cluster(part, "v_base", "v_mark"), (
        "a mark extension bound as an equivalence — that is a different missile (M1)"
    )


# ── D-13.18: the rebuild may DECLINE the grouping ─────────────────────────────────────────────────

def test_an_intra_referent_critical_conflict_declines_the_whole_grouping() -> None:
    """The reversibility gap, closed. **No atom splits; the grouping declines.**

    As spine/13 and plan/01 were written, S3 would have made an intra-document over-merge *permanent*: §4
    promises the cluster stays "a challengeable proposal", D-13.11 says atoms never split, and no document
    stated the mechanism by which a wrong grouping is undone. The referent atom is evidence ABOUT a grouping,
    never the address — so a conflict inside it de-groups to claim-atom granularity and raises.
    """
    claims = [
        entity("v_cn", "variant", "System-X", operator_branch="People's Liberation Army"),
        entity("v_pk", "variant", "System-X Export", operator_branch="Pakistan Air Force"),
        coref("System-X", "System-X Export", quote='System-X, also known as System-X Export, was seen.',
              referent="ref:d01-c1", gate="PASS", forms=("System-X", "System-X Export")),
    ]
    cfg = _cfg(attribute_roles={"variant": {"operator_branch": {"role": "critical"}}},
               critical_veto_min_grade="C")
    part = resolve(claims, cfg)

    assert not _same_cluster(part, "v_cn", "v_pk"), (
        "a grouping whose members state conflicting critical discriminators still bound (D-13.18)"
    )


def test_the_decline_reads_attr_history_not_the_first_wins_scalar() -> None:
    """The part that is **not obvious**, and without which the conflict is invisible.

    ``Entity.attrs`` is first-claim-wins (``setdefault``), so where one mention asserted two values only the
    first ever reaches the scalar and every detector reading it is blind to the second. Here both mentions
    agree on their *scalar* branch and disagree only in the retained series — which is precisely the shape
    ``attrs`` hides.
    """
    claims = [
        entity("v_a", "variant", "System-X", operator_branch="Pakistan Air Force"),
        # A second claim about the SAME entity asserting a different branch: `attrs` keeps the first, so only
        # `attr_history` records that this profile carries two incompatible operator readings.
        entity("v_a", "variant", "System-X", operator_branch="People's Liberation Army"),
        entity("v_b", "variant", "System-X Export", operator_branch="Pakistan Air Force"),
        coref("System-X", "System-X Export", quote='System-X, also known as System-X Export, was seen.',
              referent="ref:d01-c1", gate="PASS", forms=("System-X", "System-X Export")),
    ]
    cfg = _cfg(attribute_roles={"variant": {"operator_branch": {"role": "critical"}}},
               critical_veto_min_grade="C")
    part = resolve(claims, cfg)

    assert not _same_cluster(part, "v_a", "v_b"), (
        "the grouping bound even though a member's RETAINED values conflict — the decline is reading the "
        "first-wins scalar, where the losing value never appears (D-13.18)"
    )


def test_a_declined_grouping_still_reaches_the_analyst_with_the_licensing_evidence() -> None:
    """Declining is not discarding. The evidence the extractor read must still be readable by a human."""
    claims = [
        entity("v_cn", "variant", "System-X", operator_branch="People's Liberation Army"),
        entity("v_pk", "variant", "System-X Export", operator_branch="Pakistan Air Force"),
        coref("System-X", "System-X Export", quote='System-X, also known as System-X Export, was seen.',
              referent="ref:d01-c1", gate="PASS", forms=("System-X", "System-X Export")),
    ]
    cfg = _cfg(attribute_roles={"variant": {"operator_branch": {"role": "critical"}}},
               critical_veto_min_grade="C")
    part = resolve(claims, cfg)
    reasons = " ".join(part.candidate_reasons.values())

    assert "also known as" in reasons or "operator_branch" in reasons, (
        f"a declined grouping left the analyst nothing to read: {reasons!r}"
    )


# ── the licensing evidence, finally surfaced ───────────────────────────────────────────────────────

def test_a_raised_link_carries_its_verbatim_spans_and_the_gate_s_own_words() -> None:
    """The mitigation that makes raise-only acceptable — and which was fictional until now.

    Every justification of raise-only says "the analyst is handed the exact sentence"; the quote was stamped on
    the claim and read nowhere. With the gates in place this queue is load-bearing, not a fallback, so the
    reason must carry *what the document said*, *what kind of reading it was*, and *why the system would not
    act on it alone*.
    """
    part = resolve(_pair(gate="FAIL", quote=MARKER_QUOTE), _cfg())
    reason = part.candidate_reasons.get("m_long|m_short", "")

    assert "also known as CPMIEC" in reason, f"the licensing span is not surfaced: {reason!r}"
    assert "EXPLICIT_EQUIVALENCE" in reason, "the analyst is not told which kind of reading this was"
    assert "grade" in reason, "the analyst is not told how good the asserting source is"


# ── C9: document-scoped in EFFECT, not only in licence ────────────────────────────────────────────

def test_a_bind_cannot_reach_an_entity_the_contributing_document_never_attested() -> None:
    """C9. The precondition was document-scoped; the effect went through GLOBAL name/alias expansion.

    A third profile carrying the same short name, built entirely from another document, must not be swept into
    a bind licensed by this one — the licence said "this document's discourse", and the effect has to say the
    same thing.
    """
    claims = [
        *_pair(),
        # Same surface form, different document. `_matching_eids` would return it; C9 must not.
        entity("m_other", "manufacturer", "CPMIEC", source="src-other"),
    ]
    # Give the outsider its own doc_ref so the two documents are genuinely distinct.
    claims[-1] = claims[-1].model_copy(
        update={"doc_ref": claims[-1].doc_ref.model_copy(update={"file": "other.txt"})}
    )
    part = resolve(claims, _cfg())

    assert not _same_cluster(part, "m_long", "m_other"), (
        "a bind licensed by one document fused a profile attested only in another — the document-scoped "
        "precondition did not bound the effect (C9)"
    )


# ── D-13.19: the contrast lane is a CEILING, not a veto ───────────────────────────────────────────

def test_a_same_document_stated_contrast_caps_the_pair_and_never_walls_it() -> None:
    """A ceiling withholds one new fusion; a veto shatters a cluster. **Every ORBAT list is an enumeration.**

    Routing an enumeration through the hard, transitive, ungraded stated-``distinct-from`` rail would let one
    planted document — "the 8th AD Bn and the separate 12th AD Bn" — destroy a well-corroborated cluster. On
    its own lane the same evidence reaches the analyst with its quote and can never auto-merge. That is also
    why it is deliberately **ungraded**: a ceiling cannot shatter anything, so the harm a grade gate would
    have defended against does not exist.
    """
    claims = [
        entity("u_a", "unit", "8th AD Battalion", service_branch="Air Force"),
        entity("u_b", "unit", "8th AD Battalion Unit", service_branch="Air Force"),
        entity("site_a", "basing_site", "Alpha Field"),
        triple("u_a", "based-at", "site_a"),
        triple("u_b", "based-at", "site_a"),
        coref("8th AD Battalion", "8th AD Battalion Unit",
              quote="the 8th AD Bn and the separate 8th AD Battalion Unit"),
    ]
    contrast = claims[-1].model_copy()
    contrast.payload.predicate = "coref-distinct-from"
    claims[-1] = contrast
    cfg = _cfg(attribute_roles={"unit": {"service_branch": {"role": "supporting", "time_role": "durable"}}})
    part = resolve(claims, cfg)

    assert not _same_cluster(part, "u_a", "u_b"), (
        "a stated same-document contrast did not stop the auto-merge (D-13.19)"
    )
    assert ("u_a", "u_b") not in part.distinct_from, (
        "the contrast landed as a hard do-not-merge — that is the rail this design deliberately refuses, "
        "because every order of battle contains an enumeration"
    )
    assert "DISTINGUISHES" in " ".join(part.candidate_reasons.values()), (
        "the contrast is invisible to the analyst, so the quote that would let them judge it is unreadable"
    )


def test_absence_of_a_contrast_is_neutral_never_a_prior_for_merging() -> None:
    """The doctrine the anaphor gate's original formulation broke: absence is not evidence, in EITHER direction.

    The same claims minus the contrast must merge on their own merits — the ceiling is the *presence* of stated
    contrast doing work, not its absence granting a licence.
    """
    claims = [
        entity("u_a", "unit", "8th AD Battalion", service_branch="Air Force"),
        entity("u_b", "unit", "8th AD Battalion Unit", service_branch="Air Force"),
        entity("site_a", "basing_site", "Alpha Field"),
        triple("u_a", "based-at", "site_a"),
        triple("u_b", "based-at", "site_a"),
    ]
    cfg = _cfg(attribute_roles={"unit": {"service_branch": {"role": "supporting", "time_role": "durable"}}})
    part = resolve(claims, cfg)

    assert _same_cluster(part, "u_a", "u_b"), (
        "without any stated contrast the pair still did not merge — the ceiling is firing on absence, which "
        "makes it a prior rather than evidence"
    )


# ── flag-off ──────────────────────────────────────────────────────────────────────────────────────

def test_the_gate_and_the_grade_floor_are_not_flag_gated() -> None:
    """A bind is licensed by **evidence**, never by which stage is switched on.

    This assertion was inverted when I wrote it: it asserted that with the stage flag off a failing gate and a
    below-floor source could still bind, on the reasoning that flag-off must reproduce pre-S3 behaviour
    exactly. That reasoning was wrong, and the independent suite is what exposed it — the deciding input was an
    artifact only the *producer* could write, so a holder of a config bundle could not turn the policy on at
    all, and D-13.17's "structural check any reader can re-derive" was not being re-derived by anyone.

    The correct boundary: **the gate and the floor are properties of the pair** and always apply; the stage
    flag governs the caps, the walls and the decline — the things that change what an already-licensed signal
    is allowed to do. So an ungated or under-graded link never binds, flag or no flag.
    """
    off = mk_config(coref_authoritative_evidence=["EXPLICIT_EQUIVALENCE"],
                    source_reliability_grades={"src-low": "E"},
                    name_alone_caps_at_possible=True)
    assert ResolveConfig.from_bundle(off).earned_identity_on is False
    part = resolve(_pair(gate="FAIL", source="src-low"), off)

    assert not _merged(part), (
        "a link whose gate failed bound because the stage flag was off — 'is this licensed?' must never "
        "depend on which stage is enabled, or the licence is not a licence"
    )
