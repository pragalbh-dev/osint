"""API test harness — booted apps over the shared fixtures, offline (no keys), deterministic clock.

Two seed strategies (see API.md acceptance):

* **golden** — the F0 golden logs + config rebuilt through the *real* pipeline (RESOLVE→SCORE→…). Used
  for write/propagation tests (``/ingest``, ``/hitl``, ``/config``) where a live ``rebuild_and_swap`` must
  recompute honestly.
* **hero** — the ASK session's hand-authored hero view/claims/config (the C/02 thread: Karachi battery →
  CASIC, HT-233 as a *candidate* chokepoint, a planted sole-source gap). Injected as the held view for
  read-only contract tests (``/view`` lens, ``/node``, ``/evidence``, ``/ask``) — the known scenario the
  API forwards. The true corpus→pipeline→hero end-to-end is EVAL's remit.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api.state import AppState
from chanakya.config import ConfigStore
from chanakya.store import DecisionLog, EvidenceLog
from tests.agent import fixtures as hero_fx
from tests.fixtures import loaders

FIXED_TS = "2026-07-19T00:00:00+00:00"


def _clock() -> str:
    return FIXED_TS


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No keys in the environment — ASK/INGEST take their deterministic keyless paths (§6)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def build_golden_state(*, boot: bool = True) -> AppState:
    """AppState over the golden logs + config, rebuilt through the real pipeline."""
    state = AppState(
        loaders.golden_evidence_log(),
        loaders.golden_decision_log(),
        loaders.golden_config_store(),
        clock=_clock,
    )
    if boot:
        state.boot()
    return state


def build_hero_state() -> AppState:
    """AppState whose held view is the hand-authored hero view (evidence seeded with the hero claims so
    ``claims_map`` resolves; config from the hero bundle). Read-only endpoints only — a live rebuild would
    recompute from the 8 claims and not reproduce the hand-faked statuses."""
    evidence = EvidenceLog()
    evidence.append_many(list(hero_fx.hero_claims().values()))
    state = AppState(evidence, DecisionLog(), ConfigStore.from_bundle(hero_fx.hero_config()), clock=_clock)
    view = hero_fx.hero_view()
    view.alerts = []
    state.current_view = view
    state.ready = True
    return state


@pytest.fixture
def golden_state() -> AppState:
    return build_golden_state()


@pytest.fixture
def golden_client(golden_state: AppState) -> Iterator[TestClient]:
    with TestClient(create_app(golden_state)) as client:
        yield client


@pytest.fixture
def hero_state() -> AppState:
    return build_hero_state()


@pytest.fixture
def hero_client(hero_state: AppState) -> Iterator[TestClient]:
    with TestClient(create_app(hero_state)) as client:
        yield client
