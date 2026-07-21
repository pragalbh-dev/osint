"""Sub-question decomposition (spine/09) — a question that asks two or more DISTINCT things gets both
parts answered, each cited, rather than one tool answering the whole thing or the assembler dropping a half.

The live planner is steered (loop.SYSTEM_PROMPT) to decompose such a question into several ``graph_analyze``
calls; **this suite proves the deterministic assembly** of that decomposition: given a trace with two-or-more
successful ``analyze`` calls, :func:`assemble_answer` renders each as its own cited section, aggregates the
citations, records the decomposition in ``AskAnswer.sub_questions``, and keeps every assertion grounded
(``validate_answer`` passes). A single analysis is unchanged — no over-decomposition, no regression. The
model API is not exercised here (verification is fully deterministic).
"""

from __future__ import annotations

from chanakya.agent import analyses
from chanakya.agent.assemble import SUBQUESTION_HEADER_PREFIX, assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import AgentTrace, RecordedCall
from chanakya.agent.validate import validate_answer


def _ctx(view, claims, config) -> ToolContext:
    return ToolContext.build(view, claims, config)


def _multi_trace(ctx: ToolContext, question: str, specs: list[tuple[str, str]]) -> AgentTrace:
    """A trace with one recorded ``analyze`` call per (subject_id, analysis) — the exact shape the live
    ReAct loop leaves behind when the planner decomposes a question into several graph_analyze calls.
    Each result is the REAL analysis over the boot graph (analyses.analyze), so citations are real claims."""
    trace = AgentTrace(question=question, terminated="fixed")
    for subject_id, analysis in specs:
        result = analyses.analyze(ctx, subject_id, analysis)
        trace.calls.append(
            RecordedCall(name="analyze", input={"subject_id": subject_id, "analysis": analysis}, result=result)
        )
    return trace


def _headers(answer: str) -> list[str]:
    return [ln for ln in answer.split("\n") if ln.startswith(SUBQUESTION_HEADER_PREFIX)]


# ── the primary path: two distinct sub-answers, both cited ──────────────────────────────────────

def test_two_analyses_render_as_two_cited_sections(view, claims, config) -> None:
    """The flagship decomposition: 'trace HQ-9/P to its maker AND list its sole-source components' →
    a supply_chain trace AND a sole_source scan, each rendered as its own cited section."""
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(
        ctx,
        "Trace the HQ-9/P to its maker AND list its sole-source components",
        [("site_karachi", "supply_chain"), ("var_hq9p", "sole_source")],
    )
    a = assemble_answer(trace, ctx)

    assert a.refusal is None and a.answer is not None
    # BOTH sub-answers appear — each under its own header naming the sub-question it answers.
    headers = _headers(a.answer)
    assert len(headers) == 2
    assert any("supply chain" in h for h in headers)
    assert any("sole-source components" in h for h in headers)
    # the supply_chain section's key lines are present …
    assert "HT-233 is supplied by CASIC" in a.answer
    assert "Chokepoint: HT-233" in a.answer
    # … and the sole_source section's candidate line, side by side, in ONE coherent multi-section string.
    assert "HT-233 — candidate sole-source" in a.answer
    # every citation resolves to a real claim in the evidence log (the non-negotiable — never a naked assertion).
    assert a.citations and all(c in claims for c in a.citations)
    # the decomposition is recorded: sub_questions lists BOTH parts.
    assert a.sub_questions == [
        "Karachi Army Air Defence Site (Malir) — supply chain",
        "HQ-9P — sole-source components",
    ]
    # and the assembled answer passes the deterministic citation validator (headers exempt, all else cited).
    assert validate_answer(a, trace, ctx, judge=None).ok


def test_multi_section_leaves_hops_empty_so_every_line_is_cited_prose(view, claims, config) -> None:
    """The deliberate asymmetry: a multi-section answer has NO single coherent timeline, so ``hops`` is
    empty and every line renders as prose — which keeps the frontend's ``slice(hops.length)`` split valid.
    Each header line is uncited (a structural label); every non-header line carries a resolvable citation."""
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(
        ctx, "trace it AND name the sole-source parts",
        [("site_karachi", "supply_chain"), ("var_hq9p", "sole_source")],
    )
    a = assemble_answer(trace, ctx)
    assert a.hops == []  # no interleaved multi-trace timeline — the asymmetry with the single case
    for line in a.answer.split("\n"):
        if line.startswith(SUBQUESTION_HEADER_PREFIX):
            assert "[" not in line  # a header is a label, not a cited assertion
        else:
            assert line.rstrip().endswith("]")  # every content line ends with its cited claim marker


def test_single_analysis_keeps_its_hop_timeline_and_emits_no_header(view, claims, config) -> None:
    """The single-intent path is untouched: exactly one analyze call keeps its ``hops`` timeline (the
    frontend renders the first len(hops) lines as the numbered walk) and emits NO sub-question header —
    proving a single-intent question is never over-decomposed."""
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(ctx, "trace it back", [("site_karachi", "supply_chain")])
    a = assemble_answer(trace, ctx)
    assert a.answer is not None
    assert [h.edge for h in a.hops] == ["based-at", "inducted-into", "equips", "supplies-component"]
    assert _headers(a.answer) == []  # no decomposition header on a single-intent answer
    # its own 4-part sub_questions (from the supply_chain analysis) survive, not the decomposition labels.
    assert len(a.sub_questions) == 4


def test_three_analyses_combine_into_three_sections(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(
        ctx, "the chokepoint AND the supply trace AND the sole-source parts",
        [("var_hq9p", "chokepoint"), ("site_karachi", "supply_chain"), ("var_hq9p", "sole_source")],
    )
    a = assemble_answer(trace, ctx)
    assert a.refusal is None and a.answer is not None
    assert len(_headers(a.answer)) == 3
    assert len(a.sub_questions) == 3
    assert a.citations and all(c in claims for c in a.citations)
    assert validate_answer(a, trace, ctx, judge=None).ok


# ── honest refusal handling across parts ────────────────────────────────────────────────────────

def test_one_refused_one_succeeds_renders_the_success_and_names_the_gap(view, claims, config) -> None:
    """Some-succeed: render the successful part, NAME the refused part under its own header with its
    templated reason (never fabricated), and do NOT refuse the whole answer."""
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(
        ctx, "trace HQ-9/P back AND the chokepoint at the Rahwali site",
        [("site_karachi", "supply_chain"), ("site_rahwali", "chokepoint")],
    )
    a = assemble_answer(trace, ctx)
    assert a.refusal is None and a.answer is not None  # a partial success is NOT an outright refusal
    # the success renders in full …
    assert "HT-233 is supplied by CASIC" in a.answer
    # … and the refused part is named honestly under its header, with its insufficiency reason.
    assert "insufficient evidence" in a.answer.lower()
    assert len(a.sub_questions) == 2
    assert validate_answer(a, trace, ctx, judge=None).ok


def test_all_parts_refused_is_an_outright_refusal(view, claims, config) -> None:
    """All-refused: no positive body — a first-class refusal, never header-only prose asserting nothing."""
    ctx = _ctx(view, claims, config)
    trace = _multi_trace(
        ctx, "the chokepoint AND the sole-source parts at the isolated Rahwali site",
        [("site_rahwali", "chokepoint"), ("site_rahwali", "sole_source")],
    )
    a = assemble_answer(trace, ctx)
    assert a.answer is None
    assert a.refusal is not None
    assert "insufficient evidence" in a.refusal.reason.lower()
    # the attempted decomposition is still recorded on the refusal — it names the parts it tried.
    assert len(a.sub_questions) == 2
