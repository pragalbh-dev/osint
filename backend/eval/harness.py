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
* :func:`fire_relocation_observable` — **stage a live ingest** (reduce the corpus without the relocation
  evidence, then with it) and run the MONITOR delta evaluator over that pair (the seeded
  Rawalpindi→Rahwali tripwire);
* :func:`run_hero_query` — the deterministic general ``supply_chain`` analysis (no LLM, keyless-reproducible).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from chanakya import settings
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

#: A **transaction-time** rewind date: "the graph as we KNEW it on this date", *not* "as it was" on that
#: date. ``rebuild(as_of=…)`` hides claims that had not yet arrived (``timeref.claim_available_iso``); it
#: says nothing about when the underlying facts were true in the world. Kept for the historical
#: knowledge-state demo only — the relocation beat does **not** use it (D-P4.5): all frozen bundles carry
#: one pinned ingest stamp, so any availability rewind before it empties the graph rather than producing
#: an honest "before".
KNOWN_AS_OF_REWIND_DATE = "2021-12-31"
#: Human-facing label for that knob. Never render it as "as it was on <date>".
KNOWN_AS_OF_REWIND_LABEL = "as we knew it on"

#: The documents whose arrival *is* the relocation event: the two 2025 Rahwali overhead passes. Staging
#: them out and back in is the beat's before/after — a transaction-time delta ("we just learned this"),
#: which is what an alert means. Named here (not scattered as literals) so a demo operator can stage a
#: different arrival by passing ``staged_docs=``. Derived enrichment bundles ride along with their source
#: document (``<doc>__basing.json``), so excluding a doc excludes everything inferred *from* it.
STAGED_RELOCATION_DOCS: tuple[str, ...] = ("d18_rahwali_pass1", "d19_rahwali_confirm")


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


def _seed_evidence(bdir: Path, exclude_docs: Sequence[str] = ()) -> tuple[EvidenceLog, int]:
    """Append the frozen bundles under ``bdir`` into a fresh log, optionally holding some documents back.

    This is *literally* the production keyless boot path — ``seed_store_from_bundles``, the same call
    ``chanakya.api.state.seed_evidence_keyless`` makes, including its ``exclude_docs`` hold-back (which
    rides the shared ``ingest.seed.bundle_belongs_to_doc`` grouping, so a held-back document takes its
    derived enrichment bundles with it rather than leaving an inference whose premises never arrived).
    EVAL deliberately keeps no second copy of that logic: the staged "before" the beat diffs against has
    to be the same graph the app really boots with when the same documents are withheld. Pure and
    deterministic — no clock, no model, no network.
    """
    evidence = EvidenceLog()
    return evidence, seed_store_from_bundles(evidence, bdir, exclude_docs=exclude_docs)


def load_scenario(
    scenario: str = DEFAULT_SCENARIO, *, exclude_docs: Sequence[str] = ()
) -> ScenarioInputs:
    """Seed a live config store + an evidence log from the frozen scenario — the keyless boot path.

    Loads all eight ``config/*.yaml`` sections into a ``ConfigStore`` and appends every frozen claim
    bundle into a fresh in-memory ``EvidenceLog`` (deterministic, filename-sorted order). Raises a clear
    error if the bundle directory is missing so a not-yet-recorded scenario fails loudly rather than
    silently rebuilding an empty graph.

    ``exclude_docs`` holds the named source documents (and anything derived from them) out of the log —
    the "before we ingested that" state a staged live ingest diffs against (:func:`staged_ingest_views`).
    It is an *input filter*, not a rewind: the claims are simply not there yet.
    """
    bdir = bundles_dir(scenario)
    if not bdir.is_dir():
        raise FileNotFoundError(
            f"no claim bundles at {bdir} — record them first with "
            f"`python -m chanakya.ingest extract --scenario {scenario}` (needs an extraction key)"
        )
    config_store = ConfigStore.seed_from(settings.config_dir())
    evidence, count = _seed_evidence(bdir, exclude_docs)
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
    """A config snapshot for one rebuild; sets the transaction-time ``as_of`` on the local copy only."""
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

    ``as_of`` is a **transaction-time** rewind — "the graph as we *knew* it on that date", hiding claims
    that had not yet arrived. It is not a valid-time filter and must never be labelled "as it was";
    ``lens`` scopes the result to
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


# ── the seeded observable (staged ingest → before/after → delta evaluate) ────────────────────────────

def staged_ingest_views(
    inp: ScenarioInputs, *, staged_docs: Sequence[str] = STAGED_RELOCATION_DOCS
) -> tuple[GraphView, GraphView]:
    """Reduce the corpus **without** ``staged_docs``, then **with** them → the ``(before, after)`` pair.

    This is a *transaction-time* delta and the honest shape of an alert: the analyst is warned when new
    information **arrives**, so the reference point is the graph as it stood before that ingest, not the
    world as it was on some date. Concretely: rebuild the log minus the staged documents (and minus
    everything inferred from them), then rebuild the full log — exactly the two states a real
    ``make ingest`` moves the system between, with no dating assumption and no rewind.

    Why not a rewind: every frozen bundle carries the one pinned ``ingest_time``, so an availability
    rewind (:data:`KNOWN_AS_OF_REWIND_DATE`) either keeps everything or empties the graph — there is no
    delta to detect. (D-P4.5; the rewind stays a separate, honestly-labelled feature.)

    Deterministic: both halves are pure ``rebuild()`` calls over filename-sorted appends of the same
    frozen bundles, so the pair — and the alerts it yields — is byte-identical on every run (gate G2).
    """
    before = load_scenario(inp.scenario, exclude_docs=staged_docs)
    return build_view(before), build_view(inp)


def fire_relocation_observable(
    inp: ScenarioInputs, *, staged_docs: Sequence[str] = STAGED_RELOCATION_DOCS
) -> list[Alert]:
    """Run the seeded relocation tripwire end-to-end over a staged ingest and return the alerts it fires.

    Stages the two 2025 Rahwali overhead passes (:data:`STAGED_RELOCATION_DOCS`) as the *arriving*
    evidence and hands the resulting before/after pair to MONITOR's delta evaluator. Nothing in the
    observable names the sites or the year (D-P4.10) — the origin and destination appear only in the
    fired alert, sourced from the graph, with the claim ids behind both sides.
    """
    prev_view, view = staged_ingest_views(inp, staged_docs=staged_docs)
    return evaluate(prev_view, view, inp.config_store.snapshot())


# ── the deterministic worked query (general supply-chain analysis, no LLM) ───────────────────────────

def run_hero_query(inp: ScenarioInputs, view: GraphView | None = None) -> AskAnswer:
    """Run the worked multi-hop query through the general ``supply_chain`` analysis (keyless-reproducible).

    The flagship trace is no longer a special-cased path in ``ask()``: live, the planner reaches it by
    calling ``graph_analyze``. This EVAL driver runs the SAME general analysis deterministically — anchored
    on the lens's basing site, tracing back toward the origin maker — so the demo contract has a byte-stable
    regression target without needing a model key. The question string is the lens's flagship
    ``target_queries[0]`` (deliberately NOT the oracle's ``worked_query.text`` — the answer key is graded
    against, never fed back in). ``inp.claims`` gives each hop a real source span + observed/inferred tag.
    """
    from chanakya.agent.analyses import run_analysis
    from chanakya.agent.assemble import assemble_answer
    from chanakya.agent.context import ToolContext
    from chanakya.agent.loop import _typed_anchor
    from chanakya.agent.validate import validate_answer
    from chanakya.schemas import RefusalPayload

    if view is None:
        view = build_view(inp)
    config = inp.config_store.snapshot()
    lens = config.subjects.as_map().get(DEFAULT_LENS)
    if lens is None or not lens.target_queries:
        raise ValueError(f"subject lens {DEFAULT_LENS!r} declares no target_queries to run as the worked query")
    ctx = ToolContext.build(view, inp.claims, config)
    # The observed subject is the lens's basing site (the "battery now based at …"); fall back to the first
    # anchor the view actually holds so the analysis' own generic variant-resolution can take over.
    subject = _typed_anchor(ctx, list(lens.anchors), "basing_site") or next(
        (a for a in lens.anchors if a in ctx.nodes_by_id), None
    )
    trace = run_analysis(ctx, lens.target_queries[0], subject or "", "supply_chain")
    answer = assemble_answer(trace, ctx)
    # Mirror ASK's deterministic tail: a positive answer that fails the citation checks is withheld, never
    # emitted as unbacked prose (the non-negotiable). Keyless ⇒ no entailment judge (deterministic only).
    if answer.answer is not None and not validate_answer(answer, trace, ctx, judge=None).ok:
        return AskAnswer(
            question=lens.target_queries[0],
            sub_questions=answer.sub_questions,
            answer=None,
            refusal=RefusalPayload(
                kind="withheld",
                missing=["citation/entailment check failed"],
                reason="Answer withheld: one or more sentences were uncited, unsupported, or not entailed by their evidence.",
            ),
        )
    return answer
