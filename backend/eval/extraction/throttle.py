"""Per-provider request pacing — so one capped account slows its own lane and not the whole run.

WHY THIS EXISTS
───────────────
The harness had exactly one concurrency knob, global to the run. On 2026-07-26 a live three-way run died
on ``openai.RateLimitError``: that account is capped at **3 requests per minute**, the run fanned eight
calls out at it, and the exception ended the process — discarding two other candidates' completed work
along with it. The cap is an account property, not a model property, and nothing in the bake-off's config
modelled it at all.

So pacing is now declared **per provider**, in ``config/bakeoff.yaml`` beside every other knob the run
depends on, and enforced per candidate. A candidate paced at 3 rpm takes as long as 3 rpm takes; the other
lanes run at full speed alongside it, because each candidate holds its own limiter and the candidates are
independent.

THE LINE THIS DOES NOT CROSS — throttling is not retrying
─────────────────────────────────────────────────────────
:mod:`.resilience` retries **transport faults only**: a call that never received an HTTP response carries
no information about the model, so re-dialling recovers a measurement that was never taken. A returned
response is never retried, whatever its status, because ``structured_output_reliability`` exists to score
exactly that — and a 429 is a returned response. Retrying through a rate limit would launder a provider's
own behaviour into a better number inside the instrument built to expose it.

This module is the other half of that discipline, and the reason it is a *throttle* and not a retry: the
honest way to deal with a cap is to **not exceed it**. Pace the calls, let the lane take the time it takes,
and if a 429 comes back anyway it is still counted against the candidate exactly as before. Nothing here
catches, inspects or re-issues any response.

WHAT IT COSTS, STATED
─────────────────────
The wait happens **outside** :class:`~eval.extraction.recording.RecordingExtractionClient`, so
``latency_s`` still measures the provider's own response time rather than the queue in front of it. That
is deliberate: a latency number inflated by our own pacing would say nothing about the model. The cost of
the pacing is wall-clock, and wall-clock is reported by the driver's projection, not attributed to a
candidate as a score.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RateLimit(BaseModel):
    """One provider's declared pacing. ``requests_per_minute: null`` means "no cap declared"."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    #: Requests per minute this provider's account tolerates. ``None`` = unpaced (full speed).
    requests_per_minute: float | None = Field(default=None, gt=0.0)
    #: How many calls may be in flight at once for this provider, regardless of rate. ``None`` = the
    #: run's global ``--concurrency``. A cap of 3/min with unbounded concurrency still bursts 3 at once,
    #: which some accounts refuse independently of the rate.
    max_concurrent: int | None = Field(default=None, ge=1)
    #: Free-text note carried onto the plan output, so an operator reading a slow lane is told why.
    note: str = ""

    @property
    def min_interval_s(self) -> float:
        """Seconds between successive request *starts*. Zero when unpaced."""
        if not self.requests_per_minute:
            return 0.0
        return 60.0 / float(self.requests_per_minute)

    def describe(self, provider: str) -> str:
        if not self.requests_per_minute and self.max_concurrent is None:
            return f"{provider}: unpaced (full speed)"
        bits: list[str] = []
        if self.requests_per_minute:
            bits.append(f"{self.requests_per_minute:g} req/min (one call every "
                        f"{self.min_interval_s:.1f}s)")
        if self.max_concurrent is not None:
            bits.append(f"max {self.max_concurrent} in flight")
        return f"{provider}: " + ", ".join(bits) + (f" — {self.note}" if self.note else "")


#: The unpaced default, used for any provider the config does not name.
UNPACED = RateLimit()


@dataclass
class RequestPacer:
    """A thread-safe minimum-interval gate over request *starts*, plus an optional in-flight cap.

    Interval pacing rather than a token bucket, and deliberately so: a bucket lets a lane burst its whole
    allowance in the first instant of every window, which is precisely the shape that trips a
    requests-per-minute cap when the window the provider is measuring does not line up with ours. Spacing
    the starts evenly cannot burst by construction, and the difference in total wall-clock across a run of
    this size is a few seconds.
    """

    limit: RateLimit
    #: Injectable so tests never actually sleep and never actually wait on a clock.
    sleep: Any = time.sleep
    clock: Any = time.monotonic
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _next_at: float = 0.0
    #: Total seconds this pacer has made callers wait — reported, never scored.
    waited_s: float = 0.0
    _semaphore: threading.Semaphore | None = None

    def __post_init__(self) -> None:
        if self.limit.max_concurrent is not None:
            self._semaphore = threading.BoundedSemaphore(self.limit.max_concurrent)

    def _reserve(self) -> float:
        """Claim the next slot and return how long the caller must wait for it. Holds the lock briefly."""
        interval = self.limit.min_interval_s
        if interval <= 0.0:
            return 0.0
        with self._lock:
            now = self.clock()
            start_at = max(now, self._next_at)
            self._next_at = start_at + interval
            return max(0.0, start_at - now)

    def acquire(self) -> None:
        if self._semaphore is not None:
            self._semaphore.acquire()
        delay = self._reserve()
        if delay > 0.0:
            with self._lock:
                self.waited_s += delay
            self.sleep(delay)

    def release(self) -> None:
        if self._semaphore is not None:
            self._semaphore.release()


@dataclass
class ThrottledExtractionClient:
    """Wraps an ``ExtractionClient`` and paces its calls. Transparent to the pipeline.

    Sits **outside** the recorder (``Throttled(Recording(Retrying(client)))``) for the reason in the module
    docstring: the wait must not land inside the measured latency. ``model_id`` and ``last_usage`` are
    proxied so both the pipeline and the recorder see the client they expect.
    """

    inner: Any
    pacer: RequestPacer

    def __post_init__(self) -> None:
        self.model_id = getattr(self.inner, "model_id", "unknown")

    @property
    def last_usage(self) -> dict[str, int] | None:
        return getattr(self.inner, "last_usage", None)

    def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
                images: Sequence[tuple[bytes, str]] = ()) -> dict[str, Any]:
        self.pacer.acquire()
        try:
            return self.inner.extract(tool_name=tool_name, input_schema=input_schema, system=system,
                                      text=text, images=images)
        finally:
            self.pacer.release()

    def read_image(self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
                   media_type: str) -> dict[str, Any]:
        self.pacer.acquire()
        try:
            return self.inner.read_image(tool_name=tool_name, input_schema=input_schema, system=system,
                                         image=image, media_type=media_type)
        finally:
            self.pacer.release()


@dataclass
class _VirtualClock:
    """A clock that only advances when something 'sleeps' on it. Nothing ever blocks."""

    t: float = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def virtual_pacer(limit: RateLimit) -> RequestPacer:
    """A pacer that computes the wait a live run would incur without actually incurring it.

    This is what lets ``--dry-run`` exercise the throttle for real — same reservation arithmetic, same
    ordering, same in-flight cap — and report the wall-clock floor a live run would face, instead of the
    operator being handed a number somebody worked out on paper. A dry run that skipped the pacer entirely
    would leave the one mechanism added to prevent a rate-limit death completely unexercised.
    """
    clock = _VirtualClock()
    return RequestPacer(limit=limit, sleep=clock.sleep, clock=clock.now)


def limit_for(rate_limits: dict[str, RateLimit] | None, provider: str) -> RateLimit:
    """The declared limit for a provider, or :data:`UNPACED`. Never guesses a cap it was not told."""
    return (rate_limits or {}).get(provider, UNPACED)


def projected_seconds(limit: RateLimit, calls: int, *, concurrency: int) -> float:
    """Wall-clock floor for ``calls`` requests through this pacer, ignoring the provider's own latency.

    Reported as a **floor**, and named as one wherever it is printed: it is what the pacing alone imposes.
    An unpaced lane returns 0.0, which does not mean instant — it means this pacer adds nothing and the
    lane's wall-clock is the provider's response time divided by the concurrency.
    """
    if calls <= 0:
        return 0.0
    interval = limit.min_interval_s
    if interval <= 0.0:
        return 0.0
    del concurrency  # pacing spaces STARTS, so concurrency cannot beat the interval
    return interval * (calls - 1)


__all__ = ["UNPACED", "RateLimit", "RequestPacer", "ThrottledExtractionClient", "limit_for",
           "projected_seconds", "virtual_pacer"]
