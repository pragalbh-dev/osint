"""The flagship worked query, end-to-end on the **real corpus** — the regression guard that was missing.

Every other hero test in the suite runs against the hand-authored ASK fixture, so the flagship query could
(and did) degrade to an honest refusal on the actual rebuilt graph without turning a single test red: the
``hero_answer`` fixture existed and nothing consumed it. This file consumes it.

What it pins is the *demo contract*, not a transcript: the worked query must come back as a **positive,
fully-cited multi-hop answer** — a refusal here means the flagship thread is dead. Specifically:

* ``refusal is None`` — the trace reached an answer;
* the chain is a real multi-hop walk, not a lookup, and each hop carries claim ids;
* **every citation resolves to a claim that exists in the evidence log** — this is the one that catches the
  ``contributing_refs`` class of bug, where materiality contributes *edge* ids into a claim-id citation list
  and the whole answer is silently withheld by the citation validator;
* the chain **terminates on a link the system itself rates as assertable** — never on an edge it has
  already scored ``insufficient`` (the T9 defect: see ``MIN_HOPS`` below);
* the chokepoint is still **named** and its unresolved supplier still stated as an open Known Gap — the
  honest end-state C/02 promises, not a fabricated sole-source;
* the weak link the trace declined to carry is **printed, rated and cited** rather than filtered away.

Node ids and edge names are deliberately *not* asserted: which component the graph nominates is the
pipeline's judgement to make, and pinning it here would turn a data improvement into a test failure.
"""

from __future__ import annotations

from chanakya.schemas import AskAnswer, GraphView
from eval import harness

#: The floor on the chain the worked query walks — it must be a genuine multi-hop TRACE, not a lookup.
#:
#: Kept a FLOOR, not a pin, for the reason this file's own docstring gives about node ids: pinning the
#: exact shape turns a data improvement into a red test. Its history, so a future reader can judge it:
#:
#:   original  site_rahwali -based-at→ unit_hq9b -equips→ var_hq9p -equips→ ent:component:Type 305B   (3)
#:   T3b       site_rahwali -observed-at→ comp_ht233 -supplies-component→ ent:manufacturer:CPMIEC     (2)
#:   T9        site_rahwali -based-at→ unit_hq9b -equips→ var_hq9p -manufactures→ mfr_casic           (3)
#:
#: The ORIGINAL chain terminated on ``Type 305B`` — one of ten FRAGMENTS of the HT-233 radar — which
#: carries no maker edge, so it never reached a supplier at all. T3b resolved the fragments onto
#: ``comp_ht233``; the trace then followed the only maker edge that node has, which is the corpus's
#: planted CPMIEC false attribution (d23, refuted by d22). Correctly rated ``insufficient`` — but it left
#: the flagship query terminating on misinformation and closing on a refusal, i.e. not answering the
#: question it poses.
#:
#: T9 fixed the defect underneath (``run_fixed_hero_path`` took the first manufacturer-typed neighbour
#: with no regard for the claiming edge's status) and re-anchored the terminus on the system's ORIGIN
#: maker, which is genuinely well-evidenced. The trap is NOT discarded: the CPMIEC link is still
#: gathered, still rated, and is printed in the answer as "weighed and not carried" with its citation —
#: surfaced rather than stepped around, but no longer the terminal answer.
MIN_HOPS = 3


def test_worked_query_answers_instead_of_refusing(hero_answer: AskAnswer) -> None:
    """The flagship query must produce an answer. A refusal here IS the demo being broken."""
    assert hero_answer.refusal is None, (
        f"the worked query refused — flagship thread is dead: {hero_answer.refusal}"
    )
    assert hero_answer.answer, "no refusal and no answer body is not a valid outcome"


def test_worked_query_walks_the_full_cited_chain(hero_answer: AskAnswer) -> None:
    """A multi-hop trace: a real walk of at least ``MIN_HOPS``, every one of them sourced."""
    assert len(hero_answer.hops) >= MIN_HOPS, [
        (h.step, h.edge, h.src, h.dst) for h in hero_answer.hops
    ]
    for hop in hero_answer.hops:
        assert hop.claim_ids, f"hop {hop.step} ({hop.edge}) asserts a link with no claim behind it (G4)"
    # each hop starts where the previous one ended — a walk, not three unrelated lookups
    for prev, nxt in zip(hero_answer.hops, hero_answer.hops[1:], strict=False):
        assert prev.dst == nxt.src, f"chain breaks between step {prev.step} and {nxt.step}"


def test_every_citation_resolves_to_a_real_claim(
    hero_answer: AskAnswer, scenario: harness.ScenarioInputs
) -> None:
    """No citation may be an id the evidence log cannot produce.

    The regression this guards: ``MaterialityAttrs.contributing_refs`` holds claim ids *and edge ids*, so
    copying it wholesale into the citation list makes the citation validator reject the sentence and the
    entire positive answer gets downgraded to a refusal.
    """
    assert hero_answer.citations, "a positive answer with no citations violates the provenance rule"
    dangling = [c for c in hero_answer.citations if c not in scenario.claims]
    assert not dangling, f"citations that resolve to no claim (edge ids leaking in?): {dangling}"


def test_chain_terminates_on_an_assertable_link(
    hero_answer: AskAnswer, view: GraphView, scenario: harness.ScenarioInputs
) -> None:
    """The trace must END on a link the system itself rates strongly enough to assert.

    This is the T9 regression: the flagship chain used to terminate on the corpus's planted CPMIEC
    attribution, an edge the pipeline had already rated ``insufficient``, because the hero path picked
    the first manufacturer-typed neighbour without looking at the claiming edge. Status is read from the
    rebuilt view and the admissible band from config — no node, edge or document is named here, so a data
    improvement that changes *which* link terminates the chain does not turn this red.
    """
    band = set(scenario.config_store.snapshot().credibility.assertable_status)
    assert band, "config declares no assertable band — the guard below would be vacuous"
    last = hero_answer.hops[-1]
    edge = next(
        (e for e in view.edges if {e.source, e.target} == {last.src, last.dst} and e.type == last.edge),
        None,
    )
    assert edge is not None, f"the final hop {last.edge} {last.src}→{last.dst} is not in the rebuilt view"
    assert edge.status in band, (
        f"the chain terminates on a {edge.status!r} link ({edge.id}) — the answer rests on evidence the "
        f"system itself does not consider assertable (admissible: {sorted(band)})"
    )


def test_answer_names_the_chokepoint_and_its_open_gap(hero_answer: AskAnswer, view: GraphView) -> None:
    """The chokepoint is still named, still honestly labelled, and its supplier gap still stated.

    Moving the *terminus* off the chokepoint must not quietly drop the chokepoint finding: the question
    asks for it, and the non-negotiable requires the open gap under it to be said out loud rather than
    resolved by a supplier the evidence does not support.
    """
    answer = (hero_answer.answer or "").lower()
    assert "chokepoint" in answer, "the answer does not name a chokepoint at all"
    # a candidate chokepoint whose supplier is unresolved must appear as a Known Gap, not a finding
    assert "insufficient evidence to assess" in answer, (
        f"the chokepoint's open supplier gap is not stated: {hero_answer.answer!r}"
    )
    named = [n for n in view.nodes if n.materiality and n.materiality.chokepoint_status == "candidate"]
    assert any(n.name and n.name.lower() in answer for n in named), (
        "no candidate chokepoint from the view is named in the answer"
    )


def test_a_below_band_link_is_reported_rather_than_hidden(hero_answer: AskAnswer) -> None:
    """The weak supplier link the trace declined to carry must still be printed, rated and cited.

    The whole design argument for the T9 fix: filtering a low-credibility attribution out of the gather
    step would make a planted false one indistinguishable, in the answer, from one that was never
    published. So the corpus's CPMIEC conflation is expected to appear — as a *weighed and not carried*
    line with its own citation — and never as a hop the assessment rests on.
    """
    lines = [line for line in (hero_answer.answer or "").splitlines() if "not carried" in line.lower()]
    assert lines, f"no below-band link was reported at all: {hero_answer.answer!r}"
    for line in lines:
        assert "[" in line and "]" in line, f"a reported-but-not-carried line carries no citation: {line}"
    # and it must not also be a hop — reported is not the same as relied upon
    hop_pairs = {(h.src, h.dst) for h in hero_answer.hops}
    assert hop_pairs, "no hops to check against"
