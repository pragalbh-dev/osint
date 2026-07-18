"""HITL — the one cross-cutting adjudication service (session HITL; master §4.7; spine/05, §08 §3.10).

One service, one signature, callable from any spine layer or the analyst:
``enqueue(item, context, options, writeback) → decision``. Triage decides escalate-vs-auto
(deterministic, recall-biased); a disposition is written back as an **appended**
:class:`~chanakya.schemas.DecisionRecord`, and the next ``rebuild()`` applies its ``effects`` —
so "the human is in control" is *structural*, not a special code path (gate G12). All 8 control
points live in this one service (:mod:`controlpoints`); 3 are wired deep (merge / status-override /
alert-disposition), plus the analyst-initiated integrity flag.

**No LLM, no network, no clock, no RNG on the disposing path** (gate G1) — this package imports none
of ``anthropic``/``httpx``/``requests``; the triage-rank rubric LLM is offline and enters only as a
pre-baked, replayed ``frozen_rank`` (data, never a live call).
"""

from __future__ import annotations

from .controlpoints import (
    CONTROL_POINTS,
    CONTROL_POINTS_BY_KEY,
    ControlPoint,
    build_alert_disposition_item,
    build_integrity_flag_item,
    build_merge_item,
    build_status_override_item,
)
from .queue import ReviewQueue, build_item
from .service import dispose, enqueue
from .triage import STAR_TYPES, TriageConfig, order_queue, should_escalate
from .writeback import bind_writeback, build_record

__all__ = [
    # the service
    "enqueue", "dispose",
    # queue + envelope
    "ReviewQueue", "build_item",
    # triage
    "TriageConfig", "should_escalate", "order_queue", "STAR_TYPES",
    # writeback
    "bind_writeback", "build_record",
    # control points
    "CONTROL_POINTS", "CONTROL_POINTS_BY_KEY", "ControlPoint",
    "build_merge_item", "build_status_override_item", "build_alert_disposition_item",
    "build_integrity_flag_item",
]
