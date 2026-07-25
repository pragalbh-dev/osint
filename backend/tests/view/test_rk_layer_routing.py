"""A4/A3 — **split → materialize → bind**: layer routing, endpoint materialization, the two citizens.

Spec, quoted where it binds:

* **A4** (§4): "An instance-layer edge materializes the instance it implies; a cross-layer holding edge
  does not."
* **§7 RK-LAYER 2**: "design atoms → shared design node; instance atoms → instance node; an instance-layer
  edge whose mention named only the design materializes a provisional **presence**. The split trigger is an
  *instance-layer attribute on a design-layer node* — that mismatch is the signal the extractor lumped two
  things together."
* **spine/13 §5.3**, the worked example this module turns into fixtures: "a source states **'HQ-9/P at
  Rahwali,'** which the extractor emits as an **`observed-at`** sighting … It needs an *instance* endpoint
  but the mention named only the *design*, so the build does **not** point it at the shared design node —
  it materializes a provisional **presence** P … A bare sighting never forces a formation."
  And the negative: "**'Pakistan equips HQ-9/P'** is a `operator → design` *holding* edge — neither
  endpoint instance-typed — so it mints **no** presence and **no** unit."
* **A3 / D-13.13**: "``count`` is a *sourced attribute*, default unknown, never ``= reports merged``"
  (k reports ≠ k launchers); "a formation … minted **only** when organizational evidence exists".
* **D-13.13 / spine/13 §5**: "*stated* (a source directly names the unit at a site → an extractor
  ``based-at`` … normal source credibility … the stronger path) or *derived* … capped"; "Crucially
  **stated ≠ trusted**: a stated basing runs through source grade … a grade-E spoof … lands at *possible*".

Fixtures are abstract and corpus-independent (like G1/G2) but load the **shipped ontology**, because the
layer tags are the thing under test — a fixture that declared its own tags would test the fixture.
"""

from __future__ import annotations

from tests import _rk_layer as rk

DESIGN_ID, SITE_ID, UNIT_ID = "hq9p", "site_rahwali", "unit_8ad"
SIGHTING = "observed-at"
INDUCTION = "inducted-into"
BASING = "based-at"


def _cfg(**kw):
    return rk.fixture_config(**kw)


def _sighting_only(sightings: int = 1) -> list:
    """spine/13 §5.3's worked example: a design named at a site, and nothing organizational."""
    claims = [
        rk.entity_claim(DESIGN_ID, "variant", name="HQ-9/P"),
        rk.entity_claim(SITE_ID, "basing_site", name="Rahwali", attrs=rk.coords(32.28, 74.13, "rahwali")),
    ]
    for i in range(sightings):
        claims.append(
            rk.rel_claim(f"c-obs{i}", DESIGN_ID, SIGHTING, SITE_ID,
                         iso=f"2025-0{i + 1}-01", sid="s" if i % 2 == 0 else "s2")
        )
    return claims


def _instance_endpoints(view, edge_type: str) -> list[str]:
    return [e.source for e in rk.edges_of(view, edge_type)]


def _is_instance_layer_type(node_type: str) -> bool:
    return rk.layer_of_node_type(node_type) == rk.INSTANCE


def _reads_as_instance(node) -> bool:
    """Either the node's *type* is declared instance-layer (A2's uniform-by-type rule) or the node says so."""
    return _is_instance_layer_type(node.type) or str(rk.view_layer(node) or "") == rk.INSTANCE


# ── presence materialization (A4 positive + A3) ──────────────────────────────────────────────────

def test_a_sighting_materializes_a_provisional_presence_not_the_shared_design_node() -> None:
    """spine/13 §5.3: "the build does **not** point it at the shared design node — it materializes a
    provisional **presence** P"."""
    view = rk.build_view(_cfg(), _sighting_only())
    subjects = _instance_endpoints(view, SIGHTING)

    assert subjects, f"no {SIGHTING} edge survived the rebuild — the fixture is broken, not the code"
    assert DESIGN_ID not in subjects, (
        f"the {SIGHTING} sighting still binds to the shared design node {DESIGN_ID!r} "
        f"(subjects: {subjects}) — A4: 'An instance-layer edge materializes the instance it implies'; "
        f"spine/13 §5.3: the build 'does NOT point it at the shared design node'."
    )
    presence = next(n for n in view.nodes if n.id == subjects[0])
    assert _reads_as_instance(presence), (
        f"the materialized endpoint {presence.id!r} (type {presence.type!r}) does not read as an "
        f"instance-layer citizen — A3 makes the presence one of the two instance kinds. "
        f"layer recorded on the node: {rk.view_layer(presence)!r}"
    )


def test_the_materialized_presence_is_not_the_formation_citizen() -> None:
    """Ruling **L2**: the presence gets its **own** instance-layer type — "``unit`` is the **formation**
    citizen, and a presence is deliberately a *weaker* assertion than a formation … [reusing ``unit``]
    fuses the two citizens into one type, which is exactly what D-13.13 separates and what **G15 exists to
    guard**."""
    view = rk.build_view(_cfg(), _sighting_only())
    subjects = [s for s in _instance_endpoints(view, SIGHTING) if s != DESIGN_ID]
    assert subjects, (
        "no presence was materialized for the sighting — A4 materializes the instance an instance-layer "
        "edge implies."
    )

    presence = next(n for n in view.nodes if n.id == subjects[0])
    assert presence.type not in rk.FIXED_INSTANCE_TYPES, (
        f"the presence materialized as {presence.type!r}, the FORMATION citizen — a sighting asserts "
        "equipment at a place, not a named formation stationed there (D-13.13, ruling L2)"
    )
    assert presence.type in rk.presence_node_types(), (
        f"the presence materialized as {presence.type!r}, which is not a declared instance-layer presence "
        f"type (candidates from config: {rk.presence_node_types()}) — ruling L2 has S2 declare the type, so "
        "an ad-hoc/undeclared node type means the ontology and the build disagree about what exists"
    )


def test_the_presence_stays_linked_to_the_shared_design_node() -> None:
    """spine/13 §5.3: "P ``instance-of``/``fields`` HQ-9/P(design) … The design name becomes the link to
    the shared design node"."""
    view = rk.build_view(_cfg(), _sighting_only())
    presence_ids = {s for s in _instance_endpoints(view, SIGHTING) if s != DESIGN_ID}

    assert presence_ids, "no presence was materialized, so there is no link to assert"
    linked = [
        e for e in view.edges
        if {e.source, e.target} & presence_ids and DESIGN_ID in {e.source, e.target}
    ]
    assert linked, (
        f"the materialized presence {sorted(presence_ids)} is not linked to the design node "
        f"{DESIGN_ID!r} — spine/13 §5.3 binds them ('P instance-of/fields HQ-9/P(design)'), which is what "
        "keeps one design node shared across operators instead of forking per sighting. Edges present: "
        f"{[(e.type, e.source, e.target) for e in view.edges]}"
    )


def test_the_shared_design_node_survives_the_split() -> None:
    """"Design-level facts attach to the (shared) design node" (spine/13 §5.2) — the design is not consumed."""
    view = rk.build_view(_cfg(), _sighting_only())

    assert any(n.id == DESIGN_ID for n in view.nodes), (
        f"the design node {DESIGN_ID!r} disappeared when the presence was materialized — the design layer "
        "is 'abstract, geography-agnostic, legitimately shared' (spine/13 §3), never replaced by an instance"
    )


def test_a_bare_sighting_never_forces_a_formation() -> None:
    """D-13.13: a formation is "minted **only** when organizational evidence exists"; "We do **not** force a
    formation node: reifying an organizational individual we cannot source would violate the
    non-negotiable" (spine/13 §3a)."""
    view = rk.build_view(_cfg(), _sighting_only())

    assert not rk.edges_of(view, BASING), (
        f"a bare {SIGHTING} sighting produced a {BASING} formation basing "
        f"({[(e.source, e.target) for e in rk.edges_of(view, BASING)]}) with no organizational evidence in "
        "the log — D-13.13 mints a formation ONLY on organizational evidence"
    )
    assert not rk.nodes_of(view, "unit"), (
        f"a bare sighting materialized a unit node ({[n.id for n in rk.nodes_of(view, 'unit')]}) — "
        "'reifying an organizational individual we cannot source would violate the non-negotiable'"
    )


# ── the negative: a design-only edge mints nothing (A4) ──────────────────────────────────────────

#: Edges the spec says DO materialize an instance, so they can never stand in for A4's negative. Per ruling
#: **L2** the sighting lane keeps its *stated* design endpoints ("``observed-at`` keeps describing what the
#: source states (equipment → site), and the presence is materialized in the **derived** layer"), so an
#: endpoint-layer test alone would wrongly pick it up as a holding edge.
_MATERIALIZING_LANES = ("observed-at", "based-at")

#: Pure design-layer authorship/BOM lanes, preferred in this order — the same fact about a design whoever
#: fields it, which is exactly A4's "neither endpoint instance-typed" case.
_HOLDING_PREFERENCE = ("manufactures", "supplies-component", "equips", "design-authority-for",
                       "component-of")


def _design_only_edge() -> tuple[str, str, str]:
    """An edge type that materializes nothing — A4's "cross-layer holding edge", in testable form.

    spine/13 §5.3's own example ("Pakistan equips HQ-9/P", ``operator → design``) is not expressible in the
    shipped ontology — there is no ``operator`` node type — so the testable form of the same rule is an edge
    with **no instance-layer endpoint and no materializing role**: it must mint nothing.
    """
    by_name = {e.name: e for e in rk.shipped_ontology().edge_types}
    ordered = [by_name[n] for n in _HOLDING_PREFERENCE if n in by_name] + [
        e for name, e in by_name.items() if name not in _HOLDING_PREFERENCE
    ]
    for edge in ordered:
        froms, tos = edge.from_types(), edge.to_types()
        if not (froms and tos) or edge.name in _MATERIALIZING_LANES:
            continue
        if all(not _is_instance_layer_type(t) for t in froms + tos):
            return edge.name, froms[0], tos[0]
    raise AssertionError(
        "no declared edge has exclusively design-layer endpoints, so A4's negative — 'a cross-layer holding "
        "edge does not [materialize]' — cannot be exercised. Layer tagging: "
        f"{rk.node_types_by_layer()}"
    )


def test_an_edge_with_no_instance_endpoint_mints_nothing() -> None:
    """A4: "An instance-layer edge materializes the instance it implies; a cross-layer holding edge does
    not." The negative is as load-bearing as the positive — it is what keeps "country-level holdings, site
    presences, and named formations … cleanly separate" (spine/13 §5.3)."""
    predicate, from_type, to_type = _design_only_edge()
    claims = [
        rk.entity_claim("d_from", from_type, name="Alpha Design"),
        rk.entity_claim("d_to", to_type, name="Bravo Design"),
        rk.rel_claim("c-hold", "d_from", predicate, "d_to"),
    ]
    view = rk.build_view(_cfg(), claims)
    ids = sorted(n.id for n in view.nodes)

    assert ids == ["d_from", "d_to"], (
        f"the design-only {predicate!r} edge minted extra node(s): {ids} — A4: a holding edge whose "
        "endpoints are not instance-typed 'mints no presence and no unit'"
    )
    edge = rk.edges_of(view, predicate)
    assert [(e.source, e.target) for e in edge] == [("d_from", "d_to")], (
        f"the design-only {predicate!r} edge was re-pointed at a materialized endpoint "
        f"({[(e.source, e.target) for e in edge]}) — it must stay a holding edge to the shared design nodes"
    )


# ── the straddle split (A4 / D-13.5) ────────────────────────────────────────────────────────────

def test_a_straddling_mention_splits_into_two_linked_nodes() -> None:
    """D-13.5: "a straddling mention is split into linked design + instance nodes; driven by per-fact layer
    tags, so the extractor may stay blind to kind and the split self-corrects on a misplaced attribute."

    The trigger is read from the shipped tagging, never guessed: a design-layer node type that declares an
    instance-layer attribute (§7 RK-LAYER 2).
    """
    design_type, instance_attr = rk.straddle_pair()
    design_attr = next(
        (a.name for a in next(t for t in rk.shipped_ontology().node_types if t.name == design_type).attrs
         if str(rk.declared_layer(a, what=a.name)) == rk.DESIGN),
        None,
    )
    assert design_attr, (
        f"{design_type!r} declares no design-layer attribute, so a *straddling* mention (one fact of each "
        "layer) cannot be built for it — D-13.5's split has nothing to separate"
    )

    claims = [
        rk.entity_claim(
            "straddler", design_type, name="Alpha Design",
            attrs={design_attr: "design-value", instance_attr: "instance-value"},
        ),
    ]
    view = rk.build_view(_cfg(), claims)

    assert len(view.nodes) >= 2, (
        f"the straddling mention ({design_type} carrying design-layer {design_attr!r} AND instance-layer "
        f"{instance_attr!r}) produced {len(view.nodes)} node(s): "
        f"{[(n.id, n.type, dict(n.attrs)) for n in view.nodes]} — D-13.5 splits it into linked design + "
        f"instance nodes."
    )
    design_nodes = [n for n in view.nodes if not _reads_as_instance(n)]
    instance_nodes = [n for n in view.nodes if _reads_as_instance(n)]
    assert design_nodes and instance_nodes, (
        f"the split did not produce one node per layer: design={[n.id for n in design_nodes]}, "
        f"instance={[n.id for n in instance_nodes]}"
    )
    assert any(
        {e.source, e.target} == {d.id, i.id}
        for e in view.edges for d in design_nodes for i in instance_nodes
    ), (
        f"the two halves of the split are not linked ({[(e.type, e.source, e.target) for e in view.edges]}) "
        "— D-13.5 splits into *linked* design + instance nodes, or the instance loses its design"
    )


def test_the_design_half_of_a_split_keeps_only_the_design_fact() -> None:
    """spine/13 §5.2: "Design-level facts attach to the (shared) design node; instance-level facts attach to
    an instance node." The whole point of per-attribute layers is that this separation is *per fact*."""
    design_type, instance_attr = rk.straddle_pair()
    design_attr = next(
        a.name for a in next(t for t in rk.shipped_ontology().node_types if t.name == design_type).attrs
        if str(rk.declared_layer(a, what=a.name)) == rk.DESIGN
    )
    view = rk.build_view(_cfg(), [
        rk.entity_claim("straddler", design_type, name="Alpha Design",
                        attrs={design_attr: "design-value", instance_attr: "instance-value"}),
    ])
    design_nodes = [n for n in view.nodes if not _reads_as_instance(n)]
    assert design_nodes, "no design-layer node survived the split"

    for node in design_nodes:
        assert instance_attr not in node.attrs, (
            f"the instance-layer fact {instance_attr!r} is still attached to design node {node.id!r} "
            f"({dict(node.attrs)}) — an operator-scoped fact on the shared design node is exactly the "
            "conflation the split exists to undo (spine/13 §5.1)"
        )
    assert any(design_attr in n.attrs for n in design_nodes), (
        f"the design-layer fact {design_attr!r} did not land on the shared design node "
        f"({[(n.id, dict(n.attrs)) for n in design_nodes]})"
    )


# ── count as a sourced attribute (A3 / D-13.13) ──────────────────────────────────────────────────

def _count_attr_names() -> list[str]:
    """The numeric count attribute(s) ruling **L4** has S2 declare, read off the shipped ontology."""
    names = sorted({n for names in rk.equipment_count_attrs().values() for n in names})
    assert names, (
        "the shipped ontology declares no numeric equipment-count attribute, so A3's sourced `count` has "
        "no home (ruling L4 — 'S2 owns the ontology, so S2 declares it'). "
        "tests/config/test_rk_layer_a2_layer_tags.py::test_a_numeric_equipment_count_attribute_is_declared "
        "is the primary assertion; this test needs the name to build a fixture."
    )
    return names


def _count_values(element) -> dict[str, object]:
    bag = dict(getattr(element, "attrs", {}) or {})
    return {k: v for k, v in bag.items() if rk.is_count_attr(k)}


def test_three_reports_of_one_sighting_do_not_become_three_launchers() -> None:
    """A3: "``count`` is a *sourced attribute*, default unknown, **never** ``= how many reports merged``
    (k reports ≠ k launchers)". Ruling **L4** gives the rule a real declared field to bind to."""
    view = rk.build_view(_cfg(), _sighting_only(sightings=3))
    presence_ids = {s for s in _instance_endpoints(view, SIGHTING) if s != DESIGN_ID}
    assert presence_ids, (
        "no presence was materialized, so the count rule cannot be exercised — A4 materializes the instance "
        "an instance-layer edge implies."
    )

    for node in (n for n in view.nodes if n.id in presence_ids):
        supporting = len(node.claim_ids)
        for key, value in _count_values(node).items():
            assert value not in (3, supporting), (
                f"presence {node.id!r} carries {key}={value!r} with {supporting} supporting claim(s) from "
                "3 reports — A3/D-13.13: count is a sourced attribute, NEVER '= how many reports merged'"
            )


def test_a_stated_count_is_carried_as_a_sourced_attribute_of_the_presence() -> None:
    """The other half: an "imagery TEL count, a stated OOB figure" *is* data and must survive.

    spine/13 §3a: "Its ``count`` (how many launchers/TELs/rounds) is an **attribute of the presence with its
    own sourced evidence** (an imagery TEL count, a stated OOB figure)". The figure is stated *about the
    sighting*, so it is carried on the sighting claim's own attribute bag — the honest carrier, since no
    source names the presence node the build is about to materialize.
    """
    attribute = _count_attr_names()[0]
    claims = _sighting_only()
    claims[-1] = rk.rel_claim("c-obs0", DESIGN_ID, SIGHTING, SITE_ID, iso="2025-01-01",
                             attributes={attribute: 6})
    view = rk.build_view(_cfg(), claims)

    presence_ids = {s for s in _instance_endpoints(view, SIGHTING) if s != DESIGN_ID}
    assert presence_ids, (
        "no presence was materialized, so a count cannot be an attribute *of the presence*. "
        ""
    )
    reachable = {
        n.id: _count_values(n) for n in view.nodes if n.id in presence_ids and _count_values(n)
    } | {
        e.id: _count_values(e) for e in rk.edges_of(view, SIGHTING) if _count_values(e)
    }
    assert any(6 in vals.values() for vals in reachable.values()), (
        f"a source stating {attribute}=6 left no sourced count reachable from the presence "
        f"(found: {reachable}) — spine/13 §3a puts count on the presence, and it 'directly serves the OOB "
        "mission'"
    )
    for node_id in presence_ids:
        node = next(n for n in view.nodes if n.id == node_id)
        assert not any(v == len(node.claim_ids) != 6 for v in _count_values(node).values()), (
            f"presence {node_id!r}'s count equals its supporting-claim count — the stated figure must win, "
            "and a merged-report count must never be synthesised (A3)"
        )


# ── stated vs derived formation evidence (D-13.13) ───────────────────────────────────────────────

def _stated_basing(sid: str = "s", cid: str = "c-stated") -> list:
    return [
        rk.entity_claim(UNIT_ID, "unit", name="8th AD Battalion"),
        rk.entity_claim(SITE_ID, "basing_site", name="Rahwali", attrs=rk.coords(32.28, 74.13, "rahwali")),
        rk.rel_claim(cid, UNIT_ID, BASING, SITE_ID, iso="2025-03-01", sid=sid),
    ]


def test_a_stated_based_at_binds_the_formation_directly() -> None:
    """D-13.13: "*stated* (a source directly names the unit at a site → an extractor ``based-at``,
    ``kind=observation``, normal source credibility … the stronger path)"."""
    view = rk.build_view(_cfg(), _stated_basing())
    edges = rk.edges_of(view, BASING)

    assert [(e.source, e.target) for e in edges] == [(UNIT_ID, SITE_ID)], (
        f"a stated `{BASING}` did not bind the named formation to the site directly "
        f"({[(e.source, e.target) for e in edges]}) — the stated path is extractor-emitted and needs no "
        "derivation (D-13.13; spine/13 §5.3 'the stated one is stronger')"
    )
    edge = edges[0]
    assert not edge.attrs.get("derived_via"), (
        f"the stated basing is marked derived ({edge.attrs}) — a stated assertion must not be relabelled "
        "as an inference; the two paths carry different confidence by construction"
    )


def test_a_low_grade_stated_basing_still_runs_through_source_grade() -> None:
    """spine/13 §5.3: "Crucially **stated ≠ trusted**: a stated basing runs through source grade and the
    deception gates like any claim — a grade-E spoof naming a unit at a site lands at *possible*, never
    waved through for being 'stated'"."""
    strong = rk.build_view(_cfg(), _stated_basing(sid="s"))
    weak = rk.build_view(_cfg(), _stated_basing(sid="adv"))

    strong_edge, weak_edge = rk.edges_of(strong, BASING)[0], rk.edges_of(weak, BASING)[0]
    strong_conf = strong_edge.confidence.assertion_confidence if strong_edge.confidence else None
    weak_conf = weak_edge.confidence.assertion_confidence if weak_edge.confidence else None

    assert weak_edge.status != "confirmed", (
        f"a stated basing from a weak source reached {weak_edge.status!r} — stated ≠ trusted (D-13.13)"
    )
    assert weak_conf is not None and strong_conf is not None and weak_conf < strong_conf, (
        f"a stated basing scores the same whatever the source ({weak_conf} vs {strong_conf}) — the stated "
        "path carries NORMAL source credibility, not a bypass of it"
    )


def test_an_unstated_count_defaults_to_unknown_rather_than_a_number() -> None:
    """D-13.8/D-13.13 + ruling **L4**: "absent → ``unknown`` … never fabricated"; "its default is
    ``unknown``, never 'how many reports merged'". A default of 1 would be a fabricated OOB figure dressed
    up as a floor."""
    view = rk.build_view(_cfg(), _sighting_only())

    for node in view.nodes:
        for key, value in _count_values(node).items():
            assert not isinstance(value, (int, float)) or isinstance(value, bool), (
                f"{node.id} carries a numeric {key}={value!r} that no source stated — A3: 'default "
                "unknown', never invented"
            )
