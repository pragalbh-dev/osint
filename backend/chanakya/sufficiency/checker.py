"""Evidence-requirement templates → satisfied / Known Gap — the mechanism of the non-negotiable (spine/04 §3.7).

The fourth SCORE stage (master §4.3). For each assertion it finds the evidence template for its type
(``config.templates``) and asks: *are the required KINDS of evidence present?* If not, it returns an
unsatisfied evaluation carrying ``missing_slots`` + a **generated** ``next_coverage_due`` (from the
providing source's ``cadence`` — never hand-written) + the ``observability_ceiling`` — which the pipeline
turns into a first-class ``Known Gap`` node with a **deterministic templated refusal** (gate G8). This is
assessability (a required *kind* absent), orthogonal to magnitude: a fully-corroborated assertion can
still be INSUFFICIENT if the required kind is missing (spine/04 §3.7; insufficiency ≠ sparsity).

``never_observable`` templates (magazine depth, contract terms, C2 topology, true readiness)
short-circuit to unsatisfied with a fixed ceiling and no coverage date — a structural limit, never a
closable coverage lapse. An assertion type with no template has no requirement → assessable.
"""

from __future__ import annotations

from datetime import date, timedelta

from chanakya.schemas import (
    AssertionInput,
    ClaimRecord,
    ConfigBundle,
    IndependenceGroup,
    SourceRegistryEntry,
    SufficiencyEval,
)
from chanakya.schemas.values import canonical_iso_bounds
from chanakya.timeref import effective_as_of

_NEVER = "never_observable"
_ALL_OF, _ANY_OF = "all_of", "any_of"
_IMINT = "IMINT"
# Which source classes can satisfy each evidence slot → used to derive next_coverage_due from cadence.
_SLOT_SOURCE_TYPES: dict[str, tuple[str, ...]] = {
    "imagery_confirmation": ("satellite",),
    "independent_text_groups": ("trade-media", "official", "curated-register", "think-tank"),
    "independent_origin_groups": (),  # any source class
    "official_announcement": ("official",),
    "named_in_sanction_or_tender": ("customs-tender",),
}


# ── evidence-availability helpers ───────────────────────────────────────────────────────────────

def _assertion_type(supporting: list[ClaimRecord]) -> str | None:
    """The assertion's type = the predicate / event / entity type of its supporting claims."""
    for claim in supporting:
        payload = claim.payload
        atype = getattr(payload, "predicate", None) or getattr(payload, "event_type", None) or getattr(
            payload, "entity_type", None
        )
        if atype is not None:
            return str(atype)
    return None


def _discipline(source: SourceRegistryEntry | None) -> str:
    return _IMINT if source is not None and source.source_type == "satellite" else "textual"


def _latest_iso(claim: ClaimRecord) -> str | None:
    _, event_hi = canonical_iso_bounds(claim.event_time)
    if event_hi is not None:
        return event_hi
    _, report_hi = canonical_iso_bounds(claim.report_time)
    return report_hi


def _within(claim: ClaimRecord, within_days: float | None, as_of: str | None) -> bool:
    """True if the claim is within ``within_days`` of ``as_of`` (or no window is required)."""
    if within_days is None or as_of is None:
        return True
    iso = _latest_iso(claim)
    if iso is None:
        return True  # undated → do not exclude on recency (fail-open on the window only)
    age = (date.fromisoformat(as_of) - date.fromisoformat(iso)).days
    return age <= within_days


def _group_within(
    group: IndependenceGroup, claims: dict[str, ClaimRecord], within_days: float | None, as_of: str | None
) -> bool:
    return any(_within(claims[c], within_days, as_of) for c in group.claim_ids if c in claims)


# ── slot evaluation ─────────────────────────────────────────────────────────────────────────────

def _slot_satisfied(
    slot: str,
    constraints: dict,
    assertion: AssertionInput,
    supporting: list[ClaimRecord],
    claims: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    as_of: str | None,
) -> bool:
    """Is one required evidence *kind* present in the supporting evidence? Unknown slot → not satisfied."""
    within = constraints.get("within_days")
    minimum = constraints.get("min")

    if slot == "imagery_confirmation":
        return any(
            _discipline(sources.get(c.source_id)) == _IMINT and _within(c, within, as_of)
            for c in supporting
        )
    if slot == "official_announcement":
        return any(
            (s := sources.get(c.source_id)) is not None and s.source_type == "official"
            for c in supporting
        )
    if slot == "named_in_sanction_or_tender":
        return any(
            (s := sources.get(c.source_id)) is not None and s.source_type == "customs-tender"
            for c in supporting
        )
    if slot in ("independent_text_groups", "independent_origin_groups"):
        want = minimum if minimum is not None else 1
        eligible = 0
        for g in assertion.groups:
            if slot == "independent_text_groups":
                rep = next((claims[c] for c in g.claim_ids if c in claims), None)
                if rep is None or _discipline(sources.get(rep.source_id)) == _IMINT:
                    continue
            if _group_within(g, claims, within, as_of):
                eligible += 1
        return eligible >= want
    return False  # unknown slot → fail-closed (flag the gap rather than assume sufficiency)


def _eval_require(
    require: dict,
    assertion: AssertionInput,
    supporting: list[ClaimRecord],
    claims: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    as_of: str | None,
) -> tuple[bool, list[str]]:
    """Evaluate the any_of / all_of require-DSL → (satisfied, missing_slot_names)."""
    def slots(entries: list[dict]) -> list[tuple[str, dict]]:
        return [(name, cons) for entry in entries for name, cons in entry.items()]

    if _ALL_OF in require:
        results = [
            (name, _slot_satisfied(name, cons, assertion, supporting, claims, sources, as_of))
            for name, cons in slots(require[_ALL_OF])
        ]
        missing = [name for name, ok in results if not ok]
        return not missing, missing
    if _ANY_OF in require:
        pairs = slots(require[_ANY_OF])
        results = [
            (name, _slot_satisfied(name, cons, assertion, supporting, claims, sources, as_of))
            for name, cons in pairs
        ]
        if any(ok for _, ok in results):
            return True, []
        return False, [name for name, _ in results]  # none met → all are the gap
    return True, []  # no require clause → nothing to satisfy


# ── next_coverage_due (generated from the providing source's cadence) ───────────────────────────

def _cadence_days(cadence: str | None) -> int | None:
    """Parse a numeric ``"<N>d"`` cadence to days; event-driven/irregular/continuous → None (no schedule)."""
    if not cadence:
        return None
    text = cadence.strip().lower()
    if text.endswith("d") and text[:-1].isdigit():
        return int(text[:-1])
    return None


def _next_coverage_due(
    missing: list[str], sources: dict[str, SourceRegistryEntry], as_of: str | None
) -> str | None:
    """Earliest next revisit that could close a missing slot: ``as_of + min(cadence)`` over its providers."""
    if as_of is None:
        return None
    intervals: list[int] = []
    for slot in missing:
        provider_types = _SLOT_SOURCE_TYPES.get(slot)
        candidates = [
            s for s in sources.values()
            if provider_types is None or not provider_types or s.source_type in provider_types
        ]
        for s in candidates:
            days = _cadence_days(s.cadence)
            if days is not None:
                intervals.append(days)
    if not intervals:
        return None
    return (date.fromisoformat(as_of) + timedelta(days=min(intervals))).isoformat()


# ── the stage entrypoint ────────────────────────────────────────────────────────────────────────

def check(
    assertion: AssertionInput,
    claims: dict[str, ClaimRecord],
    config: ConfigBundle,
) -> SufficiencyEval:
    """Evaluate the assertion's evidence template → satisfied, or an unsatisfied gap with slots + coverage."""
    supporting_ids = [cid for g in assertion.groups for cid in g.claim_ids]
    supporting = [claims[c] for c in supporting_ids if c in claims]
    atype = _assertion_type(supporting)
    template = config.templates.as_map().get(atype) if atype else None
    if template is None:
        return SufficiencyEval(satisfied=True)  # no evidence-requirement for this type → assessable

    require = template.require or {}
    ceiling = getattr(template, "observability_ceiling", None)
    if require.get(_NEVER):
        return SufficiencyEval(
            satisfied=False,
            missing_slots=[atype] if atype else [_NEVER],
            next_coverage_due=None,  # never-observable → nothing to schedule
            ceiling=ceiling or "never-observable",
            template_id=atype,
        )

    sources = config.sources.as_map()
    as_of = effective_as_of(config, list(claims.values()))
    satisfied, missing = _eval_require(require, assertion, supporting, claims, sources, as_of)
    return SufficiencyEval(
        satisfied=satisfied,
        missing_slots=[] if satisfied else missing,
        next_coverage_due=None if satisfied else _next_coverage_due(missing, sources, as_of),
        ceiling=ceiling,
        template_id=atype,
    )
