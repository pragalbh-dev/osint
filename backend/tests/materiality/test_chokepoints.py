"""Materiality precompute — chokepoint criteria #1/#4/#6/#7/#10 (spine/09; C/01).

The sole-source in-degree TEST is a fact about the *dependent* (does it have exactly one supplier on a
function?); the chokepoint FINDING attaches to the *supplier* end — the node that fails the sustainment if
it disappears (D-P4.7). UNKNOWN substitutability renders *candidate* + a Known Gap, never a confirmed
sole-source (absence of evidence ≠ evidence of absence, the disqualifying line).
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.materiality.precompute import precompute
from chanakya.schemas import EdgeView, GraphView, NodeView
from chanakya.settings import config_dir
from tests.credibility.builders import bundle

# The real ontology carries the per-edge ``supplier_end`` + ``materiality.function_attr`` declarations
# the fix reads; use it so the tests exercise the shipped config, not a hand-rolled shadow of it.
CFG = bundle(ontology=ConfigStore.seed_from(config_dir()).snapshot().ontology)


def _equips(supplier: str = "comp", dependent: str = "variant", *, status: str | None = None,
            eid: str = "e-eq") -> EdgeView:
    # equips is Component->Variant with supplier_end=from → the component is the supplier.
    return EdgeView(id=eid, type="equips", source=supplier, target=dependent,
                    claim_ids=["c-eq"], status=status)


def _component(nid: str, *, role: str | None = None, **attrs: object) -> NodeView:
    if role is not None:
        attrs["functional_role"] = role
    return NodeView(id=nid, type="component", attrs=attrs, claim_ids=[f"c-{nid}"])


def _variant(nid: str = "variant") -> NodeView:
    return NodeView(id=nid, type="variant", claim_ids=[f"c-{nid}"])


def _mat(view: GraphView, node_id: str):
    return next(n for n in view.nodes if n.id == node_id).materiality


def test_unknown_substitutability_is_candidate_not_sole_source() -> None:
    comp, variant = _component("comp"), _variant()
    view = precompute(GraphView(nodes=[comp, variant], edges=[_equips()]), CFG)
    m = _mat(view, "comp")                            # the SUPPLIER is nominated, not the consumer
    assert m.chokepoint_status == "candidate"        # sole-source in-degree, but substitutability unknown
    assert m.substitutability_state == "UNKNOWN"
    assert any(g.related_ref == "comp" for g in view.known_gaps)  # candidate ⇒ first-class Known Gap
    assert m.contributing_refs                        # cites its basis
    assert _mat(view, "variant").chokepoint_status == "none"      # the CONSUMER is not a supply chokepoint


def test_known_alternate_dissolves_the_chokepoint() -> None:
    comp, alt, variant = _component("comp"), _component("alt"), _variant()
    sub = EdgeView(id="e-sub", type="substitutable-by", source="comp", target="alt", claim_ids=["c4"])
    view = precompute(GraphView(nodes=[comp, alt, variant], edges=[_equips(), sub]), CFG)
    m = _mat(view, "comp")
    assert m.substitutability_state == "known-alternates"
    assert m.chokepoint_status == "none"


def test_adversary_denial_alternate_is_discounted() -> None:
    # A seeded fake second-source can't dissolve a real chokepoint (C/01 criterion #3).
    comp, variant = _component("comp"), _variant()
    alt = _component("alt", adversary_denial_flag=True)
    sub = EdgeView(id="e-sub", type="substitutable-by", source="comp", target="alt", claim_ids=["c4"])
    view = precompute(GraphView(nodes=[comp, alt, variant], edges=[_equips(), sub]), CFG)
    m = _mat(view, "comp")
    assert m.substitutability_state == "UNKNOWN"       # the fake alternate is discounted
    assert m.chokepoint_status == "candidate"


def test_foreign_control_backed_confirms_severity() -> None:
    comp, variant = _component("comp", foreign_control="OEM-China"), _variant()
    view = precompute(GraphView(nodes=[comp, variant], edges=[_equips()]), CFG)
    assert _mat(view, "comp").chokepoint_status == "confirmed"


def test_all_inferred_chokepoint_is_capped_to_candidate() -> None:
    # #7 confidence ceiling: an all-inferred nomination (every supporting edge only `possible`) can't confirm.
    comp, variant = _component("comp", foreign_control="OEM-China"), _variant()
    view = precompute(GraphView(nodes=[comp, variant], edges=[_equips(status="possible")]), CFG)
    assert _mat(view, "comp").chokepoint_status == "candidate"


def test_function_role_partitions_sole_source_within_one_variant() -> None:
    # A variant equipped by three components of DIFFERENT functional roles: each is the sole provider of
    # its function → each nominated, even though the variant's raw ``equips`` in-degree is 3 (the deeper
    # fix — per-edge-type counting would surface none of them).
    radar = _component("radar", role="engagement_fire_control")
    acq = _component("acq", role="acquisition")
    tel = _component("tel", role="launcher")
    variant = _variant()
    edges = [_equips("radar", eid="e1"), _equips("acq", eid="e2"), _equips("tel", eid="e3")]
    view = precompute(GraphView(nodes=[radar, acq, tel, variant], edges=edges), CFG)
    assert _mat(view, "radar").chokepoint_status == "candidate"
    assert _mat(view, "acq").chokepoint_status == "candidate"
    assert _mat(view, "tel").chokepoint_status == "candidate"
    assert _mat(view, "variant").chokepoint_status == "none"       # the consumer is never nominated


def test_two_same_role_components_are_not_sole_source() -> None:
    # Redundancy on one function: two engagement radars on one variant → neither is a SPOF.
    r1 = _component("r1", role="engagement_fire_control")
    r2 = _component("r2", role="engagement_fire_control")
    variant = _variant()
    edges = [_equips("r1", eid="e1"), _equips("r2", eid="e2")]
    view = precompute(GraphView(nodes=[r1, r2, variant], edges=edges), CFG)
    assert _mat(view, "r1").chokepoint_status == "none"
    assert _mat(view, "r2").chokepoint_status == "none"


def test_exported_by_nominates_the_manufacturer_not_the_contract() -> None:
    # exported-by is Contract->Manufacturer with supplier_end=to: the supplier is the exporter/OEM on the
    # `to` end, so a contract with a single exporter nominates the MANUFACTURER, never the contract.
    contract = NodeView(id="ct", type="contract_import_event", claim_ids=["c1"])
    mfr = NodeView(id="cpmiec", type="manufacturer", claim_ids=["c2"])
    edge = EdgeView(id="e-exp", type="exported-by", source="ct", target="cpmiec", claim_ids=["c-exp"])
    view = precompute(GraphView(nodes=[contract, mfr], edges=[edge]), CFG)
    assert _mat(view, "cpmiec").chokepoint_status == "candidate"   # the sole exporter is the chokepoint
    assert _mat(view, "ct").chokepoint_status == "none"            # the contract is the dependent


def test_off_ontology_supplier_is_not_nominated() -> None:
    # A `unit` in equips' component-only supplier slot is a mis-lane that slipped past the extractor, not
    # a supplier — the read-time endpoint guard (mirroring the write-time re-lane) must not nominate it,
    # so no chokepoint gap ever lands on a unit/variant node.
    unit = NodeView(id="unit_paad", type="unit", claim_ids=["c1"])
    variant = _variant("ly80")
    edge = _equips("unit_paad", "ly80")  # unit -> variant on the equips (component->variant) lane
    view = precompute(GraphView(nodes=[unit, variant], edges=[edge]), CFG)
    assert _mat(view, "unit_paad").chokepoint_status == "none"
    assert not any(g.related_ref == "unit_paad" for g in view.known_gaps)


def test_precompute_is_replayable() -> None:
    def build() -> GraphView:
        return GraphView(nodes=[_component("comp"), _variant()], edges=[_equips()])
    a = precompute(build(), CFG)
    b = precompute(build(), CFG)
    assert _mat(a, "comp").model_dump() == _mat(b, "comp").model_dump()
