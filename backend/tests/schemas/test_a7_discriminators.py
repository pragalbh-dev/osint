"""RK-ATOMS S1 item 4 — **A7's structured discriminators** + the structured ``TypeDef.attrs``.

Spec (``artifacts/plan/01-replumb-implementation-plan.md`` §4 **A7**):

    "**Structured discriminators** (operator, geography, unit designation, time) are emitted as
    **structured claim context**, not buried in the untyped ``attrs`` bag. This needs new fields on the
    ``extract.py`` mention schemas plus the ``config_models.py`` structured-attrs representation they are
    declared against … ``kind`` stays a *hint* the build may override. All fields **optional** — absence
    is ``unknown``, never fabricated."

and ``spine/13`` §10:

    "**Optional**, never required: a required field would force the extractor to fabricate a value the
    source didn't state (violating the non-negotiable) or drop the claim. Absence is recorded and treated
    as ``unknown``."

and the session file (item 4): "``TypeDef.attrs`` moves from a bare ``list[str]`` to structured entries".

**Ruling of 2026-07-25 (user directive, supersedes the earlier compatibility clause).** The legacy
bare-string ``attrs`` form is **removed entirely**, not kept for compatibility:

    "a dual-form loader biases every later implementer toward the old shape, and a 'temporary' tolerance
    is exactly how the ontology never migrates and the data never bends to the design
    (working-principles #1). **One form only, from now on.** … the S1 spec item — *'the loader still
    accepts the OLD bare-string attrs form so no config file must change in S1'* — is **withdrawn**.
    ``config/ontology.yaml`` is being migrated to the structured form instead, and a bare string in
    ``attrs`` must now be a **loud validation error** rather than a silent coercion."

So the risk this module guards has **moved**: not "does the loader accept both?" but "**did the migration
silently lose or rename an attribute?**". Three things are asserted, in both directions:
  * the four dimensions are **declared** as structured context (presence);
  * every extraction field stays **optional** and defaults to nothing — a required-field regression, or a
    fabricated placeholder default, fails here (absence);
  * ``TypeDef.attrs`` is **structured-only** — a bare string **raises** — and the real
    ``config/ontology.yaml`` loads under that schema with **every declared attribute surviving name-for-name**.

Per the same ruling, nothing here asserts anything about the per-attribute ``layer`` tag: that is A2/S2's
work, the entries stay name-only at S1, and a ``layer`` assertion here would fail S1 for work it does not own.
"""

from __future__ import annotations

import json

import pytest
import yaml

from chanakya.ingest import extract
from chanakya.schemas import OntologyConfig, TypeDef
from tests import _rk_atoms as rk

# The instance-layer citizen whose individuation is the whole point of A7: two co-located batteries are
# told apart by operator + geography + designation + time, never by name (D-13.20). Its mention schema is
# where the four discriminators have to be reachable.
_INSTANCE_MENTION = extract.UnitMention

_ONTOLOGY_YAML = rk.REPO_ROOT / "config" / "ontology.yaml"


# ── the four dimensions are declared as structured claim context ──────────────────────────────────

def test_the_instance_mention_declares_all_four_discriminator_dimensions() -> None:
    """A7: operator / geography / unit designation / time, as **structured** context on the mention.

    Scoped to the unit mention because that is the instance-layer citizen the discriminators individuate
    (spine/13 §3a, D-13.20). A dimension carried on a *nested* structured-context model counts — the spec
    asks for structure, not a particular nesting.
    """
    covered = rk.dimensions_covered(_INSTANCE_MENTION)
    missing = sorted(dim for dim, hits in covered.items() if not hits)

    assert not missing, (
        f"{_INSTANCE_MENTION.__name__} declares no structured field for {missing} — A7 requires all four "
        f"of operator/geography/designation/time as structured claim context. Declared: "
        f"{sorted(rk.reachable_fields(_INSTANCE_MENTION))}. (Field *names* are a spec silence: this test "
        f"matches the token sets in tests/_rk_atoms.py::DISCRIMINATOR_DIMENSIONS.)"
    )


@pytest.mark.parametrize("dimension", sorted(rk.DISCRIMINATOR_DIMENSIONS))
def test_every_discriminator_dimension_is_reachable_from_the_extraction_surface(dimension: str) -> None:
    """Each dimension must be declared somewhere the extractor can actually fill it (regression guard)."""
    hits: list[str] = []
    for model in extract.SCHEMAS.values():
        hits.extend(rk.dimensions_covered(model)[dimension])

    assert hits, f"no extraction schema declares a {dimension!r} discriminator field (A7)"


# ── all optional; absence is unknown, never fabricated ────────────────────────────────────────────

@pytest.mark.parametrize("fmt", sorted(extract.SCHEMAS))
def test_extraction_tool_schema_declares_no_required_field(fmt: str) -> None:
    """spine/13 §10: "a required field would force the extractor to fabricate a value the source didn't
    state (violating the non-negotiable) or drop the claim." A7's new fields must not break that."""
    schema = json.dumps(extract.SCHEMAS[fmt].model_json_schema())

    assert '"required"' not in schema, (
        f"the {fmt!r} tool schema now emits a `required` list — a required discriminator invites a "
        "fabricated value (A7: all fields optional)"
    )
    assert "additionalProperties" not in schema, (
        f"the {fmt!r} tool schema now emits `additionalProperties` — the tool schema must stay permissive"
    )


@pytest.mark.parametrize("fmt", sorted(extract.SCHEMAS))
def test_no_extraction_field_carries_a_fabricated_default(fmt: str) -> None:
    """Absence must read as *unknown* — never as a placeholder value the source never stated.

    A default of ``"unknown"``, ``"Pakistan"`` or ``0`` would put an unsourced value on a claim, which is
    fabrication by another route (CLAUDE.md non-negotiable).
    """
    offenders: list[str] = []
    for qualified, info in rk.reachable_fields(extract.SCHEMAS[fmt]).items():
        if info.is_required():
            offenders.append(f"{qualified} is REQUIRED (A7: all fields optional)")
            continue
        default = info.get_default(call_default_factory=True)
        if default not in (None, "", [], {}, ()):
            offenders.append(f"{qualified} defaults to {default!r}")

    assert not offenders, (
        "extraction field(s) would put an unsourced value on a claim: " + "; ".join(offenders)
    )


@pytest.mark.parametrize("fmt", sorted(extract.SCHEMAS))
def test_an_empty_mention_carries_no_discriminator_value(fmt: str) -> None:
    """The behavioural half of "absence is ``unknown``": nothing is filled in when the source is silent."""
    model = extract.SCHEMAS[fmt]
    instance = model()  # every field optional ⇒ constructible with no input at all

    dims = rk.dimensions_covered(model)
    for dimension, qualified_names in dims.items():
        for qualified in qualified_names:
            owner, leaf = qualified.rsplit(".", 1)
            if owner != model.__name__:
                continue  # nested models are only reachable once the parent field is filled
            value = getattr(instance, leaf)
            assert value in (None, "", [], {}, ()), (
                f"{qualified} ({dimension}) is pre-filled with {value!r} on an empty mention — "
                "absence must read unknown, never a fabricated discriminator"
            )


# ── TypeDef.attrs is STRUCTURED-ONLY — the bare-string form is removed, not tolerated ──────────────

def test_typedef_accepts_structured_attr_entries() -> None:
    """Session file item 4: ``TypeDef.attrs`` "moves from a bare ``list[str]`` to structured entries"."""
    td = TypeDef.model_validate({"name": "unit", "attrs": [{"name": "designator"},
                                                           {"name": "service_branch"}]})

    assert rk.attr_names(td) == ["designator", "service_branch"], (
        "TypeDef.attrs does not accept a structured entry — A7's config half is not landed"
    )


def test_a_bare_string_attr_entry_is_rejected() -> None:
    """Ruling of 2026-07-25: "a bare string in ``attrs`` must now be a **loud validation error** rather
    than a silent coercion" — "**One form only, from now on.**"

    The failure mode this excludes is not a crash but a *quiet* one: a coerced bare string leaves the
    config looking migrated while the entry carries none of the structure later stages read off it, and
    "a 'temporary' tolerance is exactly how the ontology never migrates".
    """
    with pytest.raises(ValueError):
        TypeDef.model_validate({"name": "unit", "attrs": ["echelon", "designator", "service_branch"]})


def test_a_mixed_bare_and_structured_attrs_list_is_rejected() -> None:
    """A half-migrated type is the likeliest botched-migration artefact, and must fail loudly.

    Same ruling: one form only. A loader that accepts the mixture would let a partial migration ship
    looking complete — the bare half silently carrying no structure.
    """
    with pytest.raises(ValueError):
        TypeDef.model_validate({"name": "unit", "attrs": ["echelon", {"name": "designator"}]})


def test_a_structured_entry_with_no_name_is_rejected_or_unreadable() -> None:
    """The negative direction: an entry that names no attribute declares nothing.

    Either the loader rejects it, or ``attr_names`` must fail loudly — what must never happen is a
    silently empty per-type attribute vocabulary.
    """
    try:
        td = TypeDef.model_validate({"name": "unit", "attrs": [{"freshness_class": "durable"}]})
    except ValueError:
        return  # rejected at load — the strictest correct answer
    with pytest.raises(AssertionError):
        rk.attr_names(td)


# ── the real config/ontology.yaml under the structured-only schema (the migration net) ──────────────
#
# The pre-migration attribute vocabulary, captured verbatim from `config/ontology.yaml` on
# `design/resolution-redesign` @ d7e443c — i.e. BEFORE the structured migration ran. 13 types, 88
# attribute names. This is the yardstick a botched migration is measured against: the migration may add,
# but it may never silently lose or rename.
PRE_MIGRATION_ATTRS: dict[str, list[str]] = {
    "manufacturer": ["role", "tier", "foreign_control", "named_examples", "production_rate",
                     "export_agent", "place_ref"],
    "trading_org": ["role", "origin_country", "foreign_control", "place_ref"],
    "component": ["component_class", "functional_role", "model_designation", "radar_band",
                  "host_chassis", "observable_fingerprint", "foreign_control"],
    "variant": ["family", "base_designator", "export_designator", "aliases", "range_class", "range_km",
                "operator_branch", "associated_rounds", "associated_radars"],
    "contract_import_event": ["event_subtype", "quantity", "count_state", "variant_delivered",
                              "linked_unit", "evidence_date"],
    "unit": ["echelon", "designator", "service_branch", "parent_unit", "equipment_fingerprint",
             "count_state", "home_garrison"],
    "basing_site": ["coordinates", "site_type", "site_signature_geometry", "occupancy_state",
                    "occupancy_observed_date", "decoy_risk_flag"],
    "area_of_operations": ["area_kind", "admin_level", "coordinates", "occupancy_state"],
    "interceptor_stockpile": ["stocked_round", "magazine_depth", "consumption_rate", "days_of_supply",
                              "resupply_lead_time", "production_sole_source_flag", "foreign_control"],
    "techdata_authority": ["holds", "foreign_control"],
    "source": ["source_type", "primary_origin_id", "aggregator_of", "bias_vector",
               "coordinated_inauthenticity_flag", "adversary_denial_flag", "reliability_grade",
               "citation_url"],
    "indicator": ["indicator_class", "lifecycle_stage", "observation_date", "valid_time",
                  "resolved_entity_ref", "edge_instance_ref", "artifact_integrity", "first_seen",
                  "caption_vs_image_consistency", "evidentiary_strength"],
    "known_gap": ["observability_ceiling", "next_coverage_due", "related_ref", "missing_slots"],
}


def _repo_ontology() -> tuple[dict, OntologyConfig]:
    if not _ONTOLOGY_YAML.exists():  # pragma: no cover — repo-root config absent in a partial checkout
        pytest.skip("repo-root config/ontology.yaml absent")
    raw = yaml.safe_load(_ONTOLOGY_YAML.read_text(encoding="utf-8")) or {}
    return raw, OntologyConfig.model_validate(raw)


def _all_types(ontology: OntologyConfig) -> list[TypeDef]:
    return [*ontology.node_types, *ontology.edge_types, *ontology.event_types]


def test_the_repo_ontology_config_loads_under_the_structured_only_schema() -> None:
    """The shipped config must itself be migrated — "``config/ontology.yaml`` is being migrated to the
    structured form instead" — so no bare string may survive in the file the app boots from.

    Asserted on the raw YAML *and* through the loader: if the file were still bare-string, a
    structured-only loader would raise here, which is the point of the ruling.
    """
    raw, ontology = _repo_ontology()

    bare: list[str] = []
    for section in ("node_types", "edge_types", "event_types"):
        for entry in raw.get(section) or []:
            for attr in entry.get("attrs") or []:
                if isinstance(attr, str):
                    bare.append(f"{entry.get('name')}.{attr}")
    assert not bare, (
        f"config/ontology.yaml still declares {len(bare)} bare-string attrs entries "
        f"(first few: {bare[:5]}) — the bare form is removed, not tolerated (ruling 2026-07-25)"
    )
    assert ontology.node_types, "config/ontology.yaml declares no node types"


def test_the_loader_round_trips_the_shipped_attribute_names_name_for_name() -> None:
    """Whatever the file declares is exactly what the loader yields — no drop, no reorder, no rename.

    This is the loader half of the migration net: it compares the parsed model against the *file*, so it
    stays honest as DATA-C edits the ontology, and it fails if the structured entry ever starts swallowing
    a name.
    """
    raw, ontology = _repo_ontology()

    declared: dict[str, list[str]] = {}
    for section in ("node_types", "edge_types", "event_types"):
        for entry in raw.get(section) or []:
            declared[entry["name"]] = [rk.raw_attr_name(a) for a in entry.get("attrs") or []]

    compared = 0
    for td in _all_types(ontology):
        assert rk.attr_names(td) == declared[td.name], (
            f"{td.name}: the loader yields {rk.attr_names(td)} but the file declares {declared[td.name]}"
        )
        compared += len(declared[td.name])

    # Non-vacuity: an empty-vs-empty comparison would pass while checking nothing. The shipped ontology
    # declares 81 attribute names across 13 types, so anything near zero means the read broke, not that
    # the round-trip held.
    assert compared >= 81, (
        f"the round-trip compared only {compared} attribute names — the file read or the loader returned "
        "an empty vocabulary, so this test proved nothing"
    )


def _migration_losses(loaded: dict[str, list[str]]) -> tuple[list[str], dict[str, list[str]]]:
    """``(dropped type names, {type: attribute names lost})`` measured against the frozen yardstick.

    Factored out so the real check and its negative control below run **identical** logic — a guard whose
    detection path is only ever exercised on passing input is a guard nobody has tested.
    """
    dropped = sorted(set(PRE_MIGRATION_ATTRS) - set(loaded))
    lost = {
        type_name: gone
        for type_name, expected in PRE_MIGRATION_ATTRS.items()
        if type_name in loaded and (gone := [a for a in expected if a not in loaded[type_name]])
    }
    return dropped, lost


def test_the_frozen_pre_migration_yardstick_is_intact() -> None:
    """The yardstick must not be quietly trimmed to make the migration look lossless.

    ``PRE_MIGRATION_ATTRS`` was captured from ``config/ontology.yaml`` at ``design/resolution-redesign``
    @ ``d7e443c`` — **before** the structured migration ran — and independently of the implementer's own
    before/after diff. Pinning its size is what stops a future edit from deleting a row of the yardstick
    instead of fixing the migration.
    """
    assert len(PRE_MIGRATION_ATTRS) == 13
    assert sum(len(v) for v in PRE_MIGRATION_ATTRS.values()) == 81
    for type_name, names in PRE_MIGRATION_ATTRS.items():
        assert names, f"{type_name} has an empty attribute list in the yardstick"
        assert len(set(names)) == len(names), f"{type_name} repeats an attribute in the yardstick"


def test_the_structured_migration_loses_no_declared_attribute() -> None:
    """The content half of the migration net: the pre-migration vocabulary must survive in full.

    The risk has moved from "does the loader accept both forms?" to "did the migration silently lose or
    rename an attribute?" — a dropped attribute is a silently narrower ontology, and a renamed one detaches
    every claim already carrying the old key. Additions are fine; losses are not.
    """
    _, ontology = _repo_ontology()
    loaded = {td.name: rk.attr_names(td) for td in _all_types(ontology)}

    dropped, lost = _migration_losses(loaded)

    assert not dropped, f"the migration dropped whole type(s): {dropped}"
    assert not lost, (
        f"the structured migration lost or renamed declared attribute(s): {lost} — the ontology is now "
        "silently narrower than before the migration"
    )


def test_the_migration_loss_check_detects_a_planted_loss() -> None:
    """The negative control that makes the guard above non-vacuous (§5a: a gate that cannot fail lies).

    Two plausible botched-migration artefacts, on a synthetic post-migration vocabulary: one attribute
    dropped outright, one **renamed** (the sneakier case — the count still looks right).
    """
    intact = {name: list(names) for name, names in PRE_MIGRATION_ATTRS.items()}
    assert _migration_losses(intact) == ([], {}), "the loss check fires on a lossless migration"

    lossy = {name: list(names) for name, names in PRE_MIGRATION_ATTRS.items()}
    lossy["variant"].remove("range_km")                                  # dropped
    lossy["unit"][lossy["unit"].index("designator")] = "unit_designator"  # renamed
    del lossy["known_gap"]                                               # whole type gone

    dropped, lost = _migration_losses(lossy)

    assert dropped == ["known_gap"]
    assert lost == {"variant": ["range_km"], "unit": ["designator"]}
