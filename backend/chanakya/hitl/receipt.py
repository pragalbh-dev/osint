"""The ACKNOWLEDGEMENT half of the write path: did the analyst's instruction land, and if not, why.

**The defect this module exists to close.** ``POST /hitl/merge`` returned ``200`` and the rebuilt view for
every instruction it received, including the ones the resolver then declined to apply. Measured on the
booted corpus: three of fourteen accepts left ``GET /view`` byte-identical. The cross-type rail refusing to
fuse a ``component`` with a ``variant`` is CORRECT — that is not the bug. The bug is that nothing told the
analyst their instruction had not been applied or on what ground. A silent ``200`` on a refused instruction
is the escalate half of the non-negotiable missing on the *write* path: the system declined to act and did
not say so, which is indistinguishable from having acted.

Two surfaces are served from this one derivation so they can never disagree:

* the ``POST /hitl/merge`` response, which carries a :class:`~chanakya.schemas.AdjudicationReceipt` —
  what was received, whether it was applied, and the ground;
* ``GET /view``, where an instruction that was *not* applied is stamped onto the drawn ``same-as`` edge it
  concerns (:func:`stamp_unapplied`), so it survives the round-trip and the analyst is not asked the same
  question again with no memory that they already answered it.

Everything here is a **read of the rebuilt view** — never a prediction of what should have happened. That
is deliberate: an "applied" flag derived from the code path that wrote the record would report success
whenever the write succeeded, which is exactly the claim that was false. Pure and deterministic (gate G1):
dict/list reads over a ``GraphView`` and a ``DecisionRecord``, no clock, no RNG, no network.
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import DecisionRecord, GraphView, pair_key

#: What each verdict was asking the graph to do, in the analyst's own terms — used in the receipt so the
#: acknowledgement restates the instruction rather than merely echoing an option string.
_INSTRUCTION = {
    "accept": "fuse these two records into one entity",
    "reject": "hold these two records apart as different entities",
    "split": "reverse an existing merge and hold these two records apart",
}


def _absorbed_by(view: GraphView) -> dict[str, str]:
    """``absorbed entity id → the surviving canonical node`` from the drawn merge provenance.

    ``_merge_provenance`` stamps each accepted merge on the surviving node as
    ``attrs.resolved_from[*].merged_ref``, which is the only place the wire says "this id became that
    node". Reading it is what lets an acknowledgement speak about the pair the analyst clicked even
    after one side of it was renamed by the merge they just approved.
    """
    out: dict[str, str] = {}
    for node in view.nodes:
        for entry in (node.attrs or {}).get("resolved_from") or []:
            ref = entry.get("merged_ref") if isinstance(entry, dict) else None
            if isinstance(ref, str) and ref:
                out[ref] = node.id
    return out


def _endpoints(view: GraphView, a: str, b: str) -> tuple[str, str]:
    """The two ids as the rebuilt view knows them — an accepted merge renames one side to its canonical."""
    absorbed = _absorbed_by(view)
    return absorbed.get(a, a), absorbed.get(b, b)


def _wall(view: GraphView, a: str, b: str) -> Any:
    for edge in view.edges:
        if edge.type == "distinct-from" and {edge.source, edge.target} == {a, b}:
            return edge
    return None


def _candidate(view: GraphView, a: str, b: str) -> Any:
    for edge in view.edges:
        if edge.type == "same-as" and {edge.source, edge.target} == {a, b}:
            return edge
    return None


def _fused(view: GraphView, raw_a: str, raw_b: str) -> bool:
    """True iff the two RAW ids resolved to ONE node — the only honest test that an accept landed."""
    absorbed = _absorbed_by(view)
    return absorbed.get(raw_a, raw_a) == absorbed.get(raw_b, raw_b)


def _type_of(view: GraphView, node_id: str) -> str | None:
    return next((n.type for n in view.nodes if n.id == node_id), None)


def applied(view: GraphView, verdict: str, a: str, b: str) -> bool:
    """Did the rebuilt view actually take the instruction? Read off the wire, never assumed.

    * ``accept`` lands when the two ids are one node.
    * ``reject``/``split`` land when a ``distinct-from`` wall is drawn over the pair. A pair that merely
      stopped being proposed does NOT count: a silent disappearance is what the analyst cannot tell from
      the decision having been dropped, which is the whole defect.
    """
    if verdict == "accept":
        return _fused(view, a, b)
    return _wall(view, a, b) is not None


def ground(view: GraphView, verdict: str, a: str, b: str) -> str:
    """The most specific ground the REBUILT VIEW can state for not applying this instruction.

    Precedence, most specific first — and every branch reads something that is genuinely on the wire, so
    this can never become a fixed default wearing a rationale's clothes:

    1. a drawn ``distinct-from`` over the pair — a hard wall overrules any merge, and it states its own
       ground (curated, source-stated, gazetteer, identifier, attribute, relationship, or another analyst);
    2. the two endpoints are different ontology TYPES — exact, and read off the two rendered nodes;
    3. the pair is still a drawn ``same-as`` candidate carrying its own reason — the resolver's account of
       why this is an open question rather than a merge;
    4. nothing was recorded. That is a defect in whichever rail declined, and it says so rather than
       inventing a cause.
    """
    wall = _wall(view, a, b)
    if wall is not None and verdict == "accept":
        return (
            "a hard do-not-merge wall holds these two apart, and a wall overrules a merge: "
            f"{(wall.attrs or {}).get('reason', '(no ground recorded by the rail that raised it)')}"
        )
    ta, tb = _type_of(view, a), _type_of(view, b)
    if ta and tb and ta != tb:
        return (
            f"the two records are different ontology types — '{a}' is a {ta} and '{b}' is a {tb}. The "
            "resolver does not fuse across types: one is a kind of thing and the other is a thing of that "
            "kind, so merging them would delete a distinction rather than resolve one. If they really are "
            "one entity, the type of one of them is wrong and the fix is upstream, in extraction or in the "
            "ontology — not in this merge."
        )
    candidate = _candidate(view, a, b)
    if candidate is not None:
        why = (candidate.attrs or {}).get("reason")
        if why:
            return f"the pair is still an open identity question on the resolver's own grounds: {why}"
    return (
        "the rebuilt graph does not reflect this instruction and no rail recorded a ground for declining "
        "it. That is a defect in the declining rail, not a statement about this pair — the decision is in "
        "the append-only log either way, and it should be reported."
    )


def receipt_fields(view: GraphView, record: DecisionRecord, a: str, b: str, verdict: str) -> dict[str, Any]:
    """The acknowledgement payload shared by the POST response and the ``GET /view`` stamp."""
    ca, cb = _endpoints(view, a, b)
    was_applied = applied(view, verdict, ca, cb)
    out: dict[str, Any] = {
        "event_id": record.event_id,
        "pair": [a, b],
        "instruction": _INSTRUCTION.get(verdict, verdict),
        "decision": verdict,
        "actor": record.actor,
        "rationale": (record.decision or {}).get("rationale") if isinstance(record.decision, dict) else None,
        "recorded": True,
        "applied": was_applied,
    }
    if was_applied:
        wall = _wall(view, ca, cb)
        out["effect_ref"] = wall.id if wall is not None else ca
        out["ground"] = (
            "applied: the decision is replayed from the append-only decision log on every rebuild, so it "
            "holds without anyone editing config, and it survives a restart."
        )
    else:
        out["ground"] = ground(view, verdict, ca, cb)
        candidate = _candidate(view, ca, cb)
        out["effect_ref"] = candidate.id if candidate is not None else None
    return out


def stamp_unapplied(view: GraphView, decisions: list[DecisionRecord]) -> None:
    """Mark every drawn ``same-as`` edge an analyst already ruled on and the resolver did not apply.

    Without this the acknowledgement lives only in the POST response, so a page reload loses it and the
    analyst is asked the identical question with no record that they answered it — the "asked forever"
    half of the queue defect. Mutates ``view`` in place, from the append-only decision log, on every
    rebuild; later records win, so a re-adjudication replaces the earlier note rather than stacking.
    """
    from chanakya.resolve.aliases import adjudicated_pair  # local: avoids a resolve↔hitl import cycle

    by_edge: dict[str, dict[str, Any]] = {}
    for record in decisions:
        parsed = adjudicated_pair(record)
        if parsed is None:
            continue
        bar_or_accept, (a, b) = parsed
        verdict = _verdict_name(record, bar_or_accept)
        ca, cb = _endpoints(view, a, b)
        if applied(view, "accept" if bar_or_accept == "accept" else "reject", ca, cb):
            continue
        edge = _candidate(view, ca, cb)
        if edge is None:
            continue
        by_edge[edge.id] = {
            "decision": verdict,
            "actor": record.actor,
            "instruction": _INSTRUCTION.get(verdict, verdict),
            "applied": False,
            "ground": ground(view, "accept" if bar_or_accept == "accept" else "reject", ca, cb),
            "event_id": record.event_id,
        }
    for edge in view.edges:
        if edge.id in by_edge:
            edge.attrs = {**(edge.attrs or {}), "adjudication_not_applied": by_edge[edge.id]}


def _verdict_name(record: DecisionRecord, bar_or_accept: str) -> str:
    """The option the analyst actually clicked (``reject``/``split``), not the replay's coarse verdict."""
    chosen = record.decision.get("chosen") if isinstance(record.decision, dict) else None
    if isinstance(chosen, str) and chosen:
        return chosen
    return "accept" if bar_or_accept == "accept" else "reject"


def pair_handle(a: str, b: str) -> str:
    """The drawn ``same-as`` edge id for a pair — the handle ``POST /hitl/merge`` resolves its subject by."""
    return f"same-as:{pair_key(a, b)}"
