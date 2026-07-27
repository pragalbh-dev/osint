"""The identifier match policy, re-measured against the labeled gold on every run.

WHY THIS FILE EXISTS
────────────────────
The matcher's leniency IS the measurement, so the one knob that decides whether ``HT233`` counts as
``HT-233`` was deliberately deferred twice to the hand that owns the labeled gold, with a stated reason:
re-tuning the kernel moves every number the bake-off produces, and it must be settled against a labeled
sample rather than by whoever has just read the gold and is tempted to tune to it.

It was settled on 2026-07-25. The rule, and the costs, are written out in ``config/bakeoff.yaml`` →
``identifier_policy``. What is here is the *evidence*: the numbers in that note are not remembered, they are
re-derived from the labeled files below, so a later change to either the gold or the kernel moves this file
red instead of quietly re-baselining the decision.

THE TWO DIRECTIONS, and why both are asserted
─────────────────────────────────────────────
A matcher can be wrong two ways, and this project cares about both:

* too strict — a legitimately de-hyphenated designator reads as a MISS, which depresses recall for every
  candidate at once and adds variance to a comparison already fighting non-determinism;
* too lenient — two genuinely different designators (``HQ-9B`` and ``HQ-9BE``; two different GD numbers)
  read as the SAME claim, which is the over-merge the whole project exists to prevent.

The finding that decided the call is that the previous behaviour was wrong in **both** directions at once:
splitting an identifier into tokens made a real variant unmatchable *and* made two sibling variants score
0.91, because the tokens they share carry the pair. So the decision is not a leniency trade — it is tighter
and looser at the same time, on different pairs, and the assertions below pin each half.

RETIRED 2026-07-27 — the two slice-wide COUNTS
──────────────────────────────────────────────
Two tests stood here that re-counted the evidence base rather than asserting the rule:

* ``test_a_dehyphenated_designator_is_no_longer_a_miss`` — pinned 61 designator-bearing surfaces, 16 below
  the role floor and 24 below the pair floor under the prose kernel;
* ``test_the_slice_wide_over_merge_count_falls`` — pinned 30,371 cross pairs, 128 → 84 above the role floor
  and 30 → 9 on gold-labelled-different nodes.

The 2026-07-26 gold repair changed the surface universe itself (243 surfaces now, 29,393 cross pairs), so
every one of those numbers moved. They are *measurements of an evidence base*, not bookkeeping about the
fixture, and the first one's own failure message said to "re-measure both directions before trusting the
note's numbers" — so they are deleted rather than re-baselined, which would have laundered a changed
measurement as a repair. The numbers and the reasoning they supported are recorded in
``config/bakeoff.yaml`` → ``identifier_policy`` and in ``tmp/conv/RK-BAKEOFF-DIAGNOSIS.md``.

Both DIRECTIONS remain asserted here as *behaviour* — which is the part that decides whether the shipped
policy is right, and the part that does not rot with the census:

* direction 1 (too strict) by ``test_the_gold_own_two_spellings_of_one_designator_match``, on the slice's
  own two spellings of one designator;
* direction 2 (too lenient) by ``test_no_two_different_designators_are_conflated``, over the designator
  family, and by ``test_what_the_veto_costs_is_exactly_these_two_pairs``.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

import pytest

from eval.extraction.matcher import identifiers_agree, similarity
from eval.extraction.policy import load_bakeoff_config
from eval.extraction.surface import identifier_tokens, normalize_designator, normalize_surface

#: The shipped policy — the one that produced every number in the note. Read, never constructed, so this
#: file measures what the bake-off will actually run.
POLICY = load_bakeoff_config().match_policy
PROSE = POLICY.model_copy(update={"identifier_policy": "prose", "identifier_agreement": "ignore"})

ROLE_FLOOR = POLICY.role_min_similarity      # 0.70


def _matches(a: str, b: str, policy: Any) -> bool:
    """Would the matcher let these two role surfaces pair? (Veto first, then the floor.)"""
    return identifiers_agree(a, b, policy) and similarity(a, b, policy) >= ROLE_FLOOR


# ── the surface universe: every string the labeled slice calls a surface ───────────────────────────

def _role_surfaces(claim: dict[str, Any]) -> list[str]:
    if claim["form"] == "triple":
        vals = [claim.get("subject"), claim.get("object")]
    elif claim["form"] == "entity":
        vals = [claim.get("name")]
    else:
        vals = list(claim.get("participants") or [])
    return [str(v).strip() for v in vals if v and str(v).strip() not in ("", "-")]


@pytest.fixture(scope="module")
def surfaces(adapted: dict[str, Any], adapted_oracle: dict[str, Any]) -> list[str]:
    """Every distinct surface string in the labeled slice — claim roles, negative rows, coref mentions,
    oracle node names and their declared surface forms.

    Deliberately unpinned: the size of this universe moves whenever the gold is relabelled (247 at the
    2026-07-25 decision, 243 after the 2026-07-26 repair), and the tests that survive here assert the
    matcher's BEHAVIOUR on named pairs, which does not depend on how many surfaces there are."""
    out: dict[str, None] = {}
    def add(value: Any) -> None:
        text = str(value).strip()
        if text and text != "-":
            out.setdefault(text, None)
    for claim in adapted["claims"]:
        for surface in _role_surfaces(claim):
            add(surface)
    for block in adapted["negative_gold"].values():
        for row in block["rows"]:
            for surface in row["surfaces"]:
                add(surface)
    for cluster in adapted["coref_registry"]:
        for mention in cluster["mentions"]:
            add(mention["text"])
    for node in adapted_oracle["node_detail"]:
        add(node["name"])
        for surface in node["surface_forms"]:
            add(surface)
    return list(out)


@pytest.fixture(scope="module")
def node_of(adapted_oracle: dict[str, Any]) -> dict[str, set[str]]:
    """surface → the oracle node(s) that declare it. The gold's own same/different labelling."""
    out: dict[str, set[str]] = {}
    for node in adapted_oracle["node_detail"]:
        for surface in [node["name"], *node["surface_forms"]]:
            out.setdefault(str(surface).strip(), set()).add(node["id"])
    return out


def _squash(text: str) -> str:
    """The human test for 'the same string': identical once all punctuation and space is deleted."""
    return re.sub(r"[^0-9a-z]", "", str(text).casefold())


# ── DIRECTION 1: pairs a human calls the same string ──────────────────────────────────────────────
#
# ``test_a_dehyphenated_designator_is_no_longer_a_miss`` was retired here on 2026-07-27 (with its
# ``_dehyphenated`` / ``_IDENT_RUN`` synthesiser, whose only caller it was). See the module docstring.


def test_the_gold_own_two_spellings_of_one_designator_match(surfaces: list[str]) -> None:
    """The labeled slice contains both spellings itself — no synthesised pair needed to prove the point."""
    by_squash: dict[str, list[str]] = {}
    for surface in surfaces:
        by_squash.setdefault(_squash(surface), []).append(surface)
    same = [(a, b) for group in by_squash.values() if len(group) > 1
            for a, b in itertools.combinations(sorted(group), 2)]
    assert len(same) == 10, f"expected 10 punctuation/case-only pairs in the slice, found {len(same)}"
    assert [p for p in same if not _matches(*p, PROSE)] == [("HQ-9B", "HQ9B")], (
        "the one pair the prose kernel got wrong here was HQ-9B vs HQ9B (0.4444); that has changed"
    )
    assert [p for p in same if not _matches(*p, POLICY)] == []


# ── DIRECTION 2: pairs a human calls different ────────────────────────────────────────────────────

#: Designators of the shape this corpus is built from, all genuinely different things. HQ-9A/HQ-9B and
#: FT-2000/FT-2000A are sibling variants; the KPQA numbers are three different import declarations and the
#: gold carries an explicit distinct-from between them; the YMLUW/COSU strings are bills of lading.
DESIGNATOR_FAMILY = (
    "HQ-9", "HQ-9A", "HQ-9B", "HQ-9BE", "HQ-9P", "HQ-9/P", "HQ-16", "HQ-16FE",
    "FD-2000", "FT-2000", "FT-2000A", "HT-233", "HT-233A", "S-400", "S-300",
    "KPQA-HC-2020-118834", "KPQA-HC-2020-118835", "KPQA-HC-2020-119011",
    "YMLUW189234567", "YMLUW189234568", "COSU6178820410",
)


def test_no_two_different_designators_are_conflated() -> None:
    """40 of 684 genuinely-different designator pairs were conflated; under the decided policy, 0.

    This is the assertion that makes the change safe. The fear was that catching ``HT233`` would start
    matching ``HQ-9A`` to ``HQ-9B`` — but the prose kernel **already did**: 0.80 for HQ-9A/HQ-9B, 0.91 for
    HQ-9B/HQ-9BE, 0.95 for two different GD numbers. One changed character in a six-character designator is
    a tiny edit distance, so no threshold can separate them; only a veto can.
    """
    spellings = sorted({*DESIGNATOR_FAMILY, *(re.sub(r"[-/]", "", d) for d in DESIGNATOR_FAMILY)})
    pairs = [p for p in itertools.combinations(spellings, 2) if _squash(p[0]) != _squash(p[1])]
    assert len(pairs) == 684
    before = [p for p in pairs if _matches(*p, PROSE)]
    after = [p for p in pairs if _matches(*p, POLICY)]
    assert len(before) == 40, f"the prose kernel's measured conflation count changed: {len(before)}, was 40"
    assert after == [], f"these genuinely different designators are still scored the same claim: {after}"


# ``test_the_slice_wide_over_merge_count_falls`` was retired here on 2026-07-27. See the module docstring.


def test_what_the_veto_costs_is_exactly_these_two_pairs(
    surfaces: list[str], node_of: dict[str, set[str]],
) -> None:
    """The stated cost, asserted so it cannot grow unnoticed.

    Two same-node pairs stop matching, both to the veto, and both are explainable rather than mysterious:

    * ``the FT-2000`` vs ``FT-2000A`` — this gold declares them ONE node because d04 says "sometimes
      rendered"; in general a suffixed designator IS a different variant, so the veto is right in the
      general case and wrong on this documented alias. Fixing it needs an alias table, and an alias-aware
      matcher hands the extractor credit for resolution work it did not do.
    * ``HT-233-band engagement-radar parameters`` vs ``HT-233 engagement radar`` — the glue swallows the
      adjacent hyphenated word into the identifier, so ``ht233band`` ≠ ``ht233``.

    Both err toward a MISSED match, which is the safer direction: misses add variance, and variance makes
    the margin rule more reluctant to call a gap material, whereas leniency inflates every candidate and
    hides the fabrication line.
    """
    lost = []
    for pair in itertools.combinations(surfaces, 2):
        left, right = node_of.get(pair[0], set()), node_of.get(pair[1], set())
        if not (left and right and (left & right)):
            continue
        if _matches(*pair, PROSE) and not _matches(*pair, POLICY):
            lost.append(pair)
    assert sorted(lost) == [
        ("HT-233-band engagement-radar parameters", "HT-233 engagement radar"),
        ("the FT-2000", "FT-2000A"),
    ], f"the veto's cost on same-node pairs changed: {sorted(lost)}"
    assert all(not identifiers_agree(*p, POLICY) for p in lost), (
        "these were supposed to be lost to the identifier veto; if one is now lost to the FLOOR instead, "
        "the glue has started lowering scores and the max-of-two-readings property is broken"
    )


# ── the rule itself, stated as behaviour ──────────────────────────────────────────────────────────

def test_the_rule_is_scoped_to_identifiers_and_leaves_prose_alone() -> None:
    """One sentence, checkable: punctuation inside a letters-and-digits token is typographic; elsewhere it
    is a word boundary. That scoping is what lets the designator rule ship without touching predicates."""
    assert normalize_designator("HQ-9/P") == "hq9p"
    assert normalize_designator("KPQA-HC-2020-118834") == "kpqahc2020118834"
    # prose: unchanged, so `supplies-component` ≡ `supplies component` still holds
    assert normalize_designator("AL-NOOR CARGO SERVICES") == normalize_surface("AL-NOOR CARGO SERVICES")
    assert normalize_designator("fire-control/engagement radar") == "fire control engagement radar"
    assert normalize_designator("supplies-component") == "supplies component"
    # a date is not an identifier: no letters, so nothing is glued
    assert normalize_designator("Baseline imagery (2024-11)") == "baseline imagery 2024 11"
    # bare numbers are not identifiers, so a count can never veto anything
    assert identifier_tokens("two operational battalions") == frozenset()
    assert identifier_tokens("estimated at 6-8 TELs") == frozenset()
    assert identifier_tokens("the HQ-9B system") == frozenset({"hq9b"})


def test_the_veto_is_nested_not_equal_and_not_prefix_tolerant() -> None:
    """Nested, so a surface may carry a designator its counterpart omits; not prefix-tolerant, so a family
    name is not its own variant."""
    assert identifiers_agree("the FT-2000", "the FT-2000 (sometimes rendered FT-2000A)", POLICY)
    assert identifiers_agree("the HQ-9B system", "the system", POLICY)      # prose side has no designator
    assert not identifiers_agree("HQ-9", "HQ-9/P", POLICY)                  # family ≠ variant
    assert not identifiers_agree("HQ-9B", "HQ-9BE", POLICY)
    assert identifiers_agree("HQ-9B", "HQ-9BE", PROSE)                      # the knob is real
