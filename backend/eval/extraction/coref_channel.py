"""Is there a model-facing coreference **output channel** at all? — the coref-binding precondition.

**What this closes.** The first integration pass concluded coref-binding could not be scored, and the
reason was not "no gold" (the labeled slice carries clusters). It was that no field in any tool schema
the extraction path sends to a model asked for a mention clustering, so every candidate would return
the same empty clustering and the metric would have measured *our schema*, not the model.

**Stage S3 (RK-COREF) changed that.** Extraction now has a **pass 2**: a second forced-tool call per
document (:data:`chanakya.ingest.coref.TOOL_NAME` = ``cluster_coreferences``) whose schema carries
``clusters[].member_ids`` — a real mention-cluster field, filled by the model, whose accepted clusters
mint a referent atom that is stamped onto pass 1's own entity claims as ``ClaimRecord.referent_id``.
That is exactly the substrate ``metrics.coref_binding`` reads, so the metric now has something to score.

**Both halves of the substrate are checked, and both before the first API call.** :func:`require` covers
the system side (can the extraction path express a clustering on this config?); :func:`require_gold_labels`
covers the reference side (does the labeled slice carry clusters to score against?). Either one missing
makes the measurement impossible, and discovering that *after* N paid runs per candidate buys nothing.

WHY THIS ASKS "IS THE CHANNEL AVAILABLE", NOT "IS THE FLAG ON"
──────────────────────────────────────────────────────────────
Pass 2 **used** to ship dormant behind ``resolution.earned_identity.enabled``, and this module was written
with a marked seam so the flag's deletion would be mechanical. That deletion landed
(``design/resolution-redesign``, merged 2026-07-26): the identity machinery — the coreference producer
included — is now unconditional, and the seam has been executed. A precondition written as "is the flag on?"
would by now either refuse forever or have had to be deleted along with it; the one written here needed one
line removed.

The question this module asks is the durable one: *could a candidate express a coreference decision on
this run's config, and if not, why not?* :attr:`CorefChannel.cause` answers that as one of three causes,
each with a different remedy, and none of them is about a switch:

* :data:`NO_SCHEMA_FIELD`  — the pass-2 tool has no mention-cluster field (S3 reverted, or the model
  changed). Nothing an operator can switch; the metric is unmeasurable.
* :data:`PRODUCER_UNCONFIGURED` — ``credibility.coreference`` is absent or empty, so the producer has no
  knobs at all. This is a genuine unavailability, and it is the case the old flag-shaped message reported
  wrongly. It is now also what :func:`without_channel` produces when an operator deliberately declines to
  pay for pass 2.
* :data:`NO_CATEGORIES` — configured, but permitting no evidence kind, so the pass emits nothing.

Every cause refuses before any budget is spent. What must never happen is the third option — quietly
dropping ``coref_binding`` from ``required_metrics`` so the run goes green with the measurement missing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

#: The block the coreference producer's knobs live in, on ``ConfigBundle.credibility``. Named once so
#: :func:`_producer_block` and :func:`without_channel` cannot disagree about which block is the switch.
_PRODUCER_KEY = "coreference"

#: The metric whose substrate this channel is. Named here so the precondition and the report agree.
METRIC = "coref_binding"

Cause = Literal["", "no_schema_field", "producer_unconfigured", "no_categories"]

#: The three reasons a channel can be unavailable. None of them is a flag — see the module docstring.
#: Annotated as :data:`Cause` so a cause that is not one of the three fails at the constant rather than
#: at the call site: an unrecognised cause has no remedy, and a refusal with no remedy is the shape that
#: tempts an operator to drop the criterion instead of fixing it.
NO_SCHEMA_FIELD: Cause = "no_schema_field"
PRODUCER_UNCONFIGURED: Cause = "producer_unconfigured"
NO_CATEGORIES: Cause = "no_categories"

#: Per-cause remedy, appended to the refusal so an operator is told what would actually fix it. Keyed by
#: cause rather than baked into one sentence, because the three remedies are genuinely different and a
#: message that names a flag for a cause that is not about a flag sends the operator to the wrong file.
_REMEDY: dict[Cause, str] = {
    NO_SCHEMA_FIELD: (
        "No operator action can fix this: the extraction path has no mention-cluster field to fill, so no "
        f"candidate can express a binding. Either restore the pass-2 tool schema or remove {METRIC} from "
        "required_metrics as a deliberate, recorded decision to rank without the top-weighted criterion."
    ),
    PRODUCER_UNCONFIGURED: (
        "The producer block `credibility.coreference` is absent or empty, so the pass has no knobs to run "
        "with. Populate it (categories, max_mentions) — this is a config gap, not a switch. If this run "
        "asked for it (--no-coref suppresses the block to save a second extraction call per document), "
        f"that is the cost decision working: drop --no-coref, or remove {METRIC} from required_metrics as "
        "a deliberate, recorded decision."
    ),
    NO_CATEGORIES: (
        "`credibility.coreference.categories` permits no evidence kind, so the pass would emit nothing. An "
        "explicitly empty list means 'emit nothing' and is never read as 'emit everything'; name at least "
        "one category."
    ),
}


@dataclass(frozen=True)
class CorefChannel:
    """Whether a candidate could express a coreference decision on this run's config."""

    #: Does the extraction path actually dispatch the pass-2 call?
    live: bool
    #: The model-facing tool the clustering rides on (``None`` when the pass is not compiled in).
    tool_name: str | None
    #: The dotted path of the mention-cluster field inside that tool's schema.
    cluster_field: str | None
    #: Which evidence categories this deployment allows the model to claim.
    categories: tuple[str, ...]
    #: Human-readable statement of what was found, printed above any coref number.
    detail: str
    #: Machine-readable reason it is unavailable — ``""`` when live. See the module docstring.
    cause: Cause = ""

    @property
    def measurable(self) -> bool:
        """A live channel with at least one permitted category — the precondition for scoring."""
        return self.live and bool(self.categories)

    @property
    def remedy(self) -> str:
        return _REMEDY.get(self.cause, "")


def _schema_cluster_field() -> tuple[str | None, str | None]:
    """``(tool_name, cluster_field)`` read off the real pass-2 schema, or ``(None, None)``.

    Read from the shipped module rather than hardcoded, so this reports what the extraction path would
    actually send. If S3 were reverted, this goes back to ``(None, None)`` on its own.
    """
    try:
        from chanakya.ingest import coref
    except Exception:
        return None, None
    tool = getattr(coref, "TOOL_NAME", None)
    model = getattr(coref, "CoreferenceClusters", None)
    if tool is None or model is None:
        return None, None
    try:
        schema = model.model_json_schema()
    except Exception:
        return tool, None
    props = schema.get("properties")
    if not isinstance(props, dict) or "clusters" not in props:
        return tool, None
    defs = schema.get("$defs")
    member = "member_ids"
    if isinstance(defs, dict):
        cluster_def = defs.get("CoreferenceCluster")
        cluster_props = cluster_def.get("properties") if isinstance(cluster_def, dict) else None
        if not isinstance(cluster_props, dict) or member not in cluster_props:
            return tool, None
    return tool, f"clusters[].{member}"


def _producer_block(config: Any) -> dict[str, Any]:
    """``credibility.coreference`` as a plain dict — the producer's own knobs, read WITHOUT any gate.

    This is what separates "the deployment never configured the producer" from "something is switching the
    pass off", and it is why the refusal can name the right file in both worlds. It reads the same attribute
    ``chanakya.ingest.coref._coref_cfg`` reads *after* its gate, so the two cannot disagree about what
    "configured" means.
    """
    credibility = getattr(config, "credibility", None)
    return dict(getattr(credibility, _PRODUCER_KEY, None) or {})


def inspect(config: Any) -> CorefChannel:
    """Read the run's :class:`~chanakya.schemas.ConfigBundle` and say whether the channel is live.

    Deliberately asks the *pipeline* whether it would dispatch pass 2 (``coref._coref_cfg``) rather than
    reading any config key itself. That is what made this correct across the flag's deletion: it kept
    answering the pipeline's own question, so the day the pass became unconditional the same call started
    returning the producer block and the channel started reporting LIVE.
    """
    tool_name, cluster_field = _schema_cluster_field()
    if tool_name is None or cluster_field is None:
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            cause=NO_SCHEMA_FIELD,
            detail=("no mention-cluster field exists in any model-facing extraction tool schema — "
                    "every candidate would emit the same empty clustering, so scoring it would "
                    "measure the schema, not the model"),
        )

    from chanakya.ingest import coref

    declared = _producer_block(config)
    cfg = coref._coref_cfg(config)
    categories = coref._categories(cfg) if cfg else ()

    if not cfg or not declared:
        # A genuine unavailability that has nothing to do with any switch: this deployment does not declare
        # the producer. Reporting this as "the flag is off" (as this module used to) sent an operator to the
        # wrong file, and would keep doing so now that no flag exists. `cfg` and `declared` can no longer
        # disagree — `_coref_cfg` returns the declared block verbatim — so either being empty is the same
        # fact, and asking about both is what keeps this honest if the pipeline ever re-acquires a gate.
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            cause=PRODUCER_UNCONFIGURED,
            detail=(f"the {tool_name!r} tool exists (schema field {cluster_field}) but this deployment "
                    "declares no coreference producer at all: `credibility.coreference` is absent or "
                    f"empty, so pass 2 has nothing to run with and {METRIC} is unmeasurable"),
        )
    if not categories:
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            cause=NO_CATEGORIES,
            detail=("pass 2 would be dispatched but `credibility.coreference.categories` is empty — this "
                    "deployment permits no evidence kind, so the pass emits nothing. That is dormancy "
                    "stated a second way, not a model result"),
        )
    return CorefChannel(
        live=True, tool_name=tool_name, cluster_field=cluster_field, categories=tuple(categories),
        detail=(f"extraction pass 2 is LIVE: each document gets a second forced call to {tool_name!r}, "
                f"whose {cluster_field} is the model's own mention clustering; accepted clusters mint "
                f"the referent atom that coref_binding scores. Permitted categories: "
                f"{', '.join(categories)}"),
    )


def without_channel(config: Any) -> Any:
    """The same pipeline config with extraction pass 2 suppressed, **in memory only**.

    This replaced ``with_channel_on`` when the flag died. The direction reversed for a real reason, not a
    cosmetic one: pass 2 is now unconditional, so the thing an operator can still decide is whether to
    *decline* to pay for it — it costs a second extraction call per document, which is close to half the
    bill of a run. ``--no-coref`` is that decision, and before the flag's deletion it had quietly become a
    lie: it set a variable the run then overwrote from the (now always-live) channel, so the run printed
    LIVE and spent the second call anyway.

    Suppression is expressed by emptying the producer block rather than by reintroducing a switch, because
    the producer block already *is* the declaration — an absent one is an honest "this deployment does not
    run the second extraction pass", and :func:`inspect` already reports exactly that as
    :data:`PRODUCER_UNCONFIGURED`. So a suppressed run refuses for the same reason and with the same
    message as a misconfigured one, and no new dormancy concept enters the harness.

    In memory only, and never called by :func:`inspect` or :func:`require`: editing ``config/`` would
    change the running system, the frozen-bundle baseline and every other session's graph to serve a
    measurement. What this also removes is the footgun the old helper removed — the block hangs off a
    nested config model, so the obvious ``model_copy(update={"credibility": dict(...)})`` replaces the
    model with a plain dict and the whole credibility config reads back empty.
    """
    credibility = config.credibility
    return config.model_copy(
        update={"credibility": credibility.model_copy(update={_PRODUCER_KEY: {}})})


class CorefChannelDormant(RuntimeError):
    """Raised when the bake-off requires ``coref_binding`` but no candidate could express one."""


def require(config: Any, bakeoff_config: Any) -> CorefChannel:
    """Check the precondition before any API budget is spent. Returns the channel when it holds.

    Raises when ``coref_binding`` is declared required and the channel is unavailable **for any of the four
    causes**, because the alternative — running N extractions per candidate and *then* reporting
    INSUFFICIENT_CRITERIA — pays for a measurement that was structurally impossible before the first call
    went out. The message carries the cause-specific remedy and never changes any config itself.

    Note what is *not* checked: whether a flag exists. A live channel satisfies this whether it is live
    because someone switched it on or because the pass is unconditional.
    """
    channel = inspect(config)
    required = tuple(getattr(bakeoff_config, "required_metrics", ()) or ())
    if METRIC in required and not channel.measurable:
        raise CorefChannelDormant(
            f"{METRIC} is declared in required_metrics but cannot be measured on this config "
            f"[{channel.cause}]: {channel.detail}. {channel.remedy} Do not re-weight it to zero — that "
            "turns an honest gap into a silent one."
        )
    return channel


def require_gold_labels(gold: Iterable[Any], bakeoff_config: Any, registry: Any = None) -> None:
    """The other half of the same precondition: does the labeled slice carry clusters to score against?

    Binding needs both sides — a system clustering *and* a gold one. The channel check above covers the
    system side; this covers the reference side, and for the same reason: discovering it after N paid runs
    buys a measurement that was impossible before the first call. Nothing here reads a *value* — only
    whether the labels and the registry that gives them meaning are both present, which is a property of
    the file's completeness, not of its answers.

    ``gold`` is the loaded slice as :func:`eval.extraction.gold.load_claim_gold` returns it — a sequence of
    :class:`~eval.extraction.surface.SurfaceClaim`. ``registry`` is
    :func:`eval.extraction.gold.load_coref_registry` over the same file.

    **Why the registry is a precondition and not an optional extra.** ``coref_cluster`` carries two
    opposite meanings — "one referent" on most rows, "hold these APART" on the rows the registry marks
    ANTI_COREF — and only the registry says which. A run scored without it credits an over-merge as a
    correct binding, which is the archetypal harm this project exists to prevent, and it does so silently.
    A cluster used by a labeled claim but absent from the registry is refused for the same reason: an
    unregistered tag is exactly the shape a renamed anti-coref cluster arrives in.
    """
    required = tuple(getattr(bakeoff_config, "required_metrics", ()) or ())
    if METRIC not in required:
        return
    used = {c for claim in gold if (c := getattr(claim, "coref_cluster", None))}
    if not used:
        raise CorefChannelDormant(
            f"{METRIC} is declared in required_metrics but the labeled slice carries no coref_cluster "
            "labels, so there is nothing to score a clustering against. Either the gold gains the labels "
            f"or {METRIC} comes out of required_metrics as a deliberate, recorded decision to rank without "
            "the top-weighted criterion. Do not re-weight it to zero — that turns an honest gap into a "
            "silent one."
        )
    if registry is None or not getattr(registry, "declared", False):
        raise CorefChannelDormant(
            f"{METRIC} is declared in required_metrics and the slice carries {len(used)} cluster label(s), "
            "but the gold declares no `coref_registry`, so nothing says which of those labels license a "
            "binding and which are ANTI_COREF traps that must be held apart. Scoring without it credits an "
            "over-merge as a correct binding — the archetypal harm — and does so silently. The gold must "
            "carry the registry."
        )
    unregistered = sorted(used - set(getattr(registry, "licensed", {})))
    if unregistered:
        raise CorefChannelDormant(
            f"{METRIC} is declared in required_metrics but the labeled claims use cluster tag(s) "
            f"{unregistered} that the gold's `coref_registry` does not declare, so their licensing "
            "decision is unknown. An unregistered tag is exactly the shape a renamed anti-coreference "
            "cluster arrives in, and guessing it licenses a binding is how a scorer starts paying for an "
            "over-merge."
        )


__all__ = ["METRIC", "NO_CATEGORIES", "NO_SCHEMA_FIELD", "PRODUCER_UNCONFIGURED",
           "Cause", "CorefChannel", "CorefChannelDormant", "inspect", "require",
           "require_gold_labels", "without_channel"]
