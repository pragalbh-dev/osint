"""DEFAULT-ON P2 — **two stated different countries never fuse.** In every configuration, with a reason.

Authored from the session spec alone, implementation-blind. The property, quoted:

    "TWO STATED DIFFERENT COUNTRIES NEVER FUSE. Same name, coref-linked, differing stated origin country ⇒
    refused, in every configuration, with a visible reason. This is the class that most damages an
    operator-scoped order of battle."

**Why this pair and not a generic one.** The fixture states all three conditions because each one is
load-bearing:

* **same name** — the only evidence *for* identity, which is what makes the refusal a real decision rather
  than a low score;
* **differing stated origin country** — the evidence *against*. Two countries is not a spelling difference
  and not an unknown; it is a stated contradiction about which operator the profile belongs to;
* **coref-linked** — without it the pair is never even *considered*: the country namespace is a blocking
  key, so the two profiles sit in different blocks and no candidate is generated. The in-document
  coreference link is what injects the pair into the fusion path, which is precisely how the harm is
  reachable in production. A gate that omitted the link would pass vacuously.

**And why ``origin_country`` specifically.** The country attribute this corpus actually states is
``origin_country`` — sources write it on manufacturers and trading organisations and essentially never
write a bare ``country``. A namespace that keys only on an attribute nobody writes blocks nothing, so both
attributes are parametrized: the wall must hold on the attribute the documents use, not only on the tidy one.

**The mirror is mandatory.** A wall built as "refuse anything whose namespaces are not identical" breaks
the wildcard rule most of the graph rests on (an *unstated* namespace is unknown, never "somewhere else"),
and a wall that compares raw strings shatters legitimate merges on 'CHINA' vs 'China'. Both mirrors are
asserted here, so this cannot be satisfied by timidity.

**Fixture-only, deliberately (ruling M4):** zero coreference annotations exist in the frozen bundles, so
this family is untestable on the corpus *in principle*. Principle #4 — the mechanism is covered by
corpus-independent unit tests so data staleness can never mask a logic bug.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya.schemas import pair_key
from tests import _rk_coref as rc
from tests import _rk_layer as rk

#: One organisation name, stated identically on both sides — the whole of the evidence FOR identity.
ORG = "Alpha Precision Machinery"
QUOTE = f"{ORG}, also known as {ORG}, per the register"

#: Both attributes that can carry a country namespace. ``origin_country`` is the one the corpus states.
COUNTRY_ATTRS = ("country", "origin_country")

#: Tokens a refusal reason must contain to count as *naming its ground*. Any one of them is enough — the
#: spec fixes the ground, never the prose (gate G6 keeps the wording out of code literals anyway).
GROUND_TOKENS = ("namespace", "operator", "china", "pakistan", "country")


def _claims(country_a: str, country_b: str, *, attr: str = "origin_country",
            etype: str = "trading_org", coref_link: bool = True) -> list:
    out = [
        rc.ent("org_cn", etype, ORG, doc="d1", attrs={attr: country_a}),
        rc.ent("org_pk", etype, ORG, doc="d1", sid="mid", attrs={attr: country_b}),
    ]
    if coref_link:
        out.append(rc.coref("org_cn", "org_pk", quote=QUOTE, doc="d1"))
    return out


#: Every configuration a deployment can REACH. "In every configuration" is the property's own words, so the
#: axis is asserted rather than assumed.
def _configs() -> dict[str, Any]:
    base = rc.bundle()                              # the shipped files, untouched by this test
    return {
        "shipped": base,
        "stage-block-absent": rc.with_resolution(base, earned_identity=None),
    }


CONFIG_IDS = sorted(_configs())

#: The two spellings that try to PIN the stage, kept as data because they are still asserted below — as
#: unreachable rather than as equivalent. See :func:`test_a_configuration_that_pins_the_stage_does_not_load`.
PINNED_SPELLINGS: dict[str, Any] = {"stage-pinned-off": False, "stage-pinned-on": True}


@pytest.mark.parametrize("spelling", sorted(PINNED_SPELLINGS))
def test_a_configuration_that_pins_the_stage_does_not_load(spelling: str) -> None:
    """RULING (integration, 2026-07-26). "In every configuration" now has two configurations, not four.

    This file was authored with ``stage-pinned-off`` and ``stage-pinned-on`` in the axis, on the reading that
    a deleted flag would be *ignored*. The implementation chose to REJECT it: ``earned_identity.enabled``
    raises ``StageBlockError`` at construction, in both directions. The two hands disagreed, so the ruling is
    recorded here rather than split.

    **The implementation is right, and this assertion is strictly stronger than the one it replaces.** The
    property is "there is no configuration in which the identity machinery is off". A config that loads and
    quietly ignores ``enabled: false`` satisfies it only in the letter: the operator who wrote that line
    believes identity is off, deploys, and is wrong — and being wrong about that is the entire fabrication
    path. A config that *refuses to load* leaves nobody mistaken. Rejecting ``enabled: true`` as well is not
    over-correction: a key that loads for one value and errors for the other is a switch with a broken half,
    and the next operator will try the other half.

    It is also the doctrine this spec's own author states, one file over — the ``perishable:`` precedent, in
    ``test_defaulton_declared_values_spec``: "no migration shim outlives the stage that introduces it … a
    config still carrying it must fail at load rather than quietly read as 'no time role declared'".

    While the pinned spellings sat in the behavioural axis they contributed eight reds that never reached a
    wall, a namespace or a partition — every one died inside ``ResolveConfig.from_bundle`` while its message
    blamed the fusion path.
    """
    base = rc.bundle()
    shipped = rc.earned_identity_block()
    cfg = rc.with_resolution(
        base, earned_identity={**shipped, "enabled": PINNED_SPELLINGS[spelling]}
    )

    assert rc.raises_loudly(lambda: rc.part_of(_claims("China", "Pakistan"), cfg)), (
        f"a deployment declaring earned_identity.enabled={PINNED_SPELLINGS[spelling]!r} ({spelling}) LOADED. "
        "A key with no consumer is worse than a missing one: an operator writes it, believes the stage is "
        "pinned, and gets whatever the code does anyway. Either direction must fail at load, naming the key."
    )


def _surfaced(part: Any, a: str, b: str) -> dict[str, str]:
    """Every analyst-facing rationale the partition carries about this pair, whatever channel it rode.

    Searched rather than assumed: the spec fixes that the refusal is *visible*, not which dict holds it.
    Any ``pair_key``-indexed mapping of strings on the partition counts, so a new channel is found too.
    """
    key = pair_key(*sorted((a, b)))
    out: dict[str, str] = {}
    for name in type(part).model_fields:
        value = getattr(part, name, None)
        if isinstance(value, dict) and isinstance(value.get(key), str) and value[key].strip():
            out[name] = value[key]
    if any({x, y} == {a, b} for x, y in getattr(part, "distinct_from", [])):
        out["distinct_from"] = f"drawn do-not-merge edge {a}|{b}"
    return out


# ── the refusal ─────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("config_id", CONFIG_IDS)
@pytest.mark.parametrize("attr", COUNTRY_ATTRS)
def test_two_stated_countries_never_fuse_in_any_configuration(config_id: str, attr: str) -> None:
    """The gate. Same name + coreference link + two stated countries ⇒ **not one entity**, always.

    "Never across operators within the instance layer" is not a tuning preference: a cross-operator fusion
    silently moves an asset from one army to another, and every downstream count, chokepoint and relocation
    inherits the error with full confidence and a clean audit trail.
    """
    part = rc.part_of(_claims("China", "Pakistan", attr=attr), _configs()[config_id])

    assert not rc.fused(part, "org_cn", "org_pk"), (
        f"[{config_id} / {attr}] a China-stated and a Pakistan-stated organisation of the SAME NAME fused "
        f"into one entity (identity status {rc.status(part, 'org_cn', 'org_pk')!r}, signals "
        f"{rc.signals(part, 'org_cn', 'org_pk')}). The coreference link is what puts the pair on the fusion "
        "path at all — the country namespace is a blocking key, so without the link the two are never even "
        "compared — which is exactly how this is reachable in production. Refusing it must be a property of "
        "the pair, not of a configuration."
    )


@pytest.mark.parametrize("config_id", CONFIG_IDS)
def test_the_refusal_is_visible_and_names_the_country_ground(config_id: str) -> None:
    """"…with a visible reason." A refusal nobody can read is indistinguishable from a pair never scored.

    Two profiles that look identical and straddle two operators is either an extraction error or deliberate
    conflation, and both are the analyst's call — so the resemblance is real, is raised, and says on what
    ground the merge was withheld.
    """
    part = rc.part_of(_claims("China", "Pakistan"), _configs()[config_id])
    surfaced = _surfaced(part, "org_cn", "org_pk")
    text = " ".join(surfaced.values()).lower()

    assert surfaced, (
        f"[{config_id}] the cross-operator pair was refused with NO analyst-facing reason anywhere on the "
        f"partition (searched every pair-keyed channel; status={rc.status(part, 'org_cn', 'org_pk')!r}). "
        "Refusing is only half the contract — the analyst must actually receive it."
    )
    assert any(tok in text for tok in GROUND_TOKENS), (
        f"[{config_id}] the surfaced reason never names the ground that caused the refusal: {surfaced}. "
        f"It must state that the two profiles are scoped to different operators/countries (any of "
        f"{list(GROUND_TOKENS)}), not a generic 'not merged' — the analyst needs to know WHICH question to "
        "adjudicate, and the two stated countries are that question."
    )


@pytest.mark.parametrize("config_id", CONFIG_IDS)
def test_the_pair_is_never_silently_dropped_instead_of_refused(config_id: str) -> None:
    """The other way to fail this property: refuse the fusion and lose the pair.

    "Retained but never surfaced" is the failure mode the register names — a link that scores as a genuine
    would-be merge, is withheld, and then falls off every list. The resemblance is evidence *of something*
    (an alias, an error, a plant); dropping it destroys the finding along with the merge.

    **RULING (integration, 2026-07-26): the property stands; the probe moves off ``identity_status``.**
    This was authored as ``identity_status(...) is not None``, i.e. the pair must appear in ``candidates`` or
    ``possible``. On this pair the implementation cannot satisfy that, and should not:

    * ``identity_status`` is defined as the label of an identity **link** — ``confirmed`` (merged),
      ``probable`` (a drawn candidate ``same-as`` an analyst may accept), ``possible`` (the watch-list, "these
      might be the same"). All three assert a *degree of belief that the two are one thing*. This pair has a
      credible, stated, both-sides-attested contradiction; the honest statement is not a weak identity
      hypothesis, it is a refusal.
    * ``probable`` would draw a candidate ``same-as`` edge — an *accept-this-merge* affordance for the
      costliest over-merge in an operator-scoped ORBAT. Handing an analyst a one-click button to commit the
      exact fusion the wall exists to prevent is the fabrication direction, not the escalation direction.
    * it is a designed invariant, not an oversight: ``finalise`` filters both tiers by
      ``as_pair(p) not in distinct`` (``resolve/cluster.py``), so a walled pair is structurally excluded from
      the identity bands. And ``identity_status`` is consumed downstream by Stage-3C link weighting and
      Stage-4 coverage, which would then be reading a merge hypothesis about a walled pair.

    So the probe asks what the docstring above actually argues — did the pair "fall off every list?" — over
    every channel a human reads, and it is **stricter** than the original in the way that matters: the
    original was satisfied by bare membership in a tier, with or without a reason. This requires the refusal
    to be reachable AND to carry its grounds. Membership with no reason no longer passes.
    """
    config = _configs()[config_id]
    claims = _claims("China", "Pakistan")
    part = rc.part_of(claims, config)
    key = pair_key(*sorted(("org_cn", "org_pk")))
    gaps = [
        g for g in (rk.build_view(config, claims).known_gaps or [])
        if g.related_ref in ("org_cn", "org_pk", key)
    ]
    channels = {
        "identity band": rc.status(part, "org_cn", "org_pk"),
        "wall reason": part.wall_reasons.get(key),
        "identity refusal": part.identity_refusals.get(key),
        "candidate reason": part.candidate_reasons.get(key),
        "known gap": "; ".join(sorted(g.id for g in gaps)) or None,
    }
    reached = {name: v for name, v in channels.items() if v}

    assert reached, (
        f"[{config_id}] the resolver refused the pair and told NO ONE — searched the identity bands, the "
        f"wall-reason channel, the identity-refusal register, the candidate reasons and the Known Gaps "
        f"(candidates={part.candidates}, possible={part.possible}). A cross-operator look-alike is the "
        "single most useful thing to put in front of an analyst; it may not be the one thing the system "
        "throws away."
    )
    grounded = {n: v for n, v in reached.items() if n != "identity band"}
    assert grounded, (
        f"[{config_id}] the pair appears in an identity band ({reached}) and nowhere that carries a REASON. "
        "Membership without grounds is the quiet drop wearing a referral's clothes: the analyst gets a "
        "number and never learns which question was withheld."
    )


# ── the mirrors: this must not be satisfied by refusing everything ──────────────────────────────

@pytest.mark.parametrize("config_id", CONFIG_IDS)
def test_the_same_country_spelled_two_ways_still_fuses(config_id: str) -> None:
    """Mirror 1: 'CHINA' and 'China' are one country. Case and punctuation are never a namespace difference.

    The measured cost of getting this wrong is on record — walling on raw stated values "SHATTERS
    legitimate merges", splitting the three SINO-GALAXY spellings. The wall is a wall on *stated
    disagreement*, not on typography.
    """
    part = rc.part_of(_claims("China", "CHINA"), _configs()[config_id])

    assert rc.fused(part, "org_cn", "org_pk"), (
        f"[{config_id}] 'China' and 'CHINA' were held apart as different operators (status "
        f"{rc.status(part, 'org_cn', 'org_pk')!r}). That is a fabricated distinction no source drew, and it "
        "fragments the supply-chain map while looking like caution. Fold the value before it becomes a "
        "namespace key."
    )


@pytest.mark.parametrize("config_id", CONFIG_IDS)
def test_an_unstated_country_is_unknown_not_somewhere_else(config_id: str) -> None:
    """Mirror 2: absence is not disagreement. Most minted endpoint mentions carry no attributes at all.

    An unstated namespace is a **wildcard**. A wall that read it as a conflict would refuse nearly every
    legitimate merge in the graph — the cheap fix that breaks the system in the other direction.
    """
    claims = [
        rc.ent("org_cn", "trading_org", ORG, doc="d1", attrs={"origin_country": "China"}),
        rc.ent("org_pk", "trading_org", ORG, doc="d1", sid="mid"),  # states nothing
        rc.coref("org_cn", "org_pk", quote=QUOTE, doc="d1"),
    ]
    part = rc.part_of(claims, _configs()[config_id])

    assert rc.fused(part, "org_cn", "org_pk"), (
        f"[{config_id}] a profile stating China and a profile stating nothing were refused as "
        f"cross-operator ({rc.status(part, 'org_cn', 'org_pk')!r}). Absence is UNKNOWN, never 'somewhere "
        "else' — the same asymmetry the attribute hard-conflict rail follows. Refusing here would wall the "
        "whole graph, because an endpoint mention normally carries no attributes."
    )


def test_the_fixture_would_fuse_without_the_country_difference() -> None:
    """Non-vacuity: the two profiles genuinely reach the fusion path, so the refusal above is a decision.

    Without this control, "they did not fuse" could pass because the pair never scored, never blocked
    together, or was dropped for some unrelated reason — and the whole file would be measuring nothing.
    """
    part = rc.part_of(_claims("China", "China"), rc.bundle())

    assert rc.fused(part, "org_cn", "org_pk"), (
        "the control pair (same name, same country, coreference link) did NOT fuse, so every refusal in "
        f"this file is vacuous. status={rc.status(part, 'org_cn', 'org_pk')!r} "
        f"signals={rc.signals(part, 'org_cn', 'org_pk')}. Retune the fixture, never the assertion."
    )
