"""End-to-end acceptance for ``ask()`` (sessions/ASK.md acceptance criteria)."""

from __future__ import annotations

from chanakya.agent import analyses, ask
from chanakya.agent.assemble import _refusal, assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import AgentTrace, RecordedCall

from .mock_llm import final, planner, tool_turn

HERO_Q = "trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint"


def _hero_planner():
    """A scripted planner that reaches the flagship trace the way the live agent does — one graph_analyze
    call (supply_chain, anchored on the fixture's basing site), then stop. Fresh per call (stateful client)."""
    return planner(
        tool_turn("graph_analyze", {"subject_id": "site_karachi", "analysis": "supply_chain"}), final()
    )


def test_hero_query_traces_the_chain_and_cites_each_hop(view, claims, config) -> None:
    a = ask(HERO_Q, view, config, llm=_hero_planner(), claims=claims)
    assert a.answer is not None and a.refusal is None
    assert [h.edge for h in a.hops] == ["based-at", "inducted-into", "equips", "supplies-component"]
    for h in a.hops:
        assert h.claim_ids and all(c in claims for c in h.claim_ids), f"hop {h.edge} not cited to real claims"
    # observed-vs-inferred read structurally from each claim's kind
    assert next(h for h in a.hops if h.edge == "based-at").observed_or_inferred == "observed"
    assert next(h for h in a.hops if h.edge == "equips").observed_or_inferred == "inferred"
    assert a.citations


def test_ht233_renders_candidate_not_confirmed_sole_source(view, claims, config) -> None:
    """The disqualifying line: HT-233 is a CANDIDATE with UNKNOWN substitutability, never sole-source."""
    a = ask(HERO_Q, view, config, llm=_hero_planner(), claims=claims)
    assert a.answer is not None
    assert "chokepoint_status=candidate" in a.answer
    assert "substitutability=UNKNOWN" in a.answer
    assert "known-sole-source" not in a.answer


def test_planted_gap_returns_reasoned_insufficiency(view, claims, config) -> None:
    llm = planner(tool_turn("graph_check_sufficiency", {"scope": "comp_ht233"}), final())
    a = ask("what do we NOT know about HT-233's supplier?", view, config, llm=llm, claims=claims)
    assert a.answer is None and a.refusal is not None
    assert a.refusal.missing
    assert a.refusal.next_coverage_due == "2026-09-01"
    assert a.refusal.known_gap is not None
    assert "insufficient evidence" in a.refusal.reason.lower()


def test_hero_answer_is_deterministic(view, claims, config) -> None:
    a = ask(HERO_Q, view, config, llm=_hero_planner(), claims=claims)
    b = ask(HERO_Q, view, config, llm=_hero_planner(), claims=claims)
    assert a.model_dump() == b.model_dump()


def test_keyless_nonhero_refuses_never_fabricates(view, claims, config) -> None:
    # no llm passed + key stripped by the offline fixture → honest refusal, never a guess.
    a = ask("What is HT-233?", view, config, claims=claims)
    assert a.answer is None and a.refusal is not None
    assert a.refusal.reason


def test_keyless_refusal_is_a_capability_outage_not_an_evidence_gap(view, claims, config) -> None:
    """"We have no evidence" and "we could not look" are different claims to an analyst.

    Nothing was consulted on this path, so reporting a shortfall in the world's evidence overstates a
    gap that may not exist — the same mislabelling family as stale-vs-insufficient, and a correctness
    bug rather than copy. The refusal must say the SYSTEM could not run, name what would fix it, and
    not put an internal token where the analyst reads "missing".
    """
    a = ask("What is HT-233?", view, config, claims=claims)
    assert a.refusal is not None
    assert a.refusal.kind == "capability" != "evidence"
    assert "insufficient evidence" not in a.refusal.reason.lower()
    assert "could not run" in a.refusal.reason.lower()
    # honest-refusal discipline: name what is missing and what would fix it, in analyst-facing words
    assert any("ANTHROPIC_API_KEY" in m for m in a.refusal.missing)
    assert "live_llm_or_recorded_trace" not in a.refusal.missing


def test_refusal_names_an_unresolved_named_subject(view, claims, config) -> None:
    """CHANGE 1: when the failure was a named subject that did not BIND, the refusal names it — the query
    that failed and that the look-alikes are DISTINCT entities — instead of the generic "no supporting path"."""
    trace = AgentTrace(question="who supplies the Rahwali SAM regiment?")
    trace.calls.append(
        RecordedCall(
            name="find_entity",
            input={"text": "Rahwali SAM regiment"},
            result={
                "query": "Rahwali SAM regiment",
                "resolution": "ambiguous",
                "resolved": False,
                "candidates": [
                    {"node_id": "site_rahwali", "name": "Rahwali airfield"},
                    {"node_id": "unit_paad", "name": "PAAD regiment"},
                ],
            },
        )
    )
    r = _refusal(trace)
    assert r.kind == "evidence"
    assert "Rahwali SAM regiment" in r.reason            # the actual query text, not a hardcoded name
    assert "Rahwali airfield" in r.reason                # the closest look-alike, named from the candidates
    assert "distinct entities" in r.reason
    assert "no supporting path" not in r.reason          # NOT the generic fallback
    assert r.missing == ["Rahwali SAM regiment"]


def test_refusal_unresolved_subject_with_no_candidates_still_names_the_query(view, claims, config) -> None:
    """The ``resolution == none`` case (an error-shaped find_entity, no candidates) still names the query."""
    trace = AgentTrace(question="q")
    trace.calls.append(
        RecordedCall(
            name="find_entity",
            input={"text": "Zarad-9 launcher"},
            result={"query": "Zarad-9 launcher", "resolution": "none", "resolved": False,
                    "candidates": [], "error": "no match", "suggestion": "check spelling"},
        )
    )
    r = _refusal(trace)
    assert "Zarad-9 launcher" in r.reason and "isn't established yet" in r.reason
    assert r.missing == ["Zarad-9 launcher"]


def test_check_sufficiency_still_wins_over_an_unresolved_subject(view, claims, config) -> None:
    """The scoped check_sufficiency refusal keeps priority over the unresolved-subject reason (unchanged)."""
    llm = planner(
        tool_turn("graph_find_entity", {"text": "totally unknown thing"}),
        tool_turn("graph_check_sufficiency", {"scope": "comp_ht233"}),
        final(),
    )
    a = ask("what do we NOT know about HT-233's supplier?", view, config, llm=llm, claims=claims)
    assert a.answer is None and a.refusal is not None
    assert a.refusal.known_gap is not None                # the sufficiency branch, not the unresolved one
    assert "insufficient evidence" in a.refusal.reason.lower()


def test_refusal_askanswer_carries_the_partial_trace_it_established(view, claims, config) -> None:
    """CHANGE 2: a refusal still CARRIES whatever trace the agent established — the partial hops the analysis
    could connect reach the refusal AskAnswer, each cited to a real claim, so the UI can show "how far this
    got". It stays a refusal (answer is None, refusal set); no positive finding is asserted."""
    ctx = ToolContext.build(view, claims, config)
    # borrow a real, cited leg from the fixture's own chain so the hops resolve to real claims
    full = analyses.analyze(ctx, "site_karachi", "supply_chain")
    partial_hops = full["hops"][:2]
    assert partial_hops and all(h["claim_ids"] for h in partial_hops)
    # a supply_chain-shaped analyze RESULT that refuses but carries the partial trace (as _supply_chain now does)
    refusing = {
        "analysis": "supply_chain", "subject": "site_karachi", "subject_name": "x",
        "hops": partial_hops, "chokepoint": None, "maker": None, "weighed_not_carried": [], "sub_questions": [],
        "refusal": {"missing_slots": ["path:site_karachi->mfr"], "reason": "could not connect the chain",
                    "next_coverage_due": None, "known_gap": None},
    }
    trace = AgentTrace(question="trace it back")
    trace.calls.append(RecordedCall(name="analyze", input={"analysis": "supply_chain"}, result=refusing))
    a = assemble_answer(trace, ctx)
    assert a.answer is None and a.refusal is not None                       # still a refusal
    assert [h.edge for h in a.hops] == [h["edge"] for h in partial_hops]    # the partial trace carried through
    for h in a.hops:                                                        # every carried hop cited to a real claim
        assert h.claim_ids and all(c in claims for c in h.claim_ids)
    assert a.citations and all(c in claims for c in a.citations)


def test_free_loop_point_lookup_answers_with_citation(view, claims, config) -> None:
    llm = planner(
        tool_turn("graph_find_entity", {"text": "HT-233"}),
        tool_turn("graph_get_node", {"node_id": "comp_ht233"}),
        final(),
    )
    a = ask("What is HT-233?", view, config, llm=llm, claims=claims)
    assert a.answer is not None
    assert a.citations and all(c in claims for c in a.citations)
