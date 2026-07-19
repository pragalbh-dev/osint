"""The acceptance-run orchestrator: frozen scenario inputs → merged pipeline → assertable artifacts.

Everything here drives the *real* ``chanakya`` code over the *frozen* corpus + ``config/*.yaml``. No
scenario logic is hardcoded: the pipeline is fed only the pre-extracted claim bundles
(``corpus/scenarios/<scenario>/claims/*.json``, INGEST's keyless recording) and the eight config files;
``answer_key.json`` is loaded only as the *expectation set* the tests/report diff against, never to steer
the pipeline (master §, ``sessions/EVAL.md``).

The functions here are thin, deterministic wrappers over the frozen seams:

* :func:`load_scenario` — seed a live ``ConfigStore`` from ``config/`` + an ``EvidenceLog`` from the frozen
  bundles (the keyless boot path, byte-for-byte the live-extract output);
* :func:`build_view` — the pure reduction ``rebuild(evidence, decisions, config)`` with optional bi-temporal
  ``as_of`` rewind and subject-lens scoping;
* :func:`rebuild_with_decisions` — append analyst decisions to a decision log and re-reduce (the HITL
  propagation path, gate G12);
* :func:`fire_relocation_observable` — rewind to the pre-relocation epoch, reduce both epochs, and run the
  MONITOR delta evaluator (the seeded Rawalpindi→Rahwali tripwire);
* :func:`run_hero_query` — the deterministic fixed hero path through ASK (no LLM, keyless-reproducible).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from chanakya import settings
from chanakya.agent import ask
from chanakya.config import ConfigStore
from chanakya.ingest.seed import seed_store_from_bundles
from chanakya.observe import evaluate
from chanakya.schemas import (
    Alert,
    AskAnswer,
    ClaimRecord,
    ConfigBundle,
    DecisionRecord,
    GraphView,
)
from chanakya.store import EvidenceLog
from chanakya.view import apply_lens, rebuild

DEFAULT_SCENARIO = "hq9p_primary"
DEFAULT_LENS = "lens-hq9p-pk"
#: The epoch just before the 2025 relocation — the bi-temporal rewind that gives the observable a "before"
#: view to diff against. All 2021 basing claims are visible; the 2025 Rahwali passes are not yet.
PRE_RELOCATION_AS_OF = "2021-12-31"


# ── scenario location helpers ──────────────────────────────────────────────────────────────────────

def scenario_dir(scenario: str = DEFAULT_SCENARIO) -> Path:
    """The frozen scenario directory (docs + manifests + oracle) under the repo corpus root."""
    return settings.corpus_dir() / "scenarios" / scenario


def bundles_dir(scenario: str = DEFAULT_SCENARIO) -> Path:
    """The pre-extracted claim-bundle directory (INGEST's frozen keyless recording)."""
    return scenario_dir(scenario) / "claims"


def load_answer_key(scenario: str = DEFAULT_SCENARIO) -> dict:
    """Load the scenario oracle. **EVAL-only** — never call this from ``chanakya`` or ``config``."""
    return json.loads((scenario_dir(scenario) / "answer_key.json").read_text(encoding="utf-8"))


# ── the seeded inputs (config + evidence, the keyless boot path) ────────────────────────────────────

@dataclass(frozen=True)
class ScenarioInputs:
    """Everything a rebuild needs, seeded once from the frozen scenario (no LLM, no network).

    ``evidence`` is the append-only claim log seeded from the frozen bundles; ``claims`` is the
    ``claim_id → ClaimRecord`` lookup ASK's provenance drawer + observed-vs-inferred tagging need.
    ``answer_key`` is carried for the tests/report only — the pipeline never reads it.
    """

    scenario: str
    config_store: ConfigStore
    evidence: EvidenceLog
    claims: dict[str, ClaimRecord]
    answer_key: dict
    claim_count: int


def load_scenario(scenario: str = DEFAULT_SCENARIO) -> ScenarioInputs:
    """Seed a live config store + an evidence log from the frozen scenario — the keyless boot path.

    Loads all eight ``config/*.yaml`` sections into a ``ConfigStore`` and appends every frozen claim
    bundle into a fresh in-memory ``EvidenceLog`` (deterministic, filename-sorted order). Raises a clear
    error if the bundle directory is missing so a not-yet-recorded scenario fails loudly rather than
    silently rebuilding an empty graph.
    """
    bdir = bundles_dir(scenario)
    if not bdir.is_dir():
        raise FileNotFoundError(
            f"no claim bundles at {bdir} — record them first with "
            f"`python -m chanakya.ingest extract --scenario {scenario}` (needs an extraction key)"
        )
    config_store = ConfigStore.seed_from(settings.config_dir())
    evidence = EvidenceLog()
    count = seed_store_from_bundles(evidence, bdir)
    claims = {c.claim_id: c for c in evidence.replay()}
    return ScenarioInputs(
        scenario=scenario,
        config_store=config_store,
        evidence=evidence,
        claims=claims,
        answer_key=load_answer_key(scenario),
        claim_count=count,
    )


# ── the pure reduction (rebuild), with optional rewind + lens ───────────────────────────────────────

def _snapshot(inp: ScenarioInputs, *, as_of: str | None = None) -> ConfigBundle:
    """A config snapshot for one rebuild; sets the bi-temporal ``as_of`` on the local copy only."""
    cfg = inp.config_store.snapshot()
    if as_of is not None:
        cfg.credibility.as_of = as_of
    return cfg


def build_view(
    inp: ScenarioInputs,
    *,
    decisions: list[DecisionRecord] | None = None,
    as_of: str | None = None,
    lens: str | None = None,
) -> GraphView:
    """Reduce the seeded evidence (+ optional decisions) to a knowledge view via ``rebuild()``.

    ``as_of`` rewinds freshness/availability to a past epoch (bi-temporal); ``lens`` scopes the result to
    a subject (anchors + hop/materiality filter) via ``apply_lens``. Pure and deterministic — no LLM,
    network, clock or RNG runs inside ``rebuild()`` (gate G1/G2).
    """
    cfg = _snapshot(inp, as_of=as_of)
    view = rebuild(inp.evidence, decisions or [], cfg)
    if lens is not None:
        view = apply_lens(view, cfg.subjects.as_map()[lens])
    return view


def rebuild_with_decisions(
    inp: ScenarioInputs, decisions: list[DecisionRecord], *, lens: str | None = None
) -> GraphView:
    """Rebuild with an appended decision log — the HITL-propagation path (gate G12) as the tests drive it."""
    return build_view(inp, decisions=decisions, lens=lens)


# ── the seeded observable (bi-temporal before/after → delta evaluate) ────────────────────────────────

def fire_relocation_observable(inp: ScenarioInputs) -> list[Alert]:
    """Run the seeded Rawalpindi→Rahwali tripwire end-to-end and return the alerts it fires.

    The relocation is a *state change over time*, so the harness reduces two epochs from the one frozen
    corpus — the pre-relocation view (``as_of`` = 2021, Rawalpindi occupied) and the current view (Rahwali
    occupied, Rawalpindi superseded) — and hands the pair to MONITOR's delta evaluator. This exercises the
    whole occupancy-state-change path (armed observable → fire on rebuild) without any temporal fakery.
    """
    prev_view = build_view(inp, as_of=PRE_RELOCATION_AS_OF)
    view = build_view(inp)
    return evaluate(prev_view, view, inp.config_store.snapshot())


# ── the deterministic worked query (fixed hero path, no LLM) ─────────────────────────────────────────

def run_hero_query(inp: ScenarioInputs, view: GraphView | None = None) -> AskAnswer:
    """Run the worked multi-hop query through ASK's deterministic fixed hero path (keyless-reproducible).

    Uses the oracle's ``worked_query.text`` — which normalises to the subject lens's flagship
    ``target_query`` — so ASK takes the scripted ``link→gather→query_graph→cite`` hero path with no LLM
    call, giving a byte-stable answer/path on every run. ``claims`` is passed so each hop cites a real
    source span and observed/inferred tags resolve.
    """
    if view is None:
        view = build_view(inp)
    question = inp.answer_key["worked_query"]["text"]
    return ask(question, view, inp.config_store.snapshot(), llm=None, claims=inp.claims)
