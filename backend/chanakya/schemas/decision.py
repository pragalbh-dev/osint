"""The decision log's records — **one schema for HITL, the learning loop, and audit** (§3.2, §4.2).

The analyst-decision subset of this log is *replay input*, not just telemetry: a ``status_override``
appended here mutates the view on the next ``rebuild()`` (gate G12), which is why HITL propagation is
structural rather than a bolted-on side effect. ``effects`` carries the state changes rebuild applies.
"""

from __future__ import annotations

from typing import Any, Literal

from .base import Record

Actor = Literal["system", "analyst", "agent"]
Stage = Literal["resolution", "credibility", "integrity", "alerting", "qna", "ontology", "coverage"]
DecisionType = Literal[
    "merge_proposal",
    "merge_adjudication",
    "status_override",
    "integrity_flag",
    "alert_fired",
    "alert_disposition",
    "template_eval",
    "schema_proposal",
    "coverage_event",
]


class DecisionRecord(Record):
    """A HITL adjudication or system event (spine/08 §3.2)."""

    event_id: str
    ts: str  # ISO-8601 wall-clock stamp of when the decision was made (supplied, never read in rebuild)
    actor: Actor
    stage: Stage
    type: DecisionType
    subject_ref: str | None = None  # claim / node / edge / merge / alert id this is about
    context: dict[str, Any] = {}  # the snapshot shown to the decider
    options: list[Any] = []  # what was offered
    decision: dict[str, Any] | str | None = None  # what was chosen (+ optional rationale)
    effects: dict[str, Any] = {}  # state changes rebuild applies (e.g. {"set_status": {...}})
