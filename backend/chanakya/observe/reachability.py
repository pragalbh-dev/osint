"""Can this tripwire's trigger EVER fire on this graph? — the second half of monitoring honesty (AH-3).

**The defect this closes, measured on the running app against the real corpus.** ``anchor_diagnostics``
(AH-1/AH-2) taught a tripwire to say *"I cannot see my target"* when its declared **anchors** resolve to
nothing. That check stops at the scope. It never asks the other question — *given that I can see
everything, can the thing I am watching for occur here at all?* Two of the three shipped observables
answered **no** and said nothing about it:

* ``obs-followon-interceptor-order`` watches for a **new ``replenishes`` edge**. The rebuilt view holds
  **zero** edges of that type and **zero** ``interceptor_stockpile`` nodes for one to point at. It
  rendered as a plain armed tripwire advertising *"watching 66 node(s)"*.
* ``obs-spares-tender-probable-induction`` compiles to ``arm-only``: ``_fire`` and ``arm`` both return
  before any detector runs, so it can never emit an alert however the graph changes. ``explain()`` knew
  this and no list-level surface ever said it.

An armed tripwire that cannot fire is **an absence of alerts presented as an all-clear** — the
non-negotiable's monitoring case, and the same failure the anchor work exists to prevent, one layer up.

**The rule, and why it is honest rather than a guess.** Reachability is decided from the *trigger's own
compiled shape* against what the view and the ontology actually contain, using **the very helpers the
evaluator uses at fire time** (``_candidates`` / ``_watched`` / ``_in_scope``, imported rather than
re-derived) so the verdict cannot drift from what really fires. Each ``cannot fire`` verdict is a
statement the detector code makes true by construction:

* every detector iterates ``_candidates(new_view, ct)`` — **no candidates, no alerts**;
* every comparison operator except ``not_exists`` returns ``False`` on a ``MISSING`` field, and a
  crossing needs a *known* state on both sides — **a field no element carries can never satisfy one**;
* every detector drops an element failing ``_in_scope`` — **no candidate in scope, no alerts**.

**Conservative in the safe direction.** A false *unreachable* is dangerous: it tells an analyst to stop
trusting a wire that works. A false *reachable* is merely the status quo. So a verdict is returned
**only when the specific missing thing can be named** — the edge type, the node type, the attribute.
Everything undecidable (a threshold no element has crossed *yet*, a ``where_*`` block that happens not
to hold, whether a future document will assert something) falls through to ``reachable``, which here
means *reachable-or-undetermined* and is never a clean bill of health this module has not earned.

**Two gaps an analyst acts on differently** (``gap_kind``):

* ``data`` — the type/attribute IS modelled and simply has no coverage yet. Self-healing: the next
  document that asserts one arms the wire for real. This is a *coverage* statement, not a fault, and
  reads in the same quiet register as ``pending_coverage`` anchors.
* ``modelling`` / ``engine`` — the ontology declares no such relation, or the trigger form has no
  detector at all. **No volume of new documents fixes it**; a human must edit the ontology or the
  trigger. This is a fault.
* ``scope`` — candidates exist but none is inside the watch scope; the remedy lives in the anchor check,
  which this deliberately points at rather than restates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chanakya.schemas import ConfigBundle, GraphView, ObservableDef, TypeDef

from .dsl import MISSING, resolve_field
from .evaluator import (  # the evaluator's OWN fire-time helpers (below)
    _candidates,
    _in_scope,
    _watched,
)
from .observable import (
    ARM_ONLY,
    CROSSING,
    MATCH,
    CompiledTrigger,
    compile_trigger,
    resolve_scope_detail,
)

# ``_candidates`` / ``_watched`` / ``_in_scope`` are imported rather than re-derived on purpose: a
# reachability verdict that disagreed with what the detectors actually do at fire time would be worse
# than no verdict at all. The private names are the point — this IS the evaluator's own logic.

# ── the status vocabulary (shared by the API and the SPA; never spelled as a literal downstream) ──

REACHABLE = "reachable"  # …or undetermined. Never a positive proof that it WILL fire.
NEVER_FIRES = "never_fires"  # arm-only: no detector exists for this trigger form
TYPE_NOT_MODELLED = "type_not_modelled"  # the ontology declares no such edge/node type
NO_COVERAGE = "no_coverage"  # modelled, but the view holds no element of that type
ATTRIBUTE_NOT_COVERED = "attribute_not_covered"  # candidates exist; none carries the tracked field
OUT_OF_WATCH_SCOPE = "out_of_watch_scope"  # candidates exist; none inside the watch scope

#: What a human must actually do about it — the reason the states are kept apart at all.
GAP_KIND: dict[str, str] = {
    NEVER_FIRES: "engine",
    TYPE_NOT_MODELLED: "modelling",
    NO_COVERAGE: "data",
    ATTRIBUTE_NOT_COVERED: "data",
    OUT_OF_WATCH_SCOPE: "scope",
}

_LOCATION_FIELDS = ("location.wgs84_lat", "location.wgs84_lon")


@dataclass(frozen=True)
class TriggerReachability:
    """Whether an observable's trigger could fire on this view, and the named reason when it cannot.

    ``status is REACHABLE`` means *reachable or undetermined* — see the module docstring. ``missing``
    names the specific thing that is absent, structured so a surface can render it without parsing
    prose: ``[{"kind": "edge_type", "name": "replenishes"}, …]``.
    """

    observable_id: str
    status: str
    gap_kind: str | None = None
    missing: tuple[dict[str, str], ...] = ()
    warning: str | None = None
    candidate_count: int | None = None  # view elements of the trigger's type; None = not computed
    checked: bool = True

    @property
    def can_fire(self) -> bool:
        return self.status == REACHABLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "observable_id": self.observable_id,
            "status": self.status,
            "can_fire": self.can_fire,
            "gap_kind": self.gap_kind,
            "missing": [dict(m) for m in self.missing],
            "candidate_count": self.candidate_count,
            "checked": self.checked,
            "warning": self.warning,
        }


# ── ontology lookups (declarations only — never a scoring/threshold literal, G6) ─────────────────

def _edge_def(config: ConfigBundle, name: str) -> TypeDef | None:
    return next((t for t in config.ontology.edge_types if t.name == name), None)


def _declared_type_names(config: ConfigBundle, kind: str) -> set[str]:
    types = config.ontology.edge_types if kind == "edge" else config.ontology.node_types
    return {t.name for t in types}


def _endpoint_types(td: TypeDef | None) -> list[str]:
    """The node types an edge declares as its domain/range (``from``/``to``), flattened."""
    if td is None:
        return []
    out: list[str] = []
    for raw in (td.from_type, td.to_type):
        for name in [raw] if isinstance(raw, str) else (raw or []):
            if name and name not in out:
                out.append(str(name))
    return out


def _is_extractor(td: TypeDef | None) -> bool:
    return bool(getattr(td, "extractor", False)) if td is not None else False


# ── wording (the analyst's register — matches the anchor diagnostics: name it, state the
#    consequence, then the remedy; never "not reachable" on its own) ───────────────────────────────

def _word(kind: str) -> str:
    return "edge" if kind == "edge" else "node"


def _type_key(kind: str) -> str:
    return "edge_type" if kind == "edge" else "node_type"


def _plural(names: list[str]) -> str:
    quoted = [repr(n) for n in names]
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + " and " + quoted[-1]


def _never_fires_text(reason: str | None) -> str:
    return (
        "this tripwire cannot fire from any change to the graph: "
        f"{reason or 'its trigger form compiles to arm-only'}. It is armed, and it is counted as armed, "
        "but the evaluator has no detector for this trigger form — no ingest, decision or config write "
        "will ever produce an alert from it, so its silence carries no information and is NOT an "
        "all-clear. This is a gap in the trigger itself, not in coverage: no volume of new documents "
        "fixes it. Re-express it as a view-delta condition (new_edge / new_node / state_change / a "
        "comparator over a view field) in config/observables.yaml, or accept it as a declared-but-inert "
        "wire and stop reading its quiet as reassurance."
    )


def _not_modelled_text(kind: str, type_name: str) -> str:
    word = _word(kind)
    return (
        f"this tripwire filters on the {word} type {type_name!r}, which is not declared in the ontology "
        f"and appears on no {word} in the current view — so nothing can ever match it and it cannot "
        f"fire. Its silence is not an all-clear about {type_name!r}. This is a MODELLING gap, not a "
        "coverage gap: no volume of new documents will trip it until that type is declared in "
        f"config/ontology.yaml, or the trigger's {_type_key(kind)} is corrected in "
        "config/observables.yaml."
    )


def _no_coverage_text(
    kind: str, type_name: str | None, uncovered_endpoints: list[str], extractor: bool
) -> str:
    word = _word(kind)
    named = f"the {word} type {type_name!r}" if type_name else f"any {word}"
    head = (
        f"this tripwire filters on {named}, and the current view contains no {word} of that type at "
        f"all — so it has nothing to watch and cannot fire on this graph. Its silence is not an "
        "all-clear"
    )
    head += f" about {type_name!r}." if type_name else "."
    parts = [head]
    if type_name is None:
        # An untyped trigger over an empty graph: there is no predicate to name, so name nothing and
        # say only what is true. Inventing a specific missing thing here would be the failure mode this
        # module exists to prevent, committed by the fix itself.
        parts.append(
            f"The view holds no {word} at all, so this is a coverage statement about the whole graph "
            "rather than about any one relation."
        )
        return " ".join(parts)
    if uncovered_endpoints:
        many = len(uncovered_endpoints) > 1
        parts.append(
            f"Of the node types the ontology declares that edge between, the view holds no node of "
            f"{'types' if many else 'type'} {_plural(uncovered_endpoints)} either — so there is not "
            "even an endpoint for one to attach to."
        )
    if kind != "edge":
        # `extractor: true` is an EDGE declaration; node types carry none, so saying a node type is
        # "not in the extraction enum" would be a true-sounding sentence about a field that does not
        # exist for it. Say the general thing instead of an invented specific one.
        parts.append(
            f"This is a COVERAGE gap, not a config fault: {type_name!r} is declared in the ontology, "
            "so the first document that produces one arms this wire for real, live, with no restart. "
            "Until then, treat this beat as UNCOVERED rather than quiet."
        )
    elif extractor:
        parts.append(
            f"This is a COVERAGE gap, not a config fault: {type_name!r} is in the extraction enum, so "
            "the first document that asserts one arms this wire for real, live, with no restart. Until "
            "then, treat this beat as UNCOVERED rather than quiet."
        )
    else:
        parts.append(
            f"{type_name!r} is NOT in the extraction enum (config/ontology.yaml declares no "
            "`extractor: true` on it), so no ingest asserts one directly — it can only arrive from a "
            "derivation step inside rebuild(). Confirm such a step exists before treating this wire as "
            "live coverage; if none does, this is a modelling gap wearing a coverage gap's clothes."
        )
    return " ".join(parts)


def _attribute_text(field: str, count: int, kind: str, type_name: str | None) -> str:
    word = _word(kind)
    of_type = f" of type {type_name!r}" if type_name else ""
    return (
        f"this tripwire tracks the field {field!r}, but not one of the {count} {word}(s){of_type} in "
        "the current view carries it. Every comparison against an absent field is UNKNOWN, and an "
        "UNKNOWN never satisfies a trigger, so this wire cannot fire. This is a COVERAGE gap: the "
        "attribute is simply not populated by any source yet — it becomes live as soon as one states "
        "it. If no source will ever state it, correct `field` in the trigger instead."
    )


def _scope_text(
    count: int, kind: str, type_name: str | None, anchors: list[str], anchor_warning: str | None
) -> str:
    word = _word(kind)
    of_type = f" of type {type_name!r}" if type_name else ""
    text = (
        f"the current view holds {count} {word}(s){of_type} the trigger would match, but not one of "
        f"them falls inside the watch scope this tripwire declares ({_plural(anchors)}) — so it has no "
        "candidate and cannot fire. Its silence is about its scope, not about the world."
    )
    if anchor_warning:
        text += f" The scope itself reports: {anchor_warning}"
    else:
        text += (
            " Widen `anchors_within_hops`, or add the instance you meant to watch to `watch_instances` "
            "(config/observables.yaml) / the subject lens's anchors (config/subjects.yaml)."
        )
    return text


# ── the check ────────────────────────────────────────────────────────────────────────────────────

def _tracked_field(ct: CompiledTrigger) -> str | None:
    """The field a fire-time comparison would read, when an absent one provably blocks the trigger.

    Only ``crossing`` and ``match`` compare a field value, and only ``not_exists`` is satisfied by an
    absent one — everything else short-circuits ``False`` on ``MISSING`` (see ``dsl.OPERATORS``). A
    ``geofence`` crossing reads the location instead, handled separately.
    """
    if ct.mode not in (CROSSING, MATCH) or ct.geo_area is not None:
        return None
    if ct.op == "not_exists":
        return None
    return ct.state_field


def trigger_reachability(
    obs: ObservableDef, view: GraphView | None, config: ConfigBundle | None
) -> TriggerReachability:
    """Could ``obs``'s trigger fire against ``view``? Returns the named reason when it provably cannot.

    Without a view/config the check **cannot be performed**, and that is what is reported — an
    unperformed check is never returned as a pass (the same rule ``explain``'s anchor half follows).
    """
    if view is None or config is None:
        return TriggerReachability(
            obs.observable_id,
            REACHABLE,
            checked=False,
            warning=(
                "reachability not checked — no view supplied, so whether this trigger could fire is "
                "unknown. This is not a statement that it can."
            ),
        )

    ct = compile_trigger(obs.trigger)
    if ct.mode == ARM_ONLY:
        return TriggerReachability(
            obs.observable_id,
            NEVER_FIRES,
            GAP_KIND[NEVER_FIRES],
            ({"kind": "trigger_form", "name": str(obs.trigger.get("on", "?"))},),
            _never_fires_text(ct.reason),
        )

    kind, type_name = ct.element_kind, ct.type_filter
    candidates = _candidates(view, ct)
    count = len(candidates)

    # 1. Modelling gap — the ontology has no such relation/type, so no ingest could ever produce one.
    #    Guarded by "and none is present in the view": a view type the ontology does not declare
    #    (derived/discovered instances) is evidence the type is real, and outranks the declaration.
    if type_name is not None and not candidates and type_name not in _declared_type_names(config, kind):
        return TriggerReachability(
            obs.observable_id,
            TYPE_NOT_MODELLED,
            GAP_KIND[TYPE_NOT_MODELLED],
            ({"kind": _type_key(kind), "name": type_name},),
            _not_modelled_text(kind, type_name),
            candidate_count=0,
        )

    # 2. Data gap — modelled, but coverage has produced none. Every detector iterates the candidate
    #    map; an empty one emits nothing, whatever else the trigger declares.
    if not candidates:
        td = _edge_def(config, type_name) if kind == "edge" and type_name else None
        present = {n.type for n in view.nodes}
        uncovered = [t for t in _endpoint_types(td) if t not in present]
        missing: list[dict[str, str]] = (
            [{"kind": _type_key(kind), "name": type_name}] if type_name else []
        )
        missing += [{"kind": "node_type", "name": t} for t in uncovered]
        return TriggerReachability(
            obs.observable_id,
            NO_COVERAGE,
            GAP_KIND[NO_COVERAGE],
            tuple(missing),
            _no_coverage_text(kind, type_name, uncovered, _is_extractor(td)),
            candidate_count=0,
        )

    # 3. Data gap, one level down — the tracked attribute exists on no candidate at all, so every
    #    comparison against it is UNKNOWN and UNKNOWN never satisfies a trigger.
    tracked = _tracked_field(ct)
    if tracked and all(resolve_field(el, tracked) is MISSING for el in candidates.values()):
        return TriggerReachability(
            obs.observable_id,
            ATTRIBUTE_NOT_COVERED,
            GAP_KIND[ATTRIBUTE_NOT_COVERED],
            ({"kind": "attribute", "name": tracked},),
            _attribute_text(tracked, count, kind, type_name),
            candidate_count=count,
        )
    if ct.geo_area is not None and all(
        any(resolve_field(el, f) is MISSING or resolve_field(el, f) is None for f in _LOCATION_FIELDS)
        for el in candidates.values()
    ):
        return TriggerReachability(
            obs.observable_id,
            ATTRIBUTE_NOT_COVERED,
            GAP_KIND[ATTRIBUTE_NOT_COVERED],
            tuple({"kind": "attribute", "name": f} for f in _LOCATION_FIELDS),
            # Both field names appear verbatim so every entry in ``missing`` is findable in the
            # sentence — the property the surfaces rely on to build a chip from the prose.
            _attribute_text(" / ".join(_LOCATION_FIELDS), count, kind, type_name),
            candidate_count=count,
        )

    # 4. Scope gap — candidates exist but the watch scope excludes every one of them. The remedy is
    #    the anchor check's, so point at its sentence rather than inventing a second diagnosis.
    detail = resolve_scope_detail(obs, view, config)
    if not any(_in_scope(_watched(el), detail.node_ids) for el in candidates.values()):
        # The anchors are always non-empty here: an observable that declares none scopes to ``None``,
        # which ``_in_scope`` treats as "match everything", so this branch is unreachable for it.
        anchors = list(detail.requested)
        return TriggerReachability(
            obs.observable_id,
            OUT_OF_WATCH_SCOPE,
            GAP_KIND[OUT_OF_WATCH_SCOPE],
            tuple({"kind": "watch_scope", "name": a} for a in anchors),
            _scope_text(count, kind, type_name, anchors, detail.warning),
            candidate_count=count,
        )

    return TriggerReachability(obs.observable_id, REACHABLE, candidate_count=count)


def reachability_diagnostics(config: ConfigBundle, view: GraphView) -> list[dict[str, Any]]:
    """One entry per armed observable — the API/SPA-facing form of :func:`trigger_reachability`.

    Deliberately **complete** rather than problems-only (unlike ``anchor_diagnostics``): the Watch panel
    renders a card per armed tripwire, and a card can only state "watching, and it could fire" if the
    positive verdict is carried too. A caller wanting the action list filters on ``can_fire == false``.
    Deterministic (config order); no clock/RNG/LLM — safe on any read path.
    """
    return [
        trigger_reachability(obs, view, config).as_dict()
        for obs in config.observables.observables
    ]
