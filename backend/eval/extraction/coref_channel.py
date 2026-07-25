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
Pass 2 currently ships dormant behind :data:`FLAG`. That flag is being **deleted** by a parallel effort, so
the identity machinery — the coreference producer included — becomes unconditional; under the standing
directive a switch that can be turned off is backward compatibility. A precondition written as "is the flag
on?" would then either refuse forever or have to be deleted along with it.

So the question this module asks is the durable one: *could a candidate express a coreference decision on
this run's config, and if not, why not?* :attr:`CorefChannel.cause` answers that as one of four causes, each
with a different remedy — and only one of them, :data:`GATED_OFF`, is about a flag. In the unconditional
world that cause simply stops occurring and the other three keep doing their job:

* :data:`NO_SCHEMA_FIELD`  — the pass-2 tool has no mention-cluster field (S3 reverted, or the model
  changed). Nothing an operator can switch; the metric is unmeasurable.
* :data:`PRODUCER_UNCONFIGURED` — ``credibility.coreference`` is absent or empty, so the producer has no
  knobs at all. This is a genuine unavailability with **nothing to do with any flag**, and it is the case
  the old flag-shaped message reported wrongly.
* :data:`NO_CATEGORIES` — configured, but permitting no evidence kind, so the pass emits nothing.
* :data:`GATED_OFF` — configured and non-empty, yet the pipeline still declines to run the pass. Today that
  is exactly :data:`FLAG`. **This is the flag-deletion seam.**

Every cause refuses before any budget is spent. What must never happen is the third option — quietly
dropping ``coref_binding`` from ``required_metrics`` so the run goes green with the measurement missing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

# ══════════════════════════════════════════════════════════════════════════════════════════════════
# SEAM (flag deletion). Everything in this block is scheduled to die with
# `resolution.earned_identity.enabled`. When the flag goes, delete exactly these and nothing else:
#
#   * FLAG and _EARNED_IDENTITY_KEY (below)
#   * GATED_OFF and the branch in `inspect` that returns it
#   * the GATED_OFF entry in _REMEDY
#   * with_channel_on()
#
# Nothing else in this module reads the flag, by design: `inspect` asks the *pipeline* whether it would
# dispatch pass 2, so an unconditional pass reports LIVE without a line of this module changing.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

#: The single config flag that today decides whether extraction pass 2 runs at all. Both switches (the
#: producer block in ``credibility.coreference`` and the consumer policy in ``resolution``) key off it.
FLAG = "resolution.earned_identity.enabled"

#: The block :data:`FLAG` lives in, on ``ConfigBundle.resolution``.
_EARNED_IDENTITY_KEY = "earned_identity"

# ── end seam ──────────────────────────────────────────────────────────────────────────────────────

#: The metric whose substrate this channel is. Named here so the precondition and the report agree.
METRIC = "coref_binding"

#: The four reasons a channel can be unavailable. Only :data:`GATED_OFF` is about a flag.
NO_SCHEMA_FIELD = "no_schema_field"
PRODUCER_UNCONFIGURED = "producer_unconfigured"
NO_CATEGORIES = "no_categories"
GATED_OFF = "gated_off"

Cause = Literal["", "no_schema_field", "producer_unconfigured", "no_categories", "gated_off"]

#: Per-cause remedy, appended to the refusal so an operator is told what would actually fix it. Keyed by
#: cause rather than baked into one sentence, because the four remedies are genuinely different and a
#: message that names a flag for a cause that is not about a flag sends the operator to the wrong file.
_REMEDY: dict[str, str] = {
    NO_SCHEMA_FIELD: (
        "No operator action can fix this: the extraction path has no mention-cluster field to fill, so no "
        f"candidate can express a binding. Either restore the pass-2 tool schema or remove {METRIC} from "
        "required_metrics as a deliberate, recorded decision to rank without the top-weighted criterion."
    ),
    PRODUCER_UNCONFIGURED: (
        "The producer block `credibility.coreference` is absent or empty, so the pass has no knobs to run "
        "with. Populate it (categories, max_mentions) — this is a config gap, not a switch."
    ),
    NO_CATEGORIES: (
        "`credibility.coreference.categories` permits no evidence kind, so the pass would emit nothing. An "
        "explicitly empty list means 'emit nothing' and is never read as 'emit everything'; name at least "
        "one category."
    ),
    GATED_OFF: (
        f"The producer is configured but the pipeline still declines to dispatch pass 2 — today that is "
        f"{FLAG}, which ships false. Run with it true (it costs a second extraction call per document, "
        "which is the operator's call to make), or remove "
        f"{METRIC} from required_metrics as a deliberate, recorded decision."
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
    return dict(getattr(credibility, "coreference", None) or {})


def inspect(config: Any) -> CorefChannel:
    """Read the run's :class:`~chanakya.schemas.ConfigBundle` and say whether the channel is live.

    Deliberately asks the *pipeline* whether it would dispatch pass 2 (``coref._coref_cfg``) rather than
    reading any flag itself. That is what makes this correct in both worlds: while the flag exists a
    flag-off config reports :data:`GATED_OFF`; once the pass is unconditional the same call returns the
    producer block and the channel reports LIVE, with nothing here to change.
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

    if not cfg and not declared:
        # A genuine unavailability that has nothing to do with any switch: the deployment never configured
        # the producer. Reporting this as "the flag is off" (as this module used to) sends an operator to
        # the wrong file, and would keep doing so after the flag no longer exists.
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            cause=PRODUCER_UNCONFIGURED,
            detail=(f"the {tool_name!r} tool exists (schema field {cluster_field}) but this deployment "
                    "declares no coreference producer at all: `credibility.coreference` is absent or "
                    f"empty, so pass 2 has nothing to run with and {METRIC} is unmeasurable"),
        )
    if not cfg:
        # SEAM (flag deletion): unreachable once pass 2 is unconditional — `_coref_cfg` will then return
        # the declared block, so a non-empty `declared` can no longer coexist with an empty `cfg`.
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            cause=GATED_OFF,
            detail=(f"the {tool_name!r} tool exists (schema field {cluster_field}) and the producer IS "
                    "configured, but the extraction path still declines to dispatch pass 2, so no claim "
                    f"carries a referent_id and {METRIC} is unmeasurable. Today the gate is {FLAG}"),
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


def with_channel_on(config: Any) -> Any:
    """The same pipeline config with extraction pass 2 switched on, **in memory only**.

    SEAM (flag deletion): this helper exists only while :data:`FLAG` does. It is *not* the precondition —
    :func:`inspect` and :func:`require` never call it — so deleting it cannot weaken the check; it is a
    convenience for a driver that must measure the top-weighted criterion on a config that still ships the
    pass dormant. Once the pass is unconditional this becomes a no-op with nothing to switch, and it should
    be deleted along with the flag rather than left as a switch that can be turned off.

    The bake-off cannot measure the top-weighted criterion on the shipped config, and the fix is not to
    edit ``config/resolution.yaml`` — that would change the running system, the frozen-bundle baseline and
    every other session's graph to serve a measurement. So the driver flips the flag on the *bundle it
    hands the runner*, and this is that flip, in one place, spelled once.

    It is deliberately a function the caller invokes, never something :func:`inspect` or :func:`require`
    does on the caller's behalf: turning the flag on adds a second extraction call per document, and that
    cost is the operator's decision to take. What this removes is only the *footgun* — the flag lives on a
    nested config model, so the obvious ``model_copy(update={"resolution": dict(...)})`` silently replaces
    the model with a plain dict and the flag reads back off. That failure looks exactly like a dormant
    channel, i.e. like the answer the operator was trying to change.
    """
    resolution = config.resolution
    earned = {**dict(getattr(resolution, _EARNED_IDENTITY_KEY, None) or {}), "enabled": True}
    return config.model_copy(
        update={"resolution": resolution.model_copy(update={_EARNED_IDENTITY_KEY: earned})})


class CorefChannelDormant(RuntimeError):
    """Raised when the bake-off requires ``coref_binding`` but no candidate could express one."""


def require(config: Any, bakeoff_config: Any) -> CorefChannel:
    """Check the precondition before any API budget is spent. Returns the channel when it holds.

    Raises when ``coref_binding`` is declared required and the channel is unavailable **for any of the four
    causes**, because the alternative — running N extractions per candidate and *then* reporting
    INSUFFICIENT_CRITERIA — pays for a measurement that was structurally impossible before the first call
    went out. The message carries the cause-specific remedy and never flips anything itself.

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


def require_gold_labels(gold: Iterable[Any], bakeoff_config: Any) -> None:
    """The other half of the same precondition: does the labeled slice carry clusters to score against?

    Binding needs both sides — a system clustering *and* a gold one. The channel check above covers the
    system side; this covers the reference side, and for the same reason: discovering it after N paid runs
    buys a measurement that was impossible before the first call. Nothing here reads a *value* — only
    whether any labeled claim carries a cluster label at all, which is a property of the file's
    completeness, not of its answers.

    ``gold`` is the loaded slice as :func:`eval.extraction.gold.load_claim_gold` returns it — a sequence of
    :class:`~eval.extraction.surface.SurfaceClaim`.
    """
    required = tuple(getattr(bakeoff_config, "required_metrics", ()) or ())
    if METRIC not in required:
        return
    if any(getattr(c, "coref_cluster", None) for c in gold):
        return
    raise CorefChannelDormant(
        f"{METRIC} is declared in required_metrics but the labeled slice carries no coref_cluster labels, "
        "so there is nothing to score a clustering against. Either the gold gains the labels or "
        f"{METRIC} comes out of required_metrics as a deliberate, recorded decision to rank without the "
        "top-weighted criterion. Do not re-weight it to zero — that turns an honest gap into a silent one."
    )


__all__ = ["FLAG", "GATED_OFF", "METRIC", "NO_CATEGORIES", "NO_SCHEMA_FIELD", "PRODUCER_UNCONFIGURED",
           "Cause", "CorefChannel", "CorefChannelDormant", "inspect", "require",
           "require_gold_labels", "with_channel_on"]
