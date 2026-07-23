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
from chanakya.ontology import NodeTypeIndex
from chanakya.schemas import (
    ConfigBundle,
    EntitiesConfig,
    OntologyConfig,
    PlacesConfig,
    ResolutionConfig,
)

# merge_score signal names (also the merge_weights keys + merge_breakdown keys).
ATTRIBUTE = "attribute"
RELATIONAL = "relational"
TEMPORAL = "temporal_consistency"
SOURCE_ASSERTED = "source_asserted"
SIGNALS = (ATTRIBUTE, RELATIONAL, TEMPORAL, SOURCE_ASSERTED)

# Attribute-role names (D5/D6) — an attribute's declared bearing on IDENTITY, per entity type. Strings,
# not numbers, so gate G6 (no magic numbers in ``resolve/``) is untouched. The default for any undeclared
# attribute is NEUTRAL (no identity effect) — the safe, extendable default.
ROLE_CRITICAL = "critical"      # a STATED disagreement is a hard veto (feeds the D5 wall)
ROLE_SUPPORTING = "supporting"  # agreement raises the score; a stated disagreement is a SOFT penalty
ROLE_NEUTRAL = "neutral"        # no identity effect (and the default for an undeclared attribute)

# STANAG-2022 source-reliability grades are an ORDINAL letter scale, A (most reliable) → F (least). The
# scale's letters are a domain constant, not a tunable — "at or above floor X" is therefore just the
# lexicographic test ``grade <= floor`` on a single uppercase letter (no numeric mapping, no scoring
# literal — gate G6 untouched; the floor value itself is read from config).
_GRADE_LETTERS = "ABCDEF"


def grade_meets_floor(grade: str | None, floor: str) -> bool:
    """True iff STANAG ``grade`` is at/above ``floor`` (A best). Fail-closed on an unreadable grade/floor.

    An unknown / unreadable grade is treated as *below* the floor — the safe direction for the credibility
    gate: a conflict we cannot vouch for must not be allowed to shatter a merge on its own (it raises to a
    human instead). Mirrors the credibility rubric's fail-closed doctrine (``credibility.reliability``).
    """
    if not grade or grade not in _GRADE_LETTERS or floor not in _GRADE_LETTERS:
        return False
    return grade <= floor


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
        self._node_types: NodeTypeIndex | None = None

    @classmethod
    def from_bundle(cls, config: ConfigBundle) -> ResolveConfig:
        return cls(config.resolution, config.places, config.entities, bundle=config)

    # ── extra-knob access (extra="allow" fields authored by DATA-C) ───────────────────────────
    def _extra(self, name: str, default: Any) -> Any:
        return getattr(self._r, name, default)

    def _place_extra(self, name: str, default: Any) -> Any:
        return getattr(self._p, name, default)

    # ── node-type identity rules (config/ontology.yaml — T3b) ─────────────────────────────────
    @property
    def node_types(self) -> NodeTypeIndex:
        """The ontology's *node*-type identity rules — refinement, relational-identity, identifiers.

        Read through the same config-only path every other knob uses. A ``ResolveConfig`` built without
        a bundle (the unit fixtures) gets an empty index, so every query returns its neutral default and
        behaviour is byte-unchanged (gate G2).
        """
        if self._node_types is None:
            ontology = self._bundle.ontology if self._bundle is not None else OntologyConfig()
            self._node_types = NodeTypeIndex(ontology)
        return self._node_types

    # ── merge scoring ─────────────────────────────────────────────────────────────────────────
    def weight(self, signal: str) -> float:
        """Weight for a merge_score signal; absent ⇒ 0.0 (that signal simply doesn't contribute)."""
        w = self._r.merge_weights.get(signal)
        return float(w) if w is not None else 0.0

    @property
    def relational_support_k(self) -> int | None:
        """Distinct shared neighbours at which the relational term reaches full strength (T3b-F).

        A Jaccard overlap is scale-free: two entities whose *only* neighbour is the same one score a
        perfect 1.0, which is how a single shared hub link came to be the dominant merge signal in this
        graph. This knob makes the term proportional to the evidence under it up to ``k``. Absent ⇒ the
        raw Jaccard, i.e. the pre-fix behaviour with no code literal (gates G2/G6).
        """
        v = self._extra("relational_support_k", None)
        return int(v) if v is not None else None

    @property
    def scorable(self) -> bool:
        """True only if bands are configured — otherwise the resolver stays inert (identity)."""
        return self._r.bands.get("auto_merge") is not None and self._r.bands.get("hitl_low") is not None

    @property
    def auto_merge(self) -> float:
        return float(self._r.bands["auto_merge"])

    def auto_merge_for_pair(self, etype_a: str, etype_b: str) -> float:
        """The auto-merge floor for a candidate pair — per-type when both sides share a listed type.

        On a single-subject corpus the fuzzy score cannot separate a genuine merge from a look-alike:
        the top of the score distribution is dominated by variant-family and cross-namespace *traps*
        (HQ-9 vs HQ-9B, PAF vs PAAD), so a lowered *global* floor auto-merges a trap before any real
        merge. But for a handful of types a near-identical name reliably denotes ONE entity — an
        organisation or trading-org whose only difference is spelling/abbreviation (CPMIEC vs
        "China … Precision Machinery …", the SINO-GALAXY variants). ``bands.auto_merge_by_type`` lets
        those types auto-merge at a lower floor while every identity-sensitive type keeps the strict
        global bar. The floor applies only when **both** endpoints carry the listed type (a cross-type
        pair is never a spelling variant); absent map ⇒ the global ``auto_merge`` for all pairs, so
        behaviour is byte-unchanged (gate G2). The reviewer/veto machinery is untouched — a trap that
        happens to share the type is still stopped by the vetoes, never by this floor.
        """
        if etype_a != etype_b:
            return self.auto_merge
        by_type = self._extra("auto_merge_by_type", None) or {}
        v = by_type.get(etype_a)
        return float(v) if v is not None else self.auto_merge

    @property
    def hitl_low(self) -> float:
        return float(self._r.bands["hitl_low"])

    @property
    def possible_floor(self) -> float | None:
        """Lower bound of the retained ``possible`` watch-list tier (D4 Stage 2).

        A scored pair in ``[possible_floor, hitl_low)`` — today dropped as ``separate`` — is kept as a
        latent identity link (Partition-only; never drawn). Absent ⇒ the tier is off and sub-hitl pairs
        drop exactly as before (no code literal, gates G2/G6). A policy dial (Stage 4 surfaces it).
        """
        v = self._r.bands.get("possible_floor")
        return float(v) if v is not None else None

    @property
    def name_alone_caps_at_possible(self) -> bool:
        """D4 banked correction: a pair whose ONLY nonzero identity signal is ``attribute`` (name) may not
        reach ``probable``/HITL — it caps at ``possible``. Default ``False`` ⇒ current banding, byte-unchanged.
        """
        return bool(self._extra("name_alone_caps_at_possible", False))

    @property
    def coverage_gap_ratio(self) -> float | None:
        """Unresolved-identity load at which an entity type reads as a COLLECTION GAP (Stage 4 / D11).

        A policy dial for the identity-coverage summary (:func:`chanakya.view.coverage.identity_coverage`):
        a type whose ``(probable + possible) / max(confirmed, 1)`` reaches this ratio is one the resolver
        keeps producing candidate / watch-list links for but cannot CONFIRM — so the operator needs more
        collection there, not a better resolver. Absent ⇒ this config-driven threshold is unset (the
        summary still reports counts) — no code literal here (gate G6), matching every other band/threshold
        dial. The shipped ``config/resolution.yaml`` sets it; config is authoritative for the production run.
        """
        v = self._extra("coverage_gap_ratio", None)
        return float(v) if v is not None else None

    @property
    def surface_wall_bridges(self) -> bool:
        """D9 (Stage 3A-ii): surface a **bridge across a hard wall** as a HITL candidate — default ON.

        A hard wall (a ``distinct_from`` / geo / hard-identifier veto) is a cannot-link enforced
        transitively before any merge: a pair whose union would place both endpoints of a vetoed pair into
        one cluster is refused, so the wall holds even across a chain of merges. That refusal is normally a
        *silent* non-event. D9 turns it into an alarm: a pair refused **only** by the transitive wall — not
        directly vetoed, yet its union would fuse a vetoed pair — that nonetheless scores as a genuine
        would-be merge (merge band ``auto``/``hitl``) is surfaced to the analyst with its own reason and
        **never merged** (the wall is untouched). It means the wall is wrong, the pair is a
        conflation/extraction error, or it is deliberate deception — exactly what a human should see.

        The corroboration gate reuses the existing merge bands (no new threshold — gate G6): a band
        ``separate`` (incidental low-score) touch is not a bridge (D9 take-care: "gate on real corroboration
        to both sides, not any incidental touch"). ON by default (target-first); an operator may set it
        ``False`` to silence the alarm, reverting to the pre-D9 silent non-merge (byte-unchanged).
        """
        return bool(self._extra("surface_wall_bridges", True))

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

    # ── credibility floor on the critical-attribute veto (D5 take-care a, Stage 3A) ─────────────
    @property
    def critical_veto_min_grade(self) -> str | None:
        """Minimum STANAG source-reliability grade for a stated critical conflict to WALL (else raise).

        D5 take-care (a): one flaky low-grade source must not be able to shatter a well-corroborated
        merge. A declared-critical-attribute disagreement is a hard veto only when the conflicting value
        on **both** sides is asserted by at least one source graded at/above this floor; below it the
        pair is **raised to the analyst** (a ``probable`` candidate) rather than silently walled OR
        silently merged. STANAG A is most reliable, F least, so a floor of ``C`` walls on A/B/C and
        raises on D/E/F. Scoped strictly to the critical-attribute veto — curated ``distinct_from``, geo,
        and hard-identifier vetoes are structural and stay unconditional.

        Absent ⇒ the floor is OFF and every critical conflict walls unconditionally (the pre-Stage-3A
        behaviour, byte-unchanged — no code literal, gate G6). The shipped ``config/resolution.yaml``
        sets it ON at the target ``C``.
        """
        v = self._extra("critical_veto_min_grade", None)
        return str(v).strip().upper() if v is not None else None

    def source_grade(self, source_id: str | None) -> str | None:
        """The STANAG ``reliability_grade`` declared for a source (``config/sources.yaml``); None if unknown.

        Read straight off the registry entry — the intrinsic, analyst-authored reliability letter, the
        human-legible instrument for a coarse *admissibility* gate ("is this source trustworthy enough to
        be allowed to shatter a merge?"), distinct in role from the fine-grained weight ``R(source)`` that
        rides the continuous similarity score.
        """
        if source_id is None or self._bundle is None:
            return None
        if self._source_index is None:
            self._source_index = dict(self._bundle.sources.as_map())
        source = self._source_index.get(source_id)
        grade = getattr(source, "reliability_grade", None) if source is not None else None
        return str(grade).strip().upper() if grade else None

    def source_meets_critical_veto_floor(self, source_id: str | None) -> bool:
        """Is this source graded at/above :attr:`critical_veto_min_grade`? (Floor OFF ⇒ always True.)"""
        floor = self.critical_veto_min_grade
        if floor is None:
            return True  # floor unset ⇒ the critical veto is unconditional (pre-Stage-3A, byte-unchanged)
        return grade_meets_floor(self.source_grade(source_id), floor)

    @property
    def coref_authoritative_evidence(self) -> set[str]:
        """Which in-document coreference evidence categories may **bootstrap** (auto-merge).

        Empty by default — so every coreference cluster is merely raise-only until an operator opts a
        category in, and shipping the producer alone cannot change anyone's node topology. Naming the
        categories in config rather than in code keeps "how much authority does the extractor's
        in-document reading carry" an operator decision: run with ``[EXPLICIT_EQUIVALENCE]`` to auto-merge
        only what a document *states* verbatim, or leave it empty to send everything to the analyst queue.

        A category listed here still clears every other rail — the ``distinct-from`` veto, type and
        namespace agreement, and the hard-attribute-contradiction check (``scoring.has_hard_conflict``).
        """
        return {str(c) for c in self._extra("coref_authoritative_evidence", [])}

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

    # ── attribute roles (D5/D6): critical / supporting / neutral, per entity type ───────────────
    def attribute_roles(self, entity_type: str) -> dict[str, Any]:
        """Raw per-type attribute-role declarations (D6); default ``{}`` (every attribute neutral).

        The declarative block an author writes in ``config/resolution.yaml``::

            attribute_roles:
              <entity_type>:
                <attr_name>: {role: critical|supporting|neutral, perishable: true|false}

        ``role`` decides identity bearing (compiled by :meth:`critical_role_attrs` /
        :meth:`supporting_role_attrs`); the optional ``perishable`` flag is SCHEMA ONLY in Stage 1A —
        read by :meth:`attribute_perishable` but not yet consumed by any behaviour (the update/stale
        framework, D8, lands later). An attribute not listed here is **neutral** — no identity effect.
        """
        return dict(self._extra("attribute_roles", {}).get(entity_type, {}))

    def _role_attrs(self, entity_type: str, role: str) -> list[str]:
        """Attributes of ``entity_type`` declared with ``role``, sorted (deterministic — gate G2)."""
        roles = self._extra("attribute_roles", {}).get(entity_type, {})
        return sorted(a for a, spec in roles.items() if isinstance(spec, dict) and spec.get("role") == role)

    def critical_role_attrs(self, entity_type: str) -> list[str]:
        """Compiler: attrs whose STATED disagreement is a hard veto (the D5 wall). Absent ⇒ ``[]``.

        Lowered onto the existing detectors — :func:`scoring.critical_attribute_conflict` (and through it
        the veto contributor + :func:`scoring.has_hard_conflict`) — rather than a second scoring path.
        """
        return self._role_attrs(entity_type, ROLE_CRITICAL)

    def supporting_role_attrs(self, entity_type: str) -> list[str]:
        """Compiler: attrs whose disagreement is a SOFT penalty in ``attribute_score``, never a wall."""
        return self._role_attrs(entity_type, ROLE_SUPPORTING)

    def attribute_perishable(self, entity_type: str, attr: str) -> bool | None:
        """Whether a declared attribute is PERISHABLE (durable ⇒ ``False``). SCHEMA ONLY (Stage 1A).

        Read here but not yet consumed: the perishable/durable distinction drives the update-vs-stale
        framework (D8) in a later stage. ``None`` ⇒ the attribute declares no perishability.
        """
        spec = self.attribute_roles(entity_type).get(attr)
        if not isinstance(spec, dict) or "perishable" not in spec:
            return None
        return bool(spec["perishable"])

    def geo_conflict_max_km(self, entity_type: str | None) -> float | None:
        """How far apart two entities of this type may *state* they are and still be one entity.

        The world statement behind the geographic veto (T2): a thing is in ONE place, so two mentions
        that each carry their own coordinate and sit further apart than this cannot be the same thing,
        however alike their names or neighbourhoods look. Per-type with an optional ``default`` row,
        exactly like :meth:`place_allowed_precision_classes`; no row and no ``default`` (or no
        ``entity_type``) ⇒ the gate is **off** for that type — the pre-fix behaviour, and no numeric
        literal in code (gate G6).
        """
        configured = self._extra("entity_geo_conflict_max_km", None)
        if not configured:
            return None
        row = configured.get(entity_type) if entity_type else None
        if row is None:
            row = configured.get("default")
        return float(row) if row is not None else None

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
    def place_identity_precision_classes(self) -> set[str] | None:
        """Anchor precision classes fine enough that "same anchor" may become "**same place**".

        Resolving a mention to an anchor and declaring two mentions the same place are different acts,
        and the second only follows from the first when the anchor is a *thing* rather than an *area*.
        "Rahwali, from the DMS fix" and "Rahwali, from the relative form" are one airfield; "a fenced
        compound in central Punjab" and "an air-defence node in Punjab Province" are two different
        unknowns that happen to share a province. Without this gate, opening the gazetteer to area
        anchors (T5) would buy map coverage at the price of a silently fused ORBAT.

        ``None`` (absent/empty) ⇒ no constraint ⇒ pre-T5 behaviour, byte-identical (gate G2).
        """
        configured = self._extra("place_identity_precision_classes", None)
        return set(configured) if configured else None

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
