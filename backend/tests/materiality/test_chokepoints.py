"""Materiality precompute — chokepoint criteria #1/#4/#6/#7/#10 (spine/09; C/01).

UNKNOWN substitutability renders *candidate* + a Known Gap, never a confirmed sole-source (absence of
evidence ≠ evidence of absence, the disqualifying line).
"""

from __future__ import annotations

from chanakya.materiality.precompute import precompute
from chanakya.schemas import EdgeView, GraphView, NodeView
from tests.credibility.builders import bundle

CFG = bundle()


def _supply(target: str, *, status: str | None = None, eid: str = "e-sup") -> EdgeView:
    return EdgeView(id=eid, type="supplies-component", source="mfr", target=target,
                    claim_ids=["c-sup"], status=status)


def _mat(view: GraphView, node_id: str):
    return next(n for n in view.nodes if n.id == node_id).materiality


def test_unknown_substitutability_is_candidate_not_sole_source() -> None:
    comp = NodeView(id="comp", type="component", claim_ids=["c1"])
    mfr = NodeView(id="mfr", type="manufacturer", claim_ids=["c2"])
    view = precompute(GraphView(nodes=[comp, mfr], edges=[_supply("comp")]), CFG)
    m = _mat(view, "comp")
    assert m.chokepoint_status == "candidate"        # sole-source in-degree, but substitutability unknown
    assert m.substitutability_state == "UNKNOWN"
    assert any(g.related_ref == "comp" for g in view.known_gaps)  # candidate ⇒ first-class Known Gap
    assert m.contributing_refs                        # cites its basis


def test_known_alternate_dissolves_the_chokepoint() -> None:
    comp = NodeView(id="comp", type="component", claim_ids=["c1"])
    alt = NodeView(id="alt", type="component", claim_ids=["c2"])
    mfr = NodeView(id="mfr", type="manufacturer", claim_ids=["c3"])
    sub = EdgeView(id="e-sub", type="substitutable-by", source="comp", target="alt", claim_ids=["c4"])
    view = precompute(GraphView(nodes=[comp, alt, mfr], edges=[_supply("comp"), sub]), CFG)
    m = _mat(view, "comp")
    assert m.substitutability_state == "known-alternates"
    assert m.chokepoint_status == "none"


def test_adversary_denial_alternate_is_discounted() -> None:
    # A seeded fake second-source can't dissolve a real chokepoint (C/01 criterion #3).
    comp = NodeView(id="comp", type="component", claim_ids=["c1"])
    alt = NodeView(id="alt", type="component", attrs={"adversary_denial_flag": True}, claim_ids=["c2"])
    mfr = NodeView(id="mfr", type="manufacturer", claim_ids=["c3"])
    sub = EdgeView(id="e-sub", type="substitutable-by", source="comp", target="alt", claim_ids=["c4"])
    view = precompute(GraphView(nodes=[comp, alt, mfr], edges=[_supply("comp"), sub]), CFG)
    m = _mat(view, "comp")
    assert m.substitutability_state == "UNKNOWN"       # the fake alternate is discounted
    assert m.chokepoint_status == "candidate"


def test_foreign_control_backed_confirms_severity() -> None:
    comp = NodeView(id="comp", type="component", attrs={"foreign_control": "OEM-China"}, claim_ids=["c1"])
    mfr = NodeView(id="mfr", type="manufacturer", claim_ids=["c2"])
    view = precompute(GraphView(nodes=[comp, mfr], edges=[_supply("comp")]), CFG)
    assert _mat(view, "comp").chokepoint_status == "confirmed"


def test_all_inferred_chokepoint_is_capped_to_candidate() -> None:
    # #7 confidence ceiling: an all-inferred nomination (every supporting edge only `possible`) can't confirm.
    comp = NodeView(id="comp", type="component", attrs={"foreign_control": "OEM-China"}, claim_ids=["c1"])
    mfr = NodeView(id="mfr", type="manufacturer", claim_ids=["c2"])
    view = precompute(GraphView(nodes=[comp, mfr], edges=[_supply("comp", status="possible")]), CFG)
    assert _mat(view, "comp").chokepoint_status == "candidate"


def test_precompute_is_replayable() -> None:
    def build() -> GraphView:
        return GraphView(
            nodes=[NodeView(id="comp", type="component", claim_ids=["c1"]),
                   NodeView(id="mfr", type="manufacturer", claim_ids=["c2"])],
            edges=[_supply("comp")],
        )
    a = precompute(build(), CFG)
    b = precompute(build(), CFG)
    assert _mat(a, "comp").model_dump() == _mat(b, "comp").model_dump()
