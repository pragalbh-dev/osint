"""Discovery helpers for the RK-LAYER (S2) suite — authored from the spec, not from the implementation.

The S2 spec (``artifacts/plan/01-replumb-implementation-plan.md`` §4 **A2/A3/A4** + §7 **RK-LAYER**,
``artifacts/plan/sessions/RK-LAYER.md``, ``artifacts/spine/13-…`` §3a/§5 + D-13.3/5/6/13/14) fixes the
*concepts* this stage must land —

* "Every ``node_type`` **and** every ``attribute_type`` in ``config/ontology.yaml`` gains a ``layer`` tag
  (design | instance) … The ``ontology.py`` layer accessor reads it" (§4 A2);
* "a genuinely dual-natured attribute … is **split into two attribute-types**, one per layer — not made
  contextual" (§4 A2 / D-13.3);
* "an instance-layer edge whose mention named only the design **materializes a provisional presence**"
  (§7 RK-LAYER 2);
* "**Behind a flag**, dual-run only" (§7 RK-LAYER, Goal)

— but it never fixes the *identifiers*: not the layer accessor's name, not where a materialized node
records its layer, and not the name of the flag. This suite was written independently of the
implementation, so it **discovers** those names on the shipped surfaces and then asserts the specified
behaviour. Every discovery miss raises a loud, explanatory failure quoting the spec line it comes from;
none of them can pass for want of a guessed spelling.

The behavioural fixtures deliberately build on the **shipped** ``config/ontology.yaml`` rather than a
hand-written stub, because the layer tags *are* the thing under test: a fixture that declared its own
tags would test the fixture. Credibility / sources / resolution stay synthetic so the arithmetic is
controllable (the ``tests/credibility/builders`` idiom).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import yaml

import chanakya
from chanakya.config.store import ConfigStore
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    CredibilityConfig,
    DocRef,
    EntityDescriptor,
    ExactDate,
    OntologyConfig,
    ResolutionConfig,
    ResolvedRef,
    SourcesConfig,
    Triple,
)
from chanakya.schemas.view import EdgeView, NodeView
from chanakya.settings import config_dir
from chanakya.store import EvidenceLog
from chanakya.view import rebuild
from tests.credibility.builders import cred_config, source

PKG_ROOT = Path(chanakya.__file__).parent
REPO_ROOT = PKG_ROOT.parents[1]

#: A2's two layer values. Named in the plan as "(design | instance)" — the vocabulary, not a guess.
DESIGN, INSTANCE = "design", "instance"
LAYERS = (DESIGN, INSTANCE)

#: Node kinds ruling **L3** says are *neither* design nor instance — "system/meta kinds … Forcing a meta
#: type into ``design`` or ``instance`` would corrupt the straddle-split trigger, which fires precisely on a
#: layer *mismatch*". The ruling names five, three of them unarguably
#: (``tmp/conv/RK-LAYER-RULINGS.md`` L3); the two "arguably" ones are not asserted either way.
META_NODE_TYPES = ("source", "indicator", "known_gap")
ARGUABLY_META_NODE_TYPES = ("techdata_authority", "area_of_operations")

#: Types whose layer the design corpus fixes beyond argument: spine/13 §3 — "Type / design layer — variant,
#: component, radar, manufacturer" — and ruling L2 — "``unit`` is the **formation** citizen", i.e. instance.
FIXED_DESIGN_TYPES = ("variant", "component", "manufacturer")
FIXED_INSTANCE_TYPES = ("unit",)

#: The token every plausible spelling of A2's tag shares; the spec never fixes the rest.
LAYER_TOKEN = "layer"


# ── the shipped config (A2 is asserted on the REAL file, per the session's "81 attribute entries") ──

def shipped_bundle() -> ConfigBundle:
    """The real ``config/*.yaml`` bundle — what the app actually boots with."""
    return ConfigStore.seed_from(config_dir()).snapshot()


def shipped_ontology() -> OntologyConfig:
    return shipped_bundle().ontology


def shipped_ontology_yaml() -> dict[str, Any]:
    """``config/ontology.yaml`` as raw YAML — the file's own declaration, before any model default."""
    return yaml.safe_load((config_dir() / "ontology.yaml").read_text(encoding="utf-8")) or {}


def declared_attr_entries() -> list[tuple[str, dict[str, Any]]]:
    """``(node_type_name, raw attrs entry)`` for every attribute entry the FILE declares.

    Read off the YAML rather than the loaded model so a count assertion measures what an author wrote,
    not what a schema default filled in — a partial migration is the likeliest A2 defect.
    """
    out: list[tuple[str, dict[str, Any]]] = []
    raw = shipped_ontology_yaml()
    for section in ("node_types", "edge_types", "event_types"):
        for typedef in raw.get(section) or []:
            if not isinstance(typedef, dict):
                continue
            for entry in typedef.get("attrs") or []:
                out.append((str(typedef.get("name")), entry if isinstance(entry, dict) else {"name": entry}))
    return out


# ── reading a layer tag off a type / attribute entry ────────────────────────────────────────────

def _layer_keys(mapping: Any) -> dict[str, Any]:
    """Every key on a mapping/model whose name carries :data:`LAYER_TOKEN`."""
    if isinstance(mapping, dict):
        items = mapping.items()
    else:
        dump = getattr(mapping, "model_dump", None)
        items = (dump() if callable(dump) else vars(mapping)).items()
    return {k: v for k, v in items if LAYER_TOKEN in str(k).lower()}


def declared_layer(subject: Any, *, what: str) -> Any:
    """The layer this type/attribute entry declares. Fails loudly when it declares none.

    Tolerant of the field's exact spelling (``layer`` / ``node_layer`` / ``layers``) because A2 fixes the
    *values* — "(design | instance)" — and not the key. A key carrying a **list** of layers is returned as
    the list, so the D-13.3 dual-attribute rule can be asserted on it rather than silently accepted.
    """
    found = {k: v for k, v in _layer_keys(subject).items() if v is not None}
    assert found, (
        f"{what} declares no layer tag (plan §4 A2: 'Every node_type and every attribute_type in "
        f"config/ontology.yaml gains a layer tag (design | instance)'). Keys present: "
        f"{sorted(_layer_keys(subject)) or sorted(_as_dict(subject))}"
    )
    if len(found) > 1:
        raise AssertionError(
            f"{what} declares more than one layer-ish key {found} — A2 adds exactly one ('layer')"
        )
    return next(iter(found.values()))


def _as_dict(subject: Any) -> dict[str, Any]:
    if isinstance(subject, dict):
        return dict(subject)
    dump = getattr(subject, "model_dump", None)
    return dump() if callable(dump) else dict(vars(subject))


def node_types_by_layer() -> dict[str, list[str]]:
    """``layer -> [node type names]`` over the shipped ontology (unknown layers included as-is)."""
    out: dict[str, list[str]] = {}
    for t in shipped_ontology().node_types:
        try:
            layer = str(declared_layer(t, what=f"node type {t.name!r}"))
        except AssertionError:
            layer = "<undeclared>"
        out.setdefault(layer, []).append(t.name)
    return out


def layer_of_node_type(node_type: str | None) -> str | None:
    """The layer the shipped ontology declares for ``node_type`` (``None`` when it declares none)."""
    typedef = next((t for t in shipped_ontology().node_types if t.name == node_type), None)
    if typedef is None:
        return None
    try:
        return str(declared_layer(typedef, what=f"node type {node_type!r}"))
    except AssertionError:
        return None


def instance_node_types() -> list[str]:
    """Declared node types tagged instance-layer, in declaration order."""
    return [t.name for t in shipped_ontology().node_types
            if layer_of_node_type(t.name) == INSTANCE]


def presence_node_types() -> list[str]:
    """Instance-layer node types other than the formation citizen ``unit`` — ruling **L2**'s new type.

    L2: "add a new instance-layer node type for the presence citizen … ``unit`` is the **formation**
    citizen, and a presence is deliberately a *weaker* assertion than a formation." Reusing ``unit`` and
    refining ``unit`` are both explicitly rejected there, so the presence type is an instance-layer type
    that is neither ``unit`` nor a refinement of it.
    """
    refines = {t.name: getattr(t, "refines", None) for t in shipped_ontology().node_types}
    return [
        name for name in instance_node_types()
        if name not in FIXED_INSTANCE_TYPES and refines.get(name) not in FIXED_INSTANCE_TYPES
    ]


def site_type_vocabulary() -> dict[str, list[str]]:
    """``"section.key" -> [values]`` for every closed ``site_type`` vocabulary declared in config.

    Ruling **L1**: "``site_type`` is **unenumerated free text** … **S2 declares a closed ``site_type``
    vocabulary** in config (the *kind of place* axis only)". The location is not fixed by the ruling, so it
    is discovered: any list-of-strings under a key naming ``site_type``, anywhere in the bundle.
    """
    out: dict[str, list[str]] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, sub in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), sub)
        elif isinstance(value, (list, tuple)) and value and all(isinstance(v, str) for v in value):
            if "site_type" in prefix.lower():
                out[prefix] = list(value)

    walk("", shipped_bundle().model_dump())
    return out


def site_type_mapping() -> dict[str, str]:
    """Any declared *raw string → class* mapping for ``site_type``, folded for comparison.

    Ruling **L1** rule 4: "**Mapping the 15 existing values is DATA's job**, not S2's — S2 declares the
    vocabulary and the fail-safe; the data pass supplies the mapping. Until it lands, the third state is the
    correct, honest behaviour." So the mapping may legitimately be absent; where it exists it is discovered
    rather than guessed at.
    """
    out: dict[str, str] = {}

    def walk(prefix: str, value: Any) -> None:
        if not isinstance(value, dict):
            return
        if "site_type" in prefix.lower() and value and all(isinstance(v, str) for v in value.values()):
            out.update({str(k).strip().casefold(): str(v) for k, v in value.items()})
        for key, sub in value.items():
            walk(f"{prefix}.{key}" if prefix else str(key), sub)

    walk("", shipped_bundle().model_dump())
    return out


#: A plausible *kind of place*, used only while no vocabulary is declared. Stating **one identical string at
#: both ends** is a well-defined input either way — nothing can de-conflict two equal values — so the
#: same-class fixture stays meaningful before and after the vocabulary lands. The *differing*-class fixture has
#: no such fallback and must read the declared vocabulary.
_FALLBACK_CLASS = "garrison"


def same_class_pair() -> tuple[str, str]:
    """One declared site class, stated at **both** ends — the "this really is a relocation" input.

    C1/R1.3's middle case, and the discriminating input a mirror must state explicitly: same class ⇒ the two
    basings are one position over time ⇒ the relocation is real and must promote.
    """
    vocab = site_type_vocabulary()
    term = next(iter(vocab.values()))[0] if vocab else _FALLBACK_CLASS
    return (str(term), str(term))


def legal_layer_values() -> set[str]:
    """``{design, instance}`` plus whatever **single** third value the shipped config declares (**L3**).

    L3: "give ``layer`` a third value (or an explicit exemption) for kinds that are neither … **State the
    third value in config; do not leave it implicit.**" Discovered rather than hardcoded, so a rename of the
    meta value does not fail a test that is really about *classification*; that there is at most **one** extra
    value is asserted separately.
    """
    declared: set[str] = set()
    for typedef in shipped_ontology().node_types:
        try:
            declared.add(str(declared_layer(typedef, what=typedef.name)))
        except AssertionError:
            continue
    for _owner, entry in declared_attr_entries():
        try:
            declared.add(str(declared_layer(entry, what=str(entry.get("name")))))
        except AssertionError:
            continue
    return set(LAYERS) | {v for v in declared if v not in LAYERS}


def classify_site_type(stated: Any) -> str | None:
    """The declared class a stated ``site_type`` resolves to, or ``None`` when it cannot be classified.

    Ruling **L1** rule 2: "**The raw stated string is NEVER the key.** Keying happens on the normalized
    class." A value resolves if it *is* one of the declared vocabulary terms, or if a declared mapping sends
    it to one. Everything else — including an absent value — is L1's third state: *we do not know the class*.
    """
    if not isinstance(stated, str) or not stated.strip():
        return None
    folded = stated.strip().casefold()
    for values in site_type_vocabulary().values():
        for term in values:
            if folded == str(term).strip().casefold():
                return str(term)
    mapped = site_type_mapping().get(folded)
    return mapped if isinstance(mapped, str) else None


#: Attribute names that already exist and are **not** A3's numeric equipment count (they are state enums).
_NOT_A_COUNT = frozenset({"count_state"})

#: Name tokens that mark an attribute as A3's *figure*. Token-matched, not substring-matched, because
#: ``origin_country`` contains "count" and is a country — a substring test would report the count attribute
#: as already present and turn ruling L4's assertion green for the wrong reason.
_COUNT_TOKENS = frozenset({"count", "counts", "quantity", "qty", "number"})


def is_count_attr(name: str) -> bool:
    """Does this attribute name state a *figure* (how many), rather than a state or a country?"""
    if name in _NOT_A_COUNT:
        return False
    tokens = {t for t in name.lower().replace("-", "_").split("_") if t}
    return bool(tokens & _COUNT_TOKENS)


def equipment_count_attrs() -> dict[str, list[str]]:
    """``node_type -> [count-ish attribute names]`` — A3's sourced ``count``, per ruling **L4**.

    L4: "**No numeric equipment-count attribute** anywhere, though sourced figures exist on sighting
    events. This is A3's ``count``-as-a-sourced-attribute requirement having no home. **S2 owns the
    ontology, so S2 declares it** — and its default is ``unknown``".
    """
    out: dict[str, list[str]] = {}
    for typedef in shipped_ontology().node_types:
        names = [a.name for a in typedef.attrs if is_count_attr(a.name)]
        if names:
            out[typedef.name] = names
    return out


def straddle_pair() -> tuple[str, str]:
    """A ``(design-layer node type, instance-layer attribute)`` pair the shipped ontology declares.

    A4/D-13.5: "The split trigger is an *instance-layer attribute on a design-layer node* — that mismatch
    is the signal the extractor lumped two things together." So such a pair must EXIST in the declared
    schema, or the trigger is unreachable in production and the mechanism is dead code. Declaration order
    decides, so the answer is deterministic and reviewable in the YAML itself.
    """
    for t in shipped_ontology().node_types:
        try:
            if str(declared_layer(t, what=f"node type {t.name!r}")) != DESIGN:
                continue
        except AssertionError:
            continue
        for entry in t.attrs:
            try:
                layer = declared_layer(entry, what=f"{t.name}.{getattr(entry, 'name', entry)}")
            except AssertionError:
                continue
            if str(layer) == INSTANCE:
                return t.name, str(entry.name)
    raise AssertionError(
        "the shipped ontology declares no design-layer node type carrying an instance-layer attribute, "
        "so A4's split trigger — 'an instance-layer attribute on a design-layer node' (§7 RK-LAYER 2, "
        "D-13.5) — is unreachable in production. Declared layers: "
        f"{node_types_by_layer()}"
    )


# ── the layer accessor (§7 RK-LAYER 1: "a layer accessor in ontology.py") ───────────────────────

def layer_accessors() -> dict[str, Any]:
    """Public callables in ``chanakya.ontology`` (module- or index-level) whose name carries the token."""
    from chanakya import ontology as ont_module

    found: dict[str, Any] = {}
    for owner_name, owner in [("<module>", ont_module)] + [
        (name, obj) for name, obj in vars(ont_module).items()
        if isinstance(obj, type) and not name.startswith("_")
    ]:
        for attr in dir(owner):
            if attr.startswith("_") or LAYER_TOKEN not in attr.lower():
                continue
            value = getattr(owner, attr, None)
            if callable(value):
                found[f"{owner_name}.{attr}"] = value
    return found


# ── the staging flag is GONE, and asking for it is an ERROR ──────────────────────────────────────
#
# ``FLAG_TOKENS`` / ``flag_candidates`` / ``enable_layer_routing`` / ``flag_report`` lived here to *discover*
# the stage flags in the shipped config and switch them on for a behavioural test. There are no stage flags
# to discover: the layer split and the earned-identity machinery are unconditional, so the shipped bundle IS
# the behavioural bundle and a fixture that "turns the stage on" would be turning on something that is not a
# stage. The discovery harness is deleted rather than left returning an empty dict — a helper that always
# finds nothing reads as a broken search, not as an absent feature.
#
# Deleting it is only half. Both fixture builders here take ``**credibility`` and ``CredibilityConfig`` is
# ``extra="allow"``, so ``fixture_config(flag_on=False)`` did not fail when the parameter died — it filed a
# field named ``flag_on`` onto the credibility config, where nothing reads it. The caller believed it had
# pinned a stage; it had set a knob that does not exist, silently, and would have gone on believing it. That
# is the harness form of the exact defect this whole change is about: a surface bound BY NAME-GUESSING, which
# grades a stand-in while its failure text names the shipped code. So the retired names are refused
# explicitly, by name, with what to do instead.

#: Retired staging-flag keywords, with their replacement. Any fixture builder taking ``**credibility``
#: must run :func:`reject_dead_stage_kwargs` before the extras reach the config.
DEAD_STAGE_KWARGS = {
    "flag_on": (
        "the identity machinery is unconditional, so there is no stage for a fixture to pin — the shipped "
        "bundle IS the live one. Drop the keyword. (It used to call enable_layer_routing; once the flag died "
        "`**credibility` absorbed it into a credibility field nobody reads, so every caller silently got the "
        "opposite of an explicit pin.)"
    ),
    "earned_identity_on": (
        "the flag accessor is deleted; the shipped bundle is live. Vary a TUNABLE instead (a ceiling, a grade "
        "floor, a predicate list) via _rk_coref.with_resolution(earned_identity={...})."
    ),
}


class DeadStageKwarg(TypeError):
    """A fixture builder was handed a staging-flag keyword that no longer binds to anything."""


def reject_dead_stage_kwargs(where: str, kwargs: dict[str, Any]) -> None:
    """Fail loudly for a retired staging-flag keyword, rather than filing it as a credibility extra."""
    for dead, why in sorted(DEAD_STAGE_KWARGS.items()):
        if dead in kwargs:
            raise DeadStageKwarg(f"{where}({dead}=…) no longer binds to anything: {why}")

# ── reading the layer off a materialized view element ───────────────────────────────────────────

def view_layer(element: NodeView | EdgeView) -> Any:
    """The layer a rebuilt node/edge records, from a schema field or its ``attrs`` bag.

    ``NodeView`` is ``extra="forbid"`` and ``schemas/view.py`` is not in S2's owned paths, so the tag may
    legitimately live in ``attrs``. Either is accepted; absence returns ``None`` (the caller decides
    whether that is a failure).
    """
    for key, value in _layer_keys(element).items():
        if key != "attrs" and value is not None:
            return value
    for value in _layer_keys(getattr(element, "attrs", {}) or {}).values():
        if value is not None:
            return value
    return None


# ── the abstract fixture (corpus-independent, like G1/G2) ───────────────────────────────────────

#: The supersede quality floor, copied from ``tests/view/test_supersede.py`` so the two suites agree on
#: what "the floor cleared" means. A `strong` source clears it; a `weak` one cannot.
def _shipped_supersede_floor() -> dict[str, Any]:
    """The shipped ``supersede_floor``, READ rather than hand-copied.

    A hand-written copy silently omits any knob added later — which is exactly what happened once: a knob was
    added to the shipped floor, the copy did not have it, and R1.4(a)'s guard short-circuited so the fixture
    could never exercise it. (That knob, ``require_earned_identity``, is since deleted outright — a boolean
    with no number to tune was a switch for turning a prohibition off, and the prohibition is unconditional.)
    This module's own docstring already says knobs are "copied verbatim from the shipped ``credibility.yaml``
    rather than re-typed, so a fixture cannot pass or fail on a mis-guessed knob name"; this makes that true of
    the floor too. Falls back to the historical literals only if the shipped block is missing, so the helper
    cannot mask a deleted config section.
    """
    shipped = getattr(shipped_bundle().credibility, "supersede_floor", None)
    if isinstance(shipped, dict) and shipped:
        return dict(shipped)
    return {
        "min_band": "probable",
        "min_independent_looks": 1,
        "newer_status_allow": ["probable", "confirmed"],
        "blocking_gate_flags": ["adversary-denial", "decoy-risk", "contradiction"],
    }


SUPERSEDE_FLOOR = _shipped_supersede_floor()

#: Bands that keep a name-similar pair in the analyst's queue (`candidate`) rather than fusing it — used
#: to construct a *sub-confirmed identity* (R1.4). Values are the shipped ones' shape, not their content.
HITL_RESOLUTION = ResolutionConfig(
    merge_weights={"attribute": 0.40, "relational": 0.40, "temporal_consistency": 0.05,
                   "source_asserted": 0.15},
    bands={"auto_merge": 0.85, "hitl_low": 0.45, "possible_floor": 0.25},
    blocking_keys=["type", "name_token"],
)


def fixture_config(
    *,
    resolution: ResolutionConfig | None = None,
    supersede_floor: dict[str, Any] | None = None,
    **credibility: Any,
) -> ConfigBundle:
    """A minimal bundle over the **shipped ontology** (so the layer tags under test are the real ones).

    The basing-proposer knobs are copied verbatim from the shipped ``credibility.yaml`` rather than
    re-typed, so a fixture cannot pass or fail on a mis-guessed knob name.

    Raises :class:`DeadStageKwarg` for a retired staging-flag keyword — see :data:`DEAD_STAGE_KWARGS`.
    """
    reject_dead_stage_kwargs("fixture_config", credibility)
    shipped = shipped_bundle()
    proposer = getattr(shipped.credibility, "basing_proposer", None)
    cred: CredibilityConfig = cred_config(
        half_lives_days={"based-at": 365, "observed-at": 180, "inducted-into": 900},
        **({"basing_proposer": dict(proposer)} if isinstance(proposer, dict) else {}),
        **credibility,
    )
    if supersede_floor is not None:
        cred.supersede_floor = supersede_floor
    bundle = ConfigBundle(
        ontology=shipped.ontology,
        credibility=cred,
        sources=SourcesConfig(sources=[source("s", "strong"), source("s2", "text"),
                                       source("adv", "weak")]),
        resolution=resolution or ResolutionConfig(),
    )
    return bundle


def entity_claim(
    eid: str, etype: str, *, name: str | None = None, attrs: dict[str, Any] | None = None,
    sid: str = "s", cid: str | None = None,
) -> ClaimRecord:
    """A declared entity, pinned to a stable node id so assertions can name it."""
    return ClaimRecord(
        claim_id=cid or f"ent-{eid}", source_id=sid, doc_ref=DocRef(file=f"{eid}.txt"),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(entity_type=etype, name=name or eid, attrs=attrs or {}),
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def rel_claim(
    cid: str, subject: str, predicate: str, obj: str, *, iso: str | None = "2025-01-01",
    sid: str = "s", attributes: dict[str, Any] | None = None, kind: str = "observation",
    premises: list[str] | None = None,
) -> ClaimRecord:
    """A relationship claim with ``resolved_ref=None`` so the PRODUCTION key builder mints the instance."""
    return ClaimRecord(
        claim_id=cid, source_id=sid, doc_ref=DocRef(file=f"{cid}.txt"),
        kind=kind, asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=iso) if iso else None,
        attributes=attributes,
        premises=premises or [],
    )


def attr_claim(
    cid: str, eid: str, etype: str, attrs: dict[str, Any], *, name: str | None = None, sid: str = "s",
    iso: str | None = "2025-01-01",
) -> ClaimRecord:
    """A second entity claim carrying only *facts about* an existing node — what A4 routes by layer.

    There is no separate ``asserts="attribute"`` form: an attribute rides on an entity claim
    (``EntityDescriptor.attrs``), and the pipeline folds it onto the node the ``resolved_ref`` names.
    """
    return ClaimRecord(
        claim_id=cid, source_id=sid, doc_ref=DocRef(file=f"{cid}.txt"),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(entity_type=etype, name=name or eid, attrs=attrs),
        resolved_ref=ResolvedRef(entity_id=eid),
        event_time=ExactDate(iso_date=iso) if iso else None,
    )


def coords(lat: float, lon: float, raw: str = "site") -> dict[str, Any]:
    """A frozen WGS84 coordinate in the slot INGEST uses, so the site is a *locatable* base."""
    return {"coordinates": {"wgs84_lat": lat, "wgs84_lon": lon, "raw": raw}}


def build_view(config: ConfigBundle, claims: list[ClaimRecord], decisions: list[Any] | None = None):
    log = EvidenceLog()
    log.append_many(claims)
    return rebuild(log, decisions or [], config)


def edges_of(view: Any, edge_type: str) -> list[EdgeView]:
    return sorted((e for e in view.edges if e.type == edge_type), key=lambda e: e.id)


def nodes_of(view: Any, node_type: str) -> list[NodeView]:
    return sorted((n for n in view.nodes if n.type == node_type), key=lambda n: n.id)


# ── static scanning (G17's extension) ───────────────────────────────────────────────────────────

def _module_path(dotted: str, root: Path) -> list[Path]:
    """``chanakya.a.b`` → the file(s) that define it, under ``root``."""
    rel = dotted.split(".", 1)[1] if "." in dotted else ""
    base = root / Path(*rel.split(".")) if rel else root
    return [p for p in (base.with_suffix(".py"), base / "__init__.py") if p.is_file()]


def _imports_of(path: Path, root: Path) -> set[str]:
    """Absolute ``chanakya.*`` module names imported by ``path``, **including relative imports**.

    ``tests/gates/_srcscan.imported_modules`` reads ``node.module`` only, so ``from .supersede import x``
    is invisible to it — and the whole rebuild call-path is written with relative imports, which would make
    a reachability scan built on it silently tiny (and G17's static form vacuous).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    pkg = ".".join(("chanakya", *path.relative_to(root).parts[:-1]))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names if a.name.startswith("chanakya"))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: walk up `level - 1` packages from this file's package
                parts = pkg.split(".")
                anchor = ".".join(parts[: len(parts) - (node.level - 1)]) if node.level > 1 else pkg
                base = f"{anchor}.{node.module}" if node.module else anchor
            else:
                base = node.module or ""
            if not base.startswith("chanakya"):
                continue
            out.add(base)
            # `from chanakya.view import supersede` — the alias may itself be a module.
            out.update(f"{base}.{a.name}" for a in node.names)
    return out


def rebuild_reachable_modules(root: Path | None = None) -> list[Path]:
    """The ``chanakya`` modules reachable from ``view.pipeline`` by import — G17's static scan surface.

    An input-independent scan (the plan's second accepted form: "or use an input-independent static
    call-graph scan of rebuild-reachable modules"). Walked transitively from ``view/pipeline.py`` so a
    derivation moved into a helper module is still in scope.
    """
    base = root or PKG_ROOT
    start = base / "view" / "pipeline.py"
    seen: set[Path] = set()
    queue: list[Path] = [start]
    while queue:
        path = queue.pop()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for mod in _imports_of(path, base):
            queue.extend(_module_path(mod, base))
    return sorted(seen)


def _dotted(expr: ast.expr) -> str:
    """A best-effort dotted rendering of a call receiver (``self.store.append`` → ``self.store``)."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return f"{_dotted(expr.value)}.{expr.attr}"
    if isinstance(expr, ast.Call):
        return _dotted(expr.func)
    return type(expr).__name__


#: Receiver-name substrings that mark an ``.append(…)`` as a write to the **append-only evidence log**
#: rather than to a local list. G17 forbids ``store.append`` under ``rebuild()``; a python list append is
#: not an evidence write, and a scan that flagged both would be noise rather than a gate.
STORE_RECEIVER_TOKENS: tuple[str, ...] = ("store", "log", "evidence", "journal")

#: The append-only write surface (``chanakya.store.EvidenceLog``) and the atom constructors.
APPEND_METHODS = frozenset({"append", "append_many"})
MINT_FUNCTIONS = frozenset({"make_claim_id", "make_referent_id"})


def forbidden_writes_in(paths: list[Path], root: Path | None = None) -> dict[str, list[str]]:
    """``"what" -> ["module.py:lineno", …]`` for every claim mint / evidence-log append in ``paths``.

    The two clauses G17-as-extended names, scanned as one pass: ``make_claim_id`` / ``make_referent_id``
    calls, and ``<something store/log-ish>.append(_many)``.
    """
    base = root or PKG_ROOT
    hits: dict[str, list[str]] = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            where = f"{path.relative_to(base)}:{node.lineno}"
            func = node.func
            if isinstance(func, ast.Name) and func.id in MINT_FUNCTIONS:
                hits.setdefault(func.id, []).append(where)
            elif isinstance(func, ast.Attribute):
                if func.attr in MINT_FUNCTIONS:
                    hits.setdefault(func.attr, []).append(where)
                elif func.attr in APPEND_METHODS:
                    receiver = _dotted(func.value).lower()
                    if any(tok in receiver for tok in STORE_RECEIVER_TOKENS):
                        hits.setdefault(f"{_dotted(func.value)}.{func.attr}", []).append(where)
    return {k: sorted(v) for k, v in hits.items()}
