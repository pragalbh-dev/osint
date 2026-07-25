"""TASK 4 — the coref precondition works in BOTH worlds: flag-gated, and flag deleted.

Why this file exists. ``eval.extraction.coref_channel`` guards the top-weighted, declared-required criterion
``coref_binding`` *before* any API budget is spent. It used to ask "is ``resolution.earned_identity.enabled``
on?", and a parallel effort is **deleting that flag** so the identity machinery — the coreference producer
included — becomes unconditional (a switch that can be turned off is backward compatibility). A precondition
written around the flag would then either refuse forever or have to be deleted along with it, and a
precondition that has to be deleted is one nobody will re-derive.

So the check now asks the durable question — *could a candidate express a coreference decision on this run's
config, and if not, why not?* — and answers with one of four **causes**. Only ``gated_off`` is about a flag.
These tests pin both halves of the requirement:

* with the pass unconditional (the flag's effect removed), the precondition **passes** and nothing refuses;
* when the channel is genuinely unavailable for a reason that is *not* the flag, it still **refuses before
  any spend** — and names the right remedy.

THE FLAG-DELETION SEAM, precisely (also stated in the module docstring):

    eval/extraction/coref_channel.py   FLAG, _EARNED_IDENTITY_KEY, GATED_OFF, the ``if not cfg:`` branch in
                                       ``inspect`` that returns GATED_OFF, the GATED_OFF entry in _REMEDY,
                                       and ``with_channel_on``
    tests                              ``test_the_shipped_config_leaves_the_coref_channel_dormant_and_names
                                       _the_flag`` and ``test_switching_the_channel_on_is_an_in_memory_flip
                                       _that_actually_takes`` (test_secrets_coref_and_vlm.py),
                                       ``test_a_required_coref_metric_refuses_before_any_budget_is_spent``
                                       (test_runner_e2e.py), and ``test_the_gated_off_cause_is_the_seam``
                                       below

Nothing else reads the flag. ``inspect`` asks the *pipeline* whether it would dispatch pass 2, so an
unconditional pass reports LIVE without a line of the module changing.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from eval.extraction import coref_channel

from .fixtures import bakeoff_config

REQUIRED = "coref_binding"


@pytest.fixture
def shipped_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


@pytest.fixture
def unconditional(monkeypatch: pytest.MonkeyPatch):
    """Simulate the world after the flag is deleted: pass 2 is dispatched whenever the producer is declared.

    This is exactly what the deletion does to ``ingest.coref._coref_cfg`` — drop the early return that reads
    ``resolution.earned_identity.enabled`` and hand back ``credibility.coreference``. Patching the pipeline
    function rather than the config is the point: it proves the precondition follows the *pipeline's* answer
    and holds no opinion of its own about a flag.
    """
    from chanakya.ingest import coref

    def _unconditional(config: Any) -> dict[str, Any]:
        return dict(getattr(config.credibility, "coreference", None) or {})

    monkeypatch.setattr(coref, "_coref_cfg", _unconditional)
    return _unconditional


# ── world 2: the flag is gone and the channel is unconditional ─────────────────────────────────────

def test_with_the_pass_unconditional_the_channel_is_live_on_the_shipped_config(
        shipped_config, unconditional) -> None:
    """The flag is still FALSE on disk here. The precondition must not care: what matters is whether the
    extraction path would dispatch pass 2, and unconditionally it would."""
    channel = coref_channel.inspect(shipped_config)
    assert channel.live and channel.measurable
    assert channel.cause == ""
    assert channel.tool_name == "cluster_coreferences"
    assert "EXPLICIT_EQUIVALENCE" in channel.categories


def test_with_the_pass_unconditional_the_precondition_passes_and_does_not_refuse(
        shipped_config, unconditional) -> None:
    """The whole risk of the flag deletion: a guard that kept refusing would block the bake-off outright."""
    channel = coref_channel.require(shipped_config, bakeoff_config(required_metrics=[REQUIRED]))
    assert channel.measurable


def test_no_flag_flipping_is_needed_once_the_pass_is_unconditional(shipped_config, unconditional) -> None:
    """``with_channel_on`` becomes a no-op with nothing to switch — which is why it is a seam to delete
    rather than machinery to extend. The precondition must reach the same verdict either way."""
    plain = coref_channel.inspect(shipped_config)
    flipped = coref_channel.inspect(coref_channel.with_channel_on(shipped_config))
    assert plain.measurable and flipped.measurable
    assert plain.cause == flipped.cause == ""


# ── world 1 and world 2 alike: a genuine unavailability still refuses before any spend ──────────────

def test_a_missing_schema_field_refuses_even_when_the_pass_is_unconditional(
        shipped_config, unconditional, monkeypatch) -> None:
    """S3 reverted, or the pass-2 model changed: there is no mention-cluster field to fill, so every
    candidate would return the same empty clustering and the metric would measure our schema."""
    from pydantic import BaseModel

    from chanakya.ingest import coref

    class NoClusters(BaseModel):
        contrasts: list[str] = []

    monkeypatch.setattr(coref, "CoreferenceClusters", NoClusters)

    channel = coref_channel.inspect(shipped_config)
    assert channel.cause == coref_channel.NO_SCHEMA_FIELD and not channel.measurable
    with pytest.raises(coref_channel.CorefChannelDormant) as excinfo:
        coref_channel.require(shipped_config, bakeoff_config(required_metrics=[REQUIRED]))
    assert coref_channel.NO_SCHEMA_FIELD in str(excinfo.value)
    assert "No operator action can fix this" in str(excinfo.value)


def test_an_unconfigured_producer_refuses_and_names_the_config_gap_not_a_flag(
        shipped_config, unconditional) -> None:
    """The cause the old flag-shaped message got WRONG, in both worlds: ``credibility.coreference`` absent or
    empty is a config gap with nothing to do with any switch, and reporting it as "the flag is off" sends the
    operator to the wrong file. After the deletion there is no flag to send them to at all."""
    credibility = shipped_config.credibility.model_copy(update={"coreference": {}})
    stripped = shipped_config.model_copy(update={"credibility": credibility})

    channel = coref_channel.inspect(stripped)
    assert channel.cause == coref_channel.PRODUCER_UNCONFIGURED and not channel.measurable
    assert coref_channel.FLAG not in channel.detail
    assert coref_channel.FLAG not in channel.remedy
    assert "credibility.coreference" in channel.remedy

    with pytest.raises(coref_channel.CorefChannelDormant, match="declares no coreference producer"):
        coref_channel.require(stripped, bakeoff_config(required_metrics=[REQUIRED]))


def test_a_producer_that_permits_no_category_refuses_in_both_worlds(shipped_config,
                                                                    unconditional) -> None:
    """An explicitly empty category list means "emit nothing" and is never read as "emit everything"."""
    credibility = shipped_config.credibility.model_copy(update={"coreference": {"categories": []}})
    silenced = shipped_config.model_copy(update={"credibility": credibility})

    channel = coref_channel.inspect(silenced)
    assert channel.cause == coref_channel.NO_CATEGORIES and not channel.measurable
    with pytest.raises(coref_channel.CorefChannelDormant, match="name at least one category"):
        coref_channel.require(silenced, bakeoff_config(required_metrics=[REQUIRED]))


def test_an_unlabeled_gold_slice_still_refuses_whatever_the_channel_does(shipped_config,
                                                                        unconditional) -> None:
    """The reference half of the precondition is flag-independent and stays exactly as it was: a live channel
    scored against a slice with no cluster labels is still an impossible measurement."""
    from types import SimpleNamespace

    required = bakeoff_config(required_metrics=[REQUIRED])
    assert coref_channel.require(shipped_config, required).measurable      # system side is fine
    with pytest.raises(coref_channel.CorefChannelDormant, match="no coref_cluster labels"):
        coref_channel.require_gold_labels([SimpleNamespace(coref_cluster=None)], required)


# ── the weighting must not be quietly relaxed to make any of this easier ───────────────────────────

def test_coref_binding_stays_required_and_top_weighted() -> None:
    """The tempting shortcut through all of the above is to drop the criterion or zero its weight. Both turn
    an honest gap into a silent one, so the shipped config is held to it here."""
    from eval.extraction.policy import load_bakeoff_config

    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert REQUIRED in cfg.required_metrics
    assert cfg.weight_for(REQUIRED) == max(cfg.weights.values())


def test_the_refusal_never_flips_anything_itself(shipped_config) -> None:
    """Turning the pass on costs a second extraction call per document. While that is still a choice, it is
    the operator's — the guard names the remedy and leaves the config alone."""
    from chanakya.ingest import coref

    before = coref._coref_cfg(shipped_config)
    with pytest.raises(coref_channel.CorefChannelDormant):
        coref_channel.require(shipped_config, bakeoff_config(required_metrics=[REQUIRED]))
    assert coref._coref_cfg(shipped_config) == before


# ── the seam, asserted so its removal is mechanical rather than archaeological ─────────────────────

def test_the_gated_off_cause_is_the_seam(shipped_config) -> None:
    """DELETE WITH THE FLAG. While the flag exists, a configured-but-gated producer is ``gated_off`` and the
    remedy names the flag. Once pass 2 is unconditional this cause is unreachable — ``_coref_cfg`` will
    return the declared block — and this test goes with it. Nothing else in the module needs to change.
    """
    channel = coref_channel.inspect(shipped_config)
    assert channel.cause == coref_channel.GATED_OFF
    assert coref_channel.FLAG in channel.remedy
    assert "second extraction call per document" in channel.remedy
