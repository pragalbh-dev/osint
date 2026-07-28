"""G19 — cross-namespace **and** cross-type non-fusion, in BOTH phases.

Authored from the session spec alone. The gate row (§5, quoted):

    "Two instances in incompatible namespaces (a PLA-side and a PAF-side unit) **cannot fuse** — in the
    Phase-2 fuzzy fixpoint **and** in the Phase-1 bootstrap. Covers the alias branch: ``AliasIndex``
    equivalence must be **non-reflexive** (a real alias link) and the alias branch must be **type- and
    namespace-gated**, else the namespace-gated exact-name branch is never reached."

    Catches: "the single most dangerous over-merge class for an operator-scoped OOB map (D4); cross-**type**
    fusion through the same alias hole; a remedy that gates only the Phase-2 loop and leaves bootstrap open."

The two defects, quoted:

* **D4** (§5a): "``namespace_compatible`` gates only bootstrap-exact-name … **never the Phase-2 fuzzy
  fixpoint** — and relational blocking emits pairs with **no namespace key**. So a PLA-side and a PAF-side
  instance can be scored and auto-merged, directly contradicting spine/13 §3 ('never across operators within
  the instance layer')."
* **§4's MISS**: "``AliasIndex`` equivalence is reflexive where its own docstring promises a real alias link,
  so the namespace-gated exact-name branch is never reached — making cross-operator **and cross-type**
  fusion reachable in **Phase 1**. D4's remedy (add a namespace key to the Phase-2 loop) would have left this
  wide open."

Every prohibition here has its mirror, because the cheap fix — refuse anything whose namespaces are not
identical — breaks the wildcard rule most of the graph relies on ("an unstated namespace is a **wildcard**,
not a conflict … so a missing attribute never fabricates a difference").

**Fixture-only, by measurement — ruling M4.** "Zero coreference annotations exist anywhere in the frozen
bundles, and three fixture families are untestable **in principle** rather than merely uncovered. So **G16,
G18 and G19 are all fixture-only** for now. That is the §5a-bis *inert-because-the-data-is-sparse* case with
the mechanism at full strength — **not** hidden-to-protect-a-fixture." So do **not** add a corpus-dependent
assertion to this gate: it would fail for the wrong reason and pressure someone to weaken the mechanism.

"""

from __future__ import annotations

import pytest

from chanakya.resolve import aliases as raliases
from tests import _rk_coref as rc

#: A name that IS in the shipped alias table, so it sits inside an alias equivalence class. Read from
#: config: the reflexivity hole only opens for a name the index has heard of.
ALIASED_NAME = next(iter(rc.resolution_keys()["alias_table"]))

CHINA, PAKISTAN = "China", "Pakistan"


#: A design-layer name that is NOT in the alias table, so a same-name pair reaches the exact-name /
#: fixpoint path rather than the alias branch.
PLAIN_NAME = "Type Nine SAM"


#: The two attributes that can carry a country namespace, and the gate must cover **both**.
#:
#: Every fixture in this file used to spell it ``country`` — and no document in the corpus states that
#: attribute at all. ``origin_country`` is the one sources actually write (on manufacturers and trading
#: organisations), and it was missing from ``Entity.namespace``'s key list. So G19 was green while the harm
#: it names was happening on the live attribute: two same-named trading organisations, one stated CHINA and
#: one stated Pakistan, fused at ``confirmed``, where the identical pair keyed on ``country`` was refused. A
#: gate that keys on an attribute nothing states certifies a guard nothing reaches.
#:
#: The refusal these cases pin is now the SHIPPED behaviour for both keys. It used to exist only with the S3
#: stage flag on — ``fusion_blocked`` early-returned on it — so the shipped default had no cross-namespace
#: wall on the fusion path for any key at all. That flag is deleted; ungating this refusal was the point of
#: the change (DECISIONS.md → DEFAULT-ON).
NS_KEYS = ("country", "origin_country")


def _two(etype_a: str, etype_b: str, name: str, ns_a: str | None, ns_b: str | None,
         *, scaffold: bool = False, attrs: dict | None = None, ns_key: str = "country") -> list:
    claims = [
        rc.ent("a", etype_a, name, attrs=(attrs or {}) | ({ns_key: ns_a} if ns_a else {}), doc="d1"),
        rc.ent("b", etype_b, name, attrs=(attrs or {}) | ({ns_key: ns_b} if ns_b else {}),
               doc="d2", sid="mid"),
    ]
    return claims + (_design_scaffold("a", "b") if scaffold else [])


def _design_scaffold(a: str, b: str) -> list:
    """Two shared **design-layer** neighbours for a pair of variants — a maximal relational score.

    **Ruling M15.** The earlier version of this scaffold shared a design and an operator between two
    ``unit``s, which is "the co-location evidence class and nothing else" — and G16 forbids exactly that from
    confirming a formation merge, so G19's must-fuse control and G16's cap contended. "A gate must never be
    relaxed to satisfy another gate's fixture." G16 governs the **instance** layer, so a design-layer pair
    (sharing a manufacturer and a component) fuses for a reason no other gate restrains, which leaves the
    namespace/type gating as the only thing under test here.
    """
    return [
        rc.ent("mfr", "manufacturer", "Northern Machinery Works", doc="d1"),
        rc.ent("comp", "component", "TR-40 tracking radar", doc="d1"),
        rc.rel(f"r-man-{a}", "mfr", "manufactures", a, doc="d1", iso="2020-01-01"),
        rc.rel(f"r-man-{b}", "mfr", "manufactures", b, doc="d2", iso="2020-02-01", sid="mid"),
        rc.rel(f"r-eq-{a}", "comp", "equips", a, doc="d1", iso="2020-01-01"),
        rc.rel(f"r-eq-{b}", "comp", "equips", b, doc="d2", iso="2020-02-01", sid="mid"),
    ]


# ── the alias-index contract itself ──────────────────────────────────────────────────────────────

def test_alias_equivalence_is_not_reflexive() -> None:
    """§4: "``AliasIndex`` equivalence is **reflexive** where its own docstring promises a real alias link."

    Its docstring already states the intended contract — "True iff two *normalised* names are in the same
    alias class **via a real alias LINK**. Deliberately NOT ``a == b``: identical surface strings are handled
    by the exact-name bootstrap rule (**which also checks the namespace**)" — so a name that merely appears
    in the table must not be alias-equivalent to itself, or the namespace-gated branch is never reached.
    """
    idx = raliases.build(rc.resolution_keys()["alias_table"], rc.resolution_keys()["transliteration"],
                         None, None)
    from chanakya.resolve.normalize import normalize

    key = normalize(ALIASED_NAME, rc.resolution_keys()["transliteration"])
    assert not idx.equivalent(key, key), (
        f"AliasIndex.equivalent({key!r}, {key!r}) is True: any name inside an alias class is "
        "alias-equivalent to ITSELF, so two identically-named entities take the alias branch and never "
        "reach the exact-name branch that checks type and namespace. That is a Phase-1 bootstrap merge at "
        "confidence 1.0 across an operator boundary."
    )


def test_a_real_alias_link_is_still_equivalent() -> None:
    """The mirror: the index must keep doing its job. FD-2000 ≡ HQ-9/P is a seeded, evidence-checked class,
    and the whole alias bootstrap ("a registry entry attract[s] every one of its known surface forms at
    confidence 1.0") rests on it.
    """
    table = rc.resolution_keys()["alias_table"]
    trans = rc.resolution_keys()["transliteration"]
    idx = raliases.build(table, trans, None, None)
    from chanakya.resolve.normalize import normalize

    canonical, aliases = next((c, a) for c, a in table.items() if a)
    assert idx.equivalent(normalize(canonical, trans), normalize(aliases[0], trans)), (
        f"the seeded alias link {canonical!r} ↔ {aliases[0]!r} is no longer equivalent. Making equivalence "
        "non-reflexive must not disable real alias links — that would delete the seeded merge card and the "
        "transliteration lane with it."
    )


# ── Phase 1: the alias branch, cross-namespace and cross-type ────────────────────────────────────

def test_the_alias_branch_cannot_fuse_across_namespaces_in_phase_one() -> None:
    """spine/13 §3: identity is "never across operators within the instance layer". A PLA HQ-9 and the
    Pakistani export line are two things, and an identical surface string does not make them one.
    """
    part = rc.part_of(_two("variant", "variant", ALIASED_NAME, CHINA, PAKISTAN), rc.bundle())

    assert not rc.fused(part, "a", "b"), (
        f"two {ALIASED_NAME!r} mentions in DIFFERENT stated namespaces ({CHINA} / {PAKISTAN}) fused in the "
        "Phase-1 bootstrap. The exact-name branch is namespace-gated; the alias branch is not, and a name "
        f"inside the alias table reaches the alias branch first. same_as={part.same_as}"
    )


def test_the_alias_branch_cannot_fuse_across_types_in_phase_one() -> None:
    """§4's second half: the same hole makes **cross-type** fusion reachable in Phase 1 — and the alias
    candidate sweep is an all-pairs pass with no type gate, so the pair is generated as well as merged.
    """
    part = rc.part_of(_two("variant", "unit", ALIASED_NAME, None, None), rc.bundle())

    assert not rc.fused(part, "a", "b"), (
        f"a `variant` and a `unit` both named {ALIASED_NAME!r} were fused into one node. A weapon design "
        "and a military formation are not the same entity under any evidence — T3b-A's own words: asking "
        "whether an air-defence sector is an air-defence centre 'is not triage, it is noise'. "
        f"same_as={part.same_as}"
    )


def test_an_exact_name_match_inside_one_namespace_still_bootstraps() -> None:
    """The mirror for Phase 1: the exact-name + namespace branch must survive the alias fix.

    D-13.10 caps name *alone*, so this pair also agrees on a durable declared attribute — the "one more
    trivially-available signal" that clears the cap at the design layer. That attribute is an
    ``export_designator`` (one production line) and deliberately not ``family``: a class every member of the
    family shares cannot be the extra signal, or the cap is off for every same-kind pair in the corpus.
    """
    part = rc.part_of(
        [
            rc.ent("a", "variant", ALIASED_NAME,
                   attrs={"country": PAKISTAN, "export_designator": "FD-2000"}, doc="d1"),
            rc.ent("b", "variant", ALIASED_NAME,
                   attrs={"country": PAKISTAN, "export_designator": "FD-2000"}, doc="d2", sid="mid"),
        ],
        rc.bundle(),
    )

    assert rc.fused(part, "a", "b"), (
        "two same-name, same-namespace, same-family design mentions no longer fuse. The namespace/type gate "
        "must bite on *incompatible* namespaces only; applied bluntly it deletes the ordinary merge the "
        f"alias and exact-name bootstrap exist for. status={rc.status(part, 'a', 'b')}"
    )


# ── Phase 2: the fuzzy fixpoint, which no namespace key ever guarded ─────────────────────────────
#
# Every pair below is **design-layer** (ruling M15): G16 governs the instance layer, so co-location has no
# claim on these, and the namespace/type gating is the only thing that can decide them. The design layer is
# also the *permissive* profile ("design collapses readily"), which makes it the sharper place to assert the
# boundary: even where fusion is easy, it must not cross an operator.

@pytest.mark.parametrize("ns_key", NS_KEYS)
def test_the_phase_two_fixpoint_cannot_fuse_across_namespaces(ns_key: str) -> None:
    """D4: "``namespace_compatible`` … **never the Phase-2 fuzzy fixpoint** — and relational blocking emits
    pairs with **no namespace key**", so the pair is both generated and scored across the boundary.

    Reached by a maximal relational score with no bootstrap trigger available (the name is not in the alias
    table and the exact-name branch is namespace-gated), so it exercises the *other* code path: a remedy that
    gates only Phase 1 fails this, and one that gates only Phase 2 fails the two alias tests above.

    Parametrized over :data:`NS_KEYS` because the guard is only as wide as its key list, and the list was
    measured one attribute short: the ``origin_country`` half failed here until ``Entity.namespace`` learned
    the attribute the corpus actually states.
    """
    part = rc.part_of(
        _two("variant", "variant", PLAIN_NAME, CHINA, PAKISTAN, scaffold=True, ns_key=ns_key), rc.bundle()
    )

    assert not rc.fused(part, "a", "b"), (
        "a PLA-side and a Pakistan-side design were auto-merged by the fuzzy fixpoint on a shared "
        "manufacturer and component. This is 'the single most dangerous over-merge class for an "
        "operator-scoped OOB map' — spine/13 §3: identity is never resolved across operators. "
        f"same_as={part.same_as} breakdown={rc.signals(part, 'a', 'b')}"
    )


def test_an_unstated_namespace_is_a_wildcard_not_a_conflict() -> None:
    """The mirror that stops the fix being a blanket refusal, quoted from ``namespace_compatible``:

        "an unstated namespace is a **wildcard**, not a conflict (most minted endpoint mentions carry no
        attrs at all), so a missing attribute never fabricates a difference."

    Most of the graph is minted endpoints with no attrs; requiring both sides to *state* a matching
    namespace would stop the resolver merging almost anything.
    """
    part = rc.part_of(_two("variant", "variant", PLAIN_NAME, PAKISTAN, None, scaffold=True), rc.bundle())

    assert rc.fused(part, "a", "b"), (
        "a pair with one stated namespace and one unstated was refused. Absence is not disagreement — the "
        "same doctrine the attribute-conflict rail follows — and treating it as a conflict fabricates a "
        f"difference no source stated. status={rc.status(part, 'a', 'b')}"
    )


@pytest.mark.parametrize("ns_key", NS_KEYS)
def test_a_shared_namespace_still_fuses_in_the_fixpoint(ns_key: str) -> None:
    """The other half of the same mirror: within one namespace the fixpoint must still do its work.

    Parametrized alongside the refusal so widening the key list cannot buy the refusal at the price of a
    blanket wall — the new key has to refuse across the boundary *and* still fuse within it.
    """
    part = rc.part_of(
        _two("variant", "variant", PLAIN_NAME, PAKISTAN, PAKISTAN, scaffold=True, ns_key=ns_key),
        rc.bundle(),
    )

    assert rc.fused(part, "a", "b"), (
        "two same-namespace designs sharing a full neighbourhood no longer fuse — the namespace guard has "
        f"become a wall on every pair. status={rc.status(part, 'a', 'b')}"
    )


# ── the instance layer, without contending with G16's cap ────────────────────────────────────────

def test_the_instance_layer_cannot_fuse_across_namespaces_either() -> None:
    """spine/13 §3's clause is about the instance layer — "never across operators **within the instance
    layer**" — so it needs its own case; but the pair must be one G16 *permits*.

    Ruling M15's second option: two formations sharing a **composite ``(service_branch, designator)``**
    identifier, which "is a unit-level discriminator and therefore *legitimately* confirms under G16". So the
    only thing left that can refuse it is the namespace boundary — no cap is being leaned on, and neither
    gate has to bend.
    """
    assert rc.hard_id_unique(), (
        "`hard_id_fields.unique` is undeclared, so the composite identifier cannot fire and this pair has no "
        "legitimate route to fusion — the assertion below would pass for the wrong reason (see the ladder "
        "suite's composite-declaration test)"
    )
    part = rc.part_of(
        _two("unit", "unit", "8th AD Battalion", CHINA, PAKISTAN,
             attrs={"service_branch": "PAF", "designator": "8"}),
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        "two formations were fused across an operator boundary on a shared composite identifier. The "
        "composite key 'lifts all caps' *within* a namespace — it does not license identity across armies, "
        f"which is exactly the reuse-across-armies problem D-13.20 exists for. same_as={part.same_as}"
    )


# ── the namespace must be read on a normalized value, or the guard mis-splits ────────────────────

@pytest.mark.parametrize("value_b", ["PAKISTAN", "pakistan"])
def test_the_namespace_guard_reads_a_normalized_value(value_b: str) -> None:
    """C7's ordering, felt here: normalization "must apply **before conflict detection *and* before namespace
    derivation** (``resolve/entities.py`` reads raw attrs; normalizing only at conflict time would leave
    namespaces split)".

    The shipped config records the live instance of this — "``origin_country`` as 'CHINA' vs 'China'" — so an
    un-normalized namespace guard splits one operator into several and *creates* fragmentation while
    claiming to prevent over-merge.

    Keyed on ``origin_country`` because that is the slot the shipped config names, and because the split is
    real there: adding the attribute to the namespace key list without folding case turned the corpus's own
    'SINO-GALAXY … CHINA' / 'SINO-GALAXY … China' pair into two trading organisations (169 → 170 nodes).
    Case is never a namespace difference, with the stage flag or without it.
    """
    part = rc.part_of(
        _two("variant", "variant", PLAIN_NAME, PAKISTAN, value_b, scaffold=True,
             ns_key="origin_country"),
        rc.bundle(),
    )

    assert rc.fused(part, "a", "b"), (
        f"{PAKISTAN!r} and {value_b!r} were treated as different namespaces, so one operator became two. "
        "The guard must key on the normalized class, exactly as C1 keys the site class on its normalized "
        f"class. status={rc.status(part, 'a', 'b')}"
    )
