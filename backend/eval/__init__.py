"""Acceptance harness (EVAL) — drive the *real merged pipeline* over the frozen scenario and report.

This package wires the merged Wave-1 spine (INGEST seed → ``rebuild()`` → MONITOR → ASK) to the frozen
``corpus/scenarios/<scenario>`` inputs and produces a legible pass/fail report against the scenario's
``answer_key.json`` oracle. It writes **no module logic** — every stage it calls lives in ``chanakya`` and
every expectation lives in ``answer_key.json``; the harness only orchestrates and diffs.

The single hard rule (master §, ``sessions/EVAL.md`` scope #3): ``answer_key.json`` is **EVAL-only**. It is
read here and under ``tests/acceptance/`` — never by ``chanakya`` (the pipeline) or ``config/`` — so the
pipeline is never tuned to the oracle it is graded against. The harness feeds the pipeline only corpus
docs / pre-extracted claim bundles + ``config/*.yaml``.
"""

from __future__ import annotations

from eval.harness import (
    STAGED_RELOCATION_DOCS,
    ScenarioInputs,
    build_view,
    fire_relocation_observable,
    load_answer_key,
    load_scenario,
    rebuild_with_decisions,
    run_hero_query,
    staged_ingest_views,
)

__all__ = [
    "STAGED_RELOCATION_DOCS",
    "ScenarioInputs",
    "build_view",
    "fire_relocation_observable",
    "load_answer_key",
    "load_scenario",
    "rebuild_with_decisions",
    "run_hero_query",
    "staged_ingest_views",
]
