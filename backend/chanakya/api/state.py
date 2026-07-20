"""Held application state — the one live object every endpoint reads/writes (master §4.8, §1 inv. 3).

The API is a single always-on process wrapping the F0 store + config store + ``rebuild()`` view. This
module owns that runtime state:

* the append-only **evidence** + **decision** logs and the live **config** store;
* the last **rebuilt view** (served by ``GET /view``) and the **previous** view (fed to
  ``observe.evaluate`` for state-change alert deltas, and to ``rebuild`` for merge stability);
* an accumulating **alert feed** (``rebuild()`` never fills ``GraphView.alerts`` — MONITOR does, and the
  API stamps the wall-clock ``fired_ts`` on persist, keeping ``evaluate`` deterministic — G2).

Every write path (ingest / HITL / config) calls :meth:`AppState.rebuild_and_swap`, which rebuilds
in-process and atomically swaps the held view — so **nothing requires a restart** (§1 invariant 3). The
boot seed is source-agnostic: it prefers committed pre-extracted claim bundles (keyless), else stands up
an empty graph the analyst populates via ``/ingest`` — never fabricating a corpus that isn't there.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from chanakya import settings
from chanakya.config import ConfigStore
from chanakya.observe import evaluate
from chanakya.schemas import Alert, ClaimRecord, GraphView
from chanakya.store import DecisionLog, EvidenceLog
from chanakya.view import rebuild

# A clock is injectable so tests get deterministic ``fired_ts`` stamps (the only wall-clock the API adds).
Clock = Callable[[], str]

DEFAULT_SCENARIO = "hq9p_primary"


def utc_now_iso() -> str:
    """Wall-clock ISO-8601 (UTC) — the timestamp the API stamps onto fired alerts + decisions."""
    return datetime.now(UTC).isoformat()


class AppState:
    """The live runtime state. All view swaps are serialized under one lock; reads are lock-free
    (a view swap is a single atomic reference assignment, so a reader always sees a whole view)."""

    def __init__(
        self,
        evidence: EvidenceLog,
        decision: DecisionLog,
        config: ConfigStore,
        *,
        clock: Clock = utc_now_iso,
    ) -> None:
        self.evidence = evidence
        self.decision = decision
        self.config = config
        self._clock = clock
        self.current_view: GraphView | None = None
        self.prev_view: GraphView | None = None
        self.alerts: list[Alert] = []  # the accumulating alert feed across the session
        self.ready = False  # flips True only after the first successful rebuild() (the /health gate)
        self._lock = threading.RLock()

    # ── lifecycle ────────────────────────────────────────────────────────────────────────────────

    def boot(self) -> None:
        """Run the first ``rebuild()`` and flip readiness. Idempotent. Gates ``GET /health`` (master §7)."""
        with self._lock:
            snapshot = self.config.snapshot()
            view = rebuild(self.evidence, self.decision, snapshot)
            view.alerts = list(self.alerts)  # empty at boot — baseline is the reference point, no alerts
            self.current_view = view
            self.prev_view = None
            self.ready = True

    def rebuild_and_swap(self) -> list[Alert]:
        """Rebuild in-process from the (mutated) logs + live config, fire MONITOR on the delta, and
        atomically swap the held view. Returns the alerts fired by *this* delta (also appended to the
        session feed). This is the single mechanism behind hot-config / live-ingest / HITL propagation
        with **no restart** (§1 invariant 3, G12)."""
        with self._lock:
            snapshot = self.config.snapshot()
            old = self.current_view
            new = rebuild(self.evidence, self.decision, snapshot, prev_view=old)
            fired = evaluate(old, new, snapshot)  # [] when old is None (cold delta)
            stamp = self._clock()
            for alert in fired:
                if alert.fired_ts is None:
                    alert.fired_ts = stamp
            self.alerts.extend(fired)
            new.alerts = list(self.alerts)
            self.prev_view = old
            self.current_view = new
            return fired

    # ── accessors ────────────────────────────────────────────────────────────────────────────────

    def now(self) -> str:
        """The wall-clock stamp (injectable clock) for decisions/alerts the API persists."""
        return self._clock()

    def view(self) -> GraphView:
        """The current rebuilt view. Raises if called before :meth:`boot` (guarded by ``/health``)."""
        view = self.current_view
        if view is None:
            raise RuntimeError("app state not booted — call boot() first (see /health)")
        return view

    def claims_map(self) -> dict[str, ClaimRecord]:
        """``claim_id → ClaimRecord`` from the evidence log — the record bodies the view references by
        ID only. ASK needs this to cite a source/date/span and tag observed-vs-inferred; the provenance
        drawer needs it to resolve each claim → ``doc_ref``."""
        return {c.claim_id: c for c in self.evidence.replay()}


# ── boot seed resolution (keyless) ─────────────────────────────────────────────────────────────────


def scenario_bundles_dir(scenario: str | None = None) -> Path:
    """The frozen claim-bundle directory for ``scenario`` (``CHANAKYA_SCENARIO`` overrides the default)."""
    scenario = scenario or os.environ.get("CHANAKYA_SCENARIO", DEFAULT_SCENARIO)
    return settings.corpus_dir() / "scenarios" / scenario / "claims"


def resolve_withheld_docs(config: ConfigStore | None = None) -> list[str]:
    """The source documents deliberately **held out of the boot seed** — the reviewer's live-ingest set.

    Declared in ``config/sources.yaml`` → ``withheld_from_seed`` so the withholding is *auditable* (a
    reviewer reads which documents the boot graph is missing, in the same file that registers them),
    with ``CHANAKYA_SEED_WITHHOLD`` as the deploy-time escape hatch: a comma-separated list that
    replaces the declared one, and an **empty** value that withholds nothing (a full-corpus boot).

    Nothing here mutates a bundle — the withheld bundles ship on disk exactly as recorded and stay
    ingestable through the keyless ``POST /ingest`` lane. This decides only what is *already there* at
    boot, which is precisely what makes "the analyst is warned when evidence arrives" demonstrable.
    """
    env = os.environ.get("CHANAKYA_SEED_WITHHOLD")
    if env is not None:
        return [doc.strip() for doc in env.split(",") if doc.strip()]
    if config is None:
        return []
    return list(config.snapshot().sources.withheld_from_seed)


def seed_evidence_keyless(
    evidence: EvidenceLog,
    *,
    scenario: str | None = None,
    withheld_docs: Sequence[str] = (),
) -> int:
    """Seed the evidence log from committed pre-extracted claim bundles, if any are present.

    Returns the number of claims seeded — **0** when no bundles are committed yet (the app then boots to
    an empty graph the analyst populates via ``/ingest``, rather than inventing a corpus). The bundle
    scenario is overridable via ``CHANAKYA_SCENARIO``. This is the keyless boot path — no key, no LLM.

    ``withheld_docs`` holds the named documents (and everything derived from them) out of the seed —
    see :func:`resolve_withheld_docs`. The hold-back runs inside the *same* sorted append
    (``seed_store_from_bundles(exclude_docs=…)``), so a withheld boot is bit-for-bit the boot that would
    have happened had those documents not yet been collected — deterministic, gate G2.
    """
    from chanakya.ingest import seed_store_from_bundles  # lazy: keep `import chanakya.api` light

    bundles_dir = scenario_bundles_dir(scenario)
    if bundles_dir.is_dir() and any(bundles_dir.glob("*.json")):
        return seed_store_from_bundles(evidence, bundles_dir, exclude_docs=withheld_docs)
    return 0


def build_default_state(*, scenario: str | None = None, clock: Clock = utc_now_iso) -> AppState:
    """Build the un-booted runtime state for a keyless boot: live config store seeded from ``config/``,
    fresh in-memory logs, evidence seeded from committed bundles (if any) minus any documents the config
    withholds for the reviewer to ingest live. The caller (the lifespan startup) runs :meth:`AppState.boot`,
    so the readiness gate has an observable 503→200 transition."""
    config = ConfigStore.seed_from(settings.config_dir())
    evidence = EvidenceLog()
    decision = DecisionLog()
    seed_evidence_keyless(evidence, scenario=scenario, withheld_docs=resolve_withheld_docs(config))
    return AppState(evidence, decision, config, clock=clock)
