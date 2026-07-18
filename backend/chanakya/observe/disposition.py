"""Read alert dispositions back off the decision log into per-observable tuning stats (spine/06).

MONITOR owns the **consumption** side of the disposition loop, not the writeback: HITL renders the
alert-disposition card and appends the ``alert_disposition`` ``DecisionRecord`` (§4.7); MONITOR reads
those records back on rebuild to surface which tripwires earn their keep vs over-fire, so an analyst
can decide to tighten one (a hot-config edit — never an auto-retune). Three honesty rules:

* the allowed verdicts come from each observable's ``disposition`` config, not a hardcoded enum;
* ``needs-more`` items are flagged as **awaiting coverage** (the non-negotiable — insufficiency is
  first-class), never silently closed;
* MONITOR only reports; it mutates no graph state.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from chanakya.schemas import DecisionRecord

REAL, NOISE, NEEDS_MORE = "real", "noise", "needs-more"


@dataclass
class DispositionStats:
    """Per-observable tuning signal derived from the decision log (fired vs how it was dispositioned)."""

    observable_id: str
    fired: int = 0  # alert_fired records seen for this observable
    counts: dict[str, int] = field(default_factory=dict)  # verdict → count (real/noise/needs-more/…)
    open_needs_more: list[str] = field(default_factory=list)  # instance refs awaiting more coverage

    @property
    def noise_rate(self) -> float | None:
        """Fraction of *dispositioned* alerts marked noise — the "should I tighten this?" signal."""
        total = sum(self.counts.values())
        return None if total == 0 else self.counts.get(NOISE, 0) / total


def _observable_id(rec: DecisionRecord) -> str | None:
    ctx = rec.context or {}
    return ctx.get("observable_id") or rec.subject_ref


def _verdict(rec: DecisionRecord) -> str | None:
    d: Any = rec.decision
    if isinstance(d, dict):
        return d.get("disposition") or d.get("verdict")
    return d if isinstance(d, str) else None


def _instance_ref(rec: DecisionRecord) -> str:
    ctx = rec.context or {}
    return ctx.get("instance") or ctx.get("subject") or rec.subject_ref or ""


def read_dispositions(records: Iterable[DecisionRecord]) -> dict[str, DispositionStats]:
    """Aggregate ``alert_fired`` + ``alert_disposition`` decision-log records → per-observable stats.

    Proves the HITL→MONITOR round-trip: an ``alert_disposition`` record appended by HITL is read back
    here for tuning, without MONITOR owning the writeback. Deterministic (insertion order preserved).
    """
    stats: dict[str, DispositionStats] = {}

    def _bucket(oid: str) -> DispositionStats:
        if oid not in stats:
            stats[oid] = DispositionStats(observable_id=oid)
        return stats[oid]

    for rec in records:
        oid = _observable_id(rec)
        if oid is None:
            continue
        if rec.type == "alert_fired":
            _bucket(oid).fired += 1
        elif rec.type == "alert_disposition":
            verdict = _verdict(rec)
            if verdict is None:
                continue
            s = _bucket(oid)
            s.counts[verdict] = s.counts.get(verdict, 0) + 1
            if verdict == NEEDS_MORE:
                s.open_needs_more.append(_instance_ref(rec))
    return stats
