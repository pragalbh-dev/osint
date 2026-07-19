"""Shared fixtures for the acceptance suite — build the merged-pipeline view once, reuse everywhere.

The heavy work (seed the frozen bundles → ``rebuild()`` the whole scenario) is session-scoped so the ~26
docs are reduced once, not per test. Every fixture drives the *real* ``chanakya`` pipeline via the
:mod:`eval.harness` orchestrator; ``answer_key`` is the oracle the tests diff against.

If the frozen claim bundles have not been recorded yet (``corpus/scenarios/<scenario>/claims`` absent),
the whole corpus-dependent suite **skips** with a loud reason rather than hard-erroring — the structural
guards (e.g. the ``answer_key`` separation test) still run. Record the bundles with
``python -m chanakya.ingest extract --scenario hq9p_primary`` (needs an extraction key) to turn the suite
green.
"""

from __future__ import annotations

import os

import pytest

from eval import harness


@pytest.fixture(autouse=True)
def _offline(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip extraction/agent keys for every non-``live`` test so the default run is keyless + deterministic."""
    if request.node.get_closest_marker("live") is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture(scope="session")
def scenario() -> harness.ScenarioInputs:
    """The seeded scenario (config store + evidence log from the frozen bundles). Skips if not recorded."""
    if not harness.bundles_dir().is_dir():
        pytest.skip(
            f"no frozen claim bundles at {harness.bundles_dir()} — record with "
            f"`python -m chanakya.ingest extract --scenario {harness.DEFAULT_SCENARIO}`"
        )
    return harness.load_scenario()


@pytest.fixture(scope="session")
def answer_key(scenario: harness.ScenarioInputs) -> dict:
    """The scenario oracle (EVAL-only)."""
    return scenario.answer_key


@pytest.fixture(scope="session")
def view(scenario: harness.ScenarioInputs):
    """The full rebuilt knowledge view (no lens) — the primary assertion target."""
    return harness.build_view(scenario)


@pytest.fixture(scope="session")
def lens_view(scenario: harness.ScenarioInputs):
    """The rebuilt view scoped to the C subject lens (anchors + hop/materiality filter)."""
    return harness.build_view(scenario, lens=harness.DEFAULT_LENS)


@pytest.fixture(scope="session")
def hero_answer(scenario: harness.ScenarioInputs):
    """The worked-query answer via ASK's deterministic fixed hero path (no LLM)."""
    return harness.run_hero_query(scenario)


@pytest.fixture(scope="session")
def live_enabled() -> bool:
    """Whether a real extraction/agent key is present (gates the opt-in ``@live`` beats)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"))
