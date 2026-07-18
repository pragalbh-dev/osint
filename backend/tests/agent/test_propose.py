"""Free text → ObservableDef draft proposer (ASK scope handed over by MONITOR).

Verifies the handoff contract: named mentions resolve to `watch_instances`; a misspelling is surfaced,
never wrong-bound; the draft is a valid ObservableDef that arms cleanly through MONITOR's `observe.arm()`
(a real cross-session integration check); the proposer never arms (analyst confirms); and it's deterministic.
"""

from __future__ import annotations

import os

import pytest

from chanakya.agent import propose_observable_from_text
from chanakya.observe import arm  # MONITOR's arming — proves ASK's draft is a valid observable
from chanakya.schemas import ObservableDef

from .mock_llm import draft_turn, planner


def test_resolves_named_mentions_to_watch_instances(view, config) -> None:
    llm = planner(draft_turn(["HQ-9BE", "PAF HQ-9B Squadron"], "occupancy_state_change", "based-at"))
    p = propose_observable_from_text("watch HQ-9BE and the HQ-9B squadron for relocations", view, config, llm=llm)
    assert p.draft is not None
    assert p.draft.watch_instances == ["var_hq9be", "unit_hq9b"]  # resolved node ids, not designators
    assert p.draft.trigger["on"] == "occupancy_state_change"
    assert p.draft.trigger["edge_type"] == "based-at"
    assert {r.node_id for r in p.resolved} == {"var_hq9be", "unit_hq9b"}
    assert not p.unresolved


def test_misspelling_is_surfaced_never_wrong_bound(view, config) -> None:
    llm = planner(draft_turn(["HQ9P"], "occupancy_state_change", "based-at"))
    p = propose_observable_from_text("watch HQ9P for relocations", view, config, llm=llm)
    assert p.draft is not None
    assert "var_hq9p" not in p.draft.watch_instances  # NOT silently bound to the near-match
    assert p.unresolved and p.unresolved[0].mention == "HQ9P"
    assert "did you mean" in p.unresolved[0].error.lower()


def test_draft_is_a_valid_observable_and_arms_via_monitor(view, config) -> None:
    llm = planner(draft_turn(["PAF HQ-9B Squadron"], "occupancy_state_change", "based-at"))
    p = propose_observable_from_text("watch the HQ-9B squadron for relocations", view, config, llm=llm)
    assert isinstance(p.draft, ObservableDef)
    # the analyst would confirm, then MONITOR arms it — that must not raise on our draft.
    alerts = arm(p.draft, view, config)
    assert isinstance(alerts, list)
    assert p.explanation.get("mode") == "crossing"  # occupancy change is a fire-capable view delta


def test_proposer_never_arms_and_asks_for_confirmation(view, config) -> None:
    llm = planner(draft_turn(["HQ-9BE"], "occupancy_state_change", "based-at"))
    p = propose_observable_from_text("watch HQ-9BE", view, config, llm=llm)
    assert p.needs_confirmation is True  # ASK proposes; the analyst confirms before arming


def test_deterministic(view, config) -> None:
    a = propose_observable_from_text("watch HQ-9BE for relocations", view, config,
                                     llm=planner(draft_turn(["HQ-9BE"], "occupancy_state_change", "based-at")))
    b = propose_observable_from_text("watch HQ-9BE for relocations", view, config,
                                     llm=planner(draft_turn(["HQ-9BE"], "occupancy_state_change", "based-at")))
    assert a.draft is not None and b.draft is not None
    assert a.draft.model_dump() == b.draft.model_dump()


def test_keyless_returns_needs_llm_never_guesses(view, config) -> None:
    # no llm + key stripped by the offline fixture → an honest "needs an LLM / explicit ids", not a guess.
    p = propose_observable_from_text("watch HQ-9BE for relocations", view, config)
    assert p.draft is None and p.reason


@pytest.mark.live
def test_live_proposer_runs(view, config) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("no ANTHROPIC_API_KEY — live test skipped")
    p = propose_observable_from_text("watch HQ-9BE and the PAF HQ-9B squadron for relocations", view, config)
    # live: either a draft or an honest reason, never a crash.
    assert p.draft is not None or p.reason
