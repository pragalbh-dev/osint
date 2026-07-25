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

**But the pass ships OFF.** ``ingest.coref._coref_cfg`` early-returns ``{}`` — no second call, no
clusters, no referent ids — unless :data:`FLAG` is on, and the shipped config sets it ``false``. So the
channel exists and is *dormant*, which is a different failure from "does not exist" and needs a
different answer: turn the flag on for the bake-off run, or say plainly that the top-weighted criterion
was not measured. What must never happen is the third option — quietly dropping ``coref_binding`` from
``required_metrics`` so the run goes green with the measurement missing.

**Both halves of the substrate are checked, and both before the first API call.** :func:`require` covers
the system side (is the channel switched on?); :func:`require_gold_labels` covers the reference side (does
the labeled slice carry clusters to score against?). Either one missing makes the measurement impossible,
and discovering that *after* N paid runs per candidate buys nothing.

Nothing here mutates config on disk. :func:`with_channel_on` returns a flag-on **copy** for a driver to
hand the runner, and it is a function the caller invokes deliberately — the harness never flips the flag on
the operator's behalf, because a second extraction call per document is a real cost and a real behaviour
change, and that is the operator's call to make explicitly.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

#: The single config flag that decides whether extraction pass 2 runs at all. Both switches (the
#: producer block in ``credibility.coreference`` and the consumer policy in ``resolution``) key off it.
FLAG = "resolution.earned_identity.enabled"

#: The block :data:`FLAG` lives in, on ``ConfigBundle.resolution``.
_EARNED_IDENTITY_KEY = "earned_identity"

#: The metric whose substrate this channel is. Named here so the precondition and the report agree.
METRIC = "coref_binding"


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

    @property
    def measurable(self) -> bool:
        """A live channel with at least one permitted category — the precondition for scoring."""
        return self.live and bool(self.categories)


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


def inspect(config: Any) -> CorefChannel:
    """Read the run's :class:`~chanakya.schemas.ConfigBundle` and say whether the channel is live."""
    tool_name, cluster_field = _schema_cluster_field()
    if tool_name is None or cluster_field is None:
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            detail=("no mention-cluster field exists in any model-facing extraction tool schema — "
                    "every candidate would emit the same empty clustering, so scoring it would "
                    "measure the schema, not the model"),
        )

    from chanakya.ingest import coref

    cfg = coref._coref_cfg(config)
    categories = coref._categories(cfg) if cfg else ()
    if not cfg:
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            detail=(f"the {tool_name!r} tool exists (schema field {cluster_field}) but extraction pass 2 "
                    f"is DORMANT on this config: {FLAG} is off, so the call is never dispatched and no "
                    f"claim carries a referent_id. {METRIC} is unmeasurable until it is turned on — "
                    "which costs a second extraction call per document, and is the operator's call"),
        )
    if not categories:
        return CorefChannel(
            live=False, tool_name=tool_name, cluster_field=cluster_field, categories=(),
            detail=(f"{FLAG} is on but credibility.coreference.categories is empty — this deployment "
                    "permits no evidence kind, so the pass emits nothing. That is dormancy stated a "
                    "second way, not a model result"),
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

    Raises when ``coref_binding`` is declared required and the channel is dormant, because the
    alternative — running N extractions per candidate and *then* reporting INSUFFICIENT_CRITERIA — pays
    for a measurement that was structurally impossible before the first call went out. The error names
    the flag rather than flipping it.
    """
    channel = inspect(config)
    required = tuple(getattr(bakeoff_config, "required_metrics", ()) or ())
    if METRIC in required and not channel.measurable:
        raise CorefChannelDormant(
            f"{METRIC} is declared in required_metrics but cannot be measured on this config: "
            f"{channel.detail}. Either run with {FLAG}: true (note it ships false, and turning it on "
            f"adds a second extraction call per document), or remove {METRIC} from required_metrics as "
            "a deliberate, recorded decision to rank without the top-weighted criterion. Do not "
            "re-weight it to zero — that turns an honest gap into a silent one."
        )
    return channel


def require_gold_labels(gold: Iterable[Any], bakeoff_config: Any) -> None:
    """The other half of the same precondition: does the labeled slice carry clusters to score against?

    Binding needs both sides — a system clustering *and* a gold one. The flag check above covers the system
    side; this covers the reference side, and for the same reason: discovering it after N paid runs buys a
    measurement that was impossible before the first call. Nothing here reads a *value* — only whether any
    labeled claim carries a cluster label at all, which is a property of the file's completeness, not of
    its answers.

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


__all__ = ["FLAG", "METRIC", "CorefChannel", "CorefChannelDormant", "inspect", "require",
           "require_gold_labels", "with_channel_on"]
