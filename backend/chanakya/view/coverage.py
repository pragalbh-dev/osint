"""Stage 4 (D11) — identity-resolution COVERAGE: the unresolved-identity tail as a collection gap.

The resolver's three-status identity axis (``confirmed`` / ``probable`` / ``possible`` —
:meth:`chanakya.schemas.Partition.identity_status`) is not merely a per-pair label; read in aggregate it
is a **coverage signal**. When a whole entity type keeps producing candidate (``probable``) and watch-list
(``possible``) identity links the resolver cannot CONFIRM — because the open sources never corroborate the
identity — that is not a resolver failure, it is a *collection gap*: the operator needs more evidence on
that type before those links can be confirmed. :func:`identity_coverage` names those types.

Pure and deterministic (no clock / RNG / network — gate G1): a fold over an already-computed
:class:`Partition` plus a ``type_of`` lookup. It **reports**, it draws nothing — the summary is served on
its own read-only route (``GET /coverage``), SEPARATE from the node/edge view, so the drawn view JSON
stays byte-identical (gate G2).

**Why the view side (not ``resolve/``):** the production threshold is config-driven — the route reads
``coverage_gap_ratio`` from ``config/resolution.yaml`` through :attr:`ResolveConfig.coverage_gap_ratio`
and no scoring literal lives in ``resolve/`` (gate G6). This module also carries a small *library* default
(:data:`DEFAULT_GAP_RATIO`) so the pure function is usable standalone (a direct programmatic call with no
config in hand still produces a sensible summary). That default is a plain constant, which is why the
module lives under ``view/`` — outside the G6 no-magic-numbers scan — rather than in ``resolve/``. Config
always wins when a caller passes ``cfg``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import Partition
from chanakya.schemas.base import Record

# ``type_of`` may be a plain callable ``entity_id -> type`` or a mapping; both are accepted (contract).
TypeOf = Callable[[str], "str | None"] | Mapping[str, str]

# Bucket for an identity link whose BOTH ends are untyped (the resolver could type neither). Deterministic
# and human-legible, never a silent drop — an unresolved link with no type is still coverage information.
UNKNOWN_TYPE = "unknown"

#: Library fallback gap ratio, used ONLY when a caller supplies neither ``cfg`` nor an explicit
#: ``coverage_gap_ratio``. Production reads the value from ``config/resolution.yaml`` (config is
#: authoritative); this keeps the pure function useful for a direct/programmatic call. Kept equal to the
#: shipped config default so the two agree. "Twice as many unconfirmable links as confirmed merges."
DEFAULT_GAP_RATIO = 2.0


class TypeCounts(Record):
    """Per-entity-type identity-link counts across the three status tiers (D4)."""

    confirmed: int = 0  # accepted merges (Partition.same_as) attributed to this type
    probable: int = 0  # HITL candidate same-as links (Partition.candidates)
    possible: int = 0  # retained sub-review watch-list links (Partition.possible)


class CoveragePolicy(Record):
    """The identity policy dials in force when the summary was computed — surfaced for transparency.

    An analyst reading a coverage report has to be able to see the settings that produced it: the bands
    that decided confirmed/probable/possible, the caps and floors, and the gap ratio behind
    ``collection_gaps``. Read from :class:`ResolveConfig`; a dial left unset reads as ``None``/its default.
    """

    possible_floor: float | None = None
    hitl_low: float | None = None
    auto_merge: float | None = None
    name_alone_caps_at_possible: bool = False
    critical_veto_min_grade: str | None = None
    surface_wall_bridges: bool = True
    coverage_gap_ratio: float | None = None


class IdentityCoverage(Record):
    """The identity-resolution coverage summary (Stage 4 / D11) — a report, never a drawn element."""

    #: Overall counts across the whole partition.
    confirmed: int = 0  # number of confirmed identity links / merged pairs (len Partition.same_as)
    probable: int = 0  # len Partition.candidates
    possible: int = 0  # len Partition.possible
    #: Per entity-type breakdown, keyed by type, sorted (deterministic — gate G2).
    by_type: dict[str, TypeCounts] = {}
    #: Entity types whose UNRESOLVED identity load is high relative to confirmed merges — a collection
    #: gap. Sorted deterministically. Empty when the effective ratio is unset (gap detection off).
    collection_gaps: list[str] = []
    #: The effective gap ratio used to compute ``collection_gaps`` — echoed for transparency.
    coverage_gap_ratio: float | None = None
    #: The full set of policy dials that produced this summary.
    policy: CoveragePolicy = CoveragePolicy()


def _typer(type_of: TypeOf) -> Callable[[str], "str | None"]:
    """Normalise a callable-or-mapping ``type_of`` into a callable ``entity_id -> type | None``."""
    if isinstance(type_of, Mapping):
        return type_of.get
    return type_of


def _link_type(a: str, b: str, typer: Callable[[str], "str | None"]) -> str:
    """The entity type to attribute a two-ended identity link to.

    Merges/candidates are within-type by construction (the resolver requires equal ``etype`` before it
    will score a pair), so both ends normally agree. STABLE RULE for the edge cases: an end the resolver
    could not type contributes nothing; among the present type strings the link is bucketed under the
    **lexicographically smallest**, which is order-independent and hash-seed-independent (gate G2). Only
    when NEITHER end is typed does the link fall to :data:`UNKNOWN_TYPE`.
    """
    present = sorted(t for t in (typer(a), typer(b)) if t)
    return present[0] if present else UNKNOWN_TYPE


def _effective_ratio(cfg: ResolveConfig | None, coverage_gap_ratio: float | None) -> float | None:
    """Precedence for the gap ratio: an explicit argument wins; else the config dial (which may be unset
    ⇒ gaps OFF, honouring "absent ⇒ off"); else — only when the caller passed neither config nor an
    explicit value — the library :data:`DEFAULT_GAP_RATIO`."""
    if coverage_gap_ratio is not None:
        return coverage_gap_ratio
    if cfg is not None:
        return cfg.coverage_gap_ratio  # config authoritative; None here means "dial unset ⇒ gaps off"
    return DEFAULT_GAP_RATIO


def identity_coverage(
    partition: Partition,
    type_of: TypeOf,
    cfg: ResolveConfig | None = None,
    *,
    coverage_gap_ratio: float | None = None,
) -> IdentityCoverage:
    """Fold a resolved :class:`Partition` into the Stage-4 identity-coverage summary (D11).

    ``type_of`` is a callable/map giving an entity id's type (e.g. the map from
    :func:`chanakya.resolve.resolve_with_types`). ``cfg`` (when supplied) provides the transparency policy
    dials and the config-driven gap ratio; ``coverage_gap_ratio`` overrides it explicitly. With neither,
    the library :data:`DEFAULT_GAP_RATIO` applies so the pure function is useful standalone. Deterministic.
    """
    typer = _typer(type_of)
    by_type: dict[str, TypeCounts] = {}

    def _bump(pairs: list[tuple[str, str]], field: str) -> None:
        for a, b in pairs:
            counts = by_type.setdefault(_link_type(a, b, typer), TypeCounts())
            setattr(counts, field, getattr(counts, field) + 1)

    _bump(partition.same_as, "confirmed")
    _bump(partition.candidates, "probable")
    _bump(partition.possible, "possible")

    ratio = _effective_ratio(cfg, coverage_gap_ratio)
    collection_gaps: list[str] = []
    if ratio is not None:  # ratio unset ⇒ gap detection off; counts still reported
        for etype in sorted(by_type):
            counts = by_type[etype]
            unresolved = counts.probable + counts.possible
            if unresolved / max(counts.confirmed, 1) >= ratio:
                collection_gaps.append(etype)

    return IdentityCoverage(
        confirmed=len(partition.same_as),
        probable=len(partition.candidates),
        possible=len(partition.possible),
        by_type=dict(sorted(by_type.items())),
        collection_gaps=collection_gaps,
        coverage_gap_ratio=ratio,
        policy=_policy(cfg, ratio),
    )


def _policy(cfg: ResolveConfig | None, effective_ratio: float | None) -> CoveragePolicy:
    """Snapshot the identity policy dials for transparency. Without ``cfg`` (a bare programmatic call) the
    band dials read as ``None`` and only the effective gap ratio is populated; with ``cfg`` the full set is
    read — ``auto_merge`` / ``hitl_low`` only when bands are configured (``cfg.scorable``), so an inert
    resolver reports them as ``None`` rather than raising."""
    if cfg is None:
        return CoveragePolicy(coverage_gap_ratio=effective_ratio)
    return CoveragePolicy(
        possible_floor=cfg.possible_floor,
        hitl_low=cfg.hitl_low if cfg.scorable else None,
        auto_merge=cfg.auto_merge if cfg.scorable else None,
        name_alone_caps_at_possible=cfg.name_alone_caps_at_possible,
        critical_veto_min_grade=cfg.critical_veto_min_grade,
        surface_wall_bridges=cfg.surface_wall_bridges,
        coverage_gap_ratio=effective_ratio,
    )
