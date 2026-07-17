"""Programmatic accessors for the golden fixtures — the one place tests/gates load them from.

A Wave-1 session reusing these should import from here, not re-parse the JSON. Everything is loaded
from the committed JSON/YAML so the fixtures are the contract, and the loaders just validate them.
"""

from __future__ import annotations

import json
from pathlib import Path

from chanakya.config import ConfigStore
from chanakya.schemas import ClaimRecord, DecisionRecord, GraphView
from chanakya.store import DecisionLog, EvidenceLog
from chanakya.view import rebuild

GOLDEN = Path(__file__).parent / "golden"
PER_STAGE = Path(__file__).parent / "per_stage"


def golden_claims() -> list[ClaimRecord]:
    rows = json.loads((GOLDEN / "evidence_log.json").read_text())
    return [ClaimRecord.model_validate(r) for r in rows]


def golden_decisions() -> list[DecisionRecord]:
    rows = json.loads((GOLDEN / "decision_log.json").read_text())
    return [DecisionRecord.model_validate(r) for r in rows]


def golden_evidence_log() -> EvidenceLog:
    """A fresh in-memory evidence log seeded from the golden JSON."""
    log = EvidenceLog()
    log.seed_from(GOLDEN / "evidence_log.json")
    return log


def golden_decision_log() -> DecisionLog:
    """A fresh in-memory decision log seeded from the golden JSON."""
    log = DecisionLog()
    log.seed_from(GOLDEN / "decision_log.json")
    return log


def golden_config_store() -> ConfigStore:
    """A config store seeded from the golden ``config/*.yaml`` (also exercises the loader)."""
    return ConfigStore.seed_from(GOLDEN / "config")


def golden_view() -> GraphView:
    """The rebuilt view over the golden logs + config (the canonical golden output)."""
    store = golden_config_store()
    return rebuild(golden_evidence_log(), golden_decision_log(), store.snapshot())


def expected_view_json() -> str:
    return (GOLDEN / "expected_view.json").read_text()


# ── per-stage fixtures (seeds for Wave-1 sessions + gates G7/G8) ────────────────────────────────

def per_stage(name: str) -> dict:
    """Load a per-stage fixture JSON by name (without extension), e.g. ``per_stage("status_cases")``."""
    return json.loads((PER_STAGE / f"{name}.json").read_text())
