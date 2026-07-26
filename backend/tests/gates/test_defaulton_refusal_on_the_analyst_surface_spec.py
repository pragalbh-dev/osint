"""DEFAULT-ON P4 + P5, re-anchored on **the surface the analyst actually receives**.

The sibling gate ``test_defaulton_refuse_and_escalate_spec.py`` asserts the same two properties against
:class:`~chanakya.schemas.stage_io.Partition` — an *internal intermediate object* that never leaves
``rebuild()``. That is why 219 gates could stay green while the property was false on the real corpus. Its
``_received`` helper goes further and, at the ``distinct_from`` branch, **synthesises its own string**
(``f"drawn do-not-merge edge {a}|{b}"``) out of mere set membership and counts that as a reason the analyst
received. A test that authors the evidence it then accepts cannot fail, and a green artifact carrying a
false claim is worse than a red one: it switches off the next reader's scepticism.

So this file never reads the partition for evidence. It reads:

* ``GET /view`` — the rebuilt :class:`GraphView` JSON, the SPA's only binding target, fetched through the
  real ASGI app over a real booted :class:`AppState`. If a refusal is not in that payload, the analyst does
  not have it, whatever the partition says.
* ``GET /evidence/{id}`` — the provenance drawer, the one-click-to-source surface.
* ``POST /hitl/merge`` — the adjudication writeback, i.e. whether the analyst can *act*.
* the SPA sources, for the last hop between the wire and a human's eyes.

**The partition is still allowed as a PREDICATE, never as evidence.** Deciding whether a pair *is* an open
identity question is a question about what the resolver computed, and ``identity_status`` is the declared
reporter of exactly that (it "*reports*, it draws nothing"). Every assertion below is nevertheless made
against a wire payload. That distinction — oracle on the inside, assertion on the outside — is the whole
correction, and it is what makes a green run here mean the property holds.

**Two verdicts kept separate throughout, because conflating them is how the quiet drop hid.** *Visible*
(the rendered view carries an element that represents this identity question) and *explained* (that element
carries text stating the ground). An element with no reason is visible-but-unexplained; a reason in a dict
that never reached the wire is neither. :func:`_identity_elements` returns both, and it only ever returns
strings that arrived over HTTP.

Corpus-independent fixtures are the primary defence (principle #4: logic correctness may never rest on the
data). But every defect this file pins was invisible to synthetic fixtures too, so the last section boots
the **real corpus through the real app** and asserts *invariants* — "every open question reaches the
surface", never "23 of them do" — so they cannot go stale when the data changes.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api.state import AppState, build_default_state, scenario_bundles_dir
from chanakya.config import ConfigStore
from chanakya.resolve import resolve
from chanakya.resolve.rconfig import BAND_POSSIBLE, BAND_PROBABLE
from chanakya.schemas import pair_key
from chanakya.store import DecisionLog, EvidenceLog
from tests import _rk_coref as rc
from tests import _rk_layer as rk

FIXED_TS = "2026-07-26T00:00:00+00:00"

#: The two edge types on the wire that carry an identity decision. ``same-as`` = an open question the
#: analyst is asked to settle; ``distinct-from`` = a wall. Neither is ever scored (G5).
IDENTITY_EDGE_TYPES = ("same-as", "distinct-from")

#: The generic fallback ``view/pipeline._resolution_edges`` stamps on a wall with no computed ground —
#: read from production, not re-typed, so this file cannot drift from the string it is about.
CURATED_WALL_TEXT = "explicit do-not-merge (hard veto)"


def _live(**block: Any):
    """The shipped bundle with the named identity tunables overridden.

    Both stage flags are deleted, so the shipped block *is* the live one; ``block`` varies a dial (a
    ceiling), never a switch. ``rc.bundle`` refuses a retired staging keyword by name.
    """
    base = rc.bundle(supersede_floor=dict(rk.SUPERSEDE_FLOOR))
    return rc.with_resolution(base, earned_identity={**rc.earned_identity_block(), **block})


@contextmanager
def _booted(config: Any, claims: list[Any]) -> Iterator[TestClient]:
    """A real ASGI client over a real booted ``AppState`` seeded with ``claims``.

    Deliberately the whole app rather than ``rebuild()`` alone: the analyst reaches the graph through
    ``GET /view``, and "the refusal is on the analyst's surface" is a claim about that response body.
    """
    evidence = EvidenceLog()
    evidence.append_many(claims)
    state = AppState(evidence, DecisionLog(), ConfigStore.from_bundle(config), clock=lambda: FIXED_TS)
    state.boot()
    with TestClient(create_app(state)) as client:
        yield client


def _wire_view(config: Any, claims: list[Any]) -> dict[str, Any]:
    """The ``GET /view`` JSON — literally what the analyst's client receives."""
    with _booted(config, claims) as client:
        response = client.get("/view")
        assert response.status_code == 200, f"GET /view failed: {response.status_code} {response.text[:300]}"
        return response.json()


# ── reading the rendered surface (and NEVER writing on it) ───────────────────────────────────────

#: Keys whose value is a per-element *rationale* rather than a score/label. Searched rather than fixed to
#: one name so a new channel is found automatically — but every one of them is a real string that arrived
#: over the wire. Nothing here is ever composed from set membership.
_REASON_KEY_TOKENS = ("reason", "rationale", "why", "explanation", "grounds", "note")


def _texts_in(bag: Any) -> list[str]:
    """Every rationale-ish string in an ``attrs`` bag, at any depth. Verbatim; never synthesised."""
    out: list[str] = []
    if isinstance(bag, dict):
        for key, value in bag.items():
            if isinstance(value, str) and value.strip() and any(t in key.lower() for t in _REASON_KEY_TOKENS):
                out.append(value)
            elif isinstance(value, (dict, list)):
                out.extend(_texts_in(value))
    elif isinstance(bag, list):
        for value in bag:
            out.extend(_texts_in(value))
    return out


class Rendered(NamedTuple):
    """What the rendered view carries about one identity question.

    ``elements`` — wire element ids representing the pair (an analyst can SEE the question exists).
    ``grounds`` — element id → the verbatim rationale text on it (the analyst can READ why).
    ``merge_handles`` — ids of drawn candidate ``same-as`` edges, the only thing ``POST /hitl/merge`` accepts.

    An element with no rationale appears in ``elements`` and not in ``grounds``: visible is not explained.
    """

    elements: list[str]
    grounds: dict[str, str]
    merge_handles: list[str]

    @property
    def text(self) -> str:
        return " ".join(self.grounds.values()).lower()


def _aliases(node_id: str, canonical: dict[str, str] | None) -> set[str]:
    """``node_id`` and the canonical id it resolved to.

    A partition pair is keyed on the PRE-merge mention id while the view is keyed on the POST-merge
    canonical id, so a strict id match would report a pair "absent from the surface" merely because it was
    renamed by a merge it was not part of. Tolerating the canonical form makes the invariant a statement
    about *the analyst seeing the question*, and leaves the implementation free to fix it either way.
    """
    return {node_id, (canonical or {}).get(node_id, node_id)}


def _identity_elements(
    view: dict[str, Any], a: str, b: str, *, canonical: dict[str, str] | None = None
) -> Rendered:
    """Everything the RENDERED view carries about the identity question over ``a``/``b``.

    Searched over the wire payload only. Three channels: a drawn ``same-as`` edge (an open question), a
    drawn ``distinct-from`` edge (a wall), and a Known Gap on an endpoint that is *about identity* (the
    ``missing_slots`` say so) and names the other mention — so a generic sufficiency gap on the node can
    never be mistaken for the withheld-merge record.
    """
    ends_a, ends_b = _aliases(a, canonical), _aliases(b, canonical)
    names = {n["id"]: (n.get("name") or "") for n in view.get("nodes", [])}
    elements: list[str] = []
    grounds: dict[str, str] = {}
    handles: list[str] = []

    for edge in view.get("edges", []):
        if edge.get("type") not in IDENTITY_EDGE_TYPES:
            continue
        source, target = edge.get("source"), edge.get("target")
        if not ((source in ends_a and target in ends_b) or (source in ends_b and target in ends_a)):
            continue
        elements.append(edge["id"])
        texts = _texts_in(edge.get("attrs") or {})
        if texts:
            grounds[edge["id"]] = " ".join(texts)
        if edge["type"] == "same-as":
            handles.append(edge["id"])

    for gap in view.get("known_gaps", []):
        if "identity" not in (gap.get("missing_slots") or []):
            continue
        ref = gap.get("related_ref")
        other = ends_b if ref in ends_a else (ends_a if ref in ends_b else None)
        if other is None:
            continue
        text = gap.get("what_missing") or ""
        mentions_other = any(o and o in text for o in other) or any(
            names.get(o) and names[o] in text for o in other
        )
        if not mentions_other:
            continue  # an identity gap about some OTHER pair — not this refusal's record
        elements.append(gap["id"])
        if text.strip():
            grounds[gap["id"]] = text

    return Rendered(sorted(elements), grounds, sorted(handles))


# ── the refusal grounds ─────────────────────────────────────────────────────────────────────────

class Refusal(NamedTuple):
    claims: list[Any]
    config: Any
    pair: tuple[str, str]
    #: Substrings any one of which shows the rendered reason naming THIS ground (never the prose — G6).
    ground_tokens: tuple[str, ...]


_ORG = "Alpha Precision Machinery"
_ORG_QUOTE = f"{_ORG} of Karachi, also trading as {_ORG}, per the register"
_DESCRIPTOR = "air defence battery"


def _name_alone() -> Refusal:
    """Identical names and nothing else — the shipped name ceiling.

    Recall evidence, not a verdict; but recall evidence is still a finding, and it is the analyst's to
    accept with one click. If it never renders, the pair is indistinguishable from one that never scored.
    """
    name = "Zeta Machine Works"
    return Refusal(
        claims=[
            rc.ent("z1", "trading_org", name, doc="d1"),
            rc.ent("z2", "trading_org", name, doc="d2", sid="mid"),
        ],
        config=_live(),
        pair=("z1", "z2"),
        ground_tokens=("name", "designation"),
    )


def _colocation_at(ceiling: str) -> Refusal:
    """Two formations agreeing on nothing but where they are standing (D-13.14/G16).

    This is the over-merge the project exists to prevent: fuse them and their two sites become one unit's
    before-and-after, so the system fabricates a relocation and deletes the honest Known Gap.
    """
    return Refusal(
        claims=[
            rc.ent("unit_a", "unit", _DESCRIPTOR, doc="d1"),
            rc.ent("unit_b", "unit", _DESCRIPTOR, doc="d2", sid="mid"),
            rc.site("site", "Alpha Cantonment", doc="d1"),
            rc.rel("r-ba-a", "unit_a", "based-at", "site", doc="d1", iso="2021-03-01"),
            rc.rel("r-ba-b", "unit_b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
            *rc.shared_neighbours("unit_a", "unit_b"),
        ],
        config=_live(colocation_ceiling=ceiling),
        pair=("unit_a", "unit_b"),
        ground_tokens=("co-location", "colocation", "standing", "based-at", "where they are"),
    )


def _cross_operator() -> Refusal:
    """A same-named pair straddling two stated operators — the costliest over-merge for an ORBAT."""
    return Refusal(
        claims=[
            rc.ent("org_cn", "trading_org", _ORG, doc="d1", attrs={"origin_country": "China"}),
            rc.ent("org_pk", "trading_org", _ORG, doc="d1", sid="mid",
                   attrs={"origin_country": "Pakistan"}),
            rc.coref("org_cn", "org_pk", quote=_ORG_QUOTE, doc="d1"),
        ],
        config=_live(),
        pair=("org_cn", "org_pk"),
        ground_tokens=("origin_country", "namespace", "operator", "china", "pakistan"),
    )


def _unreadable_value() -> Refusal:
    """A wall-eligible slot stating a value no declared equivalence class covers (C7's third state).

    Neither conflict nor agreement, so it may neither wall nor fuse — and it must say WHICH slot it could
    not read, because "add a normalisation row" is a different instruction from every other ground here.
    """
    return Refusal(
        claims=[
            rc.ent("u1", "unit", "8th AD Battalion", doc="d1",
                   attrs={"service_branch": "PAF", "designator": "8"}),
            rc.ent("u2", "unit", "8th AD Battalion", doc="d2", sid="mid",
                   attrs={"service_branch": "Blue Force Air Arm", "designator": "8"}),
            *rc.shared_neighbours("u1", "u2"),
        ],
        config=_live(),
        pair=("u1", "u2"),
        ground_tokens=("service_branch", "normalis", "normaliz", "equivalence class"),
    )


REFUSALS: dict[str, Any] = {
    "name-alone": _name_alone,
    "co-location-capped-at-probable": lambda: _colocation_at(BAND_PROBABLE),
    "co-location-capped-at-possible": lambda: _colocation_at(BAND_POSSIBLE),
    "cross-operator": _cross_operator,
    "unreadable-stated-value": _unreadable_value,
}


def _refused(case: Refusal) -> tuple[Any, dict[str, Any]]:
    """``(partition, wire view)`` for a case, having first checked the pair really was NOT fused.

    The partition here is the ORACLE — "did the resolver decline to fuse, and what did it decide?" — and
    the returned view is the only thing any assertion below reads for evidence.
    """
    part = resolve(case.claims, case.config)
    a, b = case.pair
    assert not rc.fused(part, a, b), (
        f"the pair FUSED, so there is no refusal to surface (signals={rc.signals(part, a, b)}). Fix the "
        "refusal before the escalation — this file is about whether a refusal reaches a human."
    )
    return part, _wire_view(case.config, case.claims)


# ── P4: the refusal must be ON the analyst's surface, not in an intermediate object ──────────────

@pytest.mark.parametrize("ground", sorted(REFUSALS))
def test_a_withheld_merge_appears_on_the_rendered_view(ground: str) -> None:
    """The gate the partition-level version could not enforce.

    ``GET /view`` is the analyst's whole world: the SPA binds to it and to nothing else. A refusal that
    exists only as an entry in ``Partition.candidate_reasons`` has, from the analyst's side, not happened —
    it is byte-for-byte indistinguishable from a pair the resolver never scored. "Retained but never
    surfaced" is a quiet drop wearing a referral's clothes, and the register already records that defect
    happening once through one enumeration; this asserts the property so it cannot return through another.
    """
    case = REFUSALS[ground]()
    part, view = _refused(case)
    a, b = case.pair
    rendered = _identity_elements(view, a, b)

    assert rendered.elements, (
        f"[{ground}] the merge was withheld and NOTHING about it reached GET /view. The resolver decided "
        f"{part.identity_status(a, b)!r} and wrote a rationale into the partition "
        f"({rc.reason(part, a, b)[:120]!r}…), but the payload the analyst's client receives carries no "
        f"same-as edge, no distinct-from edge and no identity Known Gap over {a}|{b}. A cap may withhold "
        "ATTENTION (watch-list rather than review queue); it may not withhold the RECORD. Both halves of "
        "the non-negotiable are required: decline to assert, AND escalate to the analyst."
    )
    assert rendered.grounds, (
        f"[{ground}] the pair is visible on GET /view ({rendered.elements}) with NO stated grounds. A "
        "queue item that cannot say why it is a question teaches the analyst to skim the queue; the "
        f"resolver computed one ({rc.reason(part, a, b)[:120]!r}…) and the wire dropped it."
    )


@pytest.mark.parametrize("ground", sorted(REFUSALS))
def test_the_rendered_reason_names_the_ground_that_actually_caused_this_refusal(ground: str) -> None:
    """P5, on the wire. The ground IS the analyst's instruction, so a fixed default is not a reason.

    Adjudicate two stated countries · add a normalisation row · look for a unit-level discriminator ·
    accept a name match. Four different next actions. A generic "not merged" collapses all four.
    """
    case = REFUSALS[ground]()
    _part, view = _refused(case)
    a, b = case.pair
    rendered = _identity_elements(view, a, b)

    assert rendered.grounds, (
        f"[{ground}] no ground reached GET /view at all, so it cannot name one — see "
        "test_a_withheld_merge_appears_on_the_rendered_view, which owns that half"
    )
    assert any(tok in rendered.text for tok in case.ground_tokens), (
        f"[{ground}] the reason the ANALYST receives never names the ground that caused the refusal. "
        f"Wanted any of {list(case.ground_tokens)}; the wire said {rendered.grounds}."
    )


def test_no_two_refusal_grounds_render_the_same_words() -> None:
    """P5's sharper form, measured where it matters: on one screen, are four grounds four sentences?

    A single generic rationale reused across grounds passes every "a reason exists" check and still tells
    the analyst nothing. Comparing the grounds against each other is what makes "names its REAL ground"
    testable — if two computed grounds arrive as one string, at most one of them is being reported. Note
    that a ground rendering NOTHING collides with every other silent ground, which is the precise sense in
    which invisibility and a fixed default are the same failure.
    """
    rendered: dict[str, str] = {}
    for ground in sorted(REFUSALS):
        case = REFUSALS[ground]()
        _part, view = _refused(case)
        rendered[ground] = " ".join(sorted(_identity_elements(view, *case.pair).grounds.values())).strip()

    silent = sorted(g for g, text in rendered.items() if not text)
    assert not silent, (
        f"these grounds rendered no words at all on GET /view: {silent}. Every one of them refused a "
        "fusion, so every one owes the analyst a rationale before this comparison can mean anything."
    )
    collisions = sorted({(x, y) for x in rendered for y in rendered if x < y and rendered[x] == rendered[y]})
    assert not collisions, (
        f"two different refusal grounds arrive at the analyst as the SAME words: {collisions}. That is a "
        "fixed default, and it makes 'the reason states the ground' false while every existence check "
        "still passes."
    )


@pytest.mark.parametrize("ceiling", [BAND_PROBABLE, BAND_POSSIBLE])
def test_a_pair_capped_at_a_ceiling_keeps_its_record_on_the_rendered_view(ceiling: str) -> None:
    """A ceiling is a statement about how much ATTENTION a pair earned — not that the refusal never happened.

    Lowering it may move the pair from the review queue to the watch-list. It may not erase the pair from
    the payload, and the ceiling actually applied is part of the ground: a pair capped at ``possible`` and
    one capped at ``probable`` are being told different things, so prose that hard-codes one band while the
    config applied the other is the surfaced reason disagreeing with the computed one even though it looks
    specific.
    """
    case = _colocation_at(ceiling)
    _part, view = _refused(case)
    rendered = _identity_elements(view, *case.pair)

    assert rendered.grounds, (
        f"capped at {ceiling!r}, the co-located pair left the analyst's payload entirely — no edge, no "
        "identity gap, no reason on GET /view. This is the exact shape of the quiet-drop defect the "
        "register already names, and on this fixture the consequence is concrete: two batteries standing "
        "in one cantonment, refused a merge, with nobody told the question was ever asked."
    )
    assert ceiling in rendered.text, (
        f"capped at {ceiling!r}, the rendered reason states a different band: {rendered.grounds}. The "
        "reason must name the ceiling the system actually applied — a hard-coded band diverges from the "
        "decision the moment an operator retunes the dial, and the analyst then reads a verdict nobody "
        "computed."
    )


# ── P4's second half: RECEIVED is not enough — an open question must be ACTIONABLE ───────────────

def _open_grounds() -> list[str]:
    """Grounds where the resolver kept the identity link OPEN — the analyst is meant to settle these.

    Partition-as-predicate: ``identity_status`` is the declared reporter of what was decided, and
    ``probable``/``possible`` both mean "not fused, not walled, still a live question". Which of the two it
    is decides how much attention the pair has earned, never whether the analyst may act on it.
    """
    out = []
    for ground in sorted(REFUSALS):
        case = REFUSALS[ground]()
        part = resolve(case.claims, case.config)
        if part.identity_status(*case.pair) in (BAND_PROBABLE, BAND_POSSIBLE):
            out.append(ground)
    return out


def _adjudicate(client: TestClient, handle: str, decision: str) -> tuple[int, str]:
    """POST one merge verdict. A server-side crash is reported as ``(500, traceback tail)``, never raised.

    The analyst's experience of an unhandled exception on this route is a failed adjudication, so that is
    what the assertion should read — not a traceback that looks like a broken test.
    """
    try:
        response = client.post(
            "/hitl/merge",
            json={"item_id": f"merge:{handle}", "type": "merge", "subject": handle,
                  "decision": decision, "actor": "analyst", "rationale": "adjudicated in the spec"},
        )
    except Exception as exc:  # noqa: BLE001 — the analyst sees a 500 whatever the exception class is
        return 500, f"{type(exc).__name__}: {exc}"
    return response.status_code, response.text[:300]


@pytest.mark.parametrize("ground", _open_grounds())
def test_an_open_identity_question_is_actionable_through_the_hitl_merge_endpoint(ground: str) -> None:
    """Invisible is not the whole cost: ``POST /hitl/merge`` resolves its subject **only** through a drawn
    ``same-as`` edge in the current view, so a refusal that drew no edge is not merely unseen, it is
    **un-adjudicable**. The analyst cannot accept it, cannot reject it, and cannot record a distinct-from
    against it. The pair has left the loop entirely while the partition still calls it an open question.

    The test proves the mechanism as well as the property: where no handle exists it POSTs the conventional
    id anyway and reports the status code, so the failure message states in one line why invisibility
    equals un-actionability rather than asserting it.

    "Actionable" means **both** verdicts. Accept-only is not a review loop, it is a ratchet: the analyst
    can confirm the machine's resemblance and cannot deny it, which is precisely the direction that
    fabricates an ORBAT.
    """
    case = REFUSALS[ground]()
    a, b = case.pair
    with _booted(case.config, case.claims) as client:
        view = client.get("/view").json()
        rendered = _identity_elements(view, a, b)
        if not rendered.merge_handles:
            probe = client.post(
                "/hitl/merge",
                json={"item_id": f"merge:same-as:{pair_key(a, b)}", "type": "merge",
                      "subject": f"same-as:{pair_key(a, b)}", "decision": "reject", "actor": "analyst"},
            )
            pytest.fail(
                f"[{ground}] the resolver calls this identity question OPEN, and the analyst has no way to "
                f"settle it: GET /view draws no same-as edge over {a}|{b} (elements={rendered.elements}), "
                f"and POST /hitl/merge on the conventional id returned {probe.status_code} "
                f"({probe.text[:160]}). The endpoint's only handle IS the drawn edge, so an undrawn "
                "refusal is un-adjudicable — the pair is out of the analyst's loop while the system still "
                "records it as unsettled."
            )
        handle = rendered.merge_handles[0]
        status, body = _adjudicate(client, handle, "reject")

    assert status == 200, (
        f"[{ground}] the analyst cannot REFUSE the proposed merge: POST /hitl/merge on the drawn handle "
        f"{handle!r} returned {status} — {body}. A card whose reject button fails is worse than no card: "
        "the resolver's resemblance can be confirmed and cannot be denied, so every wrong proposal is "
        "one-way."
    )


def test_an_analyst_can_refuse_the_merge_of_two_identically_named_co_located_units() -> None:
    """The single adjudication this whole system exists to make possible.

    Two batteries carrying the same descriptor, standing in one cantonment, is the over-merge with the
    worst blast radius in the project: fuse them and their two sites become one unit's before-and-after, so
    a relocation nobody reported is fabricated, the pair leaves the queue as machine-adjudicated, and the
    honest Known Gap is deleted. The analyst's ``reject`` is the last thing standing between the graph and
    that fabrication — and because the two mentions share a name (having no designation is *why* they are
    ambiguous), it is exactly the shape the writeback path has to survive.

    Both verdicts are exercised on a fresh app so neither can mask the other, and ``accept`` is included on
    purpose: if only the fusing verdict works, the loop is a ratchet, and "keeping a human in the loop" is
    a claim about a button that does nothing.
    """
    case = _colocation_at(BAND_PROBABLE)
    outcomes: dict[str, tuple[int, str]] = {}
    for decision in ("reject", "accept"):
        with _booted(case.config, case.claims) as client:
            rendered = _identity_elements(client.get("/view").json(), *case.pair)
            assert rendered.merge_handles, (
                "fixture precondition: no candidate same-as edge to adjudicate — see "
                "test_a_withheld_merge_appears_on_the_rendered_view, which owns that half"
            )
            outcomes[decision] = _adjudicate(client, rendered.merge_handles[0], decision)

    broken = {d: r for d, r in outcomes.items() if r[0] != 200}
    assert not broken, (
        f"the analyst cannot adjudicate two identically-named co-located units: {broken} (working "
        f"verdicts: { {d: r[0] for d, r in outcomes.items() if r[0] == 200} }). If REJECT is the failing "
        "one, the only verdict the system accepts is the one that fuses them — the exact over-merge that "
        "invents a relocation, and the human in the loop has a button that raises instead of a decision "
        "that lands."
    )


# ── P5's other edge: a DERIVED finding must not speak with a curated human veto's voice ─────────

def _two_walls_one_view() -> tuple[Any, list[Any], tuple[str, str], tuple[str, str]]:
    """One graph carrying two walls of genuinely different provenance.

    * ``q1``/``q2`` — a **curated** do-not-merge an analyst wrote into config. Needs no explanation: the
      grounds are "a human decided", and the fixed text is honest.
    * ``port_a``/``port_b`` — a wall the system **derived**: it geocoded two mentions against the curated
      gazetteer, landed on two anchors declared mutually distinct, and inferred that these two entities
      cannot be one. Every step after the human's is machine inference over stated coordinates, and a
      *finding* with no stated grounds is indistinguishable from a missing edge.
    """
    base = rc.bundle(supersede_floor=dict(rk.SUPERSEDE_FLOOR))
    config = rc.with_resolution(
        base,
        earned_identity=rc.earned_identity_block(),
        distinct_from={"Zeta Alpha Works": ["Zeta Beta Works"]},
    )
    claims = [
        # the derived wall: two seaport mentions ~35 km apart that the gazetteer holds apart
        rc.site("port_a", "Karachi Port", site_class=None, lat=24.835, lon=66.982, doc="d1"),
        rc.site("port_b", "Port Qasim", site_class=None, lat=24.767, lon=67.333, doc="d2", sid="mid"),
        *rc.shared_neighbours("port_a", "port_b"),
        # the curated wall: two organisations an analyst declared distinct by name
        rc.ent("q1", "trading_org", "Zeta Alpha Works", doc="d1"),
        rc.ent("q2", "trading_org", "Zeta Beta Works", doc="d2", sid="mid"),
        *rc.shared_neighbours("q1", "q2", design="d2x", operator="op2x"),
    ]
    return config, claims, ("port_a", "port_b"), ("q1", "q2")


def test_a_derived_wall_does_not_render_the_words_of_a_curated_human_veto() -> None:
    """"A curated ``distinct_from`` needs no explanation — an analyst wrote it. A wall the system *derived*
    does." Both must therefore not read alike, and the derived one must name its own ground.

    Why this is a fabrication risk and not a wording preference: the two sentences license opposite analyst
    behaviour. "An analyst wrote this" is settled and closes the question. "The machine inferred this from
    two coordinates and a gazetteer" is a *finding* that can be wrong — the gazetteer may lack an alias,
    the coordinate may be a report of the wrong berth — and it is exactly the kind of inference the analyst
    is in the loop to check. Printing the machine's inference in the human's voice retires a live question
    by impersonation, and the analyst has no way to tell which walls are theirs.
    """
    config, claims, derived, curated = _two_walls_one_view()
    part = resolve(claims, config)
    for pair in (derived, curated):
        assert rc.walled(part, *pair), (
            f"fixture precondition: {pair} is not walled (distinct_from={part.distinct_from}); this test "
            "compares two walls and needs both to exist"
        )
    view = _wire_view(config, claims)
    derived_text = " ".join(sorted(_identity_elements(view, *derived).grounds.values()))
    curated_text = " ".join(sorted(_identity_elements(view, *curated).grounds.values()))

    assert derived_text, (
        f"the derived geographic wall reached GET /view with no grounds at all: "
        f"{_identity_elements(view, *derived).elements}"
    )
    assert derived_text != curated_text, (
        "a wall the system DERIVED and a wall a human CURATED arrive at the analyst as the same sentence "
        f"— both read {derived_text!r}. The analyst cannot tell an inference from a decision, so the "
        "machine's guess is retired behind the human's authority."
    )
    assert CURATED_WALL_TEXT not in derived_text.lower(), (
        f"the derived wall is presented as an {CURATED_WALL_TEXT!r} — a claim that a human declared these "
        f"two distinct. Nobody did: the system geocoded two mentions and inferred it. Wire said "
        f"{derived_text!r}."
    )
    assert any(tok in derived_text.lower() for tok in ("place", "location", "geo", "km", "distance",
                                                      "gazetteer", "port", "coordinate")), (
        f"the derived wall states no ground an analyst could check: {derived_text!r}. The instruction here "
        "is specific — 'verify the two coordinates / add the missing gazetteer alias' — and it is lost."
    )


# ── the licensing quote: the document's own words must travel with the escalation ────────────────

def _name_variant_case() -> tuple[Any, list[Any], tuple[str, str], str]:
    """A raise-only ``NAME_VARIANT`` coreference — the case whose whole value IS the referral.

    It is raise-only *permanently*: an authoritative bind bypasses banding, so a licensed NAME_VARIANT
    would simply be the exact-name auto-merge lane the design exists to delete. It therefore may never
    fuse, which makes the escalation the only product — and an escalation an analyst cannot adjudicate in
    one read is an unfalsifiable assertion that two mentions might be one thing.
    """
    name = "Alpha Air Defence Regiment"
    quote = f"the {name} (AADR) was inducted in March"
    claims = [
        rc.ent("reg_long", "unit", name, doc="d1"),
        rc.ent("reg_short", "unit", "AADR", doc="d1", sid="mid",
               attrs={"service_branch": "Pakistan Army"}),
        rc.coref("reg_long", "reg_short", evidence=rc.NAME_VARIANT, quote=quote, doc="d1"),
    ]
    return _live(), claims, ("reg_long", "reg_short"), quote


def test_the_rendered_escalation_carries_the_documents_licensing_quote() -> None:
    """"…a queued candidate carrying the reason **and the quote**."

    An audit already found this justification fictional once: the quote was stamped on the claim and read
    nowhere, so "the analyst is handed the sentence" described a screen nobody could see. This pins the
    words on the wire.
    """
    config, claims, pair, quote = _name_variant_case()
    part = resolve(claims, config)
    assert not rc.fused(part, *pair), "fixture precondition: a raise-only NAME_VARIANT must not fuse"
    view = _wire_view(config, claims)
    rendered = _identity_elements(view, *pair)

    assert rendered.grounds, (
        f"a raise-only coreference reached the analyst with no rationale at all (elements="
        f"{rendered.elements}). NAME_VARIANT is raise-only permanently — the referral is its whole value."
    )
    joined = " ".join(rendered.grounds.values())
    assert quote in joined, (
        f"the escalation does not carry the document's own words. Wanted {quote!r}; the wire said "
        f"{rendered.grounds}. The quote is the only thing that lets an analyst judge the proposal in one "
        "read — and, just as importantly, judge whether the REFUSAL was right."
    )


def test_the_licensing_quote_is_reachable_as_provenance_not_only_as_prose() -> None:
    """The quote must be *cited*, not merely *narrated*.

    ``view/pipeline._resolution_edges`` states the contract: the candidate edge carries
    ``claim_ids=partition.identity_claims[key]`` precisely so that "``GET /evidence/{edge_id}`` serves
    exactly this list, so no new route is needed". That is the one-click-to-source non-negotiable applied
    to an identity proposal: a sentence retyped into a rationale string cannot be audited, cannot be
    re-read in context, and carries no source id, grade or date. If the drawer is empty, the analyst is
    asked to trust the resolver's paraphrase of the evidence for the resolver's own proposal.
    """
    config, claims, pair, quote = _name_variant_case()
    with _booted(config, claims) as client:
        view = client.get("/view").json()
        rendered = _identity_elements(view, *pair)
        assert rendered.merge_handles, (
            f"no candidate same-as edge over {pair} on GET /view, so there is nothing to open a drawer on "
            f"(elements={rendered.elements})"
        )
        handle = rendered.merge_handles[0]
        drawer = client.get(f"/evidence/{handle}")
        assert drawer.status_code == 200, f"GET /evidence/{handle} → {drawer.status_code} {drawer.text[:200]}"
        body = drawer.json()

    assert body.get("claims"), (
        f"the provenance drawer for the identity proposal {handle!r} cites NOTHING (claims=[]), yet a "
        f"source did speak: a coreference claim licensed this pair with {quote!r}. The proposal's own "
        "evidence is unreachable from the surface that exists to answer 'how do you know that?'."
    )
    assert quote in drawer.text, (
        f"the drawer for {handle!r} resolves claims but not the licensing sentence: {quote!r} is absent "
        f"from the payload. A claim id without its words is a pointer, not a source."
    )


# ── the mirrors: the fix must not be "put a rationale on everything" ─────────────────────────────

def test_an_earned_merge_carries_no_refusal_record_on_the_rendered_view() -> None:
    """A queue full of reasons for merges that were never withheld is the same failure as a queue with none.

    One name, one country spelled two ways, and a document stating the equivalence: this fuses, and the
    analyst must see one record — not a candidate edge, not an identity gap, not a rationale.
    """
    name = "Zeta Machine Works"
    claims = [
        rc.ent("z1", "trading_org", name, doc="d1", attrs={"origin_country": "China"}),
        rc.ent("z2", "trading_org", name, doc="d1", sid="mid", attrs={"origin_country": "CHINA"}),
        rc.coref("z1", "z2", quote=f"{name}, also known as {name}, per the register", doc="d1"),
    ]
    config = _live()
    part = resolve(claims, config)
    assert rc.fused(part, "z1", "z2"), (
        f"the control pair did not fuse ({rc.status(part, 'z1', 'z2')!r}). If this is refused, every "
        "refusal above is measuring timidity rather than judgement."
    )
    view = _wire_view(config, claims)
    rendered = _identity_elements(view, "z1", "z2")
    assert not rendered.elements, (
        f"an accepted merge is still being presented as an open identity question: {rendered.elements} / "
        f"{rendered.grounds}. A reason on every pair is as useless as a reason on none."
    )


# ── the last hop: the SPA is where the wire becomes something a human reads ──────────────────────

def _frontend_sources() -> list[Path]:
    root = Path(__file__).resolve().parents[3] / "frontend" / "src"
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*.ts*")
        if not p.name.endswith((".test.ts", ".test.tsx", ".d.ts"))
    )


def test_the_spa_reads_the_identity_refusal_reason_off_the_wire() -> None:
    """Rendering it into ``GET /view`` is the necessary half; nobody reads JSON.

    The SPA already does exactly this for the *other* refusal on the same bag — ``adapters.ts`` pulls
    ``attrs.supersede_hold_reason`` off an edge and prints why an overtaken assertion was not retired. So
    the pattern, the plumbing and the precedent all exist, and the identity rationale is simply not wired:
    the merge card is built from ``merge_confidence`` plus the score ``breakdown``, which shows the analyst
    *how strong* the resemblance is and never *why the system refused it*. Those are different questions,
    and only the second one carries the instruction.
    """
    sources = _frontend_sources()
    if not sources:
        pytest.skip("no frontend/src tree in this checkout (backend-only build) — nothing to scan")

    pattern = re.compile(r"""attrs\s*(\?\s*)?\.\s*reason\b|attrs\s*(\?\s*)?\[\s*['"]reason['"]\s*\]""")
    hits = sorted(str(p.relative_to(p.parents[2])) for p in sources if pattern.search(p.read_text("utf-8")))

    assert hits, (
        "no SPA source reads the identity refusal reason (`attrs.reason`) off a same-as / distinct-from "
        "edge, so the rationale rebuild() renders into GET /view is displayed nowhere. The analyst sees a "
        "merge score and a set of signal bars — never the ground the resolver actually computed, and never "
        "the wall's grounds at all. `adapters.ts` already does this for `attrs.supersede_hold_reason`; "
        f"scanned {len(sources)} non-test sources under frontend/src."
    )


# ── the real booted corpus: invariants, because every defect here survived the fixtures ──────────

@pytest.fixture(scope="module")
def booted_corpus() -> Any:
    """The real app, booted the way it boots in production: real ``config/`` + the frozen claim bundles.

    Module-scoped: the boot + a full ``resolve()`` is ~2 s and every test below is a read.
    """
    if not scenario_bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {scenario_bundles_dir()} — corpus invariants cannot run")
    state = build_default_state(clock=lambda: FIXED_TS)
    state.boot()
    claims = list(state.evidence.replay())
    partition = resolve(claims, state.config.snapshot())
    with TestClient(create_app(state)) as client:
        view = client.get("/view").json()
    assert view.get("nodes"), "the booted corpus rendered an empty graph — nothing to assert against"
    return type("Corpus", (), {"partition": partition, "view": view, "claims": claims})


def test_every_open_identity_question_on_the_real_corpus_reaches_the_rendered_view(booted_corpus: Any) -> None:
    """The invariant, stated so it cannot go stale: **every** pair the resolver left open is on the surface.

    Not a count — the corpus is a regenerable fixture and a number would rot on the next extraction. The
    set is the resolver's own: ``candidates`` (pairs it explicitly put in front of a human) plus
    ``identity_refusals`` (pairs it un-fused and owes a named gap). Endpoints are matched tolerantly
    through ``entity_canonical``, so a pair is only counted absent if the analyst genuinely cannot see the
    question anywhere — never merely because a merge renamed one side.
    """
    part, view = booted_corpus.partition, booted_corpus.view
    canonical = dict(part.entity_canonical)
    open_pairs = {tuple(sorted(p)) for p in part.candidates}
    open_pairs |= {tuple(sorted(k.split("|", 1))) for k in part.identity_refusals if "|" in k}

    absent = []
    for a, b in sorted(open_pairs):
        if not _identity_elements(view, a, b, canonical=canonical).elements:
            absent.append((a, b))

    assert not absent, (
        f"{len(absent)} of {len(open_pairs)} open identity questions on the booted corpus never reach GET "
        f"/view — no same-as edge, no wall, no identity gap. The resolver is holding them as unsettled and "
        f"the analyst cannot see that any question exists, which is byte-identical (from outside) to two "
        f"mentions that never resembled each other. Examples: {absent[:6]}"
    )


def test_every_open_identity_question_on_the_real_corpus_is_adjudicable(booted_corpus: Any) -> None:
    """Visible is not enough on the corpus either: ``POST /hitl/merge`` needs a drawn ``same-as`` edge.

    Scoped to ``candidates`` — the band whose definition is "kept separate → rendered as candidate same-as
    edges for an analyst to adjudicate". If a member of that band has no drawn edge, the band's own
    contract is false, and the pair is silently out of the review loop: nothing can accept it, reject it,
    or record a distinct-from against it, ever.
    """
    part, view = booted_corpus.partition, booted_corpus.view
    canonical = dict(part.entity_canonical)
    unactionable = [
        (a, b) for a, b in sorted({tuple(sorted(p)) for p in part.candidates})
        if not _identity_elements(view, a, b, canonical=canonical).merge_handles
    ]
    assert not unactionable, (
        f"{len(unactionable)} of {len(part.candidates)} HITL-band candidates have no drawn same-as edge on "
        f"GET /view, so POST /hitl/merge has no subject to resolve and the analyst can never settle them. "
        f"Examples: {unactionable[:6]}"
    )


def test_every_wall_ground_the_corpus_resolver_computed_reaches_the_rendered_view(booted_corpus: Any) -> None:
    """A derived wall's grounds are computed and then must survive to the surface.

    ``Partition.wall_reasons`` is populated only where the system *derived* a wall — "a stated relationship
    conflict at overlapping times is a finding, and a finding with no stated grounds is indistinguishable
    from a missing edge". So every entry in it is, by construction, a finding the analyst is owed. This
    asserts survival per-pair rather than counting, so it holds across re-extractions.
    """
    part, view = booted_corpus.partition, booted_corpus.view
    canonical = dict(part.entity_canonical)
    lost = []
    for pair_ref, computed in sorted(part.wall_reasons.items()):
        if "|" not in pair_ref:
            continue
        a, b = pair_ref.split("|", 1)
        rendered = _identity_elements(view, a, b, canonical=canonical)
        text = rendered.text
        if not text or (CURATED_WALL_TEXT in text and computed.lower() not in text):
            lost.append((a, b, rendered.elements, computed[:80]))

    assert not lost, (
        f"{len(lost)} of {len(part.wall_reasons)} DERIVED wall grounds computed on the booted corpus never "
        f"reach GET /view — the pair is either absent from the payload or presented with the generic "
        f"{CURATED_WALL_TEXT!r}, i.e. as a decision a human made. The system inferred these; the analyst "
        f"is shown no ground to check and no way to tell them from a curated trap. Examples: {lost[:4]}"
    )
