"""The evaluation reference-time ("now") — resolved **clock-free** so ``rebuild()`` stays pure (G1/G2).

Freshness and staleness need a "now" to measure ``age = now − event_time`` against, but the rebuild
call-path may not read a wall clock (gate G1) and must be byte-reproducible (gate G2). So "now" is an
**explicit input**, resolved here from config + the frozen logs — never ``date.today()``:

* **pinned** — ``config.credibility.as_of`` is an ISO ``YYYY-MM-DD`` (retro-analysis; a reproducible demo;
  or "advance the clock" to watch a confirmed fact decay to stale).
* **live "now"** — the API stamps today's date into ``config.credibility.as_of`` at request time (the
  clock read happens at the edge, outside the pure reduction) — indistinguishable from a pinned date here.
* **fallback** — ``as_of`` unset ⇒ the newest date any claim became available to us (``max`` over the log).

A *past* ``as_of`` also **rewinds** the graph: :func:`is_available_by` lets ``rebuild()`` hide claims that
had not arrived yet (an honest point-in-time "what did we know then" view). Everything here is pure
string/calendar arithmetic on the ISO bounds INGEST already froze — no network, no clock, no parsing of
free text (gate G1).
"""

from __future__ import annotations

from collections.abc import Iterable

from chanakya.schemas import ClaimRecord, ConfigBundle
from chanakya.schemas.values import canonical_iso_bounds


def claim_available_iso(claim: ClaimRecord) -> str | None:
    """The ISO date a claim became available to us — ``ingest_time`` if known, else ``report_time``.

    This is the *bitemporal availability* clock (when we received it), distinct from ``event_time`` (when
    the fact was true in the world). Used for the rewind filter, so "as of a past date" excludes evidence
    that had not yet arrived. Returns the latest bound of the coarsest available stamp, or ``None``.
    """
    for stamp in (claim.ingest_time, claim.report_time):
        _, hi = canonical_iso_bounds(stamp)
        if hi is not None:
            return hi
    return None


def effective_as_of(config: ConfigBundle, claims: Iterable[ClaimRecord]) -> str | None:
    """Resolve the evaluation "now" (ISO) clock-free: pinned ``as_of`` wins, else newest available claim.

    Returns ``None`` only when nothing is pinned *and* no claim carries a usable date — freshness then
    degrades gracefully to "durable" (no decay) rather than guessing a reference.
    """
    pinned = config.credibility.as_of
    if pinned:
        return pinned
    available = [iso for c in claims if (iso := claim_available_iso(c)) is not None]
    return max(available) if available else None


def is_available_by(claim: ClaimRecord, as_of: str | None) -> bool:
    """True if the claim had arrived by ``as_of`` (or ``as_of`` is unset / the claim has no date).

    Fail-open on a missing date: an undated claim is kept (we cannot prove it arrived *after* ``as_of``),
    which keeps the rewind conservative — it hides only evidence we can *show* was not yet available.
    """
    if not as_of:
        return True
    available = claim_available_iso(claim)
    return available is None or available <= as_of
