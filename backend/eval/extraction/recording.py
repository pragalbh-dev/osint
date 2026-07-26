"""The instrumented wrapper: every extraction call, its raw filled arguments, its latency and its usage.

Three of the scored criteria can only be measured *at the call*, not on the finished ``ClaimRecord``s:

* **structured-output / tool-call reliability** — did the forced call come back at all, and did it come
  back inside the offered schema (no invented top-level fields)?
* **discriminator capture (A7)** — ``MentionContext`` is populated by the model but consumed by nothing
  downstream yet (RK-COREF/S3 is where it enters the identity judgement), so it never reaches a
  ``ClaimRecord``. The only place to see it is the raw tool payload.
* **cost + latency** — wall time per call, and token usage when the provider reports it.

So the harness wraps whatever client a candidate resolves to and records those three things, without
changing a byte of what the pipeline receives. Thread-safe, because ``lane.extract_many`` fans calls out
across threads.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CallRecord:
    """One forced-tool call as it actually happened."""

    lane: str  # "text" | "image"
    tool_name: str
    #: Top-level property names the offered schema declared — the reference set for "invented field".
    offered_fields: tuple[str, ...]
    #: The model's filled arguments, verbatim. ``None`` when the call raised.
    payload: dict[str, Any] | None
    latency_s: float
    error: str | None = None
    usage: dict[str, int] | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and isinstance(self.payload, dict)

    def invented_fields(self) -> tuple[str, ...]:
        """Top-level keys the model returned that the offered schema never declared.

        An empty ``offered_fields`` means the schema declared no ``properties`` at all, in which case
        nothing can be called invented and this returns empty — an unmeasurable case, not a clean one.
        """
        if not self.ok or not self.offered_fields:
            return ()
        assert self.payload is not None
        return tuple(sorted(k for k in self.payload if k not in set(self.offered_fields)))


@dataclass
class RecordingExtractionClient:
    """Wraps an ``ExtractionClient`` and logs every call. Transparent to the pipeline.

    ``model_id`` is proxied so ``Extraction.version`` still stamps the real model onto every claim.
    """

    inner: Any
    calls: list[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        self.model_id = getattr(self.inner, "model_id", "unknown")

    # ── plumbing ──────────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _offered(input_schema: dict[str, Any]) -> tuple[str, ...]:
        props = input_schema.get("properties") if isinstance(input_schema, dict) else None
        return tuple(sorted(props)) if isinstance(props, dict) else ()

    def _record(self, lane: str, tool_name: str, input_schema: dict[str, Any], fn: Any) -> dict[str, Any]:
        started = time.perf_counter()
        payload: dict[str, Any] | None = None
        error: str | None = None
        try:
            payload = fn()
            return payload
        except Exception as exc:  # recorded, then re-raised — reliability is a measurement, not a rescue
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = time.perf_counter() - started
            usage = getattr(self.inner, "last_usage", None)
            record = CallRecord(
                lane=lane, tool_name=tool_name, offered_fields=self._offered(input_schema),
                payload=payload if isinstance(payload, dict) else None, latency_s=elapsed,
                error=error, usage=dict(usage) if isinstance(usage, dict) else None,
            )
            with self._lock:
                self.calls.append(record)

    # ── the ExtractionClient surface ──────────────────────────────────────────────────────────────

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        return self._record(
            "text", tool_name, input_schema,
            lambda: self.inner.extract(
                tool_name=tool_name, input_schema=input_schema, system=system, text=text, images=images
            ),
        )

    def read_image(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return self._record(
            "image", tool_name, input_schema,
            lambda: self.inner.read_image(
                tool_name=tool_name, input_schema=input_schema, system=system, image=image,
                media_type=media_type,
            ),
        )

    # ── replay ────────────────────────────────────────────────────────────────────────────────────

    @classmethod
    def replay(cls, calls: Sequence[CallRecord]) -> RecordingExtractionClient:
        """A recorder holding calls that already happened — no inner client, nothing callable.

        The roll-ups below read nothing but ``self.calls``, so a run assembled from cached documents is
        scored through exactly the same object as a run that just happened. That matters more than it
        looks: three of the criteria are measured at the CALL and never reach a ``ClaimRecord``, so a
        resumed run scored without its call records would report reliability, discriminators and cost as
        unmeasured while looking complete. ``inner`` is ``None`` on purpose — calling this raises rather
        than silently re-buying a call the caller believed was cached.
        """
        return cls(inner=None, calls=list(calls))

    # ── roll-ups ──────────────────────────────────────────────────────────────────────────────────

    def image_calls(self) -> list[CallRecord]:
        """Every standalone-imagery (VLM) call — the evidence the VLM gate is judged on."""
        return [c for c in self.calls if c.lane == "image"]

    def total_latency_s(self) -> float:
        return sum(c.latency_s for c in self.calls)

    def total_usage(self) -> dict[str, int] | None:
        """Summed token usage, or ``None`` when *no* call reported any (never a fabricated zero)."""
        reported = [c.usage for c in self.calls if c.usage]
        if not reported:
            return None
        return {
            "input_tokens": sum(int(u.get("input_tokens", 0)) for u in reported),
            "output_tokens": sum(int(u.get("output_tokens", 0)) for u in reported),
            "calls_reporting_usage": len(reported),
        }


__all__ = ["CallRecord", "RecordingExtractionClient"]
