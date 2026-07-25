"""G19 — cross-**namespace** and cross-**type** non-fusion, in BOTH phases (RK-COREF/S3).

The single most dangerous over-merge class for an operator-scoped order of battle, and until S3 it was
guarded nowhere that mattered:

* ``namespace_compatible`` gated only the bootstrap's *exact-name* branch, ``_name_containment``,
  ``_identity_pairs`` and ``_coref_pairs`` — **never the Phase-2 fuzzy fixpoint** — and relational blocking
  emits pairs with **no namespace key at all**, so a PLA-side and a PAF-side instance could be scored and
  auto-merged (D4);
* cross-type was only ever a *skip in candidate collection* with an escape hatch, so the **Phase-1
  bootstrap** could fuse a component into a variant on an identical name;
* and the review found worse: ``AliasIndex.equivalent`` was **reflexive** for any name appearing in the
  alias table, so ``equivalent(n, n)`` was trivially true and the ungated alias branch matched *before* the
  namespace-gated exact-name branch. A remedy that added a namespace key only to the Phase-2 loop would have
  left cross-operator **and cross-type** fusion wide open in Phase 1, at confidence 1.0, past every band.

Every fixture here is **abstract** (ruling M4): the frozen corpus cannot exercise this — it holds essentially
one numbered formation and zero coreference annotations — so the mechanism is proven on invented data and is
honestly inert on the corpus rather than hidden to keep anything green.
"""

from __future__ import annotations

from chanakya.resolve import ResolveConfig, resolve
from chanakya.resolve.aliases import AliasIndex
from tests.resolve._helpers import entity, mk_config, triple

#: The stage block, in the shape the shipped config declares it. Only what each test needs is set — an absent
#: knob is inert by construction, which is how a test proves *which* mechanism did the work.
EARNED = {"enabled": True, "name_ceiling": "possible"}


def _cfg(**over):
    earned = {**EARNED, **over.pop("earned", {})}
    return mk_config(earned_identity=earned, name_alone_caps_at_possible=True, **over)


# ── the alias-reflexivity hole (Phase 1) ─────────────────────────────────────────────────────────

def test_alias_equivalence_is_not_reflexive_when_the_stage_flag_is_on() -> None:
    """A name in the table was alias-equivalent **to itself** — so the ungated branch fired first.

    This is the mechanism, tested at the unit it lives in: excluding names *absent* from the table (which the
    pre-S3 code did) is not the same as excluding ``a == b``. For any name that DOES appear in a class, both
    sides share a root and ``equivalent`` returned True with no type and no namespace check anywhere.
    """
    idx = AliasIndex(require_distinct_forms=True)
    idx.link("hq 9 p", "fd 2000")

    assert idx.equivalent("hq 9 p", "fd 2000"), "a real alias LINK must still be equivalent"
    assert not idx.equivalent("hq 9 p", "hq 9 p"), (
        "a name is alias-equivalent to ITSELF — the branch fires with no type or namespace gate, which is how "
        "cross-type and cross-operator fusion became reachable in Phase 1 (G19)"
    )
    legacy = AliasIndex()
    legacy.link("hq 9 p", "fd 2000")
    assert legacy.equivalent("hq 9 p", "hq 9 p"), (
        "the pre-S3 index must still be reflexive, or this test is not measuring a change"
    )


def test_cross_type_pair_with_one_name_cannot_fuse_in_phase_one() -> None:
    """A ``component`` and a ``variant`` sharing a designator: scored, never fused.

    Both sides normalise to one alias-table entry, which is exactly the shape that reached the reflexive
    branch. The pair must land nowhere in ``same_as``.
    """
    claims = [
        entity("c1", "component", "HT-233"),
        entity("v1", "variant", "HT-233"),
    ]
    cfg = _cfg(alias_table={"HT-233": ["H-200"]})
    part = resolve(claims, cfg)

    assert not part.same_as, (
        f"a cross-TYPE pair fused: {part.same_as}. Two entities of different ontology types are not one "
        "entity however identical their names — and this path bypassed the bands entirely (G19)"
    )


def test_cross_namespace_same_type_pair_cannot_fuse_and_is_raised_with_a_reason() -> None:
    """A PLA-side and a PAF-side profile of one design: refused, and the analyst is told why.

    The two halves of G19 get **different** ceilings on purpose. A type mismatch is a schema fact and stays
    out of the queue (T3b-A already ruled that asking an analyst whether a sector is a centre "is not triage,
    it is noise"). A namespace mismatch between two entities of the same type is the opposite: a look-alike
    straddling two operators is either an extraction error or deliberate conflation, and both are the
    analyst's call — so it caps at ``probable`` **with the reason**.
    """
    # A shared neighbour is what GENERATES the pair: `country_or_domain_namespace` is a blocking key, so two
    # differently-scoped entities never land in one token block — the only routes to a cross-namespace
    # candidate are relational blocking (which emits pairs with NO namespace key, D4's own finding) and the
    # all-pairs alias sweep. Using the relational route makes this the case D4 measured, not a contrived one.
    claims = [
        entity("v_cn", "variant", "HQ-9", country="China"),
        entity("v_pk", "variant", "HQ-9", country="Pakistan"),
        entity("c_shared", "component", "HT-233"),
        triple("v_cn", "equips", "c_shared"),
        triple("v_pk", "equips", "c_shared"),
    ]
    part = resolve(claims, _cfg())

    assert not part.same_as, f"a cross-NAMESPACE pair fused: {part.same_as} (G19)"
    reasons = " ".join(part.candidate_reasons.values())
    assert "cross-namespace" in reasons, (
        "the refusal is invisible: a cross-operator look-alike must reach the analyst WITH its reason, or a "
        "wall is indistinguishable from a missing edge"
    )


# ── the Phase-2 fuzzy fixpoint (D4's original half) ──────────────────────────────────────────────

def test_cross_namespace_pair_cannot_fuse_in_the_phase_two_fixpoint_either() -> None:
    """The fixpoint that ACTUALLY unions never checked the namespace, and relational blocking has no key.

    Built so the pair reaches the auto band on the *fuzzy* path rather than through any bootstrap trigger: a
    lowered per-type floor plus a near-identical name and a shared neighbour. That is the combination D4
    measured as reachable, and it is the one a Phase-1-only remedy would have missed.
    """
    claims = [
        entity("m_cn", "manufacturer", "Precision Machinery Corporation", country="China"),
        entity("m_pk", "manufacturer", "Precision Machinery Corporaton", country="Pakistan"),
        entity("v_x", "variant", "HQ-9"),
        triple("m_cn", "manufactures", "v_x"),
        triple("m_pk", "manufactures", "v_x"),
    ]
    cfg = _cfg(auto_merge_by_type={"manufacturer": 0.37})
    part = resolve(claims, cfg)

    assert not part.same_as, (
        f"the Phase-2 fixpoint auto-merged across namespaces at a lowered per-type floor: {part.same_as}. "
        "`namespace_compatible` gated four call sites and never this loop (D4/G19)"
    )


def test_the_same_pair_in_ONE_namespace_still_fuses() -> None:
    """The gate's biting clause — without this, G19 would pass by refusing everything.

    An over-refuser passes any test that only asserts absence, and over-refusal mis-tasks the analyst just as
    surely as over-merging fabricates. So the control asserts the legitimate spelling-variant merge the
    lowered per-type floor exists for **still happens** once the namespaces agree.
    """
    # ONE more trivially-available signal — a shared neighbour — which is precisely what D-13.10 says clears
    # the name cap. Without it the pair agrees on *nothing but its name*, and refusing it is the cap working:
    # a two-entity fixture with a similar name and no other evidence has not earned a confirmed identity.
    claims = [
        entity("m_a", "manufacturer", "Precision Machinery Corporation", country="China"),
        entity("m_b", "manufacturer", "Precision Machinery Corporaton", country="China"),
        entity("v_x", "variant", "HQ-9"),
        triple("m_a", "manufactures", "v_x"),
        triple("m_b", "manufactures", "v_x"),
    ]
    cfg = _cfg(auto_merge_by_type={"manufacturer": 0.37})
    part = resolve(claims, cfg)

    assert part.same_as, (
        "the same-namespace spelling variant no longer merges — G19 has become a refusal of everything, and a "
        "gate that passes by refusing everything is a gate that lies"
    )


# ── flag-off: the holes are still open, which is what makes the flag boundary real ────────────────

def test_the_alias_reflexivity_fix_is_not_flag_gated() -> None:
    """The reflexivity hole is a **bug**, so its fix ships in the default — not behind the stage flag.

    I first gated it, on the reasoning that flag-off must reproduce pre-S3 behaviour exactly. The independent
    suite rejected that, and it is right: ``AliasIndex.equivalent`` never did what its own docstring promised,
    and a fix that applies only when a stage flag is on leaves the hole open in the configuration everything
    actually runs in. Measured byte-inert on both real surfaces and the golden fixture — nothing in this
    corpus relied on a name being its own alias — so there was never a byte-identity cost to pay.

    The *caps* stay flag-gated, because they change what an earned signal may do. A method doing what it says
    is not a policy.
    """
    claims = [
        entity("c1", "component", "HT-233"),
        entity("v1", "variant", "HT-233"),
    ]
    off = mk_config(alias_table={"HT-233": ["H-200"]}, name_alone_caps_at_possible=True)
    assert ResolveConfig.from_bundle(off).earned_identity_on is False

    assert not resolve(claims, off).same_as, (
        "with the stage flag off a cross-TYPE pair still fused through the reflexive alias branch — the bug "
        "fix must hold in the shipped default, or G19's Phase-1 half is closed only where it is least needed"
    )
