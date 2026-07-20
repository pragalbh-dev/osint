"""End-to-end acceptance for ``ask()`` (sessions/ASK.md acceptance criteria)."""

from __future__ import annotations

from chanakya.agent import ask

from .mock_llm import final, planner, tool_turn

HERO_Q = "trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint"


def test_hero_query_traces_the_chain_and_cites_each_hop(view, claims, config) -> None:
    a = ask(HERO_Q, view, config, claims=claims)
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
    a = ask(HERO_Q, view, config, claims=claims)
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
    a = ask(HERO_Q, view, config, claims=claims)
    b = ask(HERO_Q, view, config, claims=claims)
    assert a.model_dump() == b.model_dump()


def test_keyless_nonhero_refuses_never_fabricates(view, claims, config) -> None:
    # no llm passed + key stripped by the offline fixture → honest refusal, never a guess.
    a = ask("What is HT-233?", view, config, claims=claims)
    assert a.answer is None and a.refusal is not None
    assert a.refusal.reason


def test_free_loop_point_lookup_answers_with_citation(view, claims, config) -> None:
    llm = planner(
        tool_turn("graph_find_entity", {"text": "HT-233"}),
        tool_turn("graph_get_node", {"node_id": "comp_ht233"}),
        final(),
    )
    a = ask("What is HT-233?", view, config, llm=llm, claims=claims)
    assert a.answer is not None
    assert a.citations and all(c in claims for c in a.citations)
