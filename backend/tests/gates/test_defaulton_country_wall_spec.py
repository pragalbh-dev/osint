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


#: Every configuration a deployment can be in. "In every configuration" is the property's own words, so the
#: axis is asserted rather than assumed — including the two that used to switch the wall off wholesale.
def _configs() -> dict[str, Any]:
    base = rc.bundle(flag_on=False)                 # the shipped files, untouched by this test
    shipped = rc.earned_identity_block()
    return {
        "shipped": base,
        "stage-pinned-off": rc.with_resolution(base, earned_identity={**shipped, "enabled": False}),
        "stage-pinned-on": rc.with_resolution(base, earned_identity={**shipped, "enabled": True}),
        "stage-block-absent": rc.with_resolution(base, earned_identity=None),
    }


CONFIG_IDS = sorted(_configs())


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
    """
    part = rc.part_of(_claims("China", "Pakistan"), _configs()[config_id])

    assert rc.status(part, "org_cn", "org_pk") is not None, (
        f"[{config_id}] the resolver never linked the two profiles at all — the refusal became a silent "
        f"non-event (candidates={part.candidates}, possible={part.possible}). A cross-operator look-alike "
        "is the single most useful thing to put in front of an analyst; it may not be the one thing the "
        "system throws away."
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
    part = rc.part_of(_claims("China", "China"), rc.bundle(flag_on=False))

    assert rc.fused(part, "org_cn", "org_pk"), (
        "the control pair (same name, same country, coreference link) did NOT fuse, so every refusal in "
        f"this file is vacuous. status={rc.status(part, 'org_cn', 'org_pk')!r} "
        f"signals={rc.signals(part, 'org_cn', 'org_pk')}. Retune the fixture, never the assertion."
    )
