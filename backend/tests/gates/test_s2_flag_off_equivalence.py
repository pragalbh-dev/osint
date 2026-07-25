"""S2's **safety** property — with the flag OFF the derived graph does not move.

Session file, "THE INVARIANT FLIPS — read this before anything else":

    "- **Flag OFF ⇒ byte-identical to S1** … That is the safety property.
     - **Flag ON ⇒ the graph MUST change.** An unchanged graph with the flag on means the stage did nothing
       (plan §5a-bis). Do not report 'byte-identical' as success."

So this file asserts **only** the flag-off half, and deliberately asserts **nothing** about flag-on
equivalence: plan §5a-bis is explicit that for S2 "an unchanged view means the stage did nothing", and
"**Never gate, default-away, or curb a target-correct capability to keep a fixture green**". A flag-on
byte-identity test would enshrine exactly the force-fitting the plan forbids.

Two test surfaces, because they fail on different mistakes:

* the **golden** fixture (``tests/fixtures/golden``) carries its own tiny ``config/ontology.yaml``, so it is
  blind to the shipped file S2 edits — it catches a change in ``view/pipeline.py`` itself;
* the **real shipped config + frozen corpus**, rebuilt through ``eval.harness`` (the *full-scenario* surface —
  see ``CORPUS_BASELINE`` for why that one and not the booted app's), is the only surface that sees S2's config
  edits (layer tags, the new predicates, the site_type re-key). A "config-only" change that quietly moves the
  graph with the flag off is invisible everywhere else.
"""

from __future__ import annotations

import hashlib

import pytest

from chanakya.view import rebuild, view_to_json
from tests import _rk_layer as rk
from tests.fixtures import loaders
from tests.gates.test_s1_zero_behavioural_change import PRE_S1_EXPECTED_VIEW_MD5
from tests.gates.test_s3_flag_off_equivalence import _pinned as _s3_off

# ── the LATER stage's flag is pinned off here too ────────────────────────────────────────────────
#
# This file measures **S2's** flag-off view, so every later stage flag must be held down while it does.
# Left ambient, the numbers below silently become "S2 off, S3 on" whenever the suite runs with
# ``--earned-identity=on``, and the S2 baseline stops meaning what its name says. Not hypothetical: with
# the S3 flag on the full-scenario node, edge and gap counts all move, so an unpinned S3 flag turns this
# gate red for a reason that has nothing to do with S2. Pinning is also what makes a flag-ON run useful —
# what it reports is then real S3 signal, not a stale S2 assertion misfiring.


def test_flag_off_rebuild_of_the_golden_logs_still_matches_the_recorded_view() -> None:
    """The recorded golden view is the S1 baseline; with the flag off a rebuild must still reproduce it.

    ``test_s1_zero_behavioural_change`` pins the *fixture file*'s md5; ``test_g2_determinism`` and
    ``tests/view/test_rebuild.py`` compare a rebuild against that fixture. This restates the pair as one
    assertion so a reader of S2 can see the safety property in one place, and so the md5 constant is *used*
    rather than merely present.
    """
    view = rebuild(
        loaders.golden_evidence_log(), loaders.golden_decision_log(),
        _s3_off(loaders.golden_config_store().snapshot()),
    )
    recorded = loaders.expected_view_json()

    assert hashlib.md5(recorded.encode("utf-8")).hexdigest() == PRE_S1_EXPECTED_VIEW_MD5, (
        "expected_view.json was re-recorded during S2 — the golden regenerates at RK-NAMECUT (S4), not here "
        "(plan §9); with the flag off S2 must not move the graph at all"
    )
    # The committed expected_view.json is written with a trailing newline (see test_g2_determinism).
    assert view_to_json(view) + "\n" == recorded, (
        "a flag-off rebuild of the golden logs no longer reproduces expected_view.json — S2's flag-off "
        "behaviour must be byte-identical to S1 (session file, 'THE INVARIANT FLIPS'). Do NOT re-record the "
        "fixture to match: the safety property is the point"
    )


# ── the surface that actually sees S2's config edits ─────────────────────────────────────────────

#: **Two valid real-corpus surfaces exist and this test deliberately pins the second one.** Both reproduce;
#: they measure different things, so a number only means something with its surface named (session file,
#: "THE INVARIANT FLIPS", resolved 2026-07-25):
#:
#:   * **booted app** (``build_default_state().boot()``) — 160 nodes / 73 edges / 18 gaps / 450 claims, hash
#:     ``22d668a3…dac3a9``: what the running system serves. It **deliberately withholds**
#:     ``d18_rahwali_pass1`` + ``d19_rahwali_confirm`` from the boot seed, to be ingested live for the demo.
#:   * **full scenario via ``eval.harness``** — the values below: every claim, nothing withheld.
#:
#: The harness surface is this gate for a load-bearing reason: **the two withheld documents are exactly the
#: flagship relocation pair**, so a flag-off assertion measured on the *booted* view is structurally blind to
#: the relocation/supersede path S2 changes most (scope items 5–7 — the ``site_type`` re-key, the
#: ``co_instances`` carry-forward, the R1.4 promotion fix). The booted number stays useful as an integration
#: check; it cannot be the gate. Measured on this worktree at the S2 baseline
#: (``design/resolution-redesign``, after the S1 merge); view md5 ``14ccc45c9f702763a1e27b9900bb56db``.
CORPUS_BASELINE = {"node_count": 169, "edge_count": 80, "event_count": 71, "known_gap_count": 20}


@pytest.mark.parametrize("metric", sorted(CORPUS_BASELINE))
def test_flag_off_leaves_the_real_corpus_graph_unchanged(metric: str) -> None:
    """Flag OFF over the **shipped** config: adding layer tags, ``operated-by``, the customs edge and the
    site_type re-key must not move the graph by themselves.

    This is the only assertion in the suite that can see a config-only regression. Parametrized per metric so
    a failure names *what* moved (a new predicate that starts drawing edges reads very differently from a
    re-key that splits an instance).

    A legitimate corpus regeneration (RK-DATA, plan §10) moves these numbers — re-record them **with a ledger
    entry**, exactly as for the golden md5, and never to make a flag-off change go green.
    """
    from eval import harness

    if not harness.bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {harness.bundles_dir()}")

    inp = harness.load_scenario()
    view = rebuild(inp.evidence, [], _s3_off(inp.config_store.snapshot()))
    got = view.meta.get(metric)

    assert got == CORPUS_BASELINE[metric], (
        f"with the S2 flag off the real-corpus {metric} moved from {CORPUS_BASELINE[metric]} to {got} — "
        "flag OFF must be byte-identical to S1 (session file, 'THE INVARIANT FLIPS'). Config-only edits "
        "(layer tags, new predicates, the site_type re-key) are exactly the changes that can move this "
        "surface while every fixture stays green"
    )


def test_the_shipped_config_still_loads_and_rebuilds_after_the_ontology_edits() -> None:
    """A cheap arrival guard: S2 edits ``config/ontology.yaml`` under a loader that **rejects** unknown
    shapes at the typed fields, and a malformed edit would surface as a boot failure rather than a test.

    Plan §5a-bis: "a bare string in ``attrs`` is now a **loud validation error**" — the same loudness must not
    become a boot break.
    """
    bundle = rk.shipped_bundle()

    assert bundle.ontology.node_types and bundle.ontology.edge_types, (
        "the shipped ontology loaded empty — an S2 edit broke the file's shape"
    )
    view = rk.build_view(rk.fixture_config(flag_on=False), [
        rk.entity_claim("n1", bundle.ontology.node_types[0].name, name="Alpha"),
    ])
    assert view.nodes, "rebuild over the shipped ontology produced no nodes"
