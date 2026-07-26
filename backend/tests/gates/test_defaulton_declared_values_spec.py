"""DEFAULT-ON P6 + P7 — **declared config values mean what they say**, and nothing is a validated no-op.

Authored from the session spec alone, implementation-blind. The two properties, quoted:

    "DECLARED CONFIG VALUES MEAN WHAT THEY SAY. A ceiling set to one declared level must behave differently
    from another; a value the code does not honour must be rejected rather than silently treated as
    something else."

    "NO VALIDATED NO-OPS. A config section that is parsed and validated must actually reach the behaviour it
    claims to control."

**Why these two are one gate.** Deleting a staging flag makes every remaining knob load-bearing: the flag
used to be the thing an operator turned, and from here on the *values* are. A dial that is read, parsed,
documented, and then quietly ignored is a worse failure than a missing dial, because the config file is the
system's own account of what it does — and the reader of that file has no way to tell. This project has
already paid for the lesson once, in the shipped comment above the ceilings:

    "They used to be declared in BOTH places … and the reader consulted this copy first. So editing the
    stage block, the block whose own header promises to hold every threshold, cap and floor the stage adds,
    was a silent no-op: setting all three to ``confirmed`` there changed nothing. Two names for one dial in
    two places is worse than either, because the copy a reader edits is the copy that does not run."

That fix moved the *declaration* to one place. It did not make the *values* mean anything: a ceiling can
still be declared at a level the code never tests for, in which case the dial is honoured for exactly one of
its three legal values and silently ignored for the others — which is the same defect one layer down.

**The three ceilings share one vocabulary, so they must share one meaning.** The system defines it itself:
ceiling ``possible`` ⇒ "withheld from fusion **and** from the analyst's queue (it has not earned
attention)"; ceiling ``probable`` ⇒ "withheld from fusion but GUARANTEED a queue place with this reason".
A ceiling of ``confirmed`` is therefore *no ceiling* — the pair may confirm on its merits. One vocabulary
with three declared levels and one behaviour is a dial with a label and no shaft.

**The remedy for a no-op may be deletion.** P7 says a parsed section must reach the behaviour it claims to
control; it does not say every current key must be wired. Where a key turns out to be genuinely redundant,
removing it from config satisfies this gate — what may not survive is the pretence.

**These fixtures put the identity machinery LIVE rather than testing the shipped flag state**, for the same
reason the escalation gate does: "the machinery is on by default" is asserted by
``test_defaulton_no_staging_switch_spec.py``, and if these tests inherited a flag-off graph they would fail
for its reason and say nothing about whether a declared value is honoured.

Abstract fixtures throughout (ruling M4).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from chanakya.resolve.rconfig import BANDS_BY_STRENGTH, ResolveConfig
from chanakya.schemas import pair_key
from tests import _rk_coref as rc
from tests import _rk_layer as rk

ONTOLOGY_BLOCK = "layer_routing"
RESOLUTION_BLOCK = "earned_identity"


def _live(**block: Any):
    """The shipped bundle with the identity stage live and the named tunables overridden.

    The stage is live because the machinery is unconditional, so "live" is just the shipped block. The two
    retired pins (``bundle(flag_on=True)``, ``earned_identity.enabled``) are gone; both bound to nothing and
    the second raised, which is what made this file's ceiling assertions unreadable. Detail in the sibling
    ``test_defaulton_refuse_and_escalate_spec._live``.

    **The damage here was the worse kind**, and it is worth naming because it is the whole reason this file
    is read carefully rather than trusted: ``test_a_legal_ceiling_value_is_never_rejected`` catches the load
    exception through ``rc.raises_loudly`` and reports "``name_ceiling='probable'`` … was rejected at load".
    The ceiling validator accepted every legal band perfectly; the raise came from ``enabled``. So nine reds
    named the wrong module — and the *mirror*, ``test_a_ceiling_value_the_code_cannot_honour_is_rejected``,
    was GREEN for the same wrong reason: it passed on the ``enabled`` error, not on ``CeilingValueError``.
    Nine false reds and nine false greens from one line of fixture. No assertion below changed.
    """
    base = rc.bundle(supersede_floor=dict(rk.SUPERSEDE_FLOOR))
    shipped = rc.earned_identity_block()
    return rc.with_resolution(base, earned_identity={**shipped, **block})


# ── the three ceilings, each with a fixture that reaches it ──────────────────────────────────────

_ORG = "Zeta Machine Works"
_DESCRIPTOR = "air defence battery"
_DESIGNATION = "8th AD Battalion"


def _name_alone_claims() -> list:
    """Identical names and nothing else — the widest fusion path in the system, and ``name_ceiling``'s."""
    return [
        rc.ent("a", "trading_org", _ORG, doc="d1"),
        rc.ent("b", "trading_org", _ORG, doc="d2", sid="mid"),
    ]


def _colocated_claims() -> list:
    """Two formations agreeing on nothing but where they are standing — ``colocation_ceiling``'s case."""
    return [
        rc.ent("a", "unit", _DESCRIPTOR, doc="d1"),
        rc.ent("b", "unit", _DESCRIPTOR, doc="d2", sid="mid"),
        rc.site("site", "Alpha Cantonment", doc="d1"),
        rc.rel("r-ba-a", "a", "based-at", "site", doc="d1", iso="2021-03-01"),
        rc.rel("r-ba-b", "b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
        *rc.shared_neighbours("a", "b"),
    ]


#: A unit-level discriminator both mentions state. Present so the CO-LOCATION cap lifts and the contrast
#: ceiling is the only thing left deciding the pair — without it two mechanisms cap the same pair and the
#: fixture would measure whichever fired first rather than the dial under test.
_FINGERPRINT = {"equipment_fingerprint": "HT-233 plus eight TEL"}


def _contrasted_claims(*, contrast: bool = True) -> list:
    """One document naming two formations and DISTINGUISHING them in its own words — ``contrast_ceiling``'s.

    ``contrast=False`` is the control: the same claims with nothing separating the two mentions, so the pair
    reaches the fusion path and a ceiling has something to withhold.
    """
    out = [
        rc.ent("a", "unit", _DESIGNATION, doc="d1", attrs=dict(_FINGERPRINT)),
        rc.ent("b", "unit", _DESIGNATION, doc="d1", sid="mid", attrs=dict(_FINGERPRINT)),
        *rc.shared_neighbours("a", "b", doc_a="d1", doc_b="d1"),
    ]
    if contrast:
        out.append(rc.contrast(
            "a", "b", doc="d1",
            quote=f"the {_DESIGNATION} and the separate {_DESIGNATION} were both inducted",
        ))
    return out


#: ``knob -> claim builder``. One entry per ceiling the stage block declares, so a new ceiling that arrives
#: without a fixture fails the coverage assertion below rather than sliding in untested.
CEILING_FIXTURES = {
    "name_ceiling": _name_alone_claims,
    "colocation_ceiling": _colocated_claims,
    "contrast_ceiling": _contrasted_claims,
}


def _outcome(knob: str, value: str) -> tuple[bool, str | None]:
    """The pair's **behaviour** under one ceiling value: ``(fused, identity status)``.

    Deliberately excludes the reason PROSE. A ceiling that changes only the sentence an analyst reads has
    not changed what the system did, and a dial whose entire effect is its own echo is the no-op this gate
    exists to catch.
    """
    claims = CEILING_FIXTURES[knob]()
    part = rc.part_of(claims, _live(**{knob: value}))
    return rc.fused(part, "a", "b"), rc.status(part, "a", "b")


def test_every_declared_ceiling_has_a_fixture_that_reaches_it() -> None:
    """Coverage control: a ceiling the stage block declares but no fixture exercises is untested, not passing.

    Without this, adding a fourth ceiling to config would leave the parametrized gates below silently
    unchanged and the new dial unmeasured.
    """
    declared = sorted(k for k in rc.earned_identity_block() if k.endswith("_ceiling"))

    assert declared == sorted(CEILING_FIXTURES), (
        f"config declares the ceilings {declared} but this gate exercises {sorted(CEILING_FIXTURES)}. Every "
        "declared ceiling needs a fixture that actually reaches it, or 'declared values mean what they say' "
        "is asserted for some of them and assumed for the rest."
    )


@pytest.mark.parametrize("knob", sorted(CEILING_FIXTURES))
def test_two_declared_ceiling_levels_never_behave_the_same(knob: str) -> None:
    """P6, first half: "a ceiling set to one declared level must behave differently from another."

    The vocabulary has three levels and they say three different things — *may confirm*, *never
    automatically but always in the queue*, *never automatically and not worth attention*. If two of them
    produce the same behaviour, one of them is not implemented, and the config file is describing a control
    the system does not have.

    Reported as the full measured table so the collision is readable rather than inferred.
    """
    table = {value: _outcome(knob, value) for value in BANDS_BY_STRENGTH}
    collisions = sorted(
        (x, y) for x in table for y in table if x < y and table[x] == table[y]
    )

    assert not collisions, (
        f"{knob}: these declared levels behave identically {collisions}. Measured table "
        f"(value -> (fused, identity status)): {table}. The three levels are three different instructions — "
        f"'{BANDS_BY_STRENGTH[0]}' is no ceiling at all (the pair may confirm on its merits), "
        f"'{BANDS_BY_STRENGTH[1]}' withholds the fusion and guarantees a queue place, "
        f"'{BANDS_BY_STRENGTH[2]}' withholds the fusion and the attention. A knob honoured for one of its "
        "legal values and ignored for the others is the silent-no-op defect the ceilings' own config comment "
        "was written about, one layer down."
    )


@pytest.mark.parametrize("knob", sorted(CEILING_FIXTURES))
@pytest.mark.parametrize("value", ["banana", "hitl", "0.5"])
def test_a_ceiling_value_the_code_cannot_honour_is_rejected(knob: str, value: str) -> None:
    """P6, second half: "a value the code does not honour must be rejected rather than silently treated as
    something else."

    The dangerous direction is specific and measured: a value outside the band vocabulary currently reads as
    "not ``possible``", i.e. it is silently downgraded to whatever restraint the code happens to default to.
    So an operator who mistypes a ceiling gets a differently-behaving system and no error — the exact shape
    of failure the ``perishable:`` key was made a loud validation error to prevent ("no migration shim
    outlives the stage that introduces it … a config still carrying it must fail at load rather than quietly
    read as 'no time role declared'"). ``hitl`` is in the list on purpose: it is a real band name *elsewhere
    in this config surface*, so it is the mistake an author is most likely to actually make.

    **An ABSENT or empty ceiling is deliberately not tested here.** "Absent ⇒ the mechanism is simply off,
    with no code literal" is a standing convention across every dial in this system (gate G6), and an empty
    string is how absence reads once compiled. Demanding an error there would break a rule the whole config
    surface depends on. The distinction this gate draws is between *nothing written* and *something
    unreadable written*.
    """
    claims = CEILING_FIXTURES[knob]()
    cfg = _live(**{knob: value})

    rejected = rc.raises_loudly(lambda: ResolveConfig.from_bundle(cfg)) or rc.raises_loudly(
        lambda: rc.part_of(claims, cfg)
    )

    assert rejected, (
        f"{knob}={value!r} was accepted silently and resolution proceeded "
        f"(fused={rc.fused(rc.part_of(claims, cfg), 'a', 'b')}). A band name is an enumerated vocabulary "
        f"({list(BANDS_BY_STRENGTH)}); a value outside it is not a weaker setting, it is a mistake, and "
        "reading it as 'whatever the code defaults to' turns a typo into a policy change nobody made. Fail "
        "at load, naming the key and the legal values."
    )


@pytest.mark.parametrize("knob", sorted(CEILING_FIXTURES))
@pytest.mark.parametrize("value", list(BANDS_BY_STRENGTH))
def test_a_legal_ceiling_value_is_never_rejected(knob: str, value: str) -> None:
    """The mirror of the rejection gate: validation must not be satisfied by rejecting everything.

    Every member of the declared vocabulary has to load and run. Without this, "reject what you cannot
    honour" could be implemented as "reject", which would make the ceilings unusable and this file green.
    """
    claims = CEILING_FIXTURES[knob]()
    cfg = _live(**{knob: value})

    assert not rc.raises_loudly(lambda: ResolveConfig.from_bundle(cfg)), (
        f"{knob}={value!r} — a member of the declared band vocabulary — was rejected at load"
    )
    assert not rc.raises_loudly(lambda: rc.part_of(claims, cfg)), (
        f"{knob}={value!r} — a member of the declared band vocabulary — raised during resolution"
    )


def test_the_contrast_fixture_would_fuse_without_the_stated_contrast() -> None:
    """Non-vacuity for ``contrast_ceiling``: absence of a contrast is NEUTRAL, never a prior for merging,
    but the pair must still *reach* the fusion path or the ceiling has nothing to cap.
    """
    part = rc.part_of(_contrasted_claims(contrast=False), _live())

    assert rc.fused(part, "a", "b"), (
        f"the control pair does not fuse without the contrast ({rc.status(part, 'a', 'b')!r}, "
        f"signals={rc.signals(part, 'a', 'b')}), so every contrast_ceiling assertion is vacuous. Retune the "
        "fixture, never the assertion."
    )


# ── P7: nothing is parsed, validated, documented and then ignored ────────────────────────────────

#: Where each stage block's *reader* lives. A key read only inside its own ``from_*`` constructor has been
#: parsed, not consumed — that is exactly the distinction P7 draws.
_CONSTRUCTORS = frozenset({"from_ontology", "from_resolution"})


def _declared_keys() -> dict[str, list[str]]:
    """``block name -> declared keys`` straight off the shipped YAML files."""
    out: dict[str, list[str]] = {}
    for file, block in (("ontology.yaml", ONTOLOGY_BLOCK), ("resolution.yaml", RESOLUTION_BLOCK)):
        raw = yaml.safe_load((Path(rk.REPO_ROOT) / "config" / file).read_text(encoding="utf-8")) or {}
        section = raw.get(block)
        out[block] = sorted(section) if isinstance(section, dict) else []
    return out


def _attribute_reads() -> dict[str, list[str]]:
    """``attribute name -> ["module.py:lineno", …]`` for every attribute READ in ``chanakya``.

    Excluded, because neither is consumption:

    * the dataclass field declaration (``AnnAssign``) — that is the parse;
    * anything inside a ``from_ontology`` / ``from_resolution`` body — that is also the parse.

    A read inside any *other* method of the reader class **does** count: ``normalise_tag`` consulting
    ``site_type_vocabulary`` is the vocabulary reaching behaviour, and its caller lives elsewhere.
    """
    root = Path(rk.PKG_ROOT)
    reads: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in _CONSTRUCTORS:
                skip.update(id(sub) for sub in ast.walk(node))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and id(node) not in skip:
                reads.setdefault(node.attr, []).append(f"{path.relative_to(root)}:{node.lineno}")
    return reads


#: Keys whose whole job is to be part of another mechanism's *declaration* rather than to be read by name.
#: Empty today, and deliberately so: an exemption list is where a no-op goes to hide, so anything added here
#: needs a stated reason in the same commit.
_P7_EXEMPT: frozenset[str] = frozenset()


def test_every_declared_stage_tunable_actually_reaches_behaviour() -> None:
    """P7. A key the stage block declares must be read somewhere other than the parser that reads the file.

    Two live examples this catches, and both read as fully-wired config from the file:

    * ``layer_routing.presence_type`` — "The instance citizen the build materializes … nothing here is a
      code literal (G6)". Parsed into a field; never read. The build gets its citizen from the ontology's
      ``instance_split`` / ``materializes`` declarations instead, so the promise that this value controls it
      is false.
    * ``earned_identity.presence_types`` — "The two citizens S2 created. A presence-level merge in a
      co-location case is EXPECTED and must not be capped." The cap is scoped by ``formation_types`` alone,
      so the exemption this key claims to grant is granted by something else and the key grants nothing.

    Either wire it or delete it. What may not survive is a config file that documents a control the system
    does not have — the reader of that file has no way to tell, which is precisely why the ceilings' "two
    names for one dial" defect went unnoticed through a whole stage.
    """
    reads = _attribute_reads()
    declared = _declared_keys()
    assert any(declared.values()), (
        "neither stage block declares any key — this gate reads the shipped YAML, so an empty result means "
        "the blocks were deleted rather than that everything is consumed"
    )
    # Non-vacuity: keys we know are consumed must be found, or the scan itself is broken.
    for known in ("wall_predicates", "absent_bucket", "site_type_vocabulary", "equivalence_markers"):
        assert reads.get(known), (
            f"the scan found no read of {known!r}, which IS consumed — the scan is broken, not the config. "
            "Fix the scan before trusting any absence below."
        )

    inert = {
        f"{block}.{key}": "parsed, never read outside the parser"
        for block, keys in declared.items()
        for key in keys
        if key not in _P7_EXEMPT and not reads.get(key)
    }

    assert not inert, (
        f"these declared config keys never reach behaviour: {inert}. Each one is parsed, validated and "
        "documented as controlling something, and then read by nobody — a dial with a label and no shaft. "
        "The remedy may be deletion; it may not be leaving the file claiming a control that does not exist."
    )


# ── a ceiling may withhold the QUEUE place, never the escalation ─────────────────────────────────

def test_a_contrast_capped_out_of_the_queue_still_escalates() -> None:
    """``contrast_ceiling: possible`` is a legal triage choice, and it may not delete the analyst's record.

    The value withholds the fusion (right) *and* the queue place, so the pair was filed on the silent
    watch-list — refuse half held, escalate half lost. The distinction is whose evidence is being set aside: a
    NAME coincidence the resolver itself noticed has earned no attention, while here a SOURCE went out of its
    way to distinguish two mentions the identity score reads as one entity. That is an extraction error or a
    deliberate conflation, and both are findings.

    So the escalation is re-routed rather than dropped: the pair leaves the queue and each endpoint carries a
    named ``withheld_escalations`` record, which ``rebuild()`` renders as a Known Gap. Deliberately a separate
    channel from ``identity_refusals`` — that one unassesses the node, and holding this pair apart is the
    CORRECT outcome, so neither node's status may move.
    """
    part = rc.part_of(_contrasted_claims(), _live(contrast_ceiling="possible"))
    key = pair_key("a", "b")

    assert not rc.fused(part, "a", "b"), "the refuse half broke: the contrast pair fused"
    assert key not in {pair_key(x, y) for x, y in part.candidates}, (
        "the fixture is not exercising the case — at ceiling 'possible' the pair must be off the queue"
    )
    assert part.withheld_escalations.get(key), (
        "the pair was withheld from the analyst's QUEUE and no escalation was recorded — the refusal holds "
        f"and nobody is told. withheld_escalations={part.withheld_escalations}"
    )
    what_missing = part.withheld_escalations[key]
    assert "adjudication" in what_missing.lower() or "analyst" in what_missing.lower(), (
        f"the escalation does not say who has to act or what would settle it: {what_missing!r}"
    )


def test_the_queueing_ceiling_needs_no_re_routed_escalation() -> None:
    """The mirror: at ``probable`` the pair keeps its queue place, so the channel stays empty.

    Emitting both would tell the analyst the same thing twice — once as a queue item and once as a gap — which
    is how a register earns being skimmed.
    """
    part = rc.part_of(_contrasted_claims(), _live(contrast_ceiling="probable"))

    assert pair_key("a", "b") in {pair_key(x, y) for x, y in part.candidates}, (
        "at ceiling 'probable' the contrast pair must be guaranteed its queue place"
    )
    assert not part.withheld_escalations, (
        f"a queued pair also produced a re-routed escalation: {part.withheld_escalations}"
    )
