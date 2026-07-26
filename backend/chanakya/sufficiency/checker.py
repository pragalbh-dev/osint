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


def _providers(
    missing: list[str], sources: dict[str, SourceRegistryEntry]
) -> list[SourceRegistryEntry]:
    """Every registered source whose class could close one of the missing slots (deduplicated, sorted).

    **A slot ABSENT from** :data:`_SLOT_SOURCE_TYPES` **contributes nothing**, and that distinction is
    load-bearing rather than a tidy-up. A declared-but-empty tuple means "any source class can close this"
    (``independent_origin_groups``); an *absent* slot means nobody has declared who could close it at all —
    ``identity``, ``named_supplier``, ``site_type``. Collapsing the two would let an identity question
    inherit the satellite constellation's 7-day revisit and be reported as "next coverage due <date>", which
    is a fabricated collection promise: no satellite pass settles which of two batteries a mention names.
    """
    out: dict[str, SourceRegistryEntry] = {}
    for slot in missing:
        if slot not in _SLOT_SOURCE_TYPES:
            continue
        provider_types = _SLOT_SOURCE_TYPES[slot]
        for s in sources.values():
            if not provider_types or s.source_type in provider_types:
                out[s.source_id] = s
    return [out[k] for k in sorted(out)]


def _next_coverage_due(
    missing: list[str], sources: dict[str, SourceRegistryEntry], as_of: str | None
) -> str | None:
    """Earliest next revisit that could close a missing slot: ``as_of + min(cadence)`` over its providers."""
    if as_of is None:
        return None
    intervals = [d for s in _providers(missing, sources) if (d := _cadence_days(s.cadence)) is not None]
    if not intervals:
        return None
    return (date.fromisoformat(as_of) + timedelta(days=min(intervals))).isoformat()


# ── the SECOND clause of the non-negotiable, stated in words ────────────────────────────────────
#
# "Names what is missing AND when next coverage is due" — and 34 of the 37 Known Gaps the booted corpus
# hands an analyst carried ``next_coverage_due: null``. A null is not a statement: to the analyst it is
# indistinguishable from a field nobody filled in, and it certainly does not say when to look again.
#
# The remedy is emphatically NOT to invent a cadence — a fabricated collection date would itself be a
# fabrication, and the worst kind, because it is actionable. So every gap now carries a coverage STATEMENT
# that is derived, never authored: where a real revisit interval exists it names the date, the interval and
# the source class it came from; where none exists it says which class could close the slot and why that
# class has no revisit date (it publishes event-driven / continuously / irregularly), or — for a gap raised
# by a stage that tasks no collection at all — that it stands as an untasked collection requirement. An
# honest "no scheduled coverage" is compliant; a silent null is not.

#: How a non-numeric cadence reads. Keys are the ``sources.yaml`` vocabulary; anything else falls through
#: to the value itself, so a new cadence word degrades to being quoted rather than being dropped.
_CADENCE_PROSE = {
    "event-driven": "only when an event prompts one to publish",
    "continuous": "continuously and unpredictably, with no scheduled revisit",
    "irregular": "irregularly, on no declared schedule",
    "per-tender": "only when a tender is issued",
}


def _class_phrase(missing: list[str], provs: list[SourceRegistryEntry]) -> str:
    """How to NAME the providers: a declared-empty slot means "any class", not a nine-item enumeration."""
    if any(slot in _SLOT_SOURCE_TYPES and not _SLOT_SOURCE_TYPES[slot] for slot in missing):
        return "any registered source class"
    return ", ".join(sorted({s.source_type for s in provs}))


def coverage_statement(
    *,
    next_coverage_due: str | None,
    missing_slots: list[str],
    ceiling: str | None,
    sources: dict[str, SourceRegistryEntry],
    unscheduled_phrase: str,
    as_of: str | None = None,
) -> tuple[str | None, str]:
    """``(next_coverage_due, statement)`` — the second clause of the non-negotiable, for EVERY gap.

    A date is DERIVED here when the gap's producer did not compute one but the registry supports one
    (``as_of`` + the shortest numeric cadence among the classes declared able to close the missing slot).
    A date is never *invented*: where no declared provider is on a revisit interval, the returned date stays
    ``None`` and the statement says why in words the analyst can act on — which class could close it and how
    that class publishes, or that nothing is tasked against the gap at all.
    """
    provs = _providers(missing_slots, sources) if missing_slots else []
    due = next_coverage_due or _next_coverage_due(missing_slots, sources, as_of)
    classes = _class_phrase(missing_slots, provs)
    if ceiling == "never-observable":
        return None, (
            "no coverage is due, and none ever will be: this is declared NEVER-OBSERVABLE in open sources, "
            "so it is a structural limit rather than a collection lapse. It closes only if the observability "
            "ceiling itself changes — not by looking again."
        )
    if due:
        intervals = [d for s in provs if (d := _cadence_days(s.cadence)) is not None]
        every = f"a {min(intervals)}-day revisit interval" if intervals else "a declared revisit interval"
        return due, (
            f"next coverage due {due} — the earliest revisit of a source class that could close this gap "
            f"({classes}), on {every} declared in the source registry."
        )
    if provs:
        how = sorted({_CADENCE_PROSE.get(s.cadence or "", f"on a '{s.cadence}' schedule") for s in provs})
        return None, (
            f"no scheduled coverage: the source class that can close this gap ({classes}) publishes "
            f"{'; '.join(how)}, so there is no revisit date to state. It closes when such a source next "
            "speaks to this point — not on any date the registry can predict."
        )
    return None, (
        f"{unscheduled_phrase}. No source class in the registry is declared able to close this gap, so no "
        "revisit interval applies: it closes only if a NEW source appears that speaks to it, or an analyst "
        "adjudicates it directly. An open collection requirement, not a date to wait for."
    )


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
