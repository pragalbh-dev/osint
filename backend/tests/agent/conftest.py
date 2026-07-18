"""Pytest fixtures for the ASK agent suite — the hand-authored hero view/claims/config as test input.

An autouse fixture strips ``ANTHROPIC_API_KEY``/``GEMINI_API_KEY`` for every non-``@live`` test so the
agent runs its deterministic offline path (fixed hero path / mocked LLM) regardless of the developer's
environment — the acceptance requires the tool layer + citations to be run-invariant (master §6).
"""

from __future__ import annotations

import pytest

from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView

from .fixtures import hero_claims, hero_config, hero_view


@pytest.fixture(autouse=True)
def _offline(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("live") is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def view() -> GraphView:
    return hero_view()


@pytest.fixture
def claims() -> dict[str, ClaimRecord]:
    return hero_claims()


@pytest.fixture
def config() -> ConfigBundle:
    return hero_config()
