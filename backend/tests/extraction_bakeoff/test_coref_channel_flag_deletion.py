"""TASK 4 — the coref precondition, after the staging flag it used to read was deleted.

Why this file exists. ``eval.extraction.coref_channel`` guards the top-weighted, declared-required criterion
``coref_binding`` *before* any API budget is spent. It used to ask "is ``resolution.earned_identity.enabled``
on?", and ``design/resolution-redesign`` **deleted that flag** so the identity machinery — the coreference
producer included — is unconditional (a switch that can be turned off is backward compatibility). A
precondition written around the flag would by now either refuse forever or have had to be deleted along with
it, and a precondition that has to be deleted is one nobody will re-derive.

So the check asks the durable question — *could a candidate express a coreference decision on this run's
config, and if not, why not?* — and answers with one of three **causes**, none of which is a switch. These
tests pin both halves of the requirement:

* on the shipped config the pass is unconditional, so the precondition **passes** and nothing refuses;
* when the channel is genuinely unavailable, it still **refuses before any spend** — and names the right
  remedy.

THE SEAM, EXECUTED (2026-07-26). Deleted with the flag, exactly as the module said and nothing more:
``FLAG``, ``_EARNED_IDENTITY_KEY``, the ``GATED_OFF`` cause with its ``inspect`` branch and ``_REMEDY``
entry, and ``with_channel_on``. What replaced the last of those is ``without_channel``, and the direction
reversal is the whole point: with pass 2 unconditional the operator can no longer switch it *on*, so the
decision that remains is whether to decline to pay for it (``--no-coref``). Dormancy is therefore
constructed here the way an operator can still construct it, never through a flag.
"""

from __future__ import annotations

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from eval.extraction import coref_channel

from .fixtures import bakeoff_config

REQUIRED = "coref_binding"


@pytest.fixture
def shipped_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


# ── the pass is unconditional: the channel is live with nothing switched ───────────────────────────

def test_the_channel_is_live_on_the_shipped_config_with_no_flag_flipping(shipped_config) -> None:
    """The property the flag deletion had to deliver. The precondition holds no opinion about a flag: what
    matters is whether the extraction path would dispatch pass 2, and unconditionally it would."""
    channel = coref_channel.inspect(shipped_config)
    assert channel.live and channel.measurable
    assert channel.cause == ""
    assert channel.tool_name == "cluster_coreferences"
    assert "EXPLICIT_EQUIVALENCE" in channel.categories


def test_the_precondition_passes_and_does_not_refuse(shipped_config) -> None:
    """The whole risk of the flag deletion: a guard that kept refusing would block the bake-off outright —
    every run would return INSUFFICIENT_CRITERIA on a criterion that is in fact measurable."""
    channel = coref_channel.require(shipped_config, bakeoff_config(required_metrics=[REQUIRED]))
    assert channel.measurable


def test_no_flag_survives_in_the_precondition_at_all(shipped_config) -> None:
    """The seam is executed, not left dangling: the deleted names are gone from the module surface, so a
    reader cannot resurrect a switch by importing one."""
    assert not hasattr(coref_channel, "FLAG")
    assert not hasattr(coref_channel, "GATED_OFF")
    assert not hasattr(coref_channel, "with_channel_on")
    assert "earned_identity" not in coref_channel.inspect(shipped_config).detail


# ── a genuine unavailability still refuses before any spend ────────────────────────────────────────

def test_a_missing_schema_field_refuses(shipped_config, monkeypatch) -> None:
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


def test_an_unconfigured_producer_refuses_and_names_the_config_gap_not_a_flag(shipped_config) -> None:
    """The cause the old flag-shaped message got WRONG: ``credibility.coreference`` absent or empty is a
    config gap with nothing to do with any switch, and reporting it as "the flag is off" sent the operator
    to the wrong file. After the deletion there is no flag to send them to at all."""
    credibility = shipped_config.credibility.model_copy(update={"coreference": {}})
    stripped = shipped_config.model_copy(update={"credibility": credibility})

    channel = coref_channel.inspect(stripped)
    assert channel.cause == coref_channel.PRODUCER_UNCONFIGURED and not channel.measurable
    assert "earned_identity" not in channel.detail
    assert "earned_identity" not in channel.remedy
    assert "credibility.coreference" in channel.remedy

    with pytest.raises(coref_channel.CorefChannelDormant, match="declares no coreference producer"):
        coref_channel.require(stripped, bakeoff_config(required_metrics=[REQUIRED]))


def test_declining_to_pay_for_pass_two_is_the_same_refusal(shipped_config) -> None:
    """``--no-coref`` is the only lever left, and it must not invent a fourth dormancy: suppressing the
    producer block reads as the config gap it literally is, and still refuses before any spend."""
    suppressed = coref_channel.without_channel(shipped_config)
    channel = coref_channel.inspect(suppressed)
    assert channel.cause == coref_channel.PRODUCER_UNCONFIGURED and not channel.measurable
    assert "--no-coref" in channel.remedy
    with pytest.raises(coref_channel.CorefChannelDormant):
        coref_channel.require(suppressed, bakeoff_config(required_metrics=[REQUIRED]))


def test_a_producer_that_permits_no_category_refuses(shipped_config) -> None:
    """An explicitly empty category list means "emit nothing" and is never read as "emit everything"."""
    credibility = shipped_config.credibility.model_copy(update={"coreference": {"categories": []}})
    silenced = shipped_config.model_copy(update={"credibility": credibility})

    channel = coref_channel.inspect(silenced)
    assert channel.cause == coref_channel.NO_CATEGORIES and not channel.measurable
    with pytest.raises(coref_channel.CorefChannelDormant, match="name at least one category"):
        coref_channel.require(silenced, bakeoff_config(required_metrics=[REQUIRED]))


def test_an_unlabeled_gold_slice_still_refuses_whatever_the_channel_does(shipped_config) -> None:
    """The reference half of the precondition was always flag-independent and stays exactly as it was: a
    live channel scored against a slice with no cluster labels is still an impossible measurement."""
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


def test_the_refusal_never_changes_the_config_itself(shipped_config) -> None:
    """Pass 2 costs a second extraction call per document. Where a run has declined that cost, the guard
    names the remedy and leaves the bundle exactly as it found it — it never buys the call back."""
    from chanakya.ingest import coref

    suppressed = coref_channel.without_channel(shipped_config)
    before = coref._coref_cfg(suppressed)
    with pytest.raises(coref_channel.CorefChannelDormant):
        coref_channel.require(suppressed, bakeoff_config(required_metrics=[REQUIRED]))
    assert coref._coref_cfg(suppressed) == before
