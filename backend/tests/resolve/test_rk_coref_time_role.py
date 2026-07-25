"""RK-COREF (S3) — C6's four-value ``time_role``, and the ``places.augment`` ordering (lever 2).

Authored from the session spec alone. C6 as re-specified (REVIEW-VERDICT "C6 re-specified"):

    "replace the boolean with a declared ``time_role``, four values, each earning its own behaviour:
    ``durable`` … ``perishable`` — *perishable-only evidence cannot confirm* … ``constitutive`` — the
    attribute **is part of what this instance is** … ``identifying`` — the attribute identifies the entity
    (a place's coordinates); **satisfies the non-perishable requirement for a confirm**."

    "``constitutive`` is what lets a **presence** confirm at all … and ``identifying`` is what lets a
    **place** confirm — which together are the missing rung C6 was created to supply, and without which
    spine/13 §6 lever 2 cannot exist."

    "**No backward compatibility** (standing directive — no migration shim outlives its stage): S3 migrates
    the existing declarations and a bare ``perishable:`` key becomes a **loud validation error**, exactly as
    S1 did for ``attrs``."

Plus the cheap ordering fix (§5b): "``places.augment`` runs **after** ``resolve_entities`` … so place merges
are invisible to ``relational_score``. spine/13 §6 lever 2 names places as a clean anchor the instance layer
crystallizes onto — **mechanically they are not one.** … Fix the ordering in S3."
"""

from __future__ import annotations

from chanakya.resolve.rconfig import ResolveConfig
from tests import _rk_coref as rc
from tests import _rk_layer as rk

# ── the declaration ─────────────────────────────────────────────────────────────────────────────

def test_every_attribute_role_declares_a_legal_time_role() -> None:
    """One declaration per (type, attribute), from C6's four values — and never the boolean it replaces."""
    entries = rc.attribute_role_entries()
    assert entries, "config/resolution.yaml declares no attribute_roles at all"

    illegal = {
        f"{etype}.{attr}": rc.time_role_of(entry)
        for etype, attr, entry in entries
        if rc.time_role_of(entry) not in rc.TIME_ROLES
    }
    assert not illegal, (
        f"these attribute_roles entries declare no legal time_role: {illegal}. C6's four values are "
        f"{rc.TIME_ROLES}; a boolean cannot carry three states, which is why the closure was re-specified."
    )


def test_the_legacy_perishable_key_is_gone_from_the_shipped_config() -> None:
    """"a bare ``perishable:`` key becomes a **loud validation error**" — so none may remain declared."""
    legacy = [
        f"{etype}.{attr}" for etype, attr, entry in rc.attribute_role_entries()
        if rc.LEGACY_PERISHABLE_KEY in entry
    ]
    assert not legacy, (
        f"these entries still carry a bare `{rc.LEGACY_PERISHABLE_KEY}:` key: {legacy}. The standing "
        "directive is that no migration shim outlives the stage that introduces it — 'a dual-form loader "
        "biases every later implementer toward the old shape'."
    )


def test_a_bare_perishable_declaration_fails_loudly() -> None:
    """The loudness itself, not merely the migration: silence here is how the old shape survives.

    Mirrors S1's precedent exactly — "a bare string in ``attrs`` is now a **loud validation error**".
    """
    legacy = {"unit": {"alert_posture": {"role": "supporting", rc.LEGACY_PERISHABLE_KEY: True}}}

    def build_and_consume() -> object:
        cfg = rc.with_resolution(rc.bundle(), attribute_roles=legacy)
        compiled = ResolveConfig.from_bundle(cfg)
        compiled.attribute_roles("unit")
        compiled.supporting_role_attrs("unit")
        return rc.part_of(
            [rc.ent("a", "unit", "Alpha", attrs={"alert_posture": "active"}, doc="d1"),
             rc.ent("b", "unit", "Bravo", attrs={"alert_posture": "active"}, doc="d2", sid="mid")],
            cfg,
        )

    assert rc.raises_loudly(build_and_consume), (
        "a config declaring the old boolean `perishable:` was accepted in silence. It then behaves as an "
        "*undeclared* time role — i.e. as `durable` — so a perishable attribute silently becomes durable "
        "identity support and the D-13.9(a) cap evaporates. That is worse than a crash."
    )


def test_the_two_new_roles_are_actually_used() -> None:
    """C6 exists to supply a **missing rung**, not to rename a boolean.

    "``constitutive`` is what lets a presence confirm … ``identifying`` what lets a place confirm — the
    missing rung without which lever 2 cannot exist." A migration that only renames the key leaves the
    system exactly as unable to confirm as before.
    """
    used = {rc.time_role_of(entry) for _, _, entry in rc.attribute_role_entries()}
    missing = [r for r in ("constitutive", "identifying") if r not in used]
    assert not missing, (
        f"no shipped declaration uses {missing} (roles in use: {sorted(r for r in used if r)}). Renaming "
        "`perishable: true|false` to `time_role: perishable|durable` carries two of the four states and "
        "leaves the anchor/design layer unable to confirm anything — rk-20 and rk-17 both."
    )


def test_the_two_new_roles_are_declared_on_the_types_that_need_them() -> None:
    """Ruling **M3**: "C6's two new ``time_role`` values have **no declaration site for the types that need
    them** — ``constitutive`` is what lets a **presence** confirm and ``identifying`` what lets a **place**
    confirm, yet ``attribute_roles`` declares neither type. Without those declarations C6 is inert and
    **lever 2 still cannot exist**."

    So the declaration is asserted where it has to live, not merely somewhere: a value declared on the wrong
    type is the same inert config with a longer name. Both type names are read from config (the presence
    citizen's type is S2's, and the place-bearing types are ``place_entity_types``).
    """
    roles = rc.resolution_keys().get("attribute_roles") or {}
    presence_types = [t for t in rk.presence_node_types()] or ["presence"]
    place_types = list(rc.resolution_keys().get("place_entity_types") or ["basing_site"])

    def declared(types: list[str], role: str) -> list[str]:
        return [
            f"{t}.{attr}" for t in types
            for attr, entry in (roles.get(t) or {}).items()
            if rc.time_role_of(dict(entry) if isinstance(entry, dict) else {}) == role
        ]

    assert declared(presence_types, "constitutive"), (
        f"no attribute of the presence citizen {presence_types} is declared `constitutive` "
        f"(attribute_roles covers {sorted(roles)}). A presence *is* operator+design+site+window, so without "
        "this the presence layer can never confirm and every report of one battery becomes another presence."
    )
    assert declared(place_types, "identifying"), (
        f"no attribute of the place-bearing types {place_types} is declared `identifying` "
        f"(attribute_roles covers {sorted(roles)}). A place's coordinates are what identify it; without the "
        "declaration the clean anchor lever 2 rests on cannot confirm either."
    )


def test_geography_is_declared_per_type_not_once() -> None:
    """C6: "``perishable`` is declared **per (type, attribute)**: geography is perishable for a *formation*,
    **constitutive** for a *presence*, and **identifying** for a *place*."

    The point of the closure is that one attribute carries different identity consequences on different
    citizens, so the same geography attribute must not carry one global role.
    """
    by_attr: dict[str, set] = {}
    for etype, attr, entry in rc.attribute_role_entries():
        by_attr.setdefault(attr, set()).add((etype, rc.time_role_of(entry)))
    geo = {a: v for a, v in by_attr.items() if "coord" in a.lower() or "geo" in a.lower()}

    assert geo, (
        "no geography attribute is declared in attribute_roles at all, so geography has no time role on "
        f"any citizen. Declared attributes: {sorted(by_attr)}"
    )
    multi = {a: v for a, v in geo.items() if len({role for _, role in v}) > 1}
    assert multi, (
        f"geography carries a single role everywhere: {geo}. C6's whole content is that a presence *is* "
        "operator+design+site+window (constitutive) while a formation moves (perishable) — one role for "
        "both collapses the distinction G15/G16 are built on."
    )


# ── the behaviour each value earns ───────────────────────────────────────────────────────────────

def _presences(lat: float, lon: float) -> list:
    return [
        rc.ent("pr1", "presence", "HQ-X seen at the revetments", attrs=rk.coords(lat, lon, "alpha"),
               doc="d1"),
        rc.ent("pr2", "presence", "a SAM battery at the same revetments",
               attrs=rk.coords(lat, lon, "alpha"), doc="d2", sid="mid"),
        rc.ent("d", "variant", "HQ-X", doc="d1"),
        rc.ent("op", "operator", "Air Force", doc="d1"),
        rc.rel("r1", "pr1", "instance-of", "d", doc="d1", iso="2025-03-01"),
        rc.rel("r2", "pr2", "instance-of", "d", doc="d2", iso="2025-03-02", sid="mid"),
        rc.rel("r3", "pr1", "operated-by", "op", doc="d1", iso="2025-03-01"),
        rc.rel("r4", "pr2", "operated-by", "op", doc="d2", iso="2025-03-02", sid="mid"),
    ]


def _anchor_dd() -> tuple[float, float]:
    """A shipped gazetteer anchor of an identity-bearing precision class — read, never invented."""
    classes = set(rc.resolution_keys().get("place_identity_precision_classes") or [])
    for place in rk.shipped_bundle().places.places:
        if place.precision_class in classes and place.canonical_dd:
            return float(place.canonical_dd[0]), float(place.canonical_dd[1])
    raise AssertionError("config/places.yaml offers no anchor in an identity-bearing precision class")


def test_two_co_located_presences_of_one_design_confirm() -> None:
    """``constitutive``: "a presence *is* operator+design+site+window", so agreement on all of it **is**
    identity — "it cannot 'change' without being a *different* instance".

    This is rk-20's closure: the spec previously "point[ed] both ways: co-located reports 'collapse into one
    presence' vs 'shared anchors top out at probable'."
    """
    lat, lon = _anchor_dd()
    part = rc.part_of(_presences(lat, lon), rc.bundle())

    assert rc.fused(part, "pr1", "pr2"), (
        "two presences of the same design, at the same coordinate, under the same operator, in the same "
        f"window did not collapse (status={rc.status(part, 'pr1', 'pr2')}, "
        f"breakdown={rc.signals(part, 'pr1', 'pr2')}). Constitutive geography is what lets a presence "
        "confirm at all; without it the presence layer fragments per report and the OOB count inflates."
    )


def test_two_mentions_of_one_place_confirm_on_their_coordinate() -> None:
    """``identifying``: "the attribute identifies the entity (a place's coordinates); **satisfies the
    non-perishable requirement for a confirm**." A place is where it is.
    """
    lat, lon = _anchor_dd()
    part = rc.part_of(
        [
            rc.site("site_x", "Northern Revetment Complex", lat=lat, lon=lon, doc="d1"),
            rc.site("site_y", "The Revetment Site", lat=lat, lon=lon, doc="d2", sid="mid"),
        ],
        rc.bundle(),
    )

    assert rc.fused(part, "site_x", "site_y"), (
        "two mentions carrying the identical frozen coordinate did not resolve to one place "
        f"(status={rc.status(part, 'site_x', 'site_y')}). Identifying coordinates are the clean anchor "
        "spine/13 §6 lever 2 rests on."
    )


def test_perishable_only_agreement_still_cannot_confirm() -> None:
    """The value that must keep its old behaviour through the migration — the D-13.9(a) cap:
    "**perishable-only evidence cannot confirm**."

    A mirror in the S2 sense: this passes today via the boolean, so it fails precisely when ``time_role``
    is declared but the *consumer* still reads ``perishable`` — the rename-without-rewiring failure that
    a hand-copied knob caused once already.
    """
    perishable = [
        f"{etype}.{attr}" for etype, attr, entry in rc.attribute_role_entries()
        if rc.time_role_of(entry) == "perishable" or entry.get(rc.LEGACY_PERISHABLE_KEY) is True
    ]
    assert perishable, "no shipped attribute is declared perishable, so this cap has nothing to bite on"
    etype, attr = perishable[0].split(".", 1)

    part = rc.part_of(
        [
            rc.ent("a", etype, "Alpha Battery", attrs={attr: "active"}, doc="d1"),
            rc.ent("b", etype, "Bravo Battery", attrs={attr: "active"}, doc="d2", sid="mid"),
            *rc.shared_neighbours("a", "b"),
        ],
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        f"a pair whose only attribute agreement is the perishable {perishable[0]} was CONFIRMED. A shared "
        "transient state is one entity or two that passed through it — 'perishable-only evidence cannot "
        f"confirm'. breakdown={rc.signals(part, 'a', 'b')}"
    )
    assert rc.status(part, "a", "b") is not None, (
        "the perishable-only pair was dropped rather than queued — the cap is 'not fused; queued and "
        "reported' (D8's terminology correction), never a silent separation."
    )


# ── the ordering fix: a place merge must be visible to the relational term ───────────────────────

def test_a_place_merge_is_visible_to_the_relational_signal() -> None:
    """§5b: "``places.augment`` runs **after** ``resolve_entities`` … so place merges are invisible to
    ``relational_score``: two units based at differently-named-but-identical sites do not share a
    neighbour key." Lever 2 "names places as a clean anchor the instance layer crystallizes onto —
    **mechanically they are not one**."

    Asserted on the *signal*, not on a merge: the two formations here carry differing designations and must
    stay apart. What must exist is the relational evidence, so the analyst sees the shared base at all.
    """
    lat, lon = _anchor_dd()
    claims = [
        rc.ent("u1", "unit", "8th AD Battalion",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d1"),
        rc.ent("u2", "unit", "12th AD Battalion",
               attrs={"service_branch": "PAF", "designator": "12"}, doc="d2", sid="mid"),
        rc.site("site_x", "Northern Revetment Complex", lat=lat, lon=lon, doc="d1"),
        rc.site("site_y", "The Revetment Site", lat=lat, lon=lon, doc="d2", sid="mid"),
        rc.rel("r1", "u1", "based-at", "site_x", doc="d1", iso="2021-01-01"),
        rc.rel("r2", "u2", "based-at", "site_y", doc="d2", iso="2021-02-01", sid="mid"),
    ]
    part = rc.part_of(claims, rc.bundle())

    assert rc.fused(part, "site_x", "site_y"), (
        "the two site mentions did not resolve to one place, so the ordering assertion below is vacuous "
        f"(status={rc.status(part, 'site_x', 'site_y')})"
    )
    relational = rc.signals(part, "u1", "u2").get("relational")
    assert relational, (
        f"the units' relational signal is {relational!r} even though both are based at what the resolver "
        "itself decided is ONE place. The place merge lands after the entity fixpoint, so the shared "
        "anchor is invisible exactly where lever 2 claims to work."
    )
