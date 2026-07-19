"""Typed, literal-free access to the resolution config (gate G6: no magic numbers in code).

Every weight, band, threshold, penalty, radius, and budget the resolver uses is read **through this
reader** from ``config.resolution`` / ``config.places`` (DATA-C-authored). Absent knobs degrade
*without a code literal*: a missing weight contributes ``0.0``, missing bands make the resolver
inert (identity partition), a missing penalty means *no* penalty (``×1.0``). Only ``0.0``/``1.0`` —
the identity elements of sum/product — ever appear as literals, which G6 explicitly allows.
"""

from __future__ import annotations

from typing import Any

from chanakya.credibility.scoring import reliability
from chanakya.schemas import ConfigBundle, EntitiesConfig, PlacesConfig, ResolutionConfig

# merge_score signal names (also the merge_weights keys + merge_breakdown keys).
ATTRIBUTE = "attribute"
RELATIONAL = "relational"
TEMPORAL = "temporal_consistency"
SOURCE_ASSERTED = "source_asserted"
SIGNALS = (ATTRIBUTE, RELATIONAL, TEMPORAL, SOURCE_ASSERTED)


class ResolveConfig:
    """A read-through view over the resolution + places + entity-registry config surfaces."""

    def __init__(
        self,
        resolution: ResolutionConfig,
        places: PlacesConfig,
        entities: EntitiesConfig | None = None,
        bundle: ConfigBundle | None = None,
    ) -> None:
        self._r = resolution
        self._p = places
        self._e = entities if entities is not None else EntitiesConfig()
        # The whole bundle, held ONLY to grade the source behind an identity assertion (D-2.5): R(source)
        # is the credibility rubric's *output* (sources.yaml class × credibility.yaml factors), so RESOLVE
        # reads it rather than re-deriving a second, divergent notion of "how good is this source".
        self._bundle = bundle
        self._source_index: dict[str, Any] | None = None

    @classmethod
    def from_bundle(cls, config: ConfigBundle) -> ResolveConfig:
        return cls(config.resolution, config.places, config.entities, bundle=config)

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

    # ── source-weighted identity assertions (D-2.5 / D-P3.4) ──────────────────────────────────
    @property
    def identity_default_weight(self) -> float:
        """Weight for an identity assertion whose source the registry does not know at all.

        Defaults to the neutral element ``1.0`` — i.e. exactly today's binary behaviour — so a config
        with no source registry (the golden fixtures, the unit-test bundles) is byte-unchanged (gate G2).
        Safe as a default because a ``same-as`` is structurally **raise-only**: the worst an ungraded
        assertion can do is put a pair in front of an analyst, never merge it (see ``cluster._band``).
        """
        v = self._extra("identity_source_weight_default", None)
        return float(v) if v is not None else 1.0

    def identity_source_weight(self, source_id: str | None) -> float:
        """R(source) for the source asserting an identity — how much its ``same-as`` is allowed to count.

        A registered source is graded by the credibility rubric (fail-closed: an unrecognised source
        *class* scores 0.0 — an unreadable pedigree is not a credible one). An entirely unregistered
        source falls back to :attr:`identity_default_weight`.
        """
        if source_id is None or self._bundle is None:
            return self.identity_default_weight
        if self._source_index is None:
            self._source_index = dict(self._bundle.sources.as_map())
        source = self._source_index.get(source_id)
        if source is None:
            return self.identity_default_weight
        return reliability(source, self._bundle)

    @property
    def identity_raise_min_weight(self) -> float:
        """Minimum source weight for a ``same-as`` to be worth an analyst's attention at all.

        Recall-biased triage means this sits at the identity element ``0.0`` (surface everything) unless
        an operator deliberately raises it to keep the queue tractable; the *score* already reflects grade.
        """
        v = self._extra("identity_raise_min_weight", None)
        return float(v) if v is not None else 0.0

    # ── open-world name triggers (P3.3: containment / acronym expansion) ──────────────────────
    @property
    def containment_min_descriptor_len(self) -> int | None:
        """Min length of the first token a longer name *adds* for it to read as a descriptor, not a mark.

        This is the whole precision story of the containment trigger: ``HT-233`` ⊂ ``HT-233 engagement
        radar`` extends the name with a **word**, whereas ``HQ-9`` ⊂ ``HQ-9/P`` extends the **designator**
        — and the second is a different missile. Absent ⇒ the trigger is off (no code literal, gate G6).
        """
        v = self._extra("containment_min_descriptor_len", None)
        return int(v) if v is not None else None

    @property
    def containment_min_short_tokens(self) -> int | None:
        """Min tokens the *shorter* name must have to be a trustworthy hook (else: too generic to bootstrap)."""
        v = self._extra("containment_min_short_tokens", None)
        return int(v) if v is not None else None

    @property
    def acronym_min_len(self) -> int | None:
        """Min letters for a single-token name to be read as an acronym of a multi-token one (else off)."""
        v = self._extra("acronym_min_len", None)
        return int(v) if v is not None else None

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

    # ── entity registry (config/entities.yaml — the 9th surface; mirrors ``places``) ────────────
    @property
    def entities(self) -> EntitiesConfig:
        """The seed entity registry — RESOLVE's *prior* for entity identity (D-B; mirrors the gazetteer).

        A curated **open world**: each entry contributes (a) a stable ``entity_id`` the resolver elects as
        its cluster's canonical node id, (b) its alias equivalence class (folded into the ``AliasIndex``,
        so a surface form equal to a registry alias bootstraps at confidence 1.0), and (c) entity-id-level
        ``distinct_from`` veto pairs. Entries **seed candidates only** — an entry becomes a view node only
        when a real claim resolves onto it. Absent surface ⇒ empty ⇒ the resolver behaves exactly as before.
        """
        return self._e

    @property
    def registry_distinct_from(self) -> list[tuple[str, str]]:
        """Entity-id-level do-not-merge pairs declared by the registry (the hard veto, before banding)."""
        return [(e.entity_id, other) for e in self._e.entities for other in e.distinct_from]

    @property
    def registry_alias_table(self) -> dict[str, list[str]]:
        """``canonical_name → aliases`` from the registry, in alias-table shape for the ``AliasIndex``."""
        return {e.canonical_name: list(e.aliases) for e in self._e.entities if e.aliases}

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

    def place_allowed_precision_classes(self, entity_type: str | None) -> set[str] | None:
        """Which gazetteer ``precision_class``es this entity type may be *pulled onto* by proximity.

        The world statement behind the RES-5 gate: a basing site takes a pad or a site; it is never a
        port terminal, a district, or a whole city. Config-driven and extensible (gate G6) — a new
        entity type declares its own row, or inherits the optional ``default`` row. ``None`` (no row,
        no default, or no ``entity_type`` supplied) ⇒ **no constraint**, i.e. the pre-P3.5 behaviour.
        """
        configured = self._extra("place_allowed_precision_classes", None)
        if not configured or entity_type is None:
            return None
        allowed = configured.get(entity_type, configured.get("default"))
        return set(allowed) if allowed is not None else None

    @property
    def place_min_geocode_confidence(self) -> float | None:
        """Minimum INGEST-stated geocode confidence for a coordinate to be trusted for *proximity*.

        A vague regional geocode must not be snapped into a precise pad. Absent ⇒ the gate is off (no
        code literal, gate G6); an *unstated* confidence is UNKNOWN rather than low and is not blocked.
        """
        v = self._extra("place_min_geocode_confidence", None)
        return float(v) if v is not None else None

    @property
    def place_bind_on_curated_toponym(self) -> bool:
        """May a mention carrying **no coordinate** bind to an anchor whose curated name it states EXACTLY?

        A mention whose toponym is, after normalisation, the *same string* as a curated
        ``canonical_name``/alias is not being **inferred** onto that anchor: the document called the
        place by the name the analyst curated for it. That is the precision standard the entity alias
        table already merges on, one level up the stack. Without it, an entity whose grid reference was
        frozen unparsed (so it holds no point) can never reach the gazetteer at all, and a base an
        analyst named by hand renders unanchored.

        A policy switch, not an always-on behaviour, so an operator may insist location rests on
        geometry alone. Absent ⇒ **off** ⇒ pre-P3.6 behaviour, byte-identical (gate G2). It never
        loosens *matching* — only **seeded** forms match — so the withheld earned-merge aliases
        ("Chaklala", Rahwali's relative form) stay unreachable by string lookup either way.
        """
        return bool(self._extra("place_bind_on_curated_toponym", False))

    @property
    def toponym_descriptive_markers(self) -> list[str]:
        """Substrings that mark a display string as a *description of where*, not a place **name**.

        Commas (an admin hierarchy), ``~``/``km`` (a bearing-and-distance form), ``/`` (a compound of
        two places). Empty ⇒ every display name is accepted as a toponym (pre-P3.5 behaviour, G2).
        """
        return [str(m) for m in self._extra("toponym_descriptive_markers", [])]

    @property
    def place_hitl_multiplier(self) -> float | None:
        v = self._place_extra("place_proximity_hitl_multiplier", None)
        if v is None:
            v = self._extra("place_proximity_hitl_multiplier", None)  # tolerated dup home
        return float(v) if v is not None else None
