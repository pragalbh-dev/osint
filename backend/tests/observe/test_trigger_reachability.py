"""AH-3 — an armed tripwire whose condition CANNOT OCCUR must say so, not render as a quiet sentry.

The defect these cover, measured by booting the real app against the real corpus (248 nodes / 226
edges) before the fix:

* ``obs-followon-interceptor-order`` watches for a **new ``replenishes`` edge**. The rebuilt view holds
  **zero** edges of that type and **zero** ``interceptor_stockpile`` nodes for one to point at. It
  reported ``anchor_check: pending_coverage`` and advertised *"watching 66 node(s)"* — i.e. it read as
  a healthy tripwire that simply had nothing to report.
* ``obs-spares-tender-probable-induction`` compiles to ``arm-only``: ``_fire`` and ``arm`` both return
  before any detector runs, so it can never emit an alert however the graph changes. ``explain()`` knew
  that; no list-level surface said it.

Both are the non-negotiable's monitoring case: **an absence of alerts presented as an all-clear**. The
anchor work (AH-1/AH-2) taught a tripwire to say "I cannot see my target"; this is the layer up — "I can
see everything, and the thing I am watching for cannot occur here."

Two properties are load-bearing and each has its own test family:

1. **Conservative in the safe direction.** A false *unreachable* tells an analyst to stop trusting a wire
   that works — far worse than the status quo. So ``reachable`` is returned for anything undetermined
   and is explicitly *not* a clean bill of health.
2. **NON-VACUITY.** The way a check like this silently dies is by returning one constant. Several tests
   below fail if every observable is reported reachable regardless of the graph — including one that
   flips the *same* observable's verdict by changing only the view, which no constant can satisfy.
"""

from __future__ import annotations

from typing import Any

from chanakya.observe import (
    ATTRIBUTE_NOT_COVERED,
    NEVER_FIRES,
    NO_COVERAGE,
    OUT_OF_WATCH_SCOPE,
    REACHABLE,
    TYPE_NOT_MODELLED,
    evaluate,
    explain,
    reachability_diagnostics,
    trigger_reachability,
)
from chanakya.schemas import (
    ObservableDef,
    OntologyConfig,
    SubjectLens,
    SubjectsConfig,
)

from .conftest import config_with, relocation_observable, view

# ── fixtures: the two shipped shapes, and a graph that does / does not support them ──────────────

_UNIT_NODES: list[dict[str, Any]] = [
    {"id": "unit_alpha", "type": "unit", "name": "Alpha Battery"},
    {"id": "site_a", "type": "basing_site", "name": "Site A"},
    {"id": "site_b", "type": "basing_site", "name": "Site B"},
]

_CONTRACT_NODES: list[dict[str, Any]] = [
    {"id": "contract_1", "type": "contract_import_event", "name": "BoL 2024-114"},
]

_STOCKPILE_NODE: dict[str, Any] = {
    "id": "stock_1", "type": "interceptor_stockpile", "name": "HQ-9/P interceptor stock",
}


def _basing_view() -> Any:
    """A graph the relocation wire can genuinely watch: a unit, sites, and a ``based-at`` edge."""
    return view(nodes=_UNIT_NODES + _CONTRACT_NODES, edges=[
        {"id": "e-a", "type": "based-at", "source": "unit_alpha", "target": "site_a",
         "edge_instance": "ei-1", "claim_ids": ["c1"]},
    ])


def _relocated_view() -> Any:
    return view(nodes=_UNIT_NODES + _CONTRACT_NODES, edges=[
        {"id": "e-b", "type": "based-at", "source": "unit_alpha", "target": "site_b",
         "edge_instance": "ei-2", "claim_ids": ["c2"]},
    ])


def _resupplied_view() -> Any:
    """The same graph AFTER coverage produces the resupply link the follow-on wire waits for."""
    return view(nodes=_UNIT_NODES + _CONTRACT_NODES + [_STOCKPILE_NODE], edges=[
        {"id": "e-a", "type": "based-at", "source": "unit_alpha", "target": "site_a",
         "edge_instance": "ei-1", "claim_ids": ["c1"]},
        {"id": "e-r", "type": "replenishes", "source": "contract_1", "target": "stock_1",
         "edge_instance": "ei-3", "claim_ids": ["c3"]},
    ])


def _followon_observable(**overrides: Any) -> ObservableDef:
    """``obs-followon-interceptor-order`` as shipped in ``config/observables.yaml``."""
    base: dict[str, Any] = {
        "observable_id": "obs-followon-interceptor-order",
        "trigger": {
            "on": "new_edge",
            "edge_type": "replenishes",
            "from_type": "contract_import_event",
            "to_type": "interceptor_stockpile",
            "match_on": ["resolved_contract", "resolved_stockpile"],
            "event_subtype": "follow-on-order",
        },
        "severity": "notify",
    }
    base.update(overrides)
    return ObservableDef.model_validate(base)


def _spares_observable() -> ObservableDef:
    """``obs-spares-tender-probable-induction`` as shipped — a ``new_claim`` trigger (arm-only)."""
    return ObservableDef.model_validate({
        "observable_id": "obs-spares-tender-probable-induction",
        "trigger": {
            "on": "new_claim",
            "source_class": "customs-tender",
            "implies_edge": "sustained-by",
            "target_status_ceiling": "probable",
            "match_on": ["resolved_unit"],
        },
        "severity": "notify",
    })


def _ontology() -> OntologyConfig:
    """The slice of ``config/ontology.yaml`` these cases turn on, declared here rather than inherited.

    The golden F0 fixture ontology predates ``replenishes`` / ``interceptor_stockpile``, and inheriting
    it would make the *coverage* case (declared, uncovered) indistinguishable from the *modelling* case
    (undeclared) — collapsing the very distinction under test into an artefact of fixture drift. So the
    shipped declarations are restated: ``replenishes`` is an ``extractor: true`` edge from a contract to
    a stockpile, exactly as ``config/ontology.yaml`` has it.
    """
    return OntologyConfig.model_validate({
        "node_types": [
            {"name": "unit"}, {"name": "basing_site"},
            {"name": "contract_import_event"}, {"name": "interceptor_stockpile"},
        ],
        "edge_types": [
            {"name": "based-at", "from": "unit", "to": "basing_site", "extractor": True,
             "instance_key": ["from"]},
            {"name": "replenishes", "from": "contract_import_event", "to": "interceptor_stockpile",
             "extractor": True},
        ],
    })


def _config(*observables: ObservableDef, lens: SubjectLens | None = None):
    """A bundle carrying these observables, the ontology slice above, and (optionally) one lens."""
    bundle = config_with(*observables).model_copy(update={"ontology": _ontology()})
    if lens is not None:
        bundle = bundle.model_copy(update={"subjects": SubjectsConfig(subjects=[lens])})
    return bundle


# ── 1. the two shipped defects, named ────────────────────────────────────────────────────────────

def test_arm_only_tripwire_is_reported_as_never_firing() -> None:
    """``obs-spares-tender-probable-induction`` can NEVER alert — and every surface must say so.

    It is not a coverage gap: no document, however perfect, produces an alert from a trigger form the
    evaluator has no detector for. So the gap kind is the one that needs a human, not a document.
    """
    obs = _spares_observable()
    v = _basing_view()
    r = trigger_reachability(obs, v, _config(obs))

    assert r.status == NEVER_FIRES
    assert r.can_fire is False
    assert r.gap_kind == "engine"  # not "data" — no ingest fixes this
    assert {"kind": "trigger_form", "name": "new_claim"} in r.missing
    assert r.warning is not None
    # It names the specific missing thing and refuses to imply an all-clear.
    assert "new_claim" in r.warning
    assert "all-clear" in r.warning
    # …and the claim is TRUE: the evaluator really emits nothing, however the graph changes.
    assert evaluate(v, _relocated_view(), _config(obs)) == []


def test_missing_edge_type_is_reported_as_a_coverage_gap_naming_the_predicate() -> None:
    """The 'watching 66 node(s)' wire: every anchor resolves, and it still cannot fire.

    The message must name the **predicate** (``replenishes``) and the **node type** the edge needs an
    endpoint of (``interceptor_stockpile``) — "not reachable" alone is useless to an analyst.
    """
    obs = _followon_observable()
    v = _basing_view()
    r = trigger_reachability(obs, v, _config(obs))

    assert r.status == NO_COVERAGE
    assert r.can_fire is False
    assert r.gap_kind == "data"  # modelled and extractable — a document fixes this
    assert r.candidate_count == 0
    assert {"kind": "edge_type", "name": "replenishes"} in r.missing
    assert {"kind": "node_type", "name": "interceptor_stockpile"} in r.missing
    assert r.warning is not None
    assert "replenishes" in r.warning and "interceptor_stockpile" in r.warning
    assert "all-clear" in r.warning
    # And the verdict is true of the running evaluator, not just of this module's opinion.
    assert evaluate(v, _relocated_view(), _config(obs)) == []


def test_the_coverage_gap_clears_itself_when_the_link_arrives() -> None:
    """A data gap is a *coverage* statement, not a fault: the same wire is reachable once a doc lands.

    This is also the sharpest non-vacuity control in the file — the observable, the config and the
    ontology are byte-identical across the two calls and only the VIEW differs, so any implementation
    that answers from the trigger alone (or answers a constant) fails here.
    """
    obs = _followon_observable()
    before = trigger_reachability(obs, _basing_view(), _config(obs))
    after = trigger_reachability(obs, _resupplied_view(), _config(obs))

    assert before.status == NO_COVERAGE and before.can_fire is False
    assert after.status == REACHABLE and after.can_fire is True
    assert after.warning is None
    # …and the evaluator agrees: the wire that "cannot fire" now does.
    fired = evaluate(_basing_view(), _resupplied_view(), _config(obs))
    assert [a.observable_id for a in fired] == ["obs-followon-interceptor-order"]


# ── 2. data gap vs modelling gap — an analyst does different things about them ───────────────────

def test_an_undeclared_type_is_a_modelling_gap_not_a_coverage_gap() -> None:
    """"No document produces this yet" and "the ontology has no such relation" must not read alike.

    The first self-heals on the next ingest; the second needs someone to edit ``config/ontology.yaml``.
    Rendering them the same way tells an analyst to wait for a document that can never help.
    """
    obs = _followon_observable(trigger={"on": "new_edge", "edge_type": "resupplies-with"})
    r = trigger_reachability(obs, _basing_view(), _config(obs))

    assert r.status == TYPE_NOT_MODELLED
    assert r.gap_kind == "modelling"
    assert {"kind": "edge_type", "name": "resupplies-with"} in r.missing
    assert r.warning is not None and "resupplies-with" in r.warning
    assert "config/ontology.yaml" in r.warning

    # Contrast, on the SAME graph: a declared-but-uncovered type is the quieter, self-healing story.
    modelled = trigger_reachability(_followon_observable(), _basing_view(), _config(obs))
    assert modelled.gap_kind == "data"
    assert modelled.status != r.status


def test_a_view_instance_outranks_the_ontology_declaration() -> None:
    """Conservative direction: a type PRESENT in the view is reachable even if undeclared.

    Derived/discovered instance types exist that the ontology does not enumerate. Calling one a
    modelling gap because it is undeclared would be a false 'unreachable' — the dangerous direction.
    """
    v = view(nodes=[{"id": "n1", "type": "wholly_undeclared_type", "name": "n"}])
    obs = ObservableDef.model_validate({
        "observable_id": "obs-odd", "trigger": {"on": "new_node", "node_type": "wholly_undeclared_type"},
    })
    assert trigger_reachability(obs, v, _config(obs)).status == REACHABLE


# ── 3. the attribute case — name the field, not just "not reachable" ─────────────────────────────

def test_a_field_no_element_carries_is_named_as_the_missing_thing() -> None:
    """Every operator but ``not_exists`` returns False on an absent field, so the wire cannot fire."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-chokepoint",
        "trigger": {"on": "ge", "edge_type": "based-at", "field": "materiality.chokepoint_count",
                    "value": 3},
    })
    r = trigger_reachability(obs, _basing_view(), _config(obs))

    assert r.status == ATTRIBUTE_NOT_COVERED
    assert r.gap_kind == "data"
    assert {"kind": "attribute", "name": "materiality.chokepoint_count"} in r.missing
    assert r.warning is not None and "materiality.chokepoint_count" in r.warning
    assert r.candidate_count == 1  # it DID find candidates — the field is what is missing
    assert evaluate(_basing_view(), _relocated_view(), _config(obs)) == []


def test_a_field_that_is_present_does_not_trip_the_attribute_check() -> None:
    """Non-vacuity for the attribute branch: a populated field must read as reachable."""
    v = view(nodes=_UNIT_NODES, edges=[
        {"id": "e-a", "type": "based-at", "source": "unit_alpha", "target": "site_a",
         "edge_instance": "ei-1", "attrs": {"readiness": "operational"}},
    ])
    obs = ObservableDef.model_validate({
        "observable_id": "obs-readiness",
        "trigger": {"on": "eq", "edge_type": "based-at", "field": "attrs.readiness",
                    "value": "operational"},
    })
    assert trigger_reachability(obs, v, _config(obs)).status == REACHABLE


# ── 4. the scope case — defers to the anchor diagnosis rather than inventing a second one ────────

def test_candidates_outside_the_watch_scope_are_reported_and_point_at_the_anchor_check() -> None:
    obs = relocation_observable(watch_instances=["unit_nowhere"])
    r = trigger_reachability(obs, _basing_view(), _config(obs))

    assert r.status == OUT_OF_WATCH_SCOPE
    assert r.gap_kind == "scope"
    assert r.candidate_count == 1
    assert r.warning is not None
    assert "unit_nowhere" in r.warning  # the anchor diagnosis is quoted, not re-derived
    assert evaluate(_basing_view(), _relocated_view(), _config(obs)) == []


def test_a_scoped_tripwire_whose_anchor_resolves_stays_reachable() -> None:
    """Do not regress the anchor work, and do not cry wolf on a healthy scoped wire."""
    obs = relocation_observable(watch_instances=["unit_alpha"])
    assert trigger_reachability(obs, _basing_view(), _config(obs)).status == REACHABLE


def test_a_lens_scoped_tripwire_over_the_lens_anchor_stays_reachable() -> None:
    lens = SubjectLens(subject_id="lens-x", anchors=["unit_alpha"], max_hops=1)
    obs = relocation_observable(subject="lens-x")
    assert trigger_reachability(obs, _basing_view(), _config(obs, lens=lens)).status == REACHABLE


# ── 5. an unperformed check is never reported as a pass ──────────────────────────────────────────

def test_without_a_view_the_check_says_it_did_not_run() -> None:
    obs = _followon_observable()
    r = trigger_reachability(obs, None, None)
    assert r.checked is False
    assert r.warning is not None and "not checked" in r.warning
    assert "not a statement that it can" in r.warning


def test_explain_carries_the_verdict_for_the_proposer_confirm_screen() -> None:
    """``agent/propose.py`` shows ``explain()`` before an analyst arms a wire — the one review moment."""
    obs = _followon_observable()
    info = explain(obs, _basing_view(), _config(obs))
    assert info["reachability"]["status"] == NO_COVERAGE
    assert info["reachability"]["can_fire"] is False
    assert "replenishes" in info["reachability_warning"]

    # Without a view it must not claim a pass it did not earn.
    blind = explain(obs)
    assert blind["reachability"]["checked"] is False


# ── 6. THE NON-VACUITY CONTROLS — this is how the check would silently die ───────────────────────

def test_the_check_discriminates_rather_than_blessing_everything() -> None:
    """FAILS if every observable is reported reachable regardless of the graph.

    A reachability check that always answers "reachable" is indistinguishable from no check at all, and
    it is exactly what this file exists to prevent: the whole point is that a *silent* tripwire and a
    *healthy* one must stop rendering identically. So one assertion pins that on one graph the verdicts
    genuinely differ across the three shipped shapes.
    """
    reloc, followon, spares = relocation_observable(), _followon_observable(), _spares_observable()
    rows = reachability_diagnostics(_config(reloc, followon, spares), _basing_view())
    by_id = {r["observable_id"]: r for r in rows}

    assert len(rows) == 3  # complete, not problems-only — a card needs the positive verdict too
    assert any(r["can_fire"] for r in rows), "no observable reachable — the check is vacuously negative"
    assert not all(r["can_fire"] for r in rows), "every observable reachable — the check is vacuous"
    assert by_id["obs-relocation"]["can_fire"] is True
    assert by_id["obs-followon-interceptor-order"]["can_fire"] is False
    assert by_id["obs-spares-tender-probable-induction"]["can_fire"] is False
    # Three distinct outcomes, not one flag reused: the analyst acts differently on each.
    assert len({r["status"] for r in rows}) == 3
    assert {r["gap_kind"] for r in rows} == {None, "data", "engine"}


def test_every_unreachable_verdict_is_true_of_the_running_evaluator() -> None:
    """The anti-drift control: nothing declared unreachable may actually fire.

    A wrong 'unreachable' is the dangerous failure — it tells an analyst to stop trusting a working
    tripwire. So every negative verdict is checked against ``evaluate()`` on a delta that exercises the
    graph, on the two views the rest of this file uses.
    """
    observables = [
        relocation_observable(),
        _followon_observable(),
        _spares_observable(),
        relocation_observable(observable_id="obs-out-of-scope", watch_instances=["unit_nowhere"]),
    ]
    cfg = _config(*observables)
    before, after = _basing_view(), _resupplied_view()
    fired = {a.observable_id for a in evaluate(before, after, cfg)}

    verdicts = {r["observable_id"]: r for r in reachability_diagnostics(cfg, after)}
    for observable_id, row in verdicts.items():
        if not row["can_fire"]:
            assert observable_id not in fired, (
                f"{observable_id} was reported unreachable but the evaluator fired it — a false "
                "'unreachable' is the dangerous direction"
            )
    # …and the control that keeps THAT assertion from passing vacuously: something did fire.
    assert fired, "nothing fired at all — the anti-drift assertion would be vacuous"


def test_every_verdict_names_a_specific_missing_thing_or_says_reachable() -> None:
    """"Not reachable" on its own is useless. A negative verdict must always name what is missing."""
    cfg = _config(relocation_observable(), _followon_observable(), _spares_observable())
    for row in reachability_diagnostics(cfg, _basing_view()):
        if row["can_fire"]:
            assert row["warning"] is None
            continue
        assert row["missing"], f"{row['observable_id']} says it cannot fire but names nothing missing"
        assert row["warning"]
        for entry in row["missing"]:
            assert entry["name"] in row["warning"], "the named thing must appear in the sentence"


def test_a_geofence_over_nodes_with_no_coordinates_is_reported() -> None:
    """The location seam's own version of the attribute gap — an uncoordinated node cannot cross a fence.

    ``within_area`` returns ``None`` without a WGS84 point, so the crossing state is indeterminate and
    the wire is silent forever. Named the same way as any other missing attribute, and both field paths
    appear in the sentence so a surface can build a chip from ``missing`` without parsing prose.
    """
    v = view(nodes=[{"id": "site_a", "type": "basing_site", "name": "Site A"}])
    obs = ObservableDef.model_validate({
        "observable_id": "obs-fence",
        "trigger": {"on": "geofence_crossing", "node_type": "basing_site",
                    "area": {"center": [32.0, 74.0], "radius_km": 25}},
    })
    r = trigger_reachability(obs, v, _config(obs))

    assert r.status == ATTRIBUTE_NOT_COVERED
    assert r.candidate_count == 1
    assert r.warning is not None
    for entry in r.missing:
        assert entry["name"] in r.warning

    # Non-vacuity: give the node a coordinate and the same wire reads as reachable.
    located = view(nodes=[{"id": "site_a", "type": "basing_site", "name": "Site A",
                           "location": {"raw": "32.1N 74.1E", "wgs84_lat": 32.1, "wgs84_lon": 74.1}}])
    assert trigger_reachability(obs, located, _config(obs)).status == REACHABLE


def test_an_untyped_trigger_over_an_empty_graph_names_nothing_it_cannot_name() -> None:
    """A trigger with no type filter has no predicate to blame — so the sentence must not invent one.

    This is the fix committing the original defect against itself: naming a specific missing thing that
    was never declared would be exactly the fabrication the module exists to prevent. It still says it
    cannot fire; it just says so about the whole graph.
    """
    obs = ObservableDef.model_validate({"observable_id": "obs-any-edge", "trigger": {"on": "new_edge"}})
    r = trigger_reachability(obs, view(nodes=_UNIT_NODES), _config(obs))

    assert r.status == NO_COVERAGE
    assert r.missing == ()  # nothing to name, so nothing named
    assert r.warning is not None and "None" not in r.warning
    assert "whole graph" in r.warning


def test_the_scope_verdict_names_the_anchors_that_define_the_scope() -> None:
    """Every entry in ``missing`` must be findable in the sentence — including the scope case.

    "Not reachable, watch scope" tells an analyst nothing. Naming the anchors that draw the scope is
    what makes the verdict actionable, and it keeps the one invariant every surface relies on: the
    structured ``missing`` list and the prose never disagree about what is absent.
    """
    obs = relocation_observable(watch_instances=["unit_nowhere", "site_elsewhere"])
    r = trigger_reachability(obs, _basing_view(), _config(obs))

    assert r.status == OUT_OF_WATCH_SCOPE
    assert {m["name"] for m in r.missing} == {"unit_nowhere", "site_elsewhere"}
    assert r.warning is not None
    for entry in r.missing:
        assert entry["name"] in r.warning


def test_an_uncovered_node_type_is_not_told_it_is_missing_from_the_extraction_enum() -> None:
    """`extractor: true` is an EDGE declaration — a node type has no such field to be absent from.

    Saying "this node type is not in the extraction enum" would be a true-sounding sentence about a
    field that does not exist for it: precisely the kind of confident-but-invented detail this module
    exists to keep off an analyst's screen.
    """
    obs = ObservableDef.model_validate({
        "observable_id": "obs-new-stockpile",
        "trigger": {"on": "new_node", "node_type": "interceptor_stockpile"},
    })
    r = trigger_reachability(obs, view(nodes=_UNIT_NODES), _config(obs))

    assert r.status == NO_COVERAGE
    assert r.gap_kind == "data"
    assert r.warning is not None
    assert "extraction enum" not in r.warning
    assert "interceptor_stockpile" in r.warning
