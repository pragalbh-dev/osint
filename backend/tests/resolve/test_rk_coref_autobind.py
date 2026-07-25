"""RK-COREF (S3) — D-13.17's auto-bind policy: what a coreference cluster may and may not *fuse*.

Authored from the session spec alone (`artifacts/plan/sessions/RK-COREF.md` scope 2 + item 7), never from
the implementation.

**Why a bind is the sharpest thing in the substrate.** §7 RK-COREF 2: "an authoritative pair is a
**Phase-1 bootstrap trigger** — it merges at hardcoded ``1.0`` and **bypasses banding entirely**, so no cap
restrains it, and today a coref bind reads **no grade at all** while a source-stated ``same-as`` is
grade-floored *and* raise-only. That inversion is the sharpest gap in the substrate."

The policy asserted here (`rk-spike-DECISIONS.md` (a)):

| category | verdict | gates |
|---|---|---|
| ``EXPLICIT_EQUIVALENCE`` | authoritative | deterministic gate **and** grade gate |
| ``UNAMBIGUOUS_ANAPHOR``  | authoritative **iff** the positive gate is built, else raise-only | both |
| ``NAME_VARIANT``         | "raise-only, permanently" | — |

Every prohibition here has its mirror: a suite that only tests refusal tests timidity. "Raise-only produces
a **``probable`` HITL candidate with the merge one click away**" (REVIEW-VERDICT §5), so the *positive*
assertion is that a well-licensed, well-sourced bind still fuses.
"""

from __future__ import annotations

import pytest

from chanakya.ingest import coref as coref_module
from tests import _rk_coref as rc

MARKER_QUOTE = "Alpha Precision Machinery (APM)"
BARE_QUOTE = "Alpha Precision Machinery and APM both shipped in March"


def _pair(sid: str = "hi", *, doc: str = "d1") -> list:
    return [
        rc.ent("m1", "manufacturer", "Alpha Precision Machinery", doc=doc, sid=sid),
        rc.ent("m2", "manufacturer", "APM", doc=doc, sid=sid),
    ]


def _opted(*categories: str):
    """The consumer switch, set to exactly the categories under test.

    Read, not re-typed: everything else in the block is the **shipped** resolution config, because "nearly
    every knob this stage adds" lives there (§7 RK-COREF owned paths) and a re-typed block cannot see a
    knob S3 declares.
    """
    return rc.with_resolution(rc.bundle(), coref_authoritative_evidence=list(categories))


# ── the grade floor (D-13.17's "Grade gate ✔", and it is not optional) ───────────────────────────

def test_a_low_grade_in_document_alias_does_not_bind() -> None:
    """§7 RK-COREF 2: "each behind **both** a deterministic gate **and** a source-grade floor".

    "Why the grade floor is not optional: an authoritative pair is a Phase-1 bootstrap trigger — it merges
    at hardcoded 1.0 and bypasses banding entirely, so no cap restrains it."
    """
    part = rc.part_of(
        [*_pair("lo"), rc.coref("m1", "m2", sid="lo", quote=MARKER_QUOTE)],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "m1", "m2"), (
        "a grade-E source's in-document alias FUSED two manufacturers at confidence 1.0. An authoritative "
        "bind bypasses banding, so the grade floor is the only thing restraining it — and a stated "
        "`same-as` from the same source would be grade-floored AND raise-only. That inversion is what "
        f"D-13.17's grade gate closes. Partition: same_as={part.same_as}"
    )


def test_a_low_grade_bind_still_reaches_the_analyst() -> None:
    """The mirror of the floor: refusing to *fuse* is not refusing to *report*.

    REVIEW-VERDICT §5: raise-only "produces a ``probable`` HITL candidate with the merge one click away".
    A floor that silently dropped the pair would delete evidence, which is the opposite of the point —
    "Demotion, not silent deletion, is the point — the evidence still reaches a human."
    """
    part = rc.part_of(
        [*_pair("lo"), rc.coref("m1", "m2", sid="lo", quote=MARKER_QUOTE)],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert rc.status(part, "m1", "m2") is not None, (
        "the below-floor bind vanished: it neither fused nor reached the analyst as a candidate/possible "
        "link. A grade floor demotes a bind to raise-only; it never deletes the extractor's reading of the "
        f"document. candidates={part.candidates} possible={part.possible}"
    )


def test_the_same_sentence_from_a_good_source_does_bind() -> None:
    """The mirror that stops the floor being set to "never".

    D-13.17 makes ``EXPLICIT_EQUIVALENCE`` **authoritative** — "the document literally *states* the
    identity"; the grade gate is a floor, not a veto. If this fails, the implementation has converted a
    graded path into a refusal, which is the over-correction §5b's rejected-whitelist note names:
    "D-13.9 says the opposite in terms: confirmed identity is reached by a **graded** path".
    """
    part = rc.part_of(
        [*_pair("hi"), rc.coref("m1", "m2", sid="hi", quote=MARKER_QUOTE)],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert rc.fused(part, "m1", "m2"), (
        "a grade-A source's parenthetical alias — 'Alpha Precision Machinery (APM)', textbook "
        "EXPLICIT_EQUIVALENCE — did NOT bind. D-13.17 grades this category authoritative; the floor is a "
        f"floor, not a veto. status={rc.status(part, 'm1', 'm2')} same_as={part.same_as}"
    )


# ── the deterministic gate (quote must carry both forms + a configured marker) ───────────────────

def test_a_quote_that_names_both_forms_without_an_equivalence_marker_does_not_bind() -> None:
    """D-13.17's deterministic gate for ``EXPLICIT_EQUIVALENCE``, third clause: the quote must contain
    "a **configured equivalence marker** (a parenthetical wrapping one form, or a term from a config list)".

    Two names in one sentence is co-occurrence, not a stated identity. C5 adds: "Also declare the seed
    equivalence-marker vocabulary in config, including verb forms."
    """
    part = rc.part_of(
        [*_pair("hi"), rc.coref("m1", "m2", sid="hi", quote=BARE_QUOTE)],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "m1", "m2"), (
        f"a bind fused on {BARE_QUOTE!r} — a sentence that merely mentions both names, with no "
        "parenthetical and no equivalence marker. Co-occurrence is not a stated equivalence, and this is "
        "the lane an extractor mislabel walks straight through (D-13.17 gate clause 3)."
    )


def test_a_quote_that_does_not_name_the_member_does_not_bind() -> None:
    """D-13.17: the quote must "contain **both** members' surface forms"."""
    part = rc.part_of(
        [
            rc.ent("m1", "manufacturer", "Alpha Precision Machinery"),
            rc.ent("m3", "manufacturer", "Beta Metalworks"),
            rc.coref("m1", "m3", quote=MARKER_QUOTE),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "m1", "m3"), (
        f"'Beta Metalworks' was fused into 'Alpha Precision Machinery' on the quote {MARKER_QUOTE!r}, "
        "which names neither of its surface forms. The licensing span is the whole basis of the category; "
        "a span that does not mention the member licenses nothing."
    )


# ── M1: the fourth conjunct — a MARK is not an alias, however the sentence is phrased ────────────

MIN_LEN = rc.descriptor_min_len()
MARK = "B"                  # a mark: shorter than the configured descriptor length
WORD = "engagement"         # a word: at or above it


def test_the_fixture_reads_the_shipped_mark_vs_word_threshold() -> None:
    """M1: "Reuse the shipped knob; do **not** introduce a second threshold for the same idea (G6)."

    The two fixtures below are only meaningful relative to the *declared* length, so the test states its
    dependence on config rather than assuming 3 — the S2 lesson about hand-copied knobs.
    """
    assert len(MARK) < MIN_LEN <= len(WORD), (
        f"containment_min_descriptor_len={MIN_LEN} no longer separates the fixture's mark ({MARK!r}, "
        f"len {len(MARK)}) from its word ({WORD!r}, len {len(WORD)}); the M1 pair below would test nothing"
    )


def test_a_mark_only_difference_is_not_a_licensed_equivalence() -> None:
    """M1: "If the longer surface form differs from the shorter only by a **mark** (a short token below the
    configured descriptor length), the equivalence is **not licensed**, regardless of how the sentence is
    phrased, and the pair goes raise-only with its quote."

    The quote below passes every other conjunct — verbatim, both surface forms, a parenthetical marker, a
    grade-A source — which is exactly why this is the one place the gate can go green on something false:
    "``<Design> (<Design>/X)`` reads exactly like an alias declaration but actually distinguishes two
    variants", and "a marker vocabulary built as a token list cannot catch it".
    """
    short, long_ = "TX-5", f"TX-5/{MARK}"
    part = rc.part_of(
        [
            rc.ent("v_short", "variant", short),
            rc.ent("v_long", "variant", long_),
            rc.coref("v_short", "v_long", quote=f"the {short} ({long_}) family"),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "v_short", "v_long"), (
        f"{short!r} and {long_!r} were fused at confidence 1.0 on a parenthetical. The longer form adds "
        f"only the mark {MARK!r} (below containment_min_descriptor_len={MIN_LEN}), so the sentence "
        "distinguishes two variants of one design rather than declaring an alias — and neither the grade "
        "floor (a good source can write it) nor the D-13.18 decline (two marks often conflict on nothing) "
        f"catches it. same_as={part.same_as}"
    )
    assert rc.status(part, "v_short", "v_long") == "probable", (
        f"the mislabelled equivalence reads {rc.status(part, 'v_short', 'v_long')!r} — M1 sends it "
        "raise-only *with its quote*, so the analyst sees the sentence and decides."
    )


def test_a_word_extension_still_licenses_the_equivalence() -> None:
    """The mirror M1 explicitly requires: "a longer form that adds a real **word** ('… engagement radar')
    *is* the same thing described more fully and must still license."

    The shipped knob's own comment is the specification: "'HT-233' + 'engagement' (a **WORD**) is the same
    radar described more fully; 'HQ-9' + 'P' (a **MARK**) is a different missile."
    """
    short, long_ = "RX-9", f"RX-9 {WORD} radar"
    part = rc.part_of(
        [
            rc.ent("c_short", "component", short),
            rc.ent("c_long", "component", long_),
            rc.coref("c_short", "c_long", quote=f"the {short} ({long_})"),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert rc.fused(part, "c_short", "c_long"), (
        f"{short!r} and {long_!r} did not bind. The added token {WORD!r} is a descriptive word at or above "
        f"the configured length {MIN_LEN}, i.e. one thing described more fully. A fourth conjunct that "
        "refuses this has become a blanket refusal of the category. "
        f"status={rc.status(part, 'c_short', 'c_long')}"
    )


# ── M2: licensing evidence is a SET of verbatim spans from ONE document ──────────────────────────

SPAN_A = "the consignee was Alpha Precision Machinery"
SPAN_B = "shipping agent: APM (Alpha Precision Machinery)"


def test_two_spans_from_one_document_license_the_bind() -> None:
    """M2: "licensing evidence is a set of verbatim spans from the same document, which together must
    contain both surface forms and the marker."

    The corpus finding that forces it: equivalences a document genuinely asserts "whose two surface forms
    sit **18–58 lines apart, or in different fields of one record** — so **no single span can contain
    both**." A one-span rule "would withhold on equivalences documents really do state".
    """
    part = rc.part_of(
        [
            *_pair("hi", doc="d1"),
            rc.coref_spans("m1", "m2", quotes=[SPAN_A, SPAN_B], docs=["d1", "d1"]),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert rc.fused(part, "m1", "m2"), (
        "a document that states its equivalence across two fields of one record did not license the bind. "
        "'A document that states an equivalence across two fields **has stated it**' — the contiguous-span "
        "requirement was 'an artifact of how the check was first imagined, not a principle'. "
        f"status={rc.status(part, 'm1', 'm2')}"
    )


def test_spans_from_two_different_documents_do_not_license() -> None:
    """The negative M2 names: spans must come from the **same** document.

    Both entities are attested in ``d1``, so C9's document-scoping is satisfied and cannot be what refuses
    this — the only thing that can is the same-document requirement on the span *set*. Stitching two
    documents' sentences together is cross-document identity, "which the extractor never decides".
    """
    part = rc.part_of(
        [
            *_pair("hi", doc="d1"),
            rc.coref_spans("m1", "m2", quotes=[SPAN_A, SPAN_B], docs=["d1", "d2"]),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "m1", "m2"), (
        "a bind was licensed by one span from d1 and one from d2. No single document stated this "
        "equivalence; assembling it across documents is a cross-document identity decision, which belongs "
        f"to Tier 1 and the analyst, not to the extractor's reading of one document. same_as={part.same_as}"
    )


def test_multiple_spans_do_not_relax_the_grade_floor() -> None:
    """M2: "**What does not change:** the grade floor … Multiple spans make the evidence *findable*, not
    *stronger*."
    """
    part = rc.part_of(
        [
            *_pair("lo", doc="d1"),
            rc.coref_spans("m1", "m2", quotes=[SPAN_A, SPAN_B], docs=["d1", "d1"], sid="lo"),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "m1", "m2"), (
        "two spans from a grade-E document bound where one span would not have. Span count is not evidence "
        f"quality. same_as={part.same_as}"
    )


def test_multiple_spans_do_not_relax_the_mark_test() -> None:
    """M2: "the mark-vs-word conjunct (M1) … still appl[ies]" — the two rulings compose rather than trade."""
    short, long_ = "TX-5", f"TX-5/{MARK}"
    part = rc.part_of(
        [
            rc.ent("v_short", "variant", short, doc="d1"),
            rc.ent("v_long", "variant", long_, doc="d1"),
            rc.coref_spans("v_short", "v_long",
                           quotes=[f"the {short} entered service", f"the {long_} followed"],
                           docs=["d1", "d1"]),
        ],
        _opted(rc.EXPLICIT_EQUIVALENCE),
    )

    assert not rc.fused(part, "v_short", "v_long"), (
        f"a two-span set bound {short!r} to {long_!r}, which differ only by the mark {MARK!r}. More spans "
        f"make an equivalence easier to find, not truer. same_as={part.same_as}"
    )


def test_every_span_in_the_set_must_occur_verbatim() -> None:
    """M2: "Each span must still occur verbatim, so the whole point is preserved — **any reader can
    re-derive the bind**."

    Asserted at the producer, because that is where the document text exists (``_quote_supported`` checks a
    span against the assembled text). Written as a differential so it cannot pass by rejecting *both*: a
    set whose spans are all present must be accepted, and one carrying a fabricated span must not.
    """
    text = f"{SPAN_A}.\n\n… eighteen lines later …\n\n{SPAN_B}."
    mentions = [
        coref_module.Mention(1, "Alpha Precision Machinery", "manufacturer", "c-1"),
        coref_module.Mention(2, "APM", "manufacturer", "c-2"),
    ]

    def _accepted(spans: list[str]) -> list:
        raw = {"clusters": [{
            "member_ids": [1, 2],
            "evidence": rc.EXPLICIT_EQUIVALENCE,
            "licensing_quote": list(spans),
            "licensing_quotes": list(spans),
        }]}
        return coref_module.valid_clusters(raw, mentions, text, [])

    assert _accepted([SPAN_A, SPAN_B]), (
        "a span set whose every member occurs verbatim in the document was rejected, so the M2 form is not "
        "accepted at all and the negative below is vacuous"
    )
    assert not _accepted([SPAN_A, "APM is a subsidiary of Alpha Precision Machinery"]), (
        "a span set containing a sentence the document never contains was accepted. The verbatim check is "
        "what makes the bind re-derivable by any reader; a set is not a licence to paraphrase."
    )


# ── C5: the gate is per LINK, so a bind is PARTIAL, never all-or-nothing ─────────────────────────

def test_a_cluster_binds_over_its_passing_link_and_not_its_failing_one() -> None:
    """C5: "the gate is evaluated per **link** (anchor→member); a cluster binds only over passing links,
    each failing link becoming an injected Tier-1 candidate pair. A **partial** bind, not all-or-nothing."
    """
    claims = [
        rc.ent("m1", "manufacturer", "Alpha Precision Machinery"),
        rc.ent("m2", "manufacturer", "APM"),
        rc.ent("m3", "manufacturer", "Beta Metalworks"),
        rc.coref("m1", "m2", quote=MARKER_QUOTE, cid="k-good", cluster="c1"),
        rc.coref("m1", "m3", quote=MARKER_QUOTE, cid="k-bad", cluster="c1"),
    ]
    part = rc.part_of(claims, _opted(rc.EXPLICIT_EQUIVALENCE))

    assert rc.fused(part, "m1", "m2"), (
        "the well-licensed link of the cluster did not bind — C5 refuses the all-or-nothing reading in "
        "*both* directions: 'it neither discards a well-licensed link nor lets one bad link license the "
        f"rest'. same_as={part.same_as}"
    )
    assert not rc.fused(part, "m1", "m3"), (
        "the failing link bound anyway: one member's licensing span was reused to fuse a mention it never "
        "names. That is the 'one bad link licenses the rest' half of C5."
    )
    assert rc.status(part, "m1", "m3") is not None, (
        "the failing link vanished instead of becoming a Tier-1 candidate pair. C5: 'each failing link "
        f"becoming an injected Tier-1 candidate pair'. candidates={part.candidates} possible={part.possible}"
    )


# ── NAME_VARIANT: raise-only permanently, even when the operator opts it in ──────────────────────

def test_name_variant_never_binds_even_when_configured() -> None:
    """D-13.17: ``NAME_VARIANT`` is "**raise-only, permanently**" — and the reason is mechanical, not
    cautious: "Because an authoritative pair bypasses banding and fuses at 1.0, 'authoritative
    NAME_VARIANT' *is* the exact-normalized-name auto-merge lane that D-13.1 exists to delete — rebuilt on
    a different predicate, and immune to the very cap (name-alone ⇒ *possible*) that D-13.10 introduces."

    So the prohibition binds the **code**, not the config: a deployment that lists the category must not
    thereby get the name lane back. This is deliberately a config-can't-override test.
    """
    part = rc.part_of(
        [
            rc.ent("n1", "manufacturer", "Sino Galaxy"),
            rc.ent("n2", "manufacturer", "SINO-GALAXY"),
            rc.coref("n1", "n2", evidence=rc.NAME_VARIANT, quote="SINO-GALAXY Trading Co"),
        ],
        _opted(rc.NAME_VARIANT, rc.EXPLICIT_EQUIVALENCE, rc.UNAMBIGUOUS_ANAPHOR),
    )

    assert not rc.fused(part, "n1", "n2"), (
        "NAME_VARIANT bound because the config listed it. That rebuilds the exact-normalized-name "
        "auto-merge lane on the coref predicate, immune to D-13.10's name cap — 'the one call all three "
        f"positions converged on'. same_as={part.same_as}"
    )
    assert rc.status(part, "n1", "n2") == "probable", (
        "a NAME_VARIANT cluster must land in the analyst's queue with its quote (raise-only), not be "
        f"dropped. status={rc.status(part, 'n1', 'n2')}"
    )


def test_the_shipped_config_never_opts_name_variant_in() -> None:
    """The same rule at the config surface — "raise-only **permanently**"."""
    assert rc.NAME_VARIANT not in rc.coref_authoritative(), (
        f"config/resolution.yaml lists {rc.NAME_VARIANT} in coref_authoritative_evidence "
        f"({rc.coref_authoritative()}). D-13.17 makes it permanently raise-only."
    )


# ── the anaphor gate must be POSITIVE (REVIEW-VERDICT §5) ────────────────────────────────────────

ANAPHOR = "the export agency"
ANAPHOR_ID = rc.endpoint_id("manufacturer", ANAPHOR)
ANAPHOR_QUOTE = f"{ANAPHOR} signed the March contract"


def _anaphor(*extra) -> list:
    """A declared antecedent plus an elliptical reference that reaches the graph as a bare endpoint.

    That is the shape the code facts report as dominant: "on the real corpus that is the common shape (both
    ``CPMIEC`` and its full expansion reach the graph only as relation endpoints)".
    """
    return [
        rc.ent("m1", "manufacturer", "Alpha Precision Machinery"),
        rc.ent("v", "variant", "HQ-X"),
        rc.rel("r-man", ANAPHOR, "manufactures", "v"),
        *extra,
        rc.coref("m1", ANAPHOR, evidence=rc.UNAMBIGUOUS_ANAPHOR, quote=ANAPHOR_QUOTE),
    ]


def test_a_second_type_compatible_mention_fails_the_anaphor_gate() -> None:
    """REVIEW-VERDICT §5 closure: "require a named, declared, ontology-typed antecedent, exactly one
    type-compatible mention".

    With two candidate antecedents the anaphor is genuinely ambiguous, and the prompt itself says so: "A
    descriptor that could refer to more than one introduced mention of that type — leave every such mention
    a singleton; a human will resolve it."
    """
    part = rc.part_of(_anaphor(rc.ent("m2", "manufacturer", "Beta Metalworks")),
                      _opted(rc.UNAMBIGUOUS_ANAPHOR))

    assert not rc.fused(part, "m1", ANAPHOR_ID), (
        "'the export agency' was bound to one of TWO declared manufacturers in the same document. The "
        "category's own licensing condition is that there is no second mention of that type it could "
        f"mean. same_as={part.same_as}"
    )


def test_an_unknown_typed_second_mention_also_fails_the_gate() -> None:
    """The under-reach case, and the one an *absence* test cannot see.

    REVIEW-VERDICT §5: the old gate "fails open … under-extraction makes the gate PASS — its failure mode
    is *anti-correlated with safety*". The closure therefore counts an under-typed mention: "exactly one
    type-compatible mention **where ``unknown``-typed endpoints COUNT as compatible** (so any second
    undeclared endpoint fails the gate)".
    """
    part = rc.part_of(
        _anaphor(rc.rel("r-man2", "the supplier", "manufactures", "v")),
        _opted(rc.UNAMBIGUOUS_ANAPHOR),
    )

    assert not rc.fused(part, "m1", ANAPHOR_ID), (
        "a second undeclared endpoint ('the supplier') did not fail the gate, so an extractor that "
        "under-declares its mentions *widens* the strongest fusion path in the system. This is the "
        f"fails-open direction the positive reformulation exists to close. same_as={part.same_as}"
    )


def test_an_anaphor_with_no_named_antecedent_never_binds() -> None:
    """"require a **named, declared, ontology-typed** antecedent" — two elliptical references are not one.

    Neither side is a name, so nothing in the document says *which* entity the pair is; binding them
    manufactures an entity out of two descriptions.
    """
    part = rc.part_of(
        [
            rc.ent("a1", rc.UNKNOWN_TYPE, "the export agency"),
            rc.ent("a2", rc.UNKNOWN_TYPE, "the company"),
            rc.coref("a1", "a2", evidence=rc.UNAMBIGUOUS_ANAPHOR, quote="the company"),
        ],
        _opted(rc.UNAMBIGUOUS_ANAPHOR),
    )

    assert not rc.fused(part, "a1", "a2"), (
        "two undeclared, untyped descriptions were fused into one entity by an anaphor bind. The positive "
        "gate requires a named, declared, ontology-typed antecedent — there is none here."
    )


def test_the_anaphor_category_and_the_shipped_config_agree() -> None:
    """The three-way fork, stated explicitly rather than defaulted into (the S2 lesson).

    "**If the positive gate is not built, ``UNAMBIGUOUS_ANAPHOR`` reverts to raise-only.**" So there are
    exactly two coherent shipped states, and the test discriminates on the config rather than assuming:

    * opted in ⇒ the unambiguous case must actually **bind** (otherwise lever 1 — "the *biggest*
      fragmentation lever" — is forfeited while the config claims it);
    * not opted in ⇒ no anaphor cluster may fuse, ever.
    """
    part = rc.part_of(_anaphor(), _opted(*rc.coref_authoritative()))
    opted_in = rc.UNAMBIGUOUS_ANAPHOR in rc.coref_authoritative()
    bound = rc.fused(part, "m1", ANAPHOR_ID)

    assert bound == opted_in, (
        f"config/resolution.yaml {'opts in' if opted_in else 'does NOT opt in'} to "
        f"{rc.UNAMBIGUOUS_ANAPHOR} (coref_authoritative_evidence={rc.coref_authoritative()}), but an "
        f"unambiguous single-antecedent anaphor {'did not bind' if opted_in else 'bound anyway'}. "
        "D-13.17's conditional is 'the gate IS the decision': either the positive gate is built and the "
        "category binds, or the category is raise-only — never a config that claims one and does the other."
    )
    assert rc.status(part, "m1", ANAPHOR_ID) is not None or bound, (
        "the anaphor pair neither bound nor reached the analyst — raise-only means queued, not discarded."
    )


# ── C9: a bind is document-scoped in EFFECT, not merely in licence ───────────────────────────────

def test_a_bind_never_instantiates_over_another_documents_homonym() -> None:
    """C9: "an authoritative coref pair may only instantiate over entity ids **attested in the
    contributing document**."

    "D-13.17 gates the bind on a *document-scoped* precondition, but the bind instantiates through
    ``_matching_eids``' **global** name/alias expansion — so the precondition does not bound the effect."
    """
    claims = [
        *_pair("hi", doc="d1"),
        rc.ent("m_other", "manufacturer", "APM", doc="d2", sid="hi"),
        rc.coref("m1", "m2", doc="d1", quote=MARKER_QUOTE),
    ]
    part = rc.part_of(claims, _opted(rc.EXPLICIT_EQUIVALENCE))

    assert rc.fused(part, "m1", "m2"), (
        "the in-document bind itself did not fire, so the leak assertion below is vacuous "
        f"(same_as={part.same_as})"
    )
    assert not rc.fused(part, "m1", "m_other"), (
        "a second document's homonymous 'APM' was swept into the bind through global name expansion. C9: "
        "a document's authority extends to its own referents only — d1 said nothing whatever about d2's "
        f"company. same_as={part.same_as}"
    )


def test_the_doc_id_carrier_exists() -> None:
    """C9 + decision (b) share one carrier: "``Entity.doc_ids: frozenset[str]`` … one field, one population
    site", populated "from ``c.doc_refs()``" — explicitly **not** by parsing a claim-id and **not**
    ``source_ids`` ("``source_id`` is the *publisher*").

    C9: "(a) must not ship without it."
    """
    from chanakya.resolve import entities as rentities

    fields = set(rentities.Entity.__dataclass_fields__)
    doc_fields = sorted(f for f in fields if "doc" in f)
    assert doc_fields, (
        "resolve.entities.Entity declares no document field. There is no document dimension anywhere "
        f"downstream (code facts D6), so C9's scoping and (b)'s same-doc contrast have no carrier. "
        f"Declared fields: {sorted(fields)}"
    )

    claims = [
        rc.ent("x1", "manufacturer", "Alpha", doc="dA"),
        rc.ent("x1", "manufacturer", "Alpha", doc="dB", cid="c-dB-x1-second"),
    ]
    graph = rentities.build(claims)
    carried = {str(v) for f in doc_fields for v in (getattr(graph.entities["x1"], f) or [])}
    assert any("dA" in c for c in carried) and any("dB" in c for c in carried), (
        f"the document carrier on an entity claimed by two documents holds {carried!r} — it must name both "
        "contributing documents, or a doc-local contrast leaks onto cross-doc pairs and the bake-off "
        "cannot measure over/under-binding at all."
    )


# ── C10: a single source may license a relocation only over its own authoritative co-reference ───

def test_a_bare_single_member_instance_does_not_license_a_relocation() -> None:
    """C10: "a relocation may be drawn from one source only when that source authoritatively co-refers its
    own mentions **and** clears the authoritative-bind grade floor; a bare single-member instance never
    licenses one."

    Here one low-grade source states both ends and co-refers nothing: the two mentions must not become one
    unit whose two sites are a before/after.
    """
    claims = [
        rc.ent("u1", "unit", "air defence battery", doc="d1", sid="lo"),
        rc.ent("u2", "unit", "air defence battery", doc="d1", sid="lo"),
        rc.site("s_old", "Bravo Depot", doc="d1", sid="lo"),
        rc.site("s_new", "Charlie Cantonment", lat=32.0, lon=72.6, doc="d1", sid="lo"),
        rc.rel("r-ba-1", "u1", "based-at", "s_old", doc="d1", iso="2021-01-01", sid="lo"),
        rc.rel("r-ba-2", "u2", "based-at", "s_new", doc="d1", iso="2025-01-01", sid="lo"),
        *rc.shared_neighbours("u1", "u2", doc_a="d1", doc_b="d1", sid_b="lo"),
    ]
    part = rc.part_of(claims, _opted(rc.EXPLICIT_EQUIVALENCE))

    assert not rc.fused(part, "u1", "u2"), (
        "one grade-E document's two unco-referenced mentions were fused, which makes their two sites one "
        "unit's before/after and licenses a relocation nobody stated. C10 requires the source to "
        f"*authoritatively co-refer its own mentions* and clear the grade floor. same_as={part.same_as}"
    )


@pytest.mark.parametrize("sid,should_bind", [("hi", True), ("lo", False)])
def test_a_relocation_needs_an_authoritative_co_reference_that_clears_the_floor(
    sid: str, should_bind: bool
) -> None:
    """The other half of C10, stated as the discriminating input: the *same* co-referring document binds
    only when its grade clears the floor. Two branches, one fixture — so neither can be tested by accident.
    """
    claims = [
        rc.ent("u1", "unit", "8th AD Battalion", doc="d1", sid=sid),
        rc.ent("u2", "unit", "the battalion", doc="d1", sid=sid),
        rc.site("s_old", "Bravo Depot", doc="d1", sid=sid),
        rc.site("s_new", "Charlie Cantonment", lat=32.0, lon=72.6, doc="d1", sid=sid),
        rc.rel("r-ba-1", "u1", "based-at", "s_old", doc="d1", iso="2021-01-01", sid=sid),
        rc.rel("r-ba-2", "u2", "based-at", "s_new", doc="d1", iso="2025-01-01", sid=sid),
        rc.coref("u1", "u2", doc="d1", sid=sid,
                 quote="the 8th AD Battalion (the battalion) moved in March"),
    ]
    part = rc.part_of(claims, _opted(rc.EXPLICIT_EQUIVALENCE))

    assert rc.fused(part, "u1", "u2") == should_bind, (
        f"a grade-{rc.GRADES[sid]} document that authoritatively co-refers its own two mentions "
        f"{'did not bind' if should_bind else 'bound anyway'}. C10 grants a source authority over its own "
        "referent — spine/13 §5 — but only above the authoritative-bind grade floor: 'a bare single-member "
        f"instance never licenses one'. same_as={part.same_as}"
    )
