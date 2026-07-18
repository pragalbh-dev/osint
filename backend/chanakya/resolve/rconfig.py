"""Typed, literal-free access to the resolution config (gate G6: no magic numbers in code).

Every weight, band, threshold, penalty, radius, and budget the resolver uses is read **through this
reader** from ``config.resolution`` / ``config.places`` (DATA-C-authored). Absent knobs degrade
*without a code literal*: a missing weight contributes ``0.0``, missing bands make the resolver
inert (identity partition), a missing penalty means *no* penalty (``×1.0``). Only ``0.0``/``1.0`` —
the identity elements of sum/product — ever appear as literals, which G6 explicitly allows.
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import ConfigBundle, PlacesConfig, ResolutionConfig

# merge_score signal names (also the merge_weights keys + merge_breakdown keys).
ATTRIBUTE = "attribute"
RELATIONAL = "relational"
TEMPORAL = "temporal_consistency"
SOURCE_ASSERTED = "source_asserted"
SIGNALS = (ATTRIBUTE, RELATIONAL, TEMPORAL, SOURCE_ASSERTED)


class ResolveConfig:
    """A read-through view over the resolution + places config surfaces."""

    def __init__(self, resolution: ResolutionConfig, places: PlacesConfig) -> None:
        self._r = resolution
        self._p = places

    @classmethod
    def from_bundle(cls, config: ConfigBundle) -> ResolveConfig:
        return cls(config.resolution, config.places)

    # ── extra-knob access (extra="allow" fields authored by DATA-C) ───────────────────────────
    def _extra(self, name: str, default: Any) -> Any:
        return getattr(self._r, name, default)

    def _place_extra(self, name: str, default: Any) -> Any:
        return getattr(self._p, name, default)

    # ── merge scoring ─────────────────────────────────────────────────────────────────────────
    def weight(self, signal: str) -> float:
        """Weight for a merge_score signal; absent ⇒ 0.0 (that signal simply doesn't contribute)."""
        w = self._r.merge_weights.get(signal)
        return float(w) if w is not None else 0.0

    @property
    def scorable(self) -> bool:
        """True only if bands are configured — otherwise the resolver stays inert (identity)."""
        return self._r.bands.get("auto_merge") is not None and self._r.bands.get("hitl_low") is not None

    @property
    def auto_merge(self) -> float:
        return float(self._r.bands["auto_merge"])

    @property
    def hitl_low(self) -> float:
        return float(self._r.bands["hitl_low"])

    # ── candidate generation ────────────────────────────────────────────────────────────────
    @property
    def blocking_keys(self) -> list[str]:
        return list(self._r.blocking_keys)

    def hard_id_fields(self, kind: str) -> dict[str, list[str]]:
        """``kind`` ∈ {unique, categorical} → {entity_type: [attr names]} (default empty)."""
        return dict(self._extra("hard_id_fields", {}).get(kind, {}))

    @property
    def orphan_block_threshold_k(self) -> int | None:
        v = self._extra("orphan_block_threshold_k", None)
        return int(v) if v is not None else None

    @property
    def high_alias_risk_types(self) -> set[str]:
        return set(self._extra("high_alias_risk_types", []))

    @property
    def llm_candidate_gen(self) -> dict[str, Any]:
        return dict(self._extra("llm_candidate_gen", {}))

    # ── alias / transliteration / distinct-from ────────────────────────────────────────────────
    @property
    def alias_table(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._r.alias_table.items()}

    @property
    def transliteration(self) -> dict[str, str]:
        return dict(self._r.transliteration)

    @property
    def distinct_from(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._extra("distinct_from", {}).items()}

    # ── attribute comparators ──────────────────────────────────────────────────────────────────
    def attribute_rules(self, entity_type: str) -> dict[str, Any]:
        """Per-type {identity:[...], conflict:[...], numeric_conflict:{field:{rel_tol}}} (default {})."""
        return dict(self._extra("attribute_rules", {}).get(entity_type, {}))

    def attribute_scoring(self, name: str) -> float | None:
        """A named attribute-scoring knob (conflict_penalty, numeric_conflict_penalty, name_floor)."""
        v = self._extra("attribute_scoring", {}).get(name)
        return float(v) if v is not None else None

    # ── places ─────────────────────────────────────────────────────────────────────────────────
    @property
    def places(self) -> PlacesConfig:
        return self._p

    def proximity_radius_m(self, precision_class: str) -> float | None:
        v = self._p.proximity_radius_m.get(precision_class)
        return float(v) if v is not None else None

    @property
    def place_entity_types(self) -> set[str]:
        """Entity types whose IDENTITY *is* a place — the only types place-resolution may fuse/keep-apart.

        A unit is *located at* a base, it is not the base; only place-type mentions of one node merge.
        Config-overridable; defaults to the location-primary type in C (a basing_site)."""
        configured = self._extra("place_entity_types", None)
        return set(configured) if configured else {"basing_site"}

    @property
    def place_hitl_multiplier(self) -> float | None:
        v = self._place_extra("place_proximity_hitl_multiplier", None)
        if v is None:
            v = self._extra("place_proximity_hitl_multiplier", None)  # tolerated dup home
        return float(v) if v is not None else None
