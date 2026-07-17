"""Shared pytest fixtures — expose the golden fixtures to every test/gate.

Everything is built fresh per test (in-memory logs) so tests never share mutable state.
"""

from __future__ import annotations

import pytest

from chanakya.config import ConfigStore
from chanakya.schemas import GraphView
from chanakya.store import DecisionLog, EvidenceLog
from tests.fixtures import loaders


@pytest.fixture
def golden_evidence() -> EvidenceLog:
    return loaders.golden_evidence_log()


@pytest.fixture
def golden_decision() -> DecisionLog:
    return loaders.golden_decision_log()


@pytest.fixture
def golden_config() -> ConfigStore:
    return loaders.golden_config_store()


@pytest.fixture
def golden_view() -> GraphView:
    return loaders.golden_view()
