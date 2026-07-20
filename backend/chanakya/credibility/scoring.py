"""Per-claim credibility — ``claim_credibility = R(source) × Π(integrity) × freshness`` (spine/04 §C).

The first of SCORE's stages (master §4.3). Pure, deterministic, config-driven — **no scoring literal
lives here** (gate G6): every weight, penalty, threshold, half-life, and the decay base is read from
``config.credibility`` through F0's live store. The three factors:

* **R(source)** — a normalised weighted sum over the analyst-tunable factor rubric
  (``factor_weights`` × the source class's ``source_class_factors``). R is the rubric's *output*, never
  a hand-typed per-class constant (Module 1).
* **Π(integrity)** — the product of four independent M4 tables (``artifact_integrity`` · ``first_seen`` ·
  ``caption`` · ``coordinated_inauthenticity``); a missing signal → ``1.0`` (never silently zeroes a
  claim). ``first_seen`` (original vs recycled) is *computed here* by matching the frozen image
  fingerprints across the claim set (spine/04 §D — "first_seen determined in rebuild over the frozen
  hashes"); the analyst integrity flag (decision-log ``flag_origin``) taints every claim sharing a
  ``primary_origin_id``, including claims ingested *after* the flag.
* **freshness** — ``base^(−age / half_life[edge])`` on the claim's ``event_time`` (fallback
  ``report_time``, flagged), against the clock-free evaluation ``as_of`` (``chanakya.timeref``); durable
  edge types (no half-life configured) skip decay (freshness = 1.0). ``model_conf`` is held at 1.0 — the
  extraction-confidence seam is INACTIVE (kept, not deleted).
"""

from __future__ import annotations

from chanakya.ingest.hashing import pdq_hamming
from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DecisionRecord,
    Freshness,
    SourceRegistryEntry,
)
from chanakya.schemas.values import canonical_iso_bounds
from chanakya.timeref import effective_as_of

# Freshness gate-flag vocabulary (must match status.py) — strings, not scoring numbers (G6).
_AGING = "aging"  # ≥1 supporting look older than 1 half-life → blocks confirmed
_STALE = "stale"  # the freshest supporting look older than 1 half-life → demote confirmed→stale
# Honesty marker: the half-life came from the freshness-CLASS default (no per-edge/variant key matched),
# so the variant was NOT tagged and we decayed at the class rate. Stamped "<marker>:<class>" onto the
# gate/breakdown vector so provenance never silently pretends we knew the variant (RCA SC-2, D-P4.13).
_VARIANT_ASSUMED = "freshness-variant-assumed"

# Integrity table names + flag vocabulary (must match config.credibility.integrity_penalties keys,
# "<table>.<flag>"). Strings, not scoring numbers — the *values* live in config (gate G6).
_ARTIFACT = "artifact_integrity"
_FIRST_SEEN = "first_seen"
_CAPTION = "caption"
_COORD_INAUTH = "coordinated_inauthenticity"
_F_ORIGINAL, _F_RECYCLED = "original", "recycled"
_F_INDEPENDENT, _F_SUSPECTED = "independent", "suspected"
# The claim.attributes keys INGEST freezes the image signals under (see ingest/hashing, ingest/imagery).
_ATTR_ARTIFACT = "artifact_integrity"
_ATTR_CAPTION = "caption_vs_image_consistency"
_ATTR_COORD = "coordinated_inauthenticity"
_ATTR_PDQ = "pdq_hash"
_ATTR_SHA = "sha256"
_ATTR_FRESH_VARIANT = "freshness_variant"
# INGEST's caption vocabulary → the credibility.yaml `caption` table flags.
_CAPTION_MAP = {"consistent": "consistent", "inconsistent": "mismatched", "no-caption": "uncheckable"}


# ── reliability R(source) ──────────────────────────────────────────────────────────────────────

def reliability(source: SourceRegistryEntry | None, config: ConfigBundle) -> float:
    """R(source) = Σ_f w_f·factor_f / Σ_f w_f over the factors present for this source class.

    Fail-closed: an unknown source class (no factor row) contributes no reliability (``0.0``) rather
    than a fabricated prior — a claim from an unrecognised source cannot silently score as credible.
    """
    weights = config.credibility.factor_weights
    if source is None:
        return 0.0
    factors = config.credibility.source_class_factors.get(source.source_type)
    if not factors:
        return 0.0
    weighted, total_w = 0.0, 0.0
    for factor, weight in weights.items():
        if factor in factors:
            weighted += weight * factors[factor]
            total_w += weight
    return weighted / total_w if total_w > 0.0 else 0.0


# ── integrity Π ──────────────────────────────────────────────────────────────────────────────

def _attrs(claim: ClaimRecord) -> dict:
    return claim.attributes or {}


def _first_seen_flag(claim: ClaimRecord, recycled_ids: set[str]) -> str | None:
    """``recycled`` if this image claim reuses an earlier-seen fingerprint, else ``original`` (or None)."""
    fp = _attrs(claim)
    if not (fp.get(_ATTR_PDQ) or fp.get(_ATTR_SHA)):
        return None  # not an image claim → the first_seen table does not apply
    return _F_RECYCLED if claim.claim_id in recycled_ids else _F_ORIGINAL


def _coord_inauth_flag(
    claim: ClaimRecord, source: SourceRegistryEntry | None, flagged_origins: dict[str, str]
) -> str:
    """The coordinated-inauthenticity flag: analyst decision (strongest) > ingest attr > source bool.

    An analyst ``flag_origin`` decision taints every claim sharing that ``primary_origin_id`` — the
    monitoring beat: it also catches claims ingested *after* the flag. Absent any signal → independent.
    """
    origin = source.primary_origin_id if source is not None else None
    if origin is not None and origin in flagged_origins:
        return flagged_origins[origin]
    stated = _attrs(claim).get(_ATTR_COORD)
    if isinstance(stated, str):
        return stated
    if source is not None and source.coordinated_inauthenticity_flag:
        return _F_SUSPECTED
    return _F_INDEPENDENT


def integrity_product(
    claim: ClaimRecord,
    source: SourceRegistryEntry | None,
    config: ConfigBundle,
    recycled_ids: set[str],
    flagged_origins: dict[str, str],
) -> float:
    """Π over the four M4 tables — a missing signal contributes ``1.0`` (never silently zeroes a claim)."""
    penalties = config.credibility.integrity_penalties
    table_flags: dict[str, str | None] = {
        _ARTIFACT: _attrs(claim).get(_ATTR_ARTIFACT),
        _FIRST_SEEN: _first_seen_flag(claim, recycled_ids),
        _CAPTION: _CAPTION_MAP.get(str(_attrs(claim).get(_ATTR_CAPTION))),
        _COORD_INAUTH: _coord_inauth_flag(claim, source, flagged_origins),
    }
    product = 1.0
    for table, flag in table_flags.items():
        if flag is not None:
            product *= penalties.get(f"{table}.{flag}", 1.0)
    return product


# ── freshness ──────────────────────────────────────────────────────────────────────────────────

def _edge_key(claim: ClaimRecord) -> str | None:
    """The half-life lookup key for a claim: its predicate/event/entity type (variant-qualified)."""
    payload = claim.payload
    base = getattr(payload, "predicate", None) or getattr(payload, "event_type", None) or getattr(
        payload, "entity_type", None
    )
    return str(base) if base is not None else None


def _days_between(start_iso: str, end_iso: str) -> float:
    """Whole-day span between two ISO dates — pure stdlib date math, no clock (G1)."""
    from datetime import date

    return float((date.fromisoformat(end_iso) - date.fromisoformat(start_iso)).days)


def _half_life_days(
    claim: ClaimRecord, config: ConfigBundle, edge_index: EdgeLaneIndex
) -> tuple[float | None, str | None]:
    """This claim's half-life + the freshness class *iff* it came from the class-level default.

    Fallback chain (spine/04): ``<edge>.<variant>`` → bare ``<edge>`` →
    ``half_life_defaults[ontology.freshness_class(edge)]`` → ``None`` (durable / no reachable half-life).
    The second element is the ``freshness_class`` name **only** when the class-default rung fired — no
    per-edge or per-variant key existed, so the variant was not tagged and we decayed at the class rate;
    the caller stamps ``freshness-variant-assumed:<class>`` for honest provenance. It is ``None`` on every
    other rung (an exact edge/variant key, or durable). Config-driven; no half-life literal here (G6).
    """
    half_lives = config.credibility.half_lives_days
    key = _edge_key(claim)
    if key is None:
        return None, None
    variant = _attrs(claim).get(_ATTR_FRESH_VARIANT)
    if variant is not None:
        specific = half_lives.get(f"{key}.{variant}")
        if specific is not None:
            return specific, None
    bare = half_lives.get(key)
    if bare is not None:
        return bare, None
    # No exact key — fall back to the edge's freshness-CLASS default so a perishable edge that carries
    # only variant sub-keys (based-at, replenishes, inducted-into) still decays instead of scoring eternal.
    defaults = getattr(config.credibility, "half_life_defaults", None) or {}
    fclass = edge_index.freshness_class(key)
    if fclass is not None:
        class_default = defaults.get(fclass)
        if class_default is not None:
            return class_default, fclass
    return None, None


def _event_iso(claim: ClaimRecord) -> tuple[str | None, bool]:
    """The claim's freshness anchor ISO: event_time, else report_time (flagged fell_back)."""
    _, event_hi = canonical_iso_bounds(claim.event_time)
    if event_hi is not None:
        return event_hi, False
    _, report_hi = canonical_iso_bounds(claim.report_time)
    return report_hi, report_hi is not None


def freshness(
    claim: ClaimRecord, as_of: str | None, config: ConfigBundle, edge_index: EdgeLaneIndex
) -> tuple[float, bool]:
    """``base^(−age/half_life)`` on event_time (fallback report_time, flagged). Returns (factor, fell_back).

    Durable edge types (no reachable half-life) skip decay → ``1.0``. A future-dated claim
    (event after as_of) clamps to fresh (``1.0``) — nothing is fresher than the evaluation date.
    """
    half_life, _ = _half_life_days(claim, config, edge_index)
    base = getattr(config.credibility, "decay_base", None)
    if half_life is None or base is None or as_of is None:
        return 1.0, False  # durable / unconfigured / no reference → no decay
    event_hi, fell_back = _event_iso(claim)
    if event_hi is None:
        return 1.0, False
    age = _days_between(event_hi, as_of)
    if age <= 0.0:
        return 1.0, fell_back  # future-relative / same-day → fresh, never > 1.0
    return base ** (-(age / half_life)), fell_back


def assertion_freshness(
    claim_ids: list[str],
    claims_by_id: dict[str, ClaimRecord],
    as_of: str | None,
    config: ConfigBundle,
) -> tuple[Freshness, list[str]]:
    """Summarise an assertion's freshness (freshest look) + the freshness gate flags for the machine.

    ``aging`` if *any* supporting look has aged past one half-life (blocks confirmed — "every look
    fresh"); ``stale`` if the *freshest* look has aged past one half-life (demote confirmed→stale).
    Durable looks never age. Pure/clock-free (G1).
    """
    base = getattr(config.credibility, "decay_base", None)
    edge_index = EdgeLaneIndex(config.ontology)
    freshest_iso: str | None = None
    freshest_decay = 1.0
    freshest_hl: float | None = None
    any_aged = False
    freshest_aged = False
    assumed_classes: set[str] = set()  # supporting looks whose half-life came from the class default
    for cid in claim_ids:
        claim = claims_by_id.get(cid)
        if claim is None:
            continue
        half_life, assumed_class = _half_life_days(claim, config, edge_index)
        if half_life is None or base is None or as_of is None:
            continue  # durable / no reference → always fresh; contributes no aging
        if assumed_class is not None:
            assumed_classes.add(assumed_class)
        event_hi, _ = _event_iso(claim)
        if event_hi is None:
            continue
        age = _days_between(event_hi, as_of)
        decay = 1.0 if age <= 0.0 else base ** (-(age / half_life))
        aged = age > half_life
        any_aged = any_aged or aged
        if freshest_iso is None or event_hi > freshest_iso:
            freshest_iso, freshest_decay, freshest_hl, freshest_aged = event_hi, decay, half_life, aged
    flags: list[str] = []
    if any_aged:
        flags.append(_AGING)
    if freshest_aged:
        flags.append(_STALE)
    # Honest provenance: a look decayed at the class default (variant untagged) — never silent (SC-2).
    for fclass in sorted(assumed_classes):
        flags.append(f"{_VARIANT_ASSUMED}:{fclass}")
    summary = Freshness(
        last_support_time=freshest_iso, half_life_days=freshest_hl, decay_factor=freshest_decay
    )
    return summary, flags


# ── first_seen precomputation (image-fingerprint dedup across the claim set) ────────────────────

def _recycled_claim_ids(claims: list[ClaimRecord], config: ConfigBundle) -> set[str]:
    """Image claims whose fingerprint re-appears from an earlier claim → recycled (circular imagery).

    Exact sha256 match, or PDQ within the configured Hamming radius; the *first* occurrence (by claim
    order) is original, later matches are recycled. The threshold is config-driven (G6); absent → exact
    match only. Deterministic: iterate in claim order, compare against already-seen fingerprints.
    """
    radius = getattr(config.credibility, "pdq_recycled_hamming", None)
    seen_sha: dict[str, str] = {}
    seen_pdq: list[tuple[str, str]] = []
    recycled: set[str] = set()
    for claim in claims:
        attrs = claim.attributes or {}
        sha, pdq = attrs.get(_ATTR_SHA), attrs.get(_ATTR_PDQ)
        if not (sha or pdq):
            continue
        is_recycled = False
        if sha is not None and sha in seen_sha:
            is_recycled = True
        elif pdq is not None and radius is not None:
            for _, seen in seen_pdq:
                if pdq_hamming(pdq, seen) <= radius:
                    is_recycled = True
                    break
        if is_recycled:
            recycled.add(claim.claim_id)
        else:
            if sha is not None:
                seen_sha.setdefault(sha, claim.claim_id)
            if pdq is not None:
                seen_pdq.append((claim.claim_id, pdq))
    return recycled


def _flagged_origins(decisions: list[DecisionRecord] | None) -> dict[str, str]:
    """Analyst integrity flags from the decision log → ``{primary_origin_id: coord-inauth flag}``."""
    flagged: dict[str, str] = {}
    for decision in decisions or []:
        origin_effect = (decision.effects or {}).get("flag_origin")
        if isinstance(origin_effect, dict):
            origin = origin_effect.get("primary_origin_id")
            if origin is not None:
                flagged[str(origin)] = str(origin_effect.get("flag", _F_SUSPECTED))
    return flagged


# ── the stage entrypoint ───────────────────────────────────────────────────────────────────────

def score_claims(
    resolved_claims: list[ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    config: ConfigBundle,
    decisions: list[DecisionRecord] | None = None,
) -> dict[str, float]:
    """Per-claim ``claim_credibility = R(source) × Π(integrity) × freshness`` for every resolved claim."""
    as_of = effective_as_of(config, resolved_claims)
    edge_index = EdgeLaneIndex(config.ontology)
    recycled_ids = _recycled_claim_ids(resolved_claims, config)
    flagged_origins = _flagged_origins(decisions)
    out: dict[str, float] = {}
    for claim in resolved_claims:
        source = sources.get(claim.source_id)
        r = reliability(source, config)
        integrity = integrity_product(claim, source, config, recycled_ids, flagged_origins)
        fresh, _ = freshness(claim, as_of, config, edge_index)
        out[claim.claim_id] = r * integrity * fresh
    return out
