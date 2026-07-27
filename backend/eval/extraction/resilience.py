"""Transport-fault retry — so a broken socket cannot destroy a paid bake-off.

A live run of this bake-off is 15 candidate-runs and ~195 billed calls, executed as one process. It has
no resume: ``run_bakeoff`` recomputes every candidate in memory and the per-candidate scores exist
nowhere on disk in a form ``decide`` could re-read. So a single raised exception anywhere in the loop
throws away every call bought before it.

That is exactly what happened on 2026-07-26. After ``anthropic-opus-5`` had completed all five runs, the
Gemini client raised a bare ``httpx.ReadError`` — ``[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]`` — out of
``generate_content``. A corrupted TLS record on one socket ended the comparison and wasted the Opus spend.

THE RULE THIS MODULE ENFORCES, AND THE LINE IT WILL NOT CROSS
─────────────────────────────────────────────────────────────
Retry **only** a call that never received an HTTP response. Never retry a response the provider actually
returned.

That line is not a convenience, it is what keeps the instrument honest:

* A transport fault — a reset socket, a corrupted TLS record, a DNS failure, a connect timeout — happened
  between this machine and the provider's edge. It is a fact about the network, and it carries **no
  information about the model**. Retrying it recovers a measurement that was never taken.
* A returned response is the model's or the provider's behaviour, and it is *scored*: a refusal, a 429, a
  500, a reply with no forced tool call, a payload outside the offered schema. ``structured_output_
  reliability`` exists to count exactly those. Retrying them would launder a candidate's reliability into
  a better number than it earned — the instrument measuring the thing it is supposed to expose. So the
  predicate below tests for transport failure and treats *everything else*, including every exception this
  repo's own clients raise (e.g. ``RuntimeError`` for a missing forced call), as final.

Nothing here changes a gate, a threshold, a metric definition or the margin rule, and it is applied
identically to all three candidates.

TWO EFFECTS ON THE NUMBERS, STATED RATHER THAN BURIED
─────────────────────────────────────────────────────
* ``structured_output_reliability`` does not count retried transport faults. It never did — before this
  module they did not produce a bad score, they produced no scorecard at all.
* ``latency_s`` is wall time, so a retried call carries its own backoff. That is honest wall time, but it
  is *network* time attributed to a candidate. ``latency_s`` carries weight 0 and is excluded from the
  composite, so it cannot move the verdict; :attr:`RetryingExtractionClient.retries` reports the count so
  a reader can see whether it happened at all.

This wrapper sits **inside** ``RecordingExtractionClient``, so the recorder logs one row per logical call
with its final outcome — a retried blip is invisible to the call log, and a genuine provider failure is
recorded and re-raised exactly as before.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

#: Total attempts per logical call (1 initial + 2 retries). Small on purpose: this exists to ride out a
#: single corrupted socket, not to paper over a provider outage. A real outage should still fail the run
#: loudly rather than burn the budget re-dialling.
MAX_ATTEMPTS = 3

#: Seconds to wait before attempt 2 and attempt 3.
BACKOFF_S = (2.0, 6.0)

#: Exception class names that every major SDK uses for "the request never reached us / no response came
#: back". Matched by name so this module imports no provider SDK and stays correct when one is absent.
_TRANSPORT_NAMES = frozenset({
    "APIConnectionError",     # openai + anthropic: connection failed / dropped
    "APITimeoutError",        # openai + anthropic: no response within the client timeout
    "ConnectError",           # httpx
    "ConnectTimeout",         # httpx
    "ReadError",              # httpx  <- the 2026-07-26 failure
    "ReadTimeout",            # httpx
    "WriteError",             # httpx
    "WriteTimeout",           # httpx
    "PoolTimeout",            # httpx
    "RemoteProtocolError",    # httpx: server closed mid-response
    "ProtocolError",          # httpcore
    "ServiceUnavailable",     # google api-core, when it surfaces a transport drop
})


def _chain(exc: BaseException) -> list[BaseException]:
    """The exception and everything it was raised from — SDKs wrap transport faults several deep."""
    seen: list[BaseException] = []
    cur: BaseException | None = exc
    while cur is not None and cur not in seen and len(seen) < 10:
        seen.append(cur)
        cur = cur.__cause__ or cur.__context__
    return seen


def is_transport_fault(exc: BaseException) -> bool:
    """True when no HTTP response was ever received, so the call carries no signal about the model.

    Deliberately conservative in the direction that protects the measurement: an exception carrying a
    ``status_code``/``response`` is a *returned* response and is never retried, whatever it is named. Only
    when nothing in the chain looks like a response, and something in it names a transport failure, does
    this return True.
    """
    chain = _chain(exc)
    # A provider that answered — even to say 429 or 500 — has told us something about itself. Final.
    for link in chain:
        if getattr(link, "status_code", None) is not None or getattr(link, "response", None) is not None:
            return False
    for link in chain:
        if type(link).__name__ in _TRANSPORT_NAMES:
            return True
        if isinstance(link, ConnectionError | TimeoutError):
            return True
    return False


@dataclass
class RetryingExtractionClient:
    """Wraps an ``ExtractionClient`` and retries **transport faults only**. See the module docstring.

    ``model_id`` is proxied and ``last_usage`` is read through to the inner client, so the wrapper is
    transparent to both the pipeline and :class:`~eval.extraction.recording.RecordingExtractionClient`.
    """

    inner: Any
    max_attempts: int = MAX_ATTEMPTS
    #: ``(description, attempt)`` for every retried fault, so a run can report whether any occurred.
    retries: list[tuple[str, int]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    #: Injectable so tests never actually sleep.
    sleep: Any = time.sleep

    def __post_init__(self) -> None:
        self.model_id = getattr(self.inner, "model_id", "unknown")

    @property
    def last_usage(self) -> dict[str, int] | None:
        """Read through, so the recorder still sees the provider's reported token usage."""
        return getattr(self.inner, "last_usage", None)

    def _attempt(self, what: str, fn: Any) -> dict[str, Any]:
        last: BaseException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except Exception as exc:
                if not is_transport_fault(exc) or attempt == self.max_attempts:
                    raise
                last = exc
                with self._lock:
                    self.retries.append((f"{what}: {type(exc).__name__}: {exc}", attempt))
                # Announced, never silent: a rescued network fault is not free — it costs a second
                # billed call and inflates that call's latency — so it has to be visible in the run log
                # rather than discovered later as an unexplained figure.
                print(f"[retry {attempt}/{self.max_attempts - 1}] transport fault on {what} "
                      f"({type(exc).__name__}: {exc}) — re-dialling", file=sys.stderr, flush=True)
                self.sleep(BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)])
        raise AssertionError(f"unreachable: retry loop exited without result or raise ({last!r})")

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        return self._attempt(
            f"extract[{tool_name}]",
            lambda: self.inner.extract(
                tool_name=tool_name, input_schema=input_schema, system=system, text=text, images=images
            ),
        )

    def read_image(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return self._attempt(
            f"read_image[{tool_name}]",
            lambda: self.inner.read_image(
                tool_name=tool_name, input_schema=input_schema, system=system, image=image,
                media_type=media_type,
            ),
        )


__all__ = ["BACKOFF_S", "MAX_ATTEMPTS", "RetryingExtractionClient", "is_transport_fault"]
