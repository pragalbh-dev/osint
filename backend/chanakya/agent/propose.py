"""Free text → ``ObservableDef`` draft proposer (ASK scope, handed over by MONITOR).

An analyst types what they want to watch — *"watch HQ-9B and the 8th SAM regiment for relocations"* — and
this turns it into a **draft** tripwire the analyst confirms before arming. It reuses the exact same
discipline as the rest of ASK:

* the **LLM proposes** the structure (which entities, what kind of trigger, urgency) — a proposer *upstream*
  of any state change, never an authority (invariant #2);
* ``find_entity`` **resolves named mentions to resolved node IDs** → ``watch_instances`` (matched on the
  resolved instance, never a designator string), and an unresolvable mention is **surfaced with its
  "did you mean" suggestion — never silently bound to the wrong entity**;
* the result is a **draft only** — ``propose_*`` never arms; the analyst confirms, then MONITOR's
  ``arm()``/``evaluate()`` take over (the human-in-the-loop gate);
* MONITOR's ``explain()`` is attached so the confirm screen shows exactly what the tripwire will do (or why
  a claim-level trigger can only *arm*, not *fire*).

MONITOR pre-wired the target for this: ``ObservableDef.watch_instances`` (F0-amendment #9) + ``explain()``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from chanakya.observe import explain
from chanakya.schemas import ConfigBundle, GraphView, ObservableDef

from .client import build_default_client
from .context import ToolContext, normalize
from .tools import run_tool

if TYPE_CHECKING:
    from chanakya.agent.client import LLMClient

# Trigger vocabulary the analyst's intent maps to (mirrors MONITOR's compile_trigger tokens). Fire-capable
# ones compile to a view-delta condition; `new_claim` is honestly arm-only (claims aren't in the view).
_TRIGGER_ONS = ["occupancy_state_change", "geofence_crossing", "state_change", "new_edge", "new_claim", "exists"]
# Default `match_on` per trigger (always resolved-instance keys, never designator strings — spine/08 §3.8).
_MATCH_ON: dict[str, list[str]] = {
    "occupancy_state_change": ["resolved_unit", "site_instance"],
    "geofence_crossing": ["resolved_unit"],
    "state_change": ["resolved_instance"],
    "new_edge": ["resolved_src", "resolved_dst"],
    "new_claim": ["resolved_unit"],
    "exists": ["resolved_instance"],
}

PROPOSE_SYSTEM = (
    "You draft a monitoring tripwire from an analyst's plain-English request. Call draft_observable ONCE "
    "with: `mentions` = every entity/unit/system/place named to watch (verbatim, for later resolution); "
    "`trigger_on` = the closest trigger kind from the enum (relocation/occupancy → occupancy_state_change; "
    "enters/leaves an area → geofence_crossing; a new supply/contract link → new_edge; a new report/claim → "
    "new_claim; a generic field change → state_change); `edge_type` = the relationship it concerns if any "
    "(e.g. based-at); `severity`. Do NOT resolve ids yourself and do NOT arm anything — you only draft."
)

DRAFT_TOOL: dict[str, Any] = {
    "name": "draft_observable",
    "description": "Emit the structured draft of a monitoring tripwire from the analyst's request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "mentions": {"type": "array", "items": {"type": "string"},
                         "description": "entities/units/systems/places named to watch, verbatim"},
            "trigger_on": {"type": "string", "enum": _TRIGGER_ONS},
            "edge_type": {"type": "string", "description": "the relationship concerned, if any (e.g. based-at)"},
            "severity": {"type": "string", "description": "e.g. notify | escalate"},
        },
        "required": ["mentions", "trigger_on"],
        "additionalProperties": False,
    },
    "strict": True,
}


@dataclass
class ResolvedMention:
    mention: str
    node_id: str
    name: str | None = None


@dataclass
class UnresolvedMention:
    mention: str
    error: str
    suggestion: str = ""


@dataclass
class ObservableProposal:
    """A draft tripwire for the analyst to confirm — never armed by ASK."""

    draft: ObservableDef | None
    explanation: dict[str, Any] = field(default_factory=dict)
    resolved: list[ResolvedMention] = field(default_factory=list)
    unresolved: list[UnresolvedMention] = field(default_factory=list)
    needs_confirmation: bool = True  # ASK proposes; the analyst confirms before MONITOR arms it
    reason: str = ""


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json(text: str) -> dict[str, Any] | None:
    m = _JSON_RE.search(text or "")
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _slug(text: str) -> str:
    tokens = [t for t in re.sub(r"[^a-z0-9\s-]", "", normalize(text)).split() if t][:5]
    return "obs-proposed-" + ("-".join(tokens) if tokens else "observable")


def propose_observable_from_text(
    text: str,
    view: GraphView,
    config: ConfigBundle,
    llm: LLMClient | None = None,
) -> ObservableProposal:
    """Draft an ``ObservableDef`` from free text — LLM proposes, ``find_entity`` resolves, analyst confirms."""
    ctx = ToolContext.build(view, {}, config)  # claims not needed to propose a tripwire
    resolved_llm = llm if llm is not None else build_default_client()
    if resolved_llm is None:
        return ObservableProposal(
            draft=None,
            reason="No LLM available to interpret the request. Set ANTHROPIC_API_KEY, or define the "
            "observable explicitly (a multi-select of resolved ids populates watch_instances directly).",
        )

    resp = resolved_llm.run_turn(system=PROPOSE_SYSTEM, messages=[{"role": "user", "content": text}], tools=[DRAFT_TOOL])
    payload: dict[str, Any] | None = resp.tool_calls[0].input if resp.tool_calls else _parse_json(resp.text)
    if not payload:
        return ObservableProposal(draft=None, reason="Could not interpret the request into an observable draft.")

    mentions = [m for m in payload.get("mentions", []) if isinstance(m, str)]
    trigger_on = payload.get("trigger_on", "state_change")
    edge_type = payload.get("edge_type")
    severity = payload.get("severity") or "notify"

    resolved: list[ResolvedMention] = []
    unresolved: list[UnresolvedMention] = []
    watch: list[str] = []
    for mention in mentions:
        r = run_tool(ctx, "graph_find_entity", {"text": mention})
        cands = r.get("candidates") or []
        # Arming a tripwire is safety-critical, so bind ONLY an EXACT resolution. A near-miss (the
        # punctuation-squashed or fuzzy tier), ambiguous, or none result is SURFACED for the analyst to
        # confirm — never silently armed on a look-alike (spine/08 §3.8; the HITL gate). The hero *query*
        # path binds a near-miss because a cited read is reversible; arming a watch is not.
        if r.get("resolution") == "exact" and cands:
            top = cands[0]
            if top["node_id"] not in watch:
                watch.append(top["node_id"])
            resolved.append(ResolvedMention(mention=mention, node_id=top["node_id"], name=top.get("name")))
        elif cands:
            top = cands[0]
            names = ", ".join((c.get("name") or c["node_id"]) for c in cands[:3])
            unresolved.append(UnresolvedMention(
                mention=mention,
                error=f"no exact match for '{mention}' — did you mean '{top.get('name') or top['node_id']}'?",
                suggestion=f"confirm one of: {names}",
            ))
        else:
            # nothing above threshold — surface the tool's own miss for the analyst.
            unresolved.append(UnresolvedMention(mention=mention, error=r.get("error", "no match"), suggestion=r.get("suggestion", "")))

    trigger: dict[str, Any] = {"on": trigger_on, "match_on": _MATCH_ON.get(trigger_on, ["resolved_instance"])}
    if edge_type:
        trigger["edge_type"] = edge_type

    draft = ObservableDef(observable_id=_slug(text), watch_instances=watch, trigger=trigger, severity=severity)
    return ObservableProposal(
        draft=draft,
        explanation=explain(draft),
        resolved=resolved,
        unresolved=unresolved,
    )
