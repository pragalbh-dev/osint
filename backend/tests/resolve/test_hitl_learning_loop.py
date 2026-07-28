"""The HITL→resolution learning loop, driven through the REAL producer→writeback→replay path.

These tests do NOT hand-construct a ``DecisionRecord`` in the shape the resolver happens to read
(``decision={"pair":[...],"verdict":"accept"}``) — the direct-construction tests in
``test_entity_resolution.py`` / ``test_review_regressions.py`` already do that, and they were passing
even while the live path was inert. Here the record is produced exactly as the running system produces
it: ``build_merge_item`` (the ★ merge card) → ``build_record`` (writeback) → append to the decision
log → ``resolve(..., decisions=...)``. That is the path the API route drives, and it is where the
learning loop was broken: the card put entity IDS in ``same_as``/``pair`` and the pair never reached
``aliases.build`` in a form it could read, so accept never linked and reject never barred.

Pair chosen (``H-200`` / ``HT-233``, component) is the same safe, un-trapped pair
``test_alias_grows_from_decision_log`` uses: no seeded alias and no ``distinct_from`` links them, so a
bare ``resolve`` leaves them apart and the analyst decision is the only thing that can move them.
"""

from __future__ import annotations

from chanakya.hitl import build_merge_item, build_record
from chanakya.resolve import resolve
from chanakya.schemas import HitlDecision
from chanakya.store import DecisionLog
from tests.resolve._helpers import entity, mk_config


def _cluster_of(part, eid: str) -> set[str]:
    """All ids fused with ``eid`` (via same_as / entity_canonical)."""
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


def _merge_card(*, decision: str):
    """The ★ merge card the resolver hands the analyst, produced with id+name candidate dicts (§4)."""
    return build_merge_item(
        item_id="mrg",
        candidate_a={"id": "comp_h200", "name": "H-200"},
        candidate_b={"id": "comp_ht233", "name": "HT-233"},
        signals=[{"signal": "name-attr", "weight": 0.3, "value": 0.8}],
        merge_score=0.6,
        band="needs-you",
        ts="t",
    )


def _record(item, chosen: str):
    """Writeback exactly as the running system does — the generic ``build_record`` mapping, no shims."""
    decision = HitlDecision(
        item_id=item.item_id, type=item.type, subject=item.subject, decision=chosen, actor="analyst"
    )
    return build_record(item, decision, ts="t")


# ── accept: the produced record must LINK the pair on replay (auto-resolve next rebuild) ─────────

def test_live_merge_accept_links_and_merges() -> None:
    cfg = mk_config()  # nothing seeded links the two
    claims = [entity("comp_h200", "component", "H-200"), entity("comp_ht233", "component", "HT-233")]
    assert resolve(claims, cfg).same_as == []  # baseline: no decision ⇒ no merge

    item = _merge_card(decision="accept")
    dl = DecisionLog()
    dl.append(_record(item, "accept"))

    part = resolve(claims, cfg, decisions=dl.replay())
    assert {"comp_h200", "comp_ht233"} <= _cluster_of(part, "comp_h200"), (
        "an accepted merge card must grow the alias table so the pair auto-resolves on replay"
    )


# ── reject: the produced record must BAR the pair on replay (do-not-merge + drawn distinct-from) ─

def test_live_merge_reject_bars_the_pair() -> None:
    # A seeded alias would otherwise fuse them, so a reject that fails to bar is *observable* as a merge.
    cfg = mk_config(alias_table={"H-200": ["HT-233"]})
    claims = [entity("comp_h200", "component", "H-200"), entity("comp_ht233", "component", "HT-233")]
    assert {"comp_h200", "comp_ht233"} <= _cluster_of(resolve(claims, cfg), "comp_h200"), (
        "precondition: the seeded alias fuses the pair when there is no reject"
    )

    item = _merge_card(decision="reject")
    dl = DecisionLog()
    dl.append(_record(item, "reject"))

    part = resolve(claims, cfg, decisions=dl.replay())
    assert not ({"comp_h200", "comp_ht233"} <= _cluster_of(part, "comp_h200")), (
        "a rejected merge card must bar the pair even against a seeded alias (learned distinct-from)"
    )
    assert frozenset({"comp_h200", "comp_ht233"}) in {frozenset(p) for p in part.distinct_from}, (
        "a learned do-not-merge stays DRAWN so the trap is visible"
    )
