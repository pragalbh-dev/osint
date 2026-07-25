"""S3's **safety** property — with ``earned_identity.enabled`` OFF the derived graph does not move.

The stage rule (plan §5a-bis): flag OFF ⇒ byte-identical to the stage before; flag ON ⇒ the graph *must*
change, and an unchanged flag-on graph is a failure signal rather than a success. So this file asserts the
flag-off half only, exactly as ``test_s2_flag_off_equivalence`` does for RK-LAYER.

**Why it exists, and why the S2 file was not enough.** The S2 gate reads the stage flag from ambient
config. Under the ordinary run that is off, so it looked like an S3 flag-off gate too — but nothing in it
mentions ``earned_identity``, so it could never have caught what the review found: S3's coreference *bind
authorisation* reached the resolver through an ungated config union while every S3 restraint early-returned
on the flag. The shipped flag-off deployment therefore ran S3's permission with none of S3's limits, and
three fusions the flag-ON run refuses happened flag-off — two co-located formations at ``confirmed``, an
explicitly contrasted pair at ``confirmed``, and a bind licensed by one document spreading onto a profile
built from another. Every assertion here **pins the flag off explicitly** rather than inheriting it, so the
gate measures the flag-off deployment whichever way the suite is run (``--earned-identity=on`` included).

Pinning, not inheriting, is the whole design of this file: a gate that reads ambient config asserts
"whatever is configured behaves as configured", which is true of every system and interesting about none.
"""

from __future__ import annotations

import hashlib

import pytest
import yaml

from chanakya.config.store import ConfigStore
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.settings import config_dir
from chanakya.view import rebuild, view_to_json
from tests import _rk_layer as rk
from tests.fixtures import loaders
from tests.gates.test_s1_zero_behavioural_change import PRE_S1_EXPECTED_VIEW_MD5

#: The stage block key, and the one flag inside it.
STAGE_BLOCK, FLAG = "earned_identity", "enabled"

#: The **full-scenario** surface (every frozen claim, nothing withheld), rebuilt through ``eval.harness``.
#: The same surface and the same numbers ``test_s2_flag_off_equivalence`` pins — deliberately, so a
#: flag-off regression reads identically whichever stage introduced it.
CORPUS_BASELINE = {"node_count": 169, "edge_count": 80, "event_count": 71, "known_gap_count": 20}

#: The **booted app** surface — what the running system serves. It withholds ``d18_rahwali_pass1`` +
#: ``d19_rahwali_confirm`` from the boot seed (they are ingested live for the demo), so it is structurally
#: blind to the relocation pair and cannot replace the harness surface. It is pinned anyway because it is
#: the only surface that exercises the real boot path, and because a fabricated relocation — the specific
#: harm S3's co-location cap exists to prevent — would show up here as a moved edge or event count.
BOOTED_BASELINE = {"node_count": 160, "edge_count": 73, "event_count": 66, "known_gap_count": 18}

#: Claims seeded into the booted evidence log. Not a graph metric: it pins the *input*, so a moved graph
#: number can be read as behaviour rather than as a corpus that quietly grew or shrank.
BOOTED_CLAIM_COUNT = 450


def _pinned(bundle):
    """``bundle`` with ``earned_identity.enabled`` forced **False** — never read from ambient config.

    Applied to a *snapshot* rather than written back through ``ConfigStore.set_section``, because a hot
    write bumps the config version and the version is serialized into the view: the golden md5 would then
    fail on the pin itself rather than on any behaviour. The pin must be invisible except for the flag.
    """
    block = {**(getattr(bundle.resolution, STAGE_BLOCK, None) or {}), FLAG: False}
    return bundle.model_copy(
        update={"resolution": bundle.resolution.model_copy(update={STAGE_BLOCK: block})}
    )


def _flag_off_bundle():
    """The shipped config, flag pinned off."""
    return _pinned(ConfigStore.seed_from(config_dir()).snapshot())


# ── the pin itself has to bite ───────────────────────────────────────────────────────────────────

def test_the_pin_actually_turns_the_stage_off() -> None:
    """Guard the guard: if ``_flag_off_bundle`` stopped disabling the stage, every assertion below would
    pass by measuring a flag-on run against flag-off numbers and calling the agreement a success.
    """
    assert ResolveConfig.from_bundle(_flag_off_bundle()).earned_identity_on is False, (
        "the flag-off pin does not turn the stage off — the block or the flag key was renamed. Fix the "
        "pin; do not let this file inherit the flag from ambient config, which is exactly the hole that "
        "let an ungated S3 authorisation ship."
    )


def test_the_shipped_config_still_ships_the_stage_off() -> None:
    """What the repo *ships*, read off the working tree — true in both run modes.

    Deliberately **not** through ``settings.config_dir()``: ``--earned-identity=on`` redirects that at a
    throwaway copy with the flag flipped, so a loader-based read would report the run mode rather than the
    file. The working tree is never modified by the switch, which is what makes this assertion spoof-proof
    in both directions.
    """
    raw = yaml.safe_load((rk.REPO_ROOT / "config" / "resolution.yaml").read_text(encoding="utf-8")) or {}
    block = raw.get(STAGE_BLOCK) or {}
    assert block.get(FLAG) is False, (
        f"config/resolution.yaml ships `{STAGE_BLOCK}.{FLAG}: {block.get(FLAG)!r}`. S3 ships OFF; a flipped "
        "default is a stage decision with a ledger entry, not a side effect of a test run."
    )


# ── nothing S3 authorises may reach a flag-off resolver ──────────────────────────────────────────

def test_flag_off_authorises_no_coreference_bootstrap() -> None:
    """The specific leak, asserted at the config surface where it happened.

    An "authoritative" coreference category is a Phase-1 bootstrap trigger: it fuses at confidence 1.0 and
    bypasses banding, so **no cap restrains it**. Granting that flag-off while the co-location cap, the
    contrast ceiling and the document-scoping of a bind all early-return on the flag is strictly worse
    than either end state. The stage's categories must be invisible to a flag-off reader.
    """
    off = ResolveConfig.from_bundle(_flag_off_bundle())
    stage_categories = set(off.earned_identity.authoritative_categories)
    assert stage_categories, (
        "the stage block declares no authoritative_categories, so this assertion would pass vacuously — "
        "the leak it guards is 'the stage's list reaches a flag-off resolver', which needs a list"
    )
    leaked = sorted(stage_categories & off.coref_authoritative_evidence)

    assert not leaked, (
        f"with the stage flag OFF the resolver still authorises {leaked} to BOOTSTRAP a merge. That is S3's "
        "permission running with none of S3's restraints, which measured as two co-located formations and "
        "an explicitly contrasted pair fusing at `confirmed` where the flag-on run held both at `probable`."
    )


# ── the three baselines, each with the flag pinned off ───────────────────────────────────────────

def test_flag_off_rebuild_of_the_golden_logs_still_matches_the_recorded_view() -> None:
    """The golden fixture carries its own tiny ``config/ontology.yaml``, so it is blind to shipped-config
    edits — it catches a change in the rebuild path itself.
    """
    view = rebuild(
        loaders.golden_evidence_log(), loaders.golden_decision_log(),
        _pinned(loaders.golden_config_store().snapshot()),
    )
    recorded = loaders.expected_view_json()

    assert hashlib.md5(recorded.encode("utf-8")).hexdigest() == PRE_S1_EXPECTED_VIEW_MD5, (
        "expected_view.json was re-recorded during S3 — the golden regenerates at RK-NAMECUT (S4), not "
        "here (plan §9); with the flag off S3 must not move the graph at all"
    )
    assert view_to_json(view) + "\n" == recorded, (
        "a flag-off rebuild of the golden logs no longer reproduces expected_view.json. Do NOT re-record "
        "the fixture to match: the safety property is the point"
    )


@pytest.mark.parametrize("metric", sorted(CORPUS_BASELINE))
def test_flag_off_leaves_the_full_scenario_graph_unchanged(metric: str) -> None:
    """The only surface that sees S3's **config** edits — the stage block, the ceilings, the category
    lists. Parametrized per metric so a failure names *what* moved.

    A legitimate corpus regeneration (RK-DATA, plan §10) moves these numbers; re-record them with a ledger
    entry, and never to make a flag-off change go green.
    """
    from eval import harness

    if not harness.bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {harness.bundles_dir()}")

    inp = harness.load_scenario()
    view = rebuild(inp.evidence, [], _pinned(inp.config_store.snapshot()))
    got = view.meta.get(metric)

    assert got == CORPUS_BASELINE[metric], (
        f"with the S3 flag pinned OFF the full-scenario {metric} moved from {CORPUS_BASELINE[metric]} to "
        f"{got}. Flag off must reproduce the S2 view exactly — a knob that acts without its flag is the "
        "defect this gate exists for."
    )


@pytest.mark.parametrize("metric", sorted(BOOTED_BASELINE))
def test_flag_off_leaves_the_booted_graph_unchanged(metric: str) -> None:
    """The production boot path — the same seeded logs and the same ``rebuild`` call ``AppState.boot``
    makes, with the config snapshot pinned flag-off on the way in.
    """
    from chanakya.api.state import build_default_state

    state = build_default_state()
    if state.evidence.count() == 0:
        pytest.skip("no seeded evidence — the booted surface has nothing to measure")
    view = rebuild(state.evidence, state.decision, _pinned(state.config.snapshot()))
    got = view.meta.get(metric)

    assert got == BOOTED_BASELINE[metric], (
        f"with the S3 flag pinned OFF the booted {metric} moved from {BOOTED_BASELINE[metric]} to {got}. "
        "This is the surface a reviewer actually hits."
    )


def test_the_booted_seed_is_the_corpus_we_measured() -> None:
    """Pin the input beside the outputs, so a moved graph number cannot be explained away as a moved corpus."""
    from chanakya.api.state import build_default_state

    state = build_default_state()
    if state.evidence.count() == 0:
        pytest.skip("no seeded evidence — the booted surface has nothing to measure")

    assert state.evidence.count() == BOOTED_CLAIM_COUNT, (
        f"the booted evidence log holds {state.evidence.count()} claims, not {BOOTED_CLAIM_COUNT}. The "
        "graph baselines above are only meaningful over the corpus they were recorded on."
    )
