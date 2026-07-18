"""One opt-in ``@live`` test exercising the real Anthropic API (skipped in CI / without a key)."""

from __future__ import annotations

import os

import pytest

from chanakya.agent import ask


@pytest.mark.live
def test_live_free_loop_answers_or_refuses(view, claims, config) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("no ANTHROPIC_API_KEY — live test skipped")
    # A non-flagship query routes to the live free loop (real planner + entailment judge).
    a = ask("Who manufactures HT-233?", view, config, claims=claims)
    # Live behaviour is non-deterministic, so assert only the invariant: a cited answer or an honest refusal.
    assert (a.answer is not None and a.citations) or a.refusal is not None
    if a.answer is not None:
        assert all(c in claims for c in a.citations)
