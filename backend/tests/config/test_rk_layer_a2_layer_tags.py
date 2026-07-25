"""A2 — **layer as a type property**, asserted on the REAL shipped ``config/ontology.yaml``.

Spec (``artifacts/plan/01-replumb-implementation-plan.md`` §4 **A2**):

    "**A2 — layer as a type property (amends the ontology contract + the config schema).** Every
    ``node_type`` **and** every ``attribute_type`` in ``config/ontology.yaml`` gains a ``layer`` tag
    (design | instance). … The ``ontology.py`` layer accessor reads it."

    "**Dual-attribute-split sub-rule (D-13.3):** a genuinely dual-natured attribute (a design's nominal
    range vs a deployment's effective range) is **split into two attribute-types**, one per layer — not
    made contextual."

and ``artifacts/plan/sessions/RK-LAYER.md`` item 1:

    "A ``layer`` (design | instance) on every node-type **and** every attribute entry in
    ``config/ontology.yaml`` … (81 attribute entries, 13 node types). Add the layer accessor in
    ``ontology.py`` beside ``refines``/``identity``."

Asserted against the **shipped file**, not a fixture: the likeliest A2 defect is a *partial* migration —
the accessor built, the schema field added, and a dozen attribute entries left untagged — and a
hand-written fixture would never see it. The counts come from the file itself as well as from the
session's stated totals, so neither a silent drop nor a silent addition passes.

This module also carries the two **ontology additions S2 owns** (§7 RK-LAYER 5): ``operated-by`` (without
which G18 tests half of itself) and D12's ``contract_import_event`` ↔ ``trading_org`` edge.
"""

from __future__ import annotations

import pytest

from chanakya.ontology import EdgeLaneIndex
from tests import _rk_layer as rk

# ── the node-type half ──────────────────────────────────────────────────────────────────────────

def test_the_layer_tagging_covers_the_whole_declared_surface() -> None:
    """The **count-independent** completeness assertion, per the session file as corrected 2026-07-25:

        "**Do NOT pin a frozen type/attribute count** (corrected 2026-07-25): this stage is *supposed* to grow
        the surface — **L2** adds an instance-layer *presence* type and **L4** a numeric equipment-count
        attribute — so a pinned count is a tripwire pointed at ourselves. The durable, count-independent
        assertion is: **every node type and every attribute entry is classified with a legal value, and no
        entry claims two layers** (D-13.3's split rule)."

    An earlier version of this test pinned 13 / 81 and failed against a *correct* implementation that had grown
    the surface to 15 / 90 — exactly what L2 and L4 told it to do. The measured totals are still **reported**,
    because a reader wants the denominator, but nothing asserts them.
    """
    ontology = rk.shipped_ontology()
    entries = rk.declared_attr_entries()
    measured = f"{len(ontology.node_types)} node types / {len(entries)} attribute entries"

    assert ontology.node_types and entries, (
        f"the shipped ontology declares no types or no attribute entries ({measured}) — A2 has nothing to tag"
    )
    legal = rk.legal_layer_values()
    extra = sorted(legal - set(rk.LAYERS))
    assert len(extra) <= 1, (
        f"the layer vocabulary is open-ended: {extra} beyond (design | instance), measured over {measured} — "
        "L3 allows a THIRD value, not one word per meta kind, and 'State the third value in config'"
    )

    def classified(subject, what: str) -> bool:
        try:
            return str(rk.declared_layer(subject, what=what)) in legal
        except AssertionError:
            return False

    types_ok = sum(classified(t, t.name) for t in ontology.node_types)
    attrs_ok = sum(classified(e, f"{owner}.{e.get('name')}") for owner, e in entries)

    assert (types_ok, attrs_ok) == (len(ontology.node_types), len(entries)), (
        f"layer classification is incomplete: {types_ok}/{len(ontology.node_types)} node types and "
        f"{attrs_ok}/{len(entries)} attribute entries carry a legal value from {sorted(legal)} — the durable "
        "assertion is coverage of the whole declared surface, whatever its size"
    )


def test_every_node_type_is_classified() -> None:
    """A2: "Every ``node_type`` … gains a ``layer`` tag", **as amended by ruling L3**.

    L3: ``source`` / ``indicator`` / ``known_gap`` "are **neither** design nor instance — they are
    system/meta kinds … give ``layer`` a third value (or an explicit exemption) for kinds that are neither.
    **State the third value in config; do not leave it implicit.**"

    So the assertion is *classified*, not *design-or-instance*: every type carries a tag, and the tag
    vocabulary stays closed — one third value, not an ad-hoc word per type. The only alternative L3 allows
    is an explicit exemption, which is accepted **only** for the meta kinds it names.
    """
    tagged: dict[str, str] = {}
    untagged: list[str] = []
    for typedef in rk.shipped_ontology().node_types:
        try:
            tagged[typedef.name] = str(rk.declared_layer(typedef, what=f"node type {typedef.name!r}"))
        except AssertionError:
            untagged.append(typedef.name)

    exemptible = set(rk.META_NODE_TYPES) | set(rk.ARGUABLY_META_NODE_TYPES)
    assert not (set(untagged) - exemptible), (
        f"node type(s) carry no layer tag and are not one of L3's meta kinds: "
        f"{sorted(set(untagged) - exemptible)} — A2 tags every node_type; L3's exemption covers only "
        f"{sorted(exemptible)}"
    )
    extra_values = sorted({v for v in tagged.values() if v not in rk.LAYERS})
    assert len(extra_values) <= 1, (
        f"the layer vocabulary is open-ended: {extra_values} beyond (design | instance) — L3 allows a "
        f"THIRD value, not one word per meta type. Tagging: {tagged}"
    )


def test_the_meta_kinds_are_not_forced_into_design_or_instance() -> None:
    """L3: "**Forcing a meta type into ``design`` or ``instance`` would corrupt the straddle-split
    trigger**, which fires precisely on a layer *mismatch* — a mis-tagged meta type would generate phantom
    splits."

    This is the clause that bites: a migration that tagged all 13 types ``design`` to satisfy A2's letter
    would pass the count test above and quietly arm the split trigger against system records.
    """
    forced = {
        name: rk.layer_of_node_type(name)
        for name in rk.META_NODE_TYPES
        if rk.layer_of_node_type(name) in rk.LAYERS
    }

    assert not forced, (
        f"meta node type(s) tagged design/instance: {forced} — L3: these are 'system/meta kinds', and "
        "forcing them into a real layer generates phantom straddle splits"
    )


def test_the_types_whose_layer_the_design_fixes_are_tagged_accordingly() -> None:
    """spine/13 §3: "Type / design layer — variant, component, radar, manufacturer". Ruling L2: "``unit`` is
    the **formation** citizen" — the earned *instance* citizen (D-13.13)."""
    wrong = {
        name: rk.layer_of_node_type(name)
        for name in rk.FIXED_DESIGN_TYPES
        if rk.layer_of_node_type(name) != rk.DESIGN
    } | {
        name: rk.layer_of_node_type(name)
        for name in rk.FIXED_INSTANCE_TYPES
        if rk.layer_of_node_type(name) != rk.INSTANCE
    }

    assert not wrong, (
        f"layer tags contradict the design: {wrong} — spine/13 §3 puts variant/component/manufacturer on "
        "the design layer, and ruling L2 makes `unit` the instance-layer formation citizen"
    )


def test_both_layers_are_actually_used() -> None:
    """A tagging pass that put every type in one layer would satisfy the letter and kill the mechanism.

    spine/13 §3 names both populations explicitly — "Type / design layer — variant, component, radar,
    manufacturer" and "Instance / individual layer — concrete, operator-bound, located, timed individuals".
    """
    by_layer = rk.node_types_by_layer()

    for layer in rk.LAYERS:
        assert by_layer.get(layer), (
            f"no node type is tagged {layer!r} (tagging: {by_layer}) — spine/13 §3 names populations for "
            "both layers; a single-layer ontology makes the split-and-route mechanism unreachable"
        )


# ── the attribute half (the non-obvious piece, per A2) ──────────────────────────────────────────

def test_every_attribute_entry_declares_a_layer() -> None:
    """A2: "… **and** every ``attribute_type`` in ``config/ontology.yaml`` gains a ``layer`` tag".

    **Count-independent** (session file, corrected 2026-07-25): *every* entry must be classified, however many
    there are, with a value from the legal set — which per **L3** is ``design | instance`` plus the one third
    value the config declares for the kinds that are neither. An earlier version of this test hardcoded
    ``{design, instance}`` and would have failed a correct implementation the moment it tagged
    ``source``/``indicator``/``known_gap`` the way L3 requires.
    """
    legal = rk.legal_layer_values()
    untagged: list[str] = []
    bad_value: dict[str, object] = {}
    for owner, entry in rk.declared_attr_entries():
        where = f"{owner}.{entry.get('name')}"
        try:
            layer = rk.declared_layer(entry, what=f"attribute entry {where}")
        except AssertionError:
            untagged.append(where)
            continue
        if str(layer) not in legal:
            bad_value[where] = layer

    total = len(rk.declared_attr_entries())
    assert not untagged, (
        f"{len(untagged)} of {total} attribute entries carry no layer tag: "
        f"{untagged[:12]}{' …' if len(untagged) > 12 else ''} — A2 tags EVERY attribute_type, and the "
        "per-attribute layer is the piece the straddle-split trigger reads (§7 RK-LAYER 2)"
    )
    assert not bad_value, (
        f"attribute entries declare a layer outside the legal set {sorted(legal)}: {bad_value} — A2 fixes the "
        "vocabulary; 'unknown'/'both'/'contextual' is expressly not one of the values"
    )


def test_no_attribute_entry_claims_both_layers() -> None:
    """D-13.3: a genuinely dual attribute is **split into two attribute-types**, never made contextual.

    "Layer is a property of the type (uniform); a genuinely dual attribute is split into two types."
    (D-13.3.) So a list-valued, comma-joined or ``both``/``either``/``contextual`` layer is the exact shape
    the decision forbids — it re-introduces the contextual reading the split exists to remove.
    """
    offenders: dict[str, object] = {}
    forbidden_words = {"both", "either", "any", "contextual", "dual", "unknown", "n/a"}
    for owner, entry in rk.declared_attr_entries():
        raw = {k: v for k, v in entry.items() if rk.LAYER_TOKEN in str(k).lower()}
        for key, value in raw.items():
            where = f"{owner}.{entry.get('name')}[{key}]"
            if isinstance(value, (list, tuple, set)):
                offenders[where] = value
            elif isinstance(value, str):
                text = value.strip().lower()
                if text in forbidden_words or "," in text or "|" in text or "/" in text:
                    offenders[where] = value

    assert not offenders, (
        f"attribute entries claim more than one layer: {offenders} — D-13.3: 'a genuinely dual attribute "
        "is split into two types' rather than made contextual"
    )


def test_the_split_trigger_is_reachable_in_the_shipped_schema() -> None:
    """§7 RK-LAYER 2: "The split trigger is an *instance-layer attribute on a design-layer node*".

    If no design-layer node type declares an instance-layer attribute, that mismatch can never arise from
    the declared schema and the straddle-split is dead code. Fails loudly with the tagging it found.
    """
    node_type, attribute = rk.straddle_pair()

    assert node_type and attribute  # rk.straddle_pair() raises with the explanation when there is none


# ── the accessor (§7 RK-LAYER 1) ────────────────────────────────────────────────────────────────

def test_a_layer_accessor_exists_in_the_ontology_module() -> None:
    """§7 RK-LAYER 1: "add … a layer accessor in ``ontology.py`` (``NodeTypeIndex``, beside
    ``refines``/``identity``)"."""
    from chanakya.ontology import NodeTypeIndex

    found = rk.layer_accessors()

    assert found, (
        "chanakya/ontology.py exposes no public callable carrying 'layer' — §7 RK-LAYER 1 puts the layer "
        "accessor there, beside `refines`/`identity`. Public methods on NodeTypeIndex today: "
        f"{sorted(n for n in dir(NodeTypeIndex) if not n.startswith('_'))}"
    )


def test_the_layer_accessor_reads_what_the_file_declares() -> None:
    """The accessor must be a *reader*, not a second, hardcoded copy of the tagging (gate G6)."""
    from chanakya.ontology import NodeTypeIndex

    ontology = rk.shipped_ontology()
    index = NodeTypeIndex(ontology)
    accessors = {
        name: fn for name, fn in rk.layer_accessors().items() if name.startswith("NodeTypeIndex.")
    }
    assert accessors, (
        f"no layer accessor on NodeTypeIndex (found elsewhere: {sorted(rk.layer_accessors())}) — "
        "§7 RK-LAYER 1 places it there"
    )

    agreed = False
    mismatches: dict[str, tuple[object, object]] = {}
    for name, _fn in accessors.items():
        method = getattr(index, name.split(".", 1)[1])
        try:
            answers = {t.name: method(t.name) for t in ontology.node_types}
        except TypeError:
            continue  # a different arity (e.g. an attribute-level accessor) — tried below
        declared = {t.name: str(rk.declared_layer(t, what=t.name)) for t in ontology.node_types}
        wrong = {k: (answers[k], declared[k]) for k in declared if str(answers[k]) != declared[k]}
        if wrong:
            mismatches[name] = wrong  # type: ignore[assignment]
        else:
            agreed = True

    assert agreed, (
        f"no NodeTypeIndex layer accessor returns the layer config declares (mismatches: {mismatches}) — "
        "the accessor reads the ontology, it does not restate it (A2, gate G6)"
    )


# ── the ontology additions S2 owns (§7 RK-LAYER 5) ──────────────────────────────────────────────

def _edge(name: str):
    return next((e for e in rk.shipped_ontology().edge_types if e.name == name), None)


def test_operated_by_exists_as_a_declared_predicate() -> None:
    """§7 RK-LAYER 5: "``operated-by`` — G18's relationship wall names it and **the predicate does not
    exist**. Add it here, or G18 silently tests half of itself." (Defect register **D7**.)"""
    edge = _edge("operated-by")

    assert edge is not None, (
        "config/ontology.yaml declares no `operated-by` edge — §7 RK-LAYER 5 assigns it to this stage "
        "because G18's relationship-conflict wall names `based-at` AND `operated-by`; without the "
        f"predicate the gate tests half of itself. Declared edges: {[e.name for e in rk.shipped_ontology().edge_types]}"
    )
    assert edge.from_types() and edge.to_types(), (
        "`operated-by` declares no from/to endpoints — spine/13 §3 lists it among the relations that "
        "*link the layers*, so its endpoint layers must be derivable from its declared endpoint types "
        "(A2: 'Edge endpoint-layers derive from the already-declared from/to')"
    )


def test_the_customs_event_to_trading_org_relation_is_expressible() -> None:
    """D12 / §7 RK-LAYER 5: the customs document's actual spine — event ↔ consignee ↔ shipper.

    "the customs document's actual spine — *event ↔ consignee ↔ shipper* — **cannot be represented**,
    because no edge type connects ``contract_import_event`` to ``trading_org``; meanwhile the schema *does*
    offer ``imported-by → unit``, which that document never states. **A schema that makes the sourced
    relation inexpressible while making the unsourced thing easy is an anti-fabrication hazard.**"
    """
    pairs = {
        e.name: (e.from_types(), e.to_types())
        for e in rk.shipped_ontology().edge_types
    }
    connecting = [
        name for name, (froms, tos) in pairs.items()
        if ("contract_import_event" in froms and "trading_org" in tos)
        or ("trading_org" in froms and "contract_import_event" in tos)
    ]

    assert connecting, (
        "no edge type connects `contract_import_event` to `trading_org`, so the customs document's own "
        "spine (event ↔ consignee ↔ shipper) stays inexpressible while `imported-by → unit` — which no "
        "such document states — stays easy. That asymmetry pressures extraction toward asserting the "
        f"unsourced relation (D12, §7 RK-LAYER 5). Declared edges: {sorted(pairs)}"
    )


def test_the_new_predicates_do_not_collide_on_endpoint_types() -> None:
    """The re-lane is only unambiguous while each *extractor* edge has a unique ``(from → to)``.

    ``operated-by`` is the trap: declared ``variant → unit`` and marked ``extractor``, it collides head-on
    with ``inducted-into``, and the write-time re-lane would start mis-laning inductions. The ontology
    already surfaces this (``EdgeLaneIndex.collisions``) — this asserts S2's additions keep it empty.
    """
    index = EdgeLaneIndex(rk.shipped_ontology())

    assert index.collisions == {}, (
        f"S2's ontology additions introduced an endpoint collision: {index.collisions} — every "
        "extractor edge must stay uniquely determined by its (from → to) pair, or the write-time re-lane "
        "silently mis-lanes facts (chanakya/ontology.py, D-A)"
    )


def test_new_decaying_edges_keep_a_reachable_half_life() -> None:
    """A perishable edge with no reachable half-life scores as **eternal** (the SC-2 trap)."""
    bundle = rk.shipped_bundle()
    offenders = EdgeLaneIndex(bundle.ontology).unreachable_half_lives(bundle.credibility)

    assert offenders == {}, (
        f"decaying edge(s) with no reachable half-life: {offenders} — a perishable tripwire that can "
        "never go stale (chanakya/ontology.py::unreachable_half_lives, SC-2)"
    )


def test_based_at_supersede_key_is_tagged_by_site_type() -> None:
    """§7 RK-LAYER 5 / **R1.3** / **C1**: "``based-at``'s supersede ``instance_key`` tagged by
    ``site_type``" — so "a unit legitimately at a garrison *and* a forward site is **two concurrent valid
    basings, not a relocation**".

    Asserted on the *declaration* (machine-readable fields only, never a comment): the ontology currently
    rests unit-only keying on "correct while the corpus has no such simultaneous pair", which
    working-principles #1 forbids as a design input. Ruling **L1** adds that the key is the **normalized
    class**, never the stated string — the behavioural half is
    ``tests/view/test_rk_layer_supersede_identity.py``.
    """
    raw = rk.shipped_ontology_yaml()
    declared = next(
        (e for e in raw.get("edge_types") or [] if isinstance(e, dict) and e.get("name") == "based-at"),
        None,
    )
    assert declared is not None, "config/ontology.yaml declares no `based-at` edge"

    machine_readable = {k: v for k, v in declared.items() if k != "name"}
    mentions_site_type = "site_type" in repr(machine_readable)

    assert mentions_site_type, (
        "`based-at`'s declaration carries no machine-readable `site_type` in its supersede/instance key "
        f"(declared: {machine_readable}) — R1.3/C1 require the key to be site_type-tagged, and today the "
        "unit-only key makes two concurrent valid basings read as a relocation (defect register D1 step 3)"
    )


@pytest.mark.parametrize("attribute", ["site_type"])
def test_site_type_is_declared_on_the_type_that_carries_it(attribute: str) -> None:
    """C7's prerequisite: ``site_type`` becomes "a config-declared closed vocabulary under the same
    normalization prerequisite" — so the slot the key reads must at least still be a declared attribute."""
    owners = [
        t.name for t in rk.shipped_ontology().node_types
        if attribute in [a.name for a in t.attrs]
    ]

    assert owners, (
        f"no node type declares a {attribute!r} attribute, yet R1.3/C1 key the based-at supersede "
        "instance on it — the key would read a slot the ontology does not declare"
    )


def test_a_closed_site_type_vocabulary_is_declared_in_config() -> None:
    """Ruling **L1**: "``site_type`` is **unenumerated free text**: no ``enum``, no allowed-values list
    anywhere in ``config/``. The 15 distinct values in the frozen claims conflate **four different
    concepts** … **S2 declares a closed ``site_type`` vocabulary** in config (the *kind of place* axis only
    — the other three concepts are different fields and must not be smuggled into it)."

    Without the vocabulary there is nothing to normalize *to*, so L1's rule 2 ("the raw stated string is
    NEVER the key") has no key to build and C1's de-confliction cannot be implemented safely at all.
    """
    vocab = rk.site_type_vocabulary()

    assert vocab, (
        "config declares no closed `site_type` vocabulary (searched every list-of-strings under a key "
        "naming site_type, across all nine surfaces) — ruling L1 rule 1. Without it the supersede key can "
        "only be the raw free-text string, which L1 shows fails in BOTH directions: differing strings for "
        "one kind of site suppress the wall, and the flagship relocation's two ends "
        "('observed-imagery-site' / 'stated_destination') stop co-locating so the relocation silently "
        "stops firing"
    )
    for where, values in vocab.items():
        assert len(values) >= 2, (
            f"the site_type vocabulary at {where} declares {values} — a single-valued 'closed vocabulary' "
            "cannot distinguish a garrison from a forward site, which is the whole point of C1"
        )


def test_a_numeric_equipment_count_attribute_is_declared() -> None:
    """Ruling **L4**: "**No numeric equipment-count attribute** anywhere, though sourced figures exist on
    sighting events. This is A3's ``count``-as-a-sourced-attribute requirement having no home. **S2 owns
    the ontology, so S2 declares it** — and its default is ``unknown``, never 'how many reports merged'."

    ``count_state`` already exists and is a state enum, so it is excluded by construction: a state cannot
    carry "six TELs".
    """
    found = rk.equipment_count_attrs()

    assert found, (
        "no node type declares a numeric equipment-count attribute (`count_state` excluded — it is a state "
        "enum, not a figure) — ruling L4 assigns the declaration to S2, because A3 requires `count` as a "
        f"SOURCED attribute of the presence. Declared attrs by type: "
        f"{ {t.name: [a.name for a in t.attrs] for t in rk.shipped_ontology().node_types} }"
    )
    instance_owners = [t for t in found if rk.layer_of_node_type(t) == rk.INSTANCE]
    assert instance_owners, (
        f"the count attribute(s) {found} sit on no instance-layer type — spine/13 §3a puts count on the "
        "PRESENCE ('an attribute of the presence with its own sourced evidence'), not on the shared design"
    )


def test_trading_org_is_reachable_by_some_edge() -> None:
    """Ruling **L4**: "``trading_org`` is named by NO edge type at all, so a correctly-typed consignee can
    only be an orphan. This is **D12's shape and worse than D12 as filed**."""
    naming = [
        e.name for e in rk.shipped_ontology().edge_types
        if "trading_org" in e.from_types() + e.to_types()
    ]

    assert naming, (
        "no edge type names `trading_org` in its from/to, so a customs consignee resolves to a node "
        "nothing can connect to — an orphan by construction (ruling L4). The ontology offers "
        "`imported-by → unit` instead, which no customs document states: the schema makes the unsourced "
        "relation easy and the sourced one inexpressible (D12)"
    )


# ── the presence citizen needs a type to be (ruling L2) ─────────────────────────────────────────

def test_an_instance_layer_presence_node_type_exists() -> None:
    """Ruling **L2**: "the **presence** citizen has no node type. S2 must create one … **add a new
    instance-layer node type for the presence citizen**."

    Both alternatives are explicitly rejected there, and both are asserted against: reusing ``unit`` with a
    discriminator attribute ("it fuses the two citizens into one type, which is exactly what D-13.13
    separates and what **G15 exists to guard**") and ``refines: unit`` ("A presence is **not a kind of
    unit** … Refinement models *narrower*, not *weaker*").
    """
    instance_types = rk.instance_node_types()
    presence_types = rk.presence_node_types()

    assert instance_types, (
        "no node type is tagged instance-layer at all — A3's two citizens have nothing to be "
        f"(layer tagging: {rk.node_types_by_layer()})"
    )
    assert presence_types, (
        "the only instance-layer node type(s) are the formation citizen `unit` (or a refinement of it): "
        f"{instance_types} — ruling L2 requires a NEW instance-layer type for the presence, because "
        "'a presence is deliberately a *weaker* assertion than a formation' and refining `unit` would "
        "inherit the organizational semantics a presence must not carry"
    )


def test_the_presence_type_is_not_a_refinement_of_the_formation() -> None:
    """L2's second rejected alternative, asserted directly on the declaration."""
    offenders = {
        t.name: getattr(t, "refines", None)
        for t in rk.shipped_ontology().node_types
        if getattr(t, "refines", None) in rk.FIXED_INSTANCE_TYPES
    }

    assert not offenders, (
        f"node type(s) declared as refinements of the formation citizen: {offenders} — L2 rejects "
        "`refines: unit` for the presence: 'A presence is not a kind of unit; it asserts less'"
    )
