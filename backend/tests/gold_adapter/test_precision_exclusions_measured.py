"""RULING 1, measured on the REAL labeled slice: what the unwired precision denominator was costing.

This file lives under ``tests/gold_adapter`` rather than ``tests/extraction_bakeoff`` for one reason: the
bake-off's scorer is corpus-blind by design and its own tests are too, so the *arithmetic* of the exclusion
is pinned on invented fixtures in ``tests/extraction_bakeoff/test_precision_exclusions.py``. What can only be
done here — where the labeled gold is a readable input — is quantifying the defect on the actual 7-document
slice, for the three candidates the ruling names.

Each candidate is synthesised mechanically from the gold itself, so nothing is hand-tuned:

* **perfect**            — emits exactly the 65 positive claims.
* **verbose but honest** — the 65 positives *plus* one unpaired emission on every one of the 29 neutral-class
  spans (19 ``unmodelled`` + 8 ``anti_coref`` + 2 ``ambiguous``). It has read more of the document and
  invented nothing.
* **fabricating**        — the 65 positives *plus* one unpaired emission on every one of the 11
  ``not_a_claim`` trap spans.

The unpaired emissions carry deliberately non-gold surfaces, because "an unpaired emission sitting on a
declared-neutral span" is exactly the case the exclusion is about; an emission that paired with positive gold
was never charged in the first place.

RETIRED 2026-07-27 — ``test_the_verbose_but_honest_model_was_losing_precision_for_reading_the_document``
─────────────────────────────────────────────────────────────────────────────────────────────────────
That test pinned the headline quantification of Ruling 1 (0.7065 unwired → 1.0 wired, a 0.2935 loss over
27 neutral spans). The 2026-07-26 gold repair moved the neutral count 27 → 29, which moves both decimals.
It is deleted rather than bumped, because those decimals are a *measured finding* about how a candidate
scored, not bookkeeping about the fixture — and the bake-off diagnosis established that several such
figures were artefacts of our own scorer. Editing the number in place would have laundered a changed
measurement as a repair. The finding, with its provenance and its caveats, lives in
``tmp/conv/RK-BAKEOFF-DIAGNOSIS.md``; the *property* it was really defending — that wiring the exclusion
stops ranking a verbose-honest model below a fabricator — is still asserted below by
``test_the_wired_denominator_ranks_the_honest_model_above_the_fabricator``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval.extraction.gold import load_claim_gold
from eval.extraction.matcher import match_claims
from eval.extraction.metrics import surface_metrics, trap_avoidance
from eval.extraction.negative_gold import emitted_spans, load_negative_gold
from eval.extraction.policy import load_bakeoff_config
from eval.extraction.surface import SpanRef, SurfaceClaim

from .conftest import EXPECTED

NEUTRAL_CLASSES = ("unmodelled", "anti_coref", "ambiguous")


@pytest.fixture(scope="module")
def policy():
    """The shipped match policy — the same leniency the real bake-off measures with."""
    from chanakya import settings

    return load_bakeoff_config(settings.config_dir() / "bakeoff.yaml").match_policy


@pytest.fixture(scope="module")
def loaded(adapted: dict[str, Any], tmp_path_factory) -> tuple[list[SurfaceClaim], Any]:
    """The adapted slice round-tripped through the two loaders the runner actually uses."""
    path = Path(tmp_path_factory.mktemp("gold")) / "claim-gold.bakeoff.json"
    path.write_text(json.dumps(adapted, ensure_ascii=False), encoding="utf-8")
    return load_claim_gold(path), load_negative_gold(path)


def _unpaired_on(row: dict[str, Any], index: int) -> SurfaceClaim:
    """One emission on a declared negative span, with surfaces no gold claim carries."""
    ref = row["doc_ref"]
    return SurfaceClaim(
        key=f"emit-{row['gold_id']}-{index}", source_id=row["source_id"], form="triple",
        polarity="positive", predicate="supplies-component",
        roles={"subject": f"Synthetic Subject {index}", "object": f"Synthetic Object {index}"},
        refs=(SpanRef(file=ref["file"], span=(int(ref["span"][0]), int(ref["span"][1]))),),
    )


def _measure(gold, negative, emitted, policy) -> dict[str, Any]:
    """Precision before and after the exclusion, from the one definition of it."""
    match = match_claims(list(gold), list(emitted), policy)
    spans = emitted_spans(list(emitted), match, negative)
    excluded = negative.excluded_keys(spans)
    wired = match.with_precision_exclusions(excluded)
    return {
        "emitted": match.extracted_total,
        "matched": len(match.pairs),
        "before": len(match.pairs) / match.extracted_total,      # the old matched/extracted denominator
        "after": surface_metrics(wired)["surface_precision"].value,
        "recall": surface_metrics(wired)["surface_recall"].value,
        "excluded": len(excluded),
        "traps": trap_avoidance(negative, spans),
    }


def _candidates(gold, negative) -> dict[str, list[SurfaceClaim]]:
    neutral = [r for cls in NEUTRAL_CLASSES for r in negative.rows(cls)]
    traps = negative.rows("not_a_claim")
    return {
        "perfect": list(gold),
        "verbose_honest": list(gold) + [_unpaired_on(r, i) for i, r in enumerate(neutral)],
        "fabricating": list(gold) + [_unpaired_on(r, i) for i, r in enumerate(traps)],
        "unmodelled_only": list(gold) + [_unpaired_on(r, i)
                                         for i, r in enumerate(negative.rows("unmodelled"))],
    }


# ── the numbers ────────────────────────────────────────────────────────────────────────────────────

def test_the_slice_declares_the_counts_this_measurement_assumes(loaded) -> None:
    """Pinned so a change to the gold breaks this loudly instead of silently re-baselining the figures.

    It did exactly that on 2026-07-26 and is re-armed against the repaired census. The neutral total is
    now derived from ``EXPECTED`` rather than written as its own literal, so this tripwire fires on the
    *classes* moving apart, not merely on their sum changing.
    """
    gold, negative = loaded
    assert len(gold) == EXPECTED["claims"]
    counts = negative.counts()
    assert counts["not_a_claim"] == EXPECTED["not_a_claim"]
    assert counts["anti_coref"] == EXPECTED["anti_coref"]
    assert counts["ambiguous"] == EXPECTED["ambiguous"]
    assert counts["unmodelled"] == EXPECTED["unmodelled"]
    assert sum(counts[c] for c in NEUTRAL_CLASSES) == sum(EXPECTED[c] for c in NEUTRAL_CLASSES) == 29


def test_a_perfect_model_scores_one_on_precision_and_recall_either_way(loaded, policy) -> None:
    """The control. A model emitting exactly the positive gold has nothing unpaired, so the exclusion cannot
    flatter it — and recall is 1.0, which is the adapter's own headline claim about this slice."""
    gold, negative = loaded
    m = _measure(gold, negative, _candidates(gold, negative)["perfect"], policy)
    assert (m["before"], m["after"]) == (pytest.approx(1.0), pytest.approx(1.0))
    assert m["recall"] == pytest.approx(1.0)
    assert m["excluded"] == 0
    assert m["traps"].value == pytest.approx(1.0)


# RETIRED 2026-07-27: ``test_the_verbose_but_honest_model_was_losing_precision_for_reading_the_document``
# stood here. It pinned 0.7065 / 0.2935 — the published quantification of a scorer ruling, not fixture
# bookkeeping — and the 2026-07-26 gold repair (27 → 29 neutral rows) moved both. Deleted rather than
# re-baselined; see this module's docstring and ``tmp/conv/RK-BAKEOFF-DIAGNOSIS.md``.


def test_the_unmodelled_rows_alone_account_for_most_of_the_loss(loaded, policy) -> None:
    """The single worst class: 19 rows the ontology cannot express, which the gold's own vocabulary calls "a
    finding, not a failure"."""
    gold, negative = loaded
    m = _measure(gold, negative, _candidates(gold, negative)["unmodelled_only"], policy)

    assert m["emitted"] == 65 + 19
    assert m["before"] == pytest.approx(0.7738, abs=5e-5)
    assert m["after"] == pytest.approx(1.0)
    assert m["after"] - m["before"] == pytest.approx(0.2262, abs=5e-5)


def test_the_fabricating_model_is_not_excused_by_the_exclusion(loaded, policy) -> None:
    """The risk of Ruling 1. If an exclusion leaked into ``not_a_claim``, wiring it would have *rewarded*
    fabrication — the exact inversion the composite-direction bug produced. Precision must be identical
    before and after, and the trap line must read 0."""
    gold, negative = loaded
    m = _measure(gold, negative, _candidates(gold, negative)["fabricating"], policy)

    assert m["emitted"] == 65 + 11
    assert m["excluded"] == 0
    assert m["before"] == pytest.approx(m["after"])
    assert m["after"] == pytest.approx(65 / 76, abs=5e-5)
    assert m["traps"].value == pytest.approx(0.0)
    assert len(m["traps"].detail["hits_by_trap"]) == EXPECTED["not_a_claim"]


def test_the_wired_denominator_ranks_the_honest_model_above_the_fabricator(loaded, policy) -> None:
    """The property that matters to a verdict, not just the arithmetic: unwired, the verbose-but-honest model
    scored WORSE on precision than the fabricator — the instrument preferred the model that invented claims
    to the one that read more of the page. Wired, that inversion is gone.

    Stated as an inequality, never as the two decimals: those move with the gold's neutral-row census (they
    did on 2026-07-26) while the inversion this test exists to catch does not."""
    gold, negative = loaded
    cands = _candidates(gold, negative)
    honest = _measure(gold, negative, cands["verbose_honest"], policy)
    fabricator = _measure(gold, negative, cands["fabricating"], policy)

    assert honest["before"] < fabricator["before"], "the premise: the unwired denominator inverted these two"
    assert honest["after"] > fabricator["after"]
    assert honest["traps"].value > fabricator["traps"].value


def test_the_measurement_is_reported_in_full(loaded, policy, capsys) -> None:
    """Print the table this ruling is reported with, so the figures are reproducible from a test run rather
    than trusted to a commit message."""
    gold, negative = loaded
    print(f"\n{'candidate':<18} {'emitted':>8} {'matched':>8} {'before':>8} {'after':>8} "
          f"{'excl':>5} {'traps':>7}")
    for name, emitted in _candidates(gold, negative).items():
        m = _measure(gold, negative, emitted, policy)
        traps = "—" if m["traps"].value is None else f"{m['traps'].value:.4f}"
        print(f"{name:<18} {m['emitted']:>8} {m['matched']:>8} {m['before']:>8.4f} "
              f"{m['after']:>8.4f} {m['excluded']:>5} {traps:>7}")
    assert "before" in capsys.readouterr().out
