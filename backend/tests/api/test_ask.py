"""``POST /ask`` — cited multi-hop answer + first-class refusal (API.md acceptance; product/03 E).

The API is thin: these assert it forwards ASK's contract over HTTP (per-hop citations, observed-vs-
inferred, and the honest refusal), not ASK's internals (covered in tests/agent)."""

from __future__ import annotations

import chanakya.agent as agent
from chanakya.schemas import AskAnswer
from tests.agent.mock_llm import final, planner, tool_turn

HERO_Q = "trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint"


def _use_hero_planner(monkeypatch) -> None:
    """The flagship trace is no longer special-cased in ask(); the planner reaches it via graph_analyze.
    Drive the endpoint's ReAct loop offline with a scripted planner that makes that one call (as ASK's own
    tests do), so the API forwards the cited multi-hop answer without a live key."""
    monkeypatch.setattr(
        agent,
        "build_default_client",
        lambda *a, **k: planner(
            tool_turn("graph_analyze", {"subject_id": "site_karachi", "analysis": "supply_chain"}), final()
        ),
    )


def test_ask_hero_query_cited_multihop_answer(hero_client, monkeypatch) -> None:
    _use_hero_planner(monkeypatch)
    r = hero_client.post("/ask", json={"question": HERO_Q})
    assert r.status_code == 200
    a = AskAnswer.model_validate(r.json())
    assert a.answer is not None and a.refusal is None
    assert [h.edge for h in a.hops] == ["based-at", "inducted-into", "equips", "supplies-component"]
    # per-hop citations resolve to real claim ids; observed-vs-inferred is read structurally.
    assert all(h.claim_ids for h in a.hops)
    assert next(h for h in a.hops if h.edge == "based-at").observed_or_inferred == "observed"
    assert next(h for h in a.hops if h.edge == "equips").observed_or_inferred == "inferred"
    # the disqualifying line never appears: HT-233 stays a candidate, not a confirmed sole-source.
    assert "chokepoint_status=candidate" in a.answer
    assert "known-sole-source" not in a.answer


def test_ask_planted_gap_returns_refusal_payload_and_known_gap(hero_client, monkeypatch) -> None:
    # Drive the ReAct loop offline with a scripted planner (as ASK's own gap test does) so the endpoint
    # produces the *evidence-based* refusal, not a keyless capability refusal.
    monkeypatch.setattr(
        agent,
        "build_default_client",
        lambda *a, **k: planner(tool_turn("graph_check_sufficiency", {"scope": "comp_ht233"}), final()),
    )
    r = hero_client.post("/ask", json={"question": "what do we NOT know about HT-233's supplier?"})
    assert r.status_code == 200
    a = AskAnswer.model_validate(r.json())
    # Never a fabricated assessment — the non-negotiable.
    assert a.answer is None and a.refusal is not None
    assert a.refusal.missing
    assert a.refusal.next_coverage_due == "2026-09-01"
    assert a.refusal.known_gap is not None
    assert "insufficient evidence" in a.refusal.reason.lower()


def test_ask_is_deterministic_over_http(hero_client, monkeypatch) -> None:
    _use_hero_planner(monkeypatch)  # a fresh planner per ask() call → byte-stable, deterministic replay
    a = hero_client.post("/ask", json={"question": HERO_Q}).json()
    b = hero_client.post("/ask", json={"question": HERO_Q}).json()
    assert a == b


def test_ask_unknown_subject_lens_404(hero_client) -> None:
    r = hero_client.post("/ask", json={"question": HERO_Q, "subject": "lens-nope"})
    assert r.status_code == 404
