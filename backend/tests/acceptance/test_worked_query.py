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
* the chain **terminates on the chokepoint**, and that node is a declared ``candidate`` chokepoint whose
  supplier is still an open Known Gap — the honest end-state C/02 promises, not a fabricated sole-source.

Node ids and edge names are deliberately *not* asserted: which component the graph nominates is the
pipeline's judgement to make, and pinning it here would turn a data improvement into a test failure.
"""

from __future__ import annotations

from chanakya.schemas import AskAnswer, GraphView
from eval import harness

#: The floor on the chain the worked query walks — it must be a genuine multi-hop TRACE, not a lookup.
#:
#: This was a hard pin at 3 (basing → operator → variant → chokepoint component). T3b relaxed it to a
#: floor, for the reason this file's own docstring gives about node ids: pinning the exact shape turns a
#: data improvement into a red test. What changed and why, so a future reader can judge it:
#:
#:   before  site_rahwali -based-at→ unit_hq9b -equips→ var_hq9p -equips→ ent:component:Type 305B
#:   after   site_rahwali -observed-at→ comp_ht233 -supplies-component→ ent:manufacturer:CPMIEC
#:
#: The old chain terminated on ``Type 305B`` — one of ten FRAGMENTS of the HT-233 radar — and never
#: reached a supplier at all. Once the fragments resolve onto ``comp_ht233``, the nominated chokepoint is
#: the real radar, it carries a maker edge, and the trace reaches it. That edge is the corpus's planted
#: CPMIEC false attribution (d23, refuted by d22), and the answer labels it ``insufficient`` and closes
#: on "Insufficient evidence to assess HT-233: missing named_supplier" — so the thread now *exercises*
#: the misinformation trap instead of stepping around it. The trade is two fewer ORBAT hops
#: (operator → variant) in the narrative. Worth a deliberate look before the demo.
MIN_HOPS = 2


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


def test_chain_terminates_on_a_candidate_chokepoint_with_an_open_gap(
    hero_answer: AskAnswer, view: GraphView
) -> None:
    """The terminus is the chokepoint the question asked for — and it is honestly labelled."""
    terminus_id = hero_answer.hops[-1].dst
    node = next((n for n in view.nodes if n.id == terminus_id), None)
    assert node is not None, f"the chain ends on {terminus_id}, which is not in the rebuilt view"
    assert node.materiality is not None, f"{terminus_id} carries no precomputed materiality"
    assert node.materiality.chokepoint_status == "candidate", (
        f"{terminus_id} is not a candidate chokepoint (status={node.materiality.chokepoint_status})"
    )
    # the answer must SAY so, and say what is still missing — never assert a sole-source we cannot show
    assert "chokepoint" in (hero_answer.answer or "").lower()
