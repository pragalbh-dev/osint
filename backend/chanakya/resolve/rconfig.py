"""Typed, literal-free access to the resolution config (gate G6: no magic numbers in code).

Every weight, band, threshold, penalty, radius, and budget the resolver uses is read **through this
reader** from ``config.resolution`` / ``config.places`` (DATA-C-authored). Absent knobs degrade
*without a code literal*: a missing weight contributes ``0.0``, missing bands make the resolver
inert (identity partition), a missing penalty means *no* penalty (``×1.0``). Only ``0.0``/``1.0`` —
the identity elements of sum/product — ever appear as literals, which G6 explicitly allows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chanakya.credibility.scoring import reliability
from chanakya.ontology import LayerRouting, NodeTypeIndex
from chanakya.resolve.entities import fold_value
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

#: The two lines of evidence ``attribute`` fuses at a single ``max`` (D-13.20's split). They are
#: **diagnostic sub-signals**, never weighted terms: ``attribute`` keeps its whole ``merge_weights`` share,
#: so decomposing it moves no score. They exist because "a name match reaches at most *possible*, and one
#: more trivially-available signal clears it" (D-13.10) is *unexpressible* while the two live in one number.
NAME = "name"
DISCRIMINATOR = "discriminator"
SUB_SIGNALS = (NAME, DISCRIMINATOR)

# Attribute-role names (D5/D6) — an attribute's declared bearing on IDENTITY, per entity type. Strings,
# not numbers, so gate G6 (no magic numbers in ``resolve/``) is untouched. The default for any undeclared
# attribute is NEUTRAL (no identity effect) — the safe, extendable default.
ROLE_CRITICAL = "critical"      # a STATED disagreement is a hard veto (feeds the D5 wall)
ROLE_SUPPORTING = "supporting"  # agreement raises the score; a stated disagreement is a SOFT penalty
ROLE_NEUTRAL = "neutral"        # no identity effect (and the default for an undeclared attribute)

# ── C6 (re-specified): an attribute's TIME ROLE — four values, not a boolean ─────────────────────
#
# The shipped field was ``perishable: true|false`` and C6 needs **three** states beyond durable, so the
# closure as first written could not be built (RK-LAYER follow-up 2). These four are the declared
# vocabulary; each earns its own identity consequence, and an attribute may declare exactly one.
TIME_DURABLE = "durable"            # a stable spec: agreement supports identity normally
TIME_PERISHABLE = "perishable"      # expected to change: perishable-only evidence cannot confirm (D-13.9a)
TIME_CONSTITUTIVE = "constitutive"  # part of WHAT this instance IS ⇒ a difference is DISTINCTNESS, not staleness
TIME_IDENTIFYING = "identifying"    # the attribute identifies the entity ⇒ satisfies the confirm requirement
TIME_ROLES = (TIME_DURABLE, TIME_PERISHABLE, TIME_CONSTITUTIVE, TIME_IDENTIFYING)
#: The roles whose *agreement* is durable identity evidence — i.e. everything that is not transient.
#: ``constitutive`` is what lets a **presence** confirm (its geography is definitional, not perishable) and
#: ``identifying`` is what lets a **place** confirm; together they are the rung spine/13 §6 lever 2 needs.
TIME_ROLES_CONFIRMING = (TIME_DURABLE, TIME_CONSTITUTIVE, TIME_IDENTIFYING)

#: The legacy boolean key. Its presence is a **loud validation error** — no migration shim outlives the
#: stage that introduces it (plan §5a-bis), and a silently-tolerated old form biases every later author.
_LEGACY_PERISHABLE_KEY = "perishable"
_TIME_ROLE_KEY = "time_role"
#: Per-ROW stage gate on an ``attribute_roles`` entry: ``requires: earned_identity`` ⇒ the row is consumed
#: only while that flag is on. It is the stage flag at row granularity, and it exists so C6's two new
#: ``time_role`` values can live in the ONE ``attribute_roles`` block a reader and an auditor inspect, rather
#: than in a parallel overlay nobody would find — ruling M3's whole point being that a vocabulary declared
#: anywhere other than the types that need it is inert config with a longer name. Dies with the flag at S4.
_REQUIRES_KEY = "requires"
_REQUIRES_EARNED = "earned_identity"
#: A per-FIELD stage override on an ``attribute_roles`` entry: ``earned_role`` replaces ``role`` while the flag
#: is on. Used where the row **predates** S3 and must keep its earlier declaration flag-off — gating such a row
#: wholesale would delete a pre-S3 declaration and silently move flag-off scoring, because a dropped row leaves
#: the agreement ratio. ``requires:`` is for rows that are wholly new and have no earlier form to preserve.
_EARNED_ROLE_KEY = "earned_role"

#: Identity *bands*, by name. A ceiling is declared as a band NAME and never as a float: analyst B's
#: arithmetic (rk-spike-DECISIONS §b) showed any ×coefficient can drop a pair **two** bands — out of the
#: analyst's queue entirely — and its safe value depends on thresholds that will move. A band name is
#: threshold-independent and states the intent directly ("not automatically", never "not at all").
BAND_CONFIRMED = "confirmed"
BAND_PROBABLE = "probable"
BAND_POSSIBLE = "possible"
BANDS_BY_STRENGTH = (BAND_CONFIRMED, BAND_PROBABLE, BAND_POSSIBLE)


class AttributeRoleError(ValueError):
    """A declared ``attribute_roles`` entry uses the retired boolean ``perishable`` key, or a bad role."""


# ── the RK-COREF (S3) stage flag and its knobs ───────────────────────────────────────────────────
#
# Read from ``config/resolution.yaml``'s top-level ``earned_identity`` block (``ResolutionConfig`` is
# ``extra="allow"``, the same precedent ``llm_candidate_gen`` sets). **One flag**, mirroring S2's
# ``layer_routing.enabled``, because the pieces are one change to *what earns identity* and half of them
# would be incoherent: promoting coreference to a required tier without the decline mechanism, or binding
# the caps to the bootstrap without the per-layer profile, each makes the system worse than either end
# state. Flag OFF ⇒ every mechanism below is inert and the graph is byte-identical to S2's flag-off view.
#
# **Inertness means the AUTHORISATIONS too, not only the restraints.** The review measured the one place
# that broke it: :attr:`ResolveConfig.coref_authoritative_evidence` unioned the stage's
# ``authoritative_categories`` into the resolver with no flag test, while the co-location cap, the name
# cap, the contrast ceiling, the relationship wall, the referent decline and the doc-scoping of a bind all
# early-returned when the flag was off. Flag-off therefore ran S3's *permission* with none of S3's
# *limits* — the one arrangement strictly worse than either end state. Any future knob that grants a
# capability belongs behind the same flag test as the knob that bounds it; a stage flag that gates only
# the restraints is an anti-safety device.
#
# Every threshold, cap, floor, category list and vocabulary here is **config**, never a code literal
# (gate G6). Absent block ⇒ :attr:`enabled` False ⇒ inert.

_EARNED_IDENTITY = "earned_identity"


@dataclass(frozen=True)
class EarnedIdentity:
    """``config/resolution.yaml → earned_identity``, compiled. Absent ⇒ :attr:`enabled` False ⇒ inert.

    "Inert" is a claim about **every** field below, the permissive ones included. Each consumer must test
    :attr:`enabled` before reading — the one field that did not (:attr:`authoritative_categories`) made the
    flag-off deployment less safe than the flag-on one, because it granted S3's bootstrap authority while
    every S3 cap and wall stayed switched off. Compiling a field here is not what makes it inert; the
    consumer's flag test is.
    """

    enabled: bool = False

    # ── D-13.17: which coreference categories may BOOTSTRAP, and behind what floor ────────────────
    #: Categories allowed to bootstrap **once their per-link deterministic gate passes** (C5).
    #: ``NAME_VARIANT`` is deliberately absent — see the config comment.
    #:
    #: Read **only when** :attr:`enabled`, and that gating is load-bearing rather than tidy: this is the
    #: only knob in the block that *grants* rather than *bounds*, so an ungated read hands flag-off runs
    #: the authorisation without the co-location cap, the contrast ceiling or the document-scoping that
    #: exist to bound it. Measured on the shipped bundle before the gate went in: two co-located
    #: formations and an explicitly-contrasted pair each fused at ``confirmed`` flag-off, where the
    #: flag-on run held both at ``probable``. The pre-S3 top-level ``coref_authoritative_evidence`` knob is
    #: separate and stays flag-independent — an operator who wrote it meant it; it ships ``[]``.
    authoritative_categories: tuple[str, ...] = ()
    #: STANAG floor the *asserting document's* source must clear for a bind to be authoritative. Not
    #: optional: an authoritative bind fuses at 1.0 and bypasses banding, so it acts **harder** than the
    #: assertion it most resembles (a stated ``same-as``, which is grade-floored *and* raise-only).
    bind_min_grade: str | None = None
    #: Seed equivalence-marker vocabulary for the ``EXPLICIT_EQUIVALENCE`` gate, verb forms included.
    equivalence_markers: tuple[str, ...] = ()
    #: Relative weights of the two ``attribute`` sub-signals (D-13.20's split), read from the TOP-LEVEL
    #: ``merge_weights`` beside the four scored terms. They scale each sub-signal before the two are fused at
    #: a ``max``; they are **not** summed into the total, which keeps ``attribute``'s whole share intact. Both
    #: ship at the neutral element ``1.0``, so the shipped values reproduce ``max(name, discriminator)``
    #: exactly — but the numbers are in config, so splitting the signal cannot bury a coefficient in the
    #: source (gate G6).
    name_weight: float = 1.0
    discriminator_weight: float = 1.0
    #: The MARK-vs-WORD threshold for the gate's fourth conjunct (ruling M1) — read from the **existing**
    #: top-level ``containment_min_descriptor_len``, never re-declared. One threshold for one idea (gate G6):
    #: *"HT-233" + "engagement" (a WORD) is the same radar described more fully; "HQ-9" + "P" (a MARK) is a
    #: different missile.* Without this conjunct a sentence that *distinguishes* two variants —
    #: ``"<Design> (<Design>/X)"`` — passes every other conjunct, because the parenthetical marker really is
    #: present and no token-list vocabulary can tell the two apart.
    min_descriptor_len: int | None = None

    # ── D-13.10 / D-13.20: the caps, as band names ────────────────────────────────────────────────
    #: Ceiling for a pair carried by the NAME sub-signal alone, at **every** layer.
    name_ceiling: str = ""
    #: Ceiling for a formation pair whose only agreement is co-location (D-13.14 / G16).
    colocation_ceiling: str = ""
    #: Ceiling for a same-document **stated-contrast** pair (D-13.19). Ungraded by design: a band ceiling
    #: cannot *shatter* an existing cluster, which is the harm a grade gate would have defended against.
    contrast_ceiling: str = ""

    # ── D-13.14 / G16: the co-location cap ────────────────────────────────────────────────────────
    formation_types: tuple[str, ...] = ()
    presence_types: tuple[str, ...] = ()
    #: Predicates whose shared endpoint is *co-location* evidence rather than identity evidence.
    colocation_predicates: tuple[str, ...] = ()
    #: Per-type unit-level discriminators that CAN confirm a formation (over and above co-location).
    formation_discriminators: tuple[str, ...] = ()

    # ── D-13.8 / G18: the relationship-conflict wall ──────────────────────────────────────────────
    #: Predicates a **stated** conflict on which hard-walls a merge.
    wall_predicates: tuple[str, ...] = ()
    #: The attribute carrying the site class the ``based-at`` half of the wall is scoped within (C1).
    wall_scope_attr: str = ""

    # ── C7: value normalization is a prerequisite for walling on ANY slot ─────────────────────────
    #: ``attr → {canonical value: [stated variants]}``. Applied before conflict detection **and** before
    #: namespace derivation (normalising only at conflict time would leave namespaces split).
    value_normalization: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = ()
    #: Attributes for which an unnormalizable stated value takes the **third state** — no wall AND no
    #: fusion, plus a named gap. A gap that does not bind the fusion path is decoration (rk-14 probe).
    normalization_required_attrs: tuple[str, ...] = ()

    # ── C6: the per-(type, attribute) overlay that only exists with the flag on ───────────────────
    #: Extra ``attribute_roles`` rows merged over the base block when :attr:`enabled`. Kept separate so
    #: the *base* block stays exactly what the flag-off view scores on — the flag boundary in one place.
    attribute_roles_overlay: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_resolution(cls, resolution: ResolutionConfig) -> EarnedIdentity:
        block = getattr(resolution, _EARNED_IDENTITY, None)
        # Ruling M1 reuses the shipped containment knob rather than declaring a second threshold for the
        # same idea, so it is read from the TOP level even when the stage block is absent.
        raw_desc = getattr(resolution, "containment_min_descriptor_len", None)
        min_desc = int(raw_desc) if raw_desc is not None else None
        if not isinstance(block, dict):
            return cls(min_descriptor_len=min_desc)

        def _strs(key: str) -> tuple[str, ...]:
            raw = block.get(key)
            return tuple(str(x) for x in raw) if isinstance(raw, (list, tuple)) else ()

        def _str(key: str) -> str:
            v = block.get(key)
            return str(v) if v else ""

        norm_raw = block.get("value_normalization")
        normalization: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = ()
        if isinstance(norm_raw, dict):
            normalization = tuple(
                (
                    str(attr),
                    tuple(
                        (str(canonical), tuple(str(v) for v in variants))
                        for canonical, variants in sorted(classes.items())
                        if isinstance(variants, (list, tuple))
                    ),
                )
                for attr, classes in sorted(norm_raw.items())
                if isinstance(classes, dict)
            )
        overlay_raw = block.get("attribute_roles")
        overlay = (
            {str(t): dict(rows) for t, rows in overlay_raw.items() if isinstance(rows, dict)}
            if isinstance(overlay_raw, dict) else {}
        )
        grade = block.get("bind_min_grade")
        weights = getattr(resolution, "merge_weights", None) or {}

        def _w(key: str) -> float:
            v = weights.get(key)
            return float(v) if v is not None else 1.0

        return cls(
            enabled=bool(block.get("enabled", False)),
            authoritative_categories=_strs("authoritative_categories"),
            bind_min_grade=str(grade).strip().upper() if grade else None,
            equivalence_markers=_strs("equivalence_markers"),
            name_weight=_w(NAME),
            discriminator_weight=_w(DISCRIMINATOR),
            min_descriptor_len=min_desc,
            # Read from the top level (beside ``name_alone_caps_at_possible`` and ``possible_floor``, the
            # policy dials they belong with), falling back to the stage block so an operator who scoped them
            # there still gets them.
            name_ceiling=str(getattr(resolution, "name_ceiling", "") or _str("name_ceiling")),
            colocation_ceiling=str(
                getattr(resolution, "colocation_ceiling", "") or _str("colocation_ceiling")
            ),
            contrast_ceiling=str(
                getattr(resolution, "contrast_band_ceiling", "") or _str("contrast_ceiling")
            ),
            formation_types=_strs("formation_types"),
            presence_types=_strs("presence_types"),
            colocation_predicates=_strs("colocation_predicates"),
            formation_discriminators=_strs("formation_discriminators"),
            wall_predicates=_strs("wall_predicates"),
            wall_scope_attr=_str("wall_scope_attr"),
            value_normalization=normalization,
            normalization_required_attrs=_strs("normalization_required_attrs"),
            attribute_roles_overlay=overlay,
        )

    def normalise_value(self, attr: str, value: object) -> tuple[str, bool]:
        """A stated attribute value → ``(canonical, mapped)`` — C7's normalisation prerequisite.

        Casefolds and collapses punctuation/whitespace on both sides, so only genuine synonyms need an
        entry ('PAF' ≡ 'Pakistan Air Force', not 'CHINA' ≡ 'China'). ``mapped=True`` ⇒ the value is a
        known member of a declared equivalence class and may be compared — walled on, fused on, or used
        as a namespace key.

        ``mapped=False`` is the **third state** and the caller owes all three parts of it:
        **no wall** · **no fusion** · **a named gap**. Returning the folded form as the bucket gives the
        caller a stable comparison key for the *unknown* case without ever letting it de-conflict.
        An attribute with no declared classes at all is *not* normalization-required, so it reports
        ``mapped=True`` on its folded form — this is a wall prerequisite, not a whitelist of legal values.
        """
        folded = _fold_value(value)
        classes = dict(self.value_normalization).get(attr)
        if not classes:
            return folded, True  # nothing declared for this slot ⇒ no normalisation prerequisite
        for canonical, variants in classes:
            if folded == _fold_value(canonical) or any(folded == _fold_value(v) for v in variants):
                return _fold_value(canonical), True
        return folded, False


#: Casefold + collapse punctuation/whitespace, so only genuine synonyms need a config entry. Defined in
#: ``resolve.entities`` because ``Entity.namespace`` folds with no config in hand (the normaliser is
#: flag-gated) — one function, so the flag cannot change what counts as the same spelling.
_fold_value = fold_value

# STANAG-2022 source-reliability grades are an ORDINAL letter scale, A (most reliable) → F (least). The
# scale's letters are a domain constant, not a tunable — "at or above floor X" is therefore just the
# lexicographic test ``grade <= floor`` on a single uppercase letter (no numeric mapping, no scoring
# literal — gate G6 untouched; the floor value itself is read from config).
_GRADE_LETTERS = "ABCDEF"


def _validate_attribute_roles(roles: Any) -> None:
    """Reject a retired ``perishable:`` key or an unknown ``time_role`` — loudly, at construction (C6).

    "No migration shim outlives the stage that introduces it" (plan §5a-bis). A dual-form loader biases
    every later author toward the old shape, and a tolerated boolean cannot express ``constitutive`` or
    ``identifying`` — so the boolean is *gone*, and a config still carrying it must fail at load rather
    than quietly read as "no time role declared".
    """
    if not isinstance(roles, dict):
        return
    for entity_type, attrs in sorted(roles.items()):
        if not isinstance(attrs, dict):
            continue
        for attr, spec in sorted(attrs.items()):
            if not isinstance(spec, dict):
                continue
            if _LEGACY_PERISHABLE_KEY in spec:
                raise AttributeRoleError(
                    f"attribute_roles.{entity_type}.{attr} declares the retired boolean "
                    f"'{_LEGACY_PERISHABLE_KEY}:' — C6 replaced it with '{_TIME_ROLE_KEY}:' taking one of "
                    f"{list(TIME_ROLES)}. A boolean cannot carry three states, and no migration shim "
                    f"outlives its stage: rewrite 'perishable: true' as 'time_role: perishable' and "
                    f"'perishable: false' as 'time_role: durable'."
                )
            role = spec.get(_TIME_ROLE_KEY)
            if role is not None and role not in TIME_ROLES:
                raise AttributeRoleError(
                    f"attribute_roles.{entity_type}.{attr} declares {_TIME_ROLE_KEY}={role!r}, which is "
                    f"not one of {list(TIME_ROLES)} (C6)."
                )


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
        self._earned: EarnedIdentity = EarnedIdentity.from_resolution(resolution)
        # C6: validate the declared time roles ONCE, here, rather than at every hot read. A retired
        # ``perishable:`` key must be a **loud** error at construction (the same loudness S1 gave a bare
        # ``attrs`` string), not a value silently read as ``None`` deep inside the scorer.
        _validate_attribute_roles(self._extra("attribute_roles", {}))
        _validate_attribute_roles(self._earned.attribute_roles_overlay)

    @classmethod
    def from_bundle(cls, config: ConfigBundle) -> ResolveConfig:
        return cls(config.resolution, config.places, config.entities, bundle=config)

    # ── extra-knob access (extra="allow" fields authored by DATA-C) ───────────────────────────
    def _extra(self, name: str, default: Any) -> Any:
        return getattr(self._r, name, default)

    def _place_extra(self, name: str, default: Any) -> Any:
        return getattr(self._p, name, default)

    # ── the RK-COREF (S3) stage flag ──────────────────────────────────────────────────────────
    @property
    def earned_identity(self) -> EarnedIdentity:
        """The S3 knob block. ``.enabled`` False ⇒ every S3 mechanism is inert (flag-off byte-identity)."""
        return self._earned

    @property
    def earned_identity_on(self) -> bool:
        """The one flag test, so the boundary is read from exactly one place."""
        return self._earned.enabled

    @property
    def namespace_normaliser(self) -> Any:
        """C7's value normaliser for the **namespace** key, or ``None`` with the flag off.

        Namespaces are derived from raw stated attrs (``Entity.namespace``), so normalising only at
        conflict-detection time would fix the wall and leave the *blocking* split — 'PAF' and 'Pakistan Air
        Force' would still sit in two different namespaces, which is half of D4 left open. Handed to
        ``Entity.namespace`` / ``namespace_compatible`` as a plain callable so ``resolve.entities`` never has
        to import this reader.
        """
        if not self._earned.enabled:
            return None
        earned = self._earned

        def _norm(attr: str, value: Any) -> str:
            canonical, _mapped = earned.normalise_value(attr, value)
            return canonical

        return _norm

    @property
    def layer_routing(self) -> LayerRouting:
        """S2's layer block — read here **only** for its ``site_type`` vocabulary + normaliser.

        G18's ``based-at`` half fires within one *site class* (C1), and the closed vocabulary plus its
        fail-safe already live there (ruling L1). Reading them rather than declaring a second copy is the
        point: C1 is "one declaration, two consumers", and two vocabularies would drift. Note this reads the
        vocabulary irrespective of ``layer_routing.enabled`` — the *declaration* is unconditional; what S2's
        flag gates is the *keying*, which is a different consumer.
        """
        ontology = self._bundle.ontology if self._bundle is not None else OntologyConfig()
        return LayerRouting.from_ontology(ontology)

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

        Two lists feed this, and they answer to different switches:

        * the **legacy top-level** ``coref_authoritative_evidence`` — the pre-S3 operator knob, honoured
          whatever the stage flag says, because an operator who wrote it meant it. It ships ``[]``.
        * ``earned_identity.authoritative_categories`` — the **stage's** opt-in, read **only while the
          stage flag is on**, exactly like every restraint S3 introduces.

        That gating is the load-bearing part, and it was measured missing. S3 authorises two categories;
        S3's caps, walls, decline and doc-scoping all early-return with the flag off. Union the two lists
        unconditionally and the shipped **flag-off** deployment gets the authorisation without a single one
        of the restraints — strictly *less* safe than flag-on. Measured on the shipped bundle: two
        co-located formations fused at ``confirmed`` (flag-on: ``probable``, capped), a pair the document
        explicitly contrasts fused at ``confirmed`` (flag-on: ``probable``), and a bind licensed by one
        document spread onto a profile built from another. Authorisation and restraint now flip together.

        A category listed by either route still clears every other rail — the ``distinct-from`` veto, type
        and namespace agreement, the hard-attribute-contradiction check (``scoring.has_hard_conflict``) —
        and **its own per-link deterministic gate plus a source-grade floor** (D-13.17). Those are properties
        of the *pair* and stay flag-independent: a bind is licensed by evidence or it is not. What the stage
        flag decides is the prior question — whether the operator has authorised the category at all.
        """
        legacy = {str(c) for c in self._extra("coref_authoritative_evidence", [])}
        if not self.earned_identity_on:
            return legacy
        return legacy | set(self._earned.authoritative_categories)

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
        """``kind`` ∈ {unique, categorical} → {entity_type: [attr names]} (default empty).

        **Only bare-string rows** are returned. A row that is itself a list is a *composite AND-key* and is
        served by :meth:`unique_id_keys` instead — the two shapes coexist in one declaration because they
        answer the same question ("what identifies this type?") at different arities, and a flat consumer
        handed a list would compare an unhashable value and silently never match.
        """
        return {
            etype: [a for a in attrs if isinstance(a, str)]
            for etype, attrs in self._extra("hard_id_fields", {}).get(kind, {}).items()
        }

    def unique_id_keys(self, entity_type: str) -> list[tuple[str, ...]]:
        """The **composite AND-keys** that uniquely identify this type (D-13.20), or ``[]`` with the flag off.

        **The load-bearing call: a shared designation is NOT a unique identifier.** Designations are reused
        across armies and across time — "3rd Battalion" names a different unit in two services and a
        different unit in two decades — so one shared designation string may never confirm a formation merge.
        The mechanism is that ``hard_id_fields.unique`` holds a list of **composite AND-keys**:
        ``(service_branch, designator)`` is an identifier, a bare ``designator`` is not.

        That is stronger than declaring the designator a "non-perishable discriminator", because it makes the
        operator requirement **structural in the identifier declaration** rather than dependent on a separate
        namespace check — and that namespace check was measured broken in the Phase-2 fixpoint (D4). It also
        preserves the asymmetry the codebase already embodies for bills of lading, which must not be "fixed":
        **differing identifiers veto; shared ones do not confirm** unless the whole AND-key agrees.

        A bare-string row is read as a 1-tuple, so the legacy flat shape keeps its old meaning; the shipped
        config declares only composites. Gated on the stage flag because ``hard_id_fields`` is empty today,
        so declaring it at all would otherwise move the flag-off graph (the spike measured
        ``_shared_unique_id`` as permanently False for exactly this reason).
        """
        if not self._earned.enabled:
            return []
        rows = self._extra("hard_id_fields", {}).get("unique", {}).get(entity_type, [])
        out: list[tuple[str, ...]] = []
        for row in rows if isinstance(rows, (list, tuple)) else []:
            key = (str(row),) if isinstance(row, str) else tuple(str(a) for a in row)
            if key and key not in out:
                out.append(key)
        return out

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
        """Per-type attribute-role declarations (D6); default ``{}`` (every attribute neutral).

        The declarative block an author writes in ``config/resolution.yaml``::

            attribute_roles:
              <entity_type>:
                <attr_name>: {role: critical|supporting|neutral,
                              time_role: durable|perishable|constitutive|identifying}

        ``role`` decides identity bearing (compiled by :meth:`critical_role_attrs` /
        :meth:`supporting_role_attrs`); ``time_role`` (C6, re-specified) decides what the attribute's
        *agreement* and its *difference* mean over time — read by :meth:`attribute_time_role`. An
        attribute not listed here is **neutral** — no identity effect.

        Two stage markers, and the difference between them matters. A row carrying
        ``requires: earned_identity`` is consumed **only while that flag is on** — for rows S3 introduces, which
        have no earlier form. A row carrying ``earned_role:`` keeps its declared ``role`` flag-off and takes the
        override flag-on — for rows that **predate** S3, where dropping the row would delete a pre-S3
        declaration and move flag-off scoring by removing it from the agreement ratio. That
        marker is what lets C6's declarations live in this one block rather than in a parallel overlay: a new
        ``identifying`` or ``constitutive`` row *is* a behavioural change (it enters the agreement ratio and
        the durable-support test), so it cannot be consumed unconditionally without moving the flag-off graph
        — but hiding it elsewhere is exactly the inertness ruling M3 was written to prevent.
        """
        rows = dict(self._extra("attribute_roles", {}).get(entity_type, {}))
        if not self._earned.enabled:
            return {
                attr: spec for attr, spec in rows.items()
                if not (isinstance(spec, dict) and spec.get(_REQUIRES_KEY) == _REQUIRES_EARNED)
            }
        return {
            attr: ({**spec, "role": spec[_EARNED_ROLE_KEY]}
                   if isinstance(spec, dict) and spec.get(_EARNED_ROLE_KEY) else spec)
            for attr, spec in rows.items()
        }

    def _role_attrs(self, entity_type: str, role: str) -> list[str]:
        """Attributes of ``entity_type`` declared with ``role``, sorted (deterministic — gate G2)."""
        roles = self.attribute_roles(entity_type)
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

    def attribute_time_role(self, entity_type: str, attr: str) -> str | None:
        """The declared ``time_role`` of an attribute (C6) — one of :data:`TIME_ROLES`, or ``None``.

        ``None`` ⇒ the attribute declares no time role. An undeclared attribute is treated *as if* durable
        by every consumer (agreement counts, no succession waiver), which is the conservative direction:
        the waiver is an allowance a declaration has to *earn*.
        """
        spec = self.attribute_roles(entity_type).get(attr)
        if not isinstance(spec, dict):
            return None
        value = spec.get(_TIME_ROLE_KEY)
        return str(value) if value in TIME_ROLES else None

    def attribute_perishable(self, entity_type: str, attr: str) -> bool | None:
        """Is this attribute's value **transient**? — the boolean projection of :meth:`attribute_time_role`.

        Not a back-compat shim: it is the one question the *time-aware conflict* axis asks ("may a clean
        ordered succession of differing values be forgiven?"), and exactly one of the four time roles
        answers yes. ``perishable`` ⇒ ``True``; ``durable`` / ``constitutive`` / ``identifying`` ⇒
        ``False`` (a constitutive difference is **distinctness**, an identifying one is a different
        entity — neither is a legitimate update); undeclared ⇒ ``None``.
        """
        role = self.attribute_time_role(entity_type, attr)
        if role is None:
            return None
        return role == TIME_PERISHABLE

    def attribute_confirms_identity(self, entity_type: str, attr: str) -> bool:
        """May *agreement* on this attribute carry a confirm? (C6's positive half.)

        True for ``durable`` / ``constitutive`` / ``identifying`` **and for an undeclared attribute**
        (matching the pre-S3 ``attribute_perishable(...) is not True`` test byte-for-byte). ``constitutive``
        is what lets a **presence** confirm at all — its geography is definitional rather than perishable —
        and ``identifying`` is what lets a **place** confirm. Without those two rungs spine/13 §6 lever 2
        cannot exist.
        """
        role = self.attribute_time_role(entity_type, attr)
        return role is None or role in TIME_ROLES_CONFIRMING

    def constitutive_attrs(self, entity_type: str) -> list[str]:
        """Attributes declared ``constitutive`` for this type — a *difference* on one is DISTINCTNESS.

        A constitutive attribute cannot change without the thing being a *different* instance, so a stated
        difference is anti-identity evidence in its own right, whatever the attribute's ``role`` says.
        Consumed only with the S3 flag on (:meth:`earned_identity_on`).
        """
        roles = self.attribute_roles(entity_type)
        return sorted(
            a for a, spec in roles.items()
            if isinstance(spec, dict) and spec.get(_TIME_ROLE_KEY) == TIME_CONSTITUTIVE
        )

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
