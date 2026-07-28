"""A pair a CAP withheld is retained **with its reason** — "retained but never surfaced" is a quiet drop.

Two tiers can hold a pair the machinery refused to fuse, and they make opposite promises: ``candidates`` is
"the analyst must decide this" and ``possible`` is "retained, but it has not earned attention". Both are
legitimate. What is not legitimate is a pair whose *confidence and breakdown* are recorded while the **reason**
is thrown away — the analyst then gets a number with no grounds, or nothing at all.

That was measurably the case: ``candidate_reasons`` was written only on the ``hitl`` branch, so every pair
capped at the ``possible`` ceiling recorded its score and lost its rationale, and ``finalise`` then filtered
the reasons down to the candidate queue, deleting any that had survived. For a type whose only honest identity
signal is its name (``area_of_operations``, whose coordinates identify the *area* and never what is inside it)
the name cap is the common case rather than an edge case, so the common case was the silent one.

Corpus-independent throughout: abstract fixtures, no corpus document and no answer key.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import pair_key
from chanakya.view.coverage import identity_coverage
from tests.resolve._helpers import entity, mk_config, triple

#: The name cap, and nothing else — so a failure names the mechanism rather than the config.
EARNED = {"name_ceiling": "possible"}


def _cfg(**over):
    over.setdefault("possible_floor", 0.25)
    over.setdefault("hitl_low", 0.30)
    return mk_config(earned_identity={**EARNED, **over.pop("earned", {})}, **over)


def _name_only_areas():
    """Two areas of operations whose only agreement is what they are called.

    The type the cap bites hardest on: an area answers "roughly where", so it has no discriminator to state
    and no neighbourhood that means identity. A name match is all there ever is.
    """
    return [
        entity("aoo_north", "area_of_operations", "Northern Air Defence Sector"),
        entity("aoo_north_2", "area_of_operations", "Northern Air Defense Sector"),
    ]


def test_a_pair_capped_at_possible_is_retained_WITH_its_reason() -> None:
    part = resolve(_name_only_areas(), _cfg())
    key = pair_key("aoo_north", "aoo_north_2")

    assert ("aoo_north", "aoo_north_2") in part.possible, (
        "the capped pair was not retained at all — a cap is a decision about a pair the machinery had an "
        "opinion on, so dropping it discards the decision"
    )
    assert key in part.merge_confidence and key in part.merge_breakdown
    reason = part.candidate_reasons.get(key, "")
    assert "name-only identity" in reason, (
        f"the capped pair kept its score and lost its grounds: {reason!r}. The analyst gets a number and never "
        "the quote, which is 'retained but never surfaced' — a quiet drop with a confidence attached"
    )
    assert "clears the cap" in reason, "the reason must state what would LIFT the cap, not only that it fired"


def test_the_reason_survives_finalise() -> None:
    """``finalise`` filtered the reasons to the candidate queue, deleting the ones a cap had just written.

    A separate assertion from the one above because they fail differently: the writer can be right while the
    survival filter drops the row, and the pair then reaches the Partition retained and unexplained.
    """
    part = resolve(_name_only_areas(), _cfg())

    assert part.possible, "fixture drift: nothing was retained, so the filter is not under test"
    for a, b in part.possible:
        assert pair_key(a, b) in part.candidate_reasons, (
            f"the retained pair {a}/{b} reached the Partition with no reason — the survival filter kept the "
            "link and dropped the grounds a cap had just written for it"
        )


def test_a_capped_pair_is_retained_even_BELOW_the_possible_floor() -> None:
    """The floor is about scores; a cap is about a decision, and the two must not be confused.

    Letting a capped pair fall through ``possible_floor`` throws away the refusal *and* its reason on exactly
    the pairs where the cap did the most work — the weak-scoring ones it was written for.
    """
    part = resolve(_name_only_areas(), _cfg(possible_floor=0.99))

    assert ("aoo_north", "aoo_north_2") in part.possible, (
        "a capped pair fell through the possible floor: the cap's decision and its stated reason are both gone"
    )


def test_the_coverage_report_lists_the_withheld_links_with_their_reasons() -> None:
    """The retained tier is never drawn, so the coverage report is where a human can read it.

    ``IdentityCoverage`` already promises exactly this — residual fragmentation is a coverage gap "only if the
    reader can see WHICH refusals produced it" — and reported counts alone, which cannot distinguish missing
    collection from stated policy.
    """
    part = resolve(_name_only_areas(), _cfg())
    summary = identity_coverage(part, {"aoo_north": "area_of_operations",
                                       "aoo_north_2": "area_of_operations"})

    assert summary.possible == 1
    assert len(summary.withheld) == 1, (
        f"the withheld link is counted and not listed: {summary.withheld}. A count cannot tell an analyst "
        "whether the tail is a collection problem or a policy the system applied"
    )
    withheld = summary.withheld[0]
    assert {withheld.a, withheld.b} == {"aoo_north", "aoo_north_2"}
    assert "name-only identity" in withheld.reason
    assert withheld.confidence is not None


def test_an_ordinary_sub_review_link_is_listed_with_its_own_ground_and_no_invented_cap() -> None:
    """A merely low-scoring pair IS listed — and its ground says so, without claiming a cap that never fired.

    **Re-pointed 2026-07-26, and it asserts MORE than it did.** It used to require ``withheld == []`` for
    this pair, on the reasoning that nothing refused it so claiming a ground would over-claim. The first
    half of that is right and is still enforced below; the second half had a measured cost. ``withheld`` is
    the ONLY channel that carries the ``possible`` watch-list anywhere — it is not drawn on ``GET /view`` by
    design — so "no recorded reason" meant "reaches no surface at all": 24 of 355 retained pairs on the
    booted corpus were invisible to the analyst and byte-indistinguishable from pairs the resolver never
    scored. "No cap fired" is not a reason to disappear; it is itself the reason, and a perfectly good one.
    The pair is now listed with a ground derived from its own confidence against the configured bar, and
    the over-claim this test exists to prevent is checked directly: the ground must not assert a cap."""
    claims = [
        entity("unit_a", "unit", "Zulu"),
        entity("unit_b", "unit", "Kappa"),
        entity("comp_x", "component", "CX"),
        entity("comp_y", "component", "CY"),
        triple("unit_a", "fields", "comp_x"),
        triple("unit_a", "fields", "comp_y"),
        triple("unit_b", "fields", "comp_x"),
        triple("unit_b", "fields", "comp_y"),
    ]
    part = resolve(claims, mk_config(earned_identity=EARNED, possible_floor=0.25,
                                     relational_support_k=3))
    summary = identity_coverage(part, {"unit_a": "unit", "unit_b": "unit"})

    assert ("unit_a", "unit_b") in part.possible
    listed = [w for w in summary.withheld if {w.a, w.b} == {"unit_a", "unit_b"}]
    assert listed, (
        f"a merely low-scoring link reaches NO surface: withheld={summary.withheld}. GET /coverage is the "
        "only channel carrying the possible tier, so a pair omitted from it is invisible to the analyst — "
        "indistinguishable from one the resolver never scored. A cap may withhold ATTENTION, not the RECORD."
    )
    ground = listed[0].reason
    assert ground, "the pair is listed with an empty ground, which states nothing"
    assert not any(word in ground.lower() for word in ("capped at", "cap refused", "withheld by a cap")), (
        f"the ground claims a cap that never fired: {ground!r}. Nothing refused this pair — it simply "
        "scored short of the bar, and saying anything stronger over-claims the system's own decision."
    )
    assert "stopped short of the bar" in ground, (
        f"the ground does not state what actually happened to this pair: {ground!r}"
    )
