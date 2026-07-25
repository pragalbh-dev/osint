"""AH-1 (lens half) — an unresolved lens anchor must reach a surface, not just ``meta``.

``apply_lens`` has recorded ``meta.anchors_resolved`` / ``anchors_missing`` / ``anchor_resolution``
since AR-2, and a grep across ``frontend/`` and ``backend/chanakya/api/`` found **zero** consumers
outside ``lens.py`` and its own tests. So in practice a lens that could not find its own subject
returned a quietly smaller — or entirely empty — graph, and the analyst was told nothing. An empty
result that means "we could not look" is indistinguishable from one that means "there is nothing there",
which is the failure this system exists to refuse.

The fix routes it into the object this system already uses for exactly this: a first-class Known Gap,
which rides on ``GET /view`` and is read by the retrieval tools. These tests pin both directions — a
healthy lens gains nothing, a broken one gains a named refusal.
"""

from __future__ import annotations

from chanakya.schemas import EdgeView, GraphView, KnownGap, NodeView, SubjectLens
from chanakya.view import apply_lens


def _view() -> GraphView:
    return GraphView(
        nodes=[
            NodeView(id="unit_paad", type="unit", name="Pakistan Army Air Defence"),
            NodeView(id="var_hq9p", type="variant", name="HQ-9/P"),
            NodeView(id="site_x", type="basing_site", name="Site X"),
        ],
        edges=[
            EdgeView(id="e1", type="fields", source="unit_paad", target="var_hq9p"),
            EdgeView(id="e2", type="based-at", source="unit_paad", target="site_x"),
        ],
        known_gaps=[KnownGap(id="pre-existing", what_missing="something else", observability_ceiling="confirmable")],
    )


def _gap(out: GraphView) -> KnownGap | None:
    return next((g for g in out.known_gaps if g.id.startswith("gap-anchor-unresolved")), None)


# ── the working path is untouched ────────────────────────────────────────────────────────────────

def test_healthy_lens_gains_no_gap_and_no_warning() -> None:
    """A lens whose anchors all resolve is byte-identical to before — no cry-wolf gap, no meta key."""
    out = apply_lens(_view(), SubjectLens(subject_id="s", anchors=["unit_paad"], max_hops=3))
    assert [g.id for g in out.known_gaps] == ["pre-existing"]
    assert "anchor_warning" not in out.meta
    assert len(out.nodes) == 3


# ── a broken anchor is loud ──────────────────────────────────────────────────────────────────────

def test_all_miss_emits_a_named_known_gap_not_a_bare_empty_view() -> None:
    out = apply_lens(_view(), SubjectLens(subject_id="s", anchors=["unit_paaad_typo"], max_hops=3))
    assert out.nodes == []

    gap = _gap(out)
    assert gap is not None, "an empty view with no gap says 'nothing to report' — the disqualifying lie"
    assert "unit_paaad_typo" in gap.what_missing
    assert "NOT because there is nothing to report" in gap.what_missing
    assert gap.missing_slots == ["anchor:unit_paaad_typo"]
    # It names the next step rather than inventing a coverage date it cannot know.
    assert "Next step" in gap.what_missing
    assert gap.next_coverage_due is None


def test_all_miss_carries_the_same_sentence_on_meta() -> None:
    """One sentence, so a consumer never has to re-derive the meaning from three parallel lists."""
    out = apply_lens(_view(), SubjectLens(subject_id="s", anchors=["unit_paaad_typo"], max_hops=3))
    assert "unit_paaad_typo" in out.meta["anchor_warning"]
    gap = _gap(out)
    assert gap is not None
    assert out.meta["anchor_warning"] in gap.what_missing


def test_partial_miss_is_reported_even_though_the_lens_still_returns_a_graph() -> None:
    """The dangerous case: a plausible-looking graph that is quietly missing a whole branch."""
    lens = SubjectLens(subject_id="s", anchors=["unit_paad", "site_gone_typo"], max_hops=3)
    out = apply_lens(_view(), lens)
    assert len(out.nodes) == 3, "the resolvable anchor still scopes normally"

    gap = _gap(out)
    assert gap is not None
    assert "site_gone_typo" in gap.what_missing
    assert "partially scoped" in gap.what_missing
    assert "1 of 2" in gap.what_missing  # not reported as a total failure
    assert "not evidence of absence" in gap.what_missing


def test_the_gap_survives_lens_scoping() -> None:
    """The anchor gap is about the lens itself, so it must not be filtered out by the lens's own scope."""
    out = apply_lens(_view(), SubjectLens(subject_id="s", anchors=["gone_a", "gone_b"], max_hops=3))
    assert out.nodes == [] and out.edges == []
    assert _gap(out) is not None
