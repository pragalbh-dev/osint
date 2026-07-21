"""The general multi-hop analyses behind ``graph_analyze`` (replaces the old hardcoded hero path).

Every analysis is deterministic given the view, exposes only STATUS LABELS + names + claim ids (never a
confidence number), and surfaces UNKNOWN as a Known Gap — never a confident "no". These drive the fixture
directly; the real-corpus flagship contract lives in tests/acceptance/test_worked_query.py.
"""

from __future__ import annotations

from chanakya.agent import analyses
from chanakya.agent.assemble import assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.tools import run_tool


def _ctx(view, claims, config) -> ToolContext:
    return ToolContext.build(view, claims, config)


# ── chokepoint ────────────────────────────────────────────────────────────────────────────────

def test_chokepoint_leads_with_ht233_and_names_its_known_gap(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "var_hq9p", "chokepoint")
    assert r["refusal"] is None
    leading = r["leading"]
    assert leading["node_id"] == "comp_ht233"  # the best-evidenced nominee on the HQ-9/P fixture
    assert leading["chokepoint_status"] == "candidate"
    assert leading["substitutability_state"] == "UNKNOWN"
    # its Known Gap is attached, and every citation resolves to a real claim (never an edge id)
    assert leading["known_gap"]["id"] == "gap:comp_ht233:sole_source"
    assert leading["claim_ids"] and all(c in claims for c in leading["claim_ids"])
    assert isinstance(r["also_nominated"], list)  # the rest (none on this single-chokepoint fixture)


def test_chokepoint_never_exposes_a_confidence_number(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "var_hq9p", "chokepoint")
    for key in ("confidence", "assertion_confidence", "score"):
        assert key not in r["leading"]


def test_chokepoint_answer_renders_a_cited_derived_line(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    trace = analyses.run_analysis(ctx, "which component is the chokepoint?", "var_hq9p", "chokepoint")
    a = assemble_answer(trace, ctx)
    assert a.refusal is None and a.answer is not None
    assert "Chokepoint: HT-233 — chokepoint_status=candidate, substitutability=UNKNOWN" in a.answer
    assert a.citations and all(c in claims for c in a.citations)


def test_chokepoint_returns_its_traversal_and_renders_it_before_the_conclusion(view, claims, config) -> None:
    """Every analysis shows how it was traced: the chokepoint result carries hops (subject → leading
    component, same shape as supply_chain's), and the assembled answer puts that timeline FIRST, ahead of
    the 'Chokepoint:' conclusion (the frontend reads the first len(hops) lines as the timeline)."""
    ctx = _ctx(view, claims, config)
    r = analyses.analyze(ctx, "site_karachi", "chokepoint")
    # the internal traversal, in the same hop shape as supply_chain
    assert [h["edge"] for h in r["hops"]] == ["based-at", "inducted-into", "equips"]
    assert r["hops"][-1]["dst"] == "comp_ht233"  # the walk reaches the leading component
    for h in r["hops"]:
        assert set(h) >= {"src", "dst", "edge", "edge_id", "claim_ids", "status"}
        assert h["claim_ids"] and all(c in claims for c in h["claim_ids"])

    a = assemble_answer(analyses.run_analysis(ctx, "trace the chokepoint", "site_karachi", "chokepoint"), ctx)
    assert a.refusal is None and a.answer is not None
    # AskAnswer.hops is the timeline; it is non-empty and its lines come before the 'Chokepoint:' conclusion.
    assert [h.edge for h in a.hops] == ["based-at", "inducted-into", "equips"]
    lines = a.answer.split("\n")
    assert len(lines) > len(a.hops)  # timeline lines + at least the conclusion line
    assert not lines[0].startswith("Chokepoint:")           # hop timeline comes first
    assert lines[len(a.hops)].startswith("Chokepoint:")      # conclusion immediately after the timeline


def test_chokepoint_empty_pool_is_an_honest_refusal_not_a_no(view, claims, config) -> None:
    # site_rahwali is an isolated stale node with no chokepoint component nearby → insufficiency, not "none".
    r = analyses.analyze(_ctx(view, claims, config), "site_rahwali", "chokepoint")
    assert r["leading"] is None
    assert r["refusal"]["missing_slots"] == ["chokepoint_component"]
    assert "insufficient evidence" in r["refusal"]["reason"].lower()


# ── supply_chain ────────────────────────────────────────────────────────────────────────────────

def test_supply_chain_returns_the_full_chain_and_the_chokepoint(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "site_karachi", "supply_chain")
    assert r["refusal"] is None
    assert [h["edge"] for h in r["hops"]] == ["based-at", "inducted-into", "equips", "supplies-component"]
    assert r["chokepoint"]["node_id"] == "comp_ht233"
    assert r["chokepoint"]["known_gap"]["id"] == "gap:comp_ht233:sole_source"
    assert r["maker"]["node_id"] == "mfr_casic"
    assert r["sub_questions"] and len(r["sub_questions"]) == 4
    # every hop is cited to a real claim (no naked assertions)
    for h in r["hops"]:
        assert h["claim_ids"] and all(c in claims for c in h["claim_ids"])


def test_supply_chain_answer_names_the_chokepoint_gap(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    trace = analyses.run_analysis(ctx, "trace it back and name the chokepoint", "site_karachi", "supply_chain")
    a = assemble_answer(trace, ctx)
    assert a.refusal is None
    assert "chokepoint_status=candidate" in a.answer
    assert "insufficient evidence to assess" in a.answer.lower()
    assert a.sub_questions and len(a.sub_questions) == 4


def test_supply_chain_no_variant_refuses(view, claims, config) -> None:
    # from the isolated Rahwali node nothing resolves to a system/variant → an honest refusal, not a guess.
    r = analyses.analyze(_ctx(view, claims, config), "site_rahwali", "supply_chain")
    assert r["hops"] == [] and r["chokepoint"] is None
    assert r["refusal"]["missing_slots"] == ["variant"]


# ── sole_source ──────────────────────────────────────────────────────────────────────────────

def test_sole_source_splits_confirmed_from_candidate(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "var_hq9p", "sole_source")
    assert r["refusal"] is None
    # HT-233's substitutability is UNKNOWN → NOT a confirmed sole-source (the disqualifying line) …
    assert r["confirmed"] == []
    # … but it IS a candidate sole-source, carried as a Known Gap, never dropped.
    assert [el["node_id"] for el in r["candidates"]] == ["comp_ht233"]
    assert r["candidates"][0]["known_gap"]["id"] == "gap:comp_ht233:sole_source"
    assert r["candidates"][0]["claim_ids"] and all(c in claims for c in r["candidates"][0]["claim_ids"])


def test_sole_source_answer_labels_the_candidate(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    trace = analyses.run_analysis(ctx, "which parts are sole-source?", "var_hq9p", "sole_source")
    a = assemble_answer(trace, ctx)
    assert a.refusal is None and a.answer is not None
    assert "candidate sole-source" in a.answer
    assert "known-sole-source" not in a.answer


def test_sole_source_none_found_is_a_refusal(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "site_rahwali", "sole_source")
    assert r["confirmed"] == [] and r["candidates"] == []
    assert r["refusal"]["missing_slots"] == ["sole_source_component"]


# ── error guards + dispatch ─────────────────────────────────────────────────────────────────────

def test_analyze_unknown_subject_is_an_error(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "no_such_node", "chokepoint")
    assert r["error"] and "no node" in r["error"]
    assert "find_entity" in r["suggestion"]


def test_analyze_unknown_analysis_is_an_error(view, claims, config) -> None:
    r = analyses.analyze(_ctx(view, claims, config), "var_hq9p", "teleport")
    assert r["error"] and "teleport" in r["error"]
    assert "chokepoint, supply_chain, sole_source" in r["suggestion"]


def test_graph_analyze_dispatches_through_run_tool(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    ok = run_tool(ctx, "graph_analyze", {"subject_id": "var_hq9p", "analysis": "chokepoint"})
    assert ok.get("analysis") == "chokepoint" and ok["leading"]["node_id"] == "comp_ht233"
    # required-param validation is enforced by the dispatcher, like every other tool
    bad = run_tool(ctx, "graph_analyze", {"subject_id": "var_hq9p"})
    assert "error" in bad and "analysis" in bad["error"]
