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

and the session file (item 4): "``TypeDef.attrs`` moves from a bare ``list[str]`` to structured entries";
plus its binding correction: "S1 restructures it, S2 adds ``layer``. Design the entry so S2 adds a field
and nothing else is reshaped."

Three things are therefore asserted, in both directions:
  * the four dimensions are **declared** as structured context (presence);
  * every extraction field stays **optional** and defaults to nothing — a required-field regression, or a
    fabricated placeholder default, fails here (absence);
  * ``TypeDef`` accepts the **new structured** entries **and the old bare strings**, so **no config file
    has to change in S1** — and the repo's real ``config/ontology.yaml`` still loads.
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


# ── TypeDef.attrs: structured entries, without breaking the bare-string form ───────────────────────

def test_typedef_still_accepts_the_old_bare_string_attrs_form() -> None:
    """Session file, Acceptance: S1 is non-breaking — "no config file must change in S1"."""
    td = TypeDef.model_validate({"name": "unit", "attrs": ["echelon", "designator", "service_branch"]})

    assert rk.attr_names(td) == ["echelon", "designator", "service_branch"]


def test_typedef_accepts_structured_attr_entries() -> None:
    """Session file item 4: ``TypeDef.attrs`` "moves from a bare ``list[str]`` to structured entries"."""
    td = TypeDef.model_validate({"name": "unit", "attrs": [{"name": "designator"},
                                                           {"name": "service_branch"}]})

    assert rk.attr_names(td) == ["designator", "service_branch"], (
        "TypeDef.attrs does not accept a structured entry — A7's config half is not landed"
    )


def test_attribute_names_read_the_same_from_either_form() -> None:
    """One vocabulary, two spellings: whatever reads the attrs must not care which form a config used."""
    bare = TypeDef.model_validate({"name": "unit", "attrs": ["designator"]})
    structured = TypeDef.model_validate({"name": "unit", "attrs": [{"name": "designator"}]})

    assert rk.attr_names(bare) == rk.attr_names(structured) == ["designator"]


def test_a_structured_attr_entry_tolerates_an_unfamiliar_key() -> None:
    """The S1→S2 seam: "Design the entry so **S2 adds a field** and nothing else is reshaped."

    S2 adds the per-attribute ``layer``; if the entry forbids unknown keys, S2's config lands as a
    validation error instead of an added field.
    """
    td = TypeDef.model_validate({"name": "unit", "attrs": [{"name": "designator", "layer": "instance"}]})

    assert rk.attr_names(td) == ["designator"]


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


def test_mixed_bare_and_structured_entries_in_one_type_still_read() -> None:
    """A partially-migrated config must not silently drop half its vocabulary."""
    td = TypeDef.model_validate({"name": "unit", "attrs": ["echelon", {"name": "designator"}]})

    assert rk.attr_names(td) == ["echelon", "designator"]


def test_the_repo_ontology_config_still_loads_after_the_restructure() -> None:
    """The headline non-breaking check, against the real file: ``config/ontology.yaml`` is untouched in S1."""
    if not _ONTOLOGY_YAML.exists():  # pragma: no cover — repo-root config absent in a partial checkout
        pytest.skip("repo-root config/ontology.yaml absent")
    raw = yaml.safe_load(_ONTOLOGY_YAML.read_text(encoding="utf-8")) or {}

    ontology = OntologyConfig.model_validate(raw)

    assert ontology.node_types, "config/ontology.yaml declares no node types"
    for td in [*ontology.node_types, *ontology.edge_types, *ontology.event_types]:
        names = rk.attr_names(td)
        assert all(isinstance(n, str) and n for n in names), f"{td.name} has an unreadable attr entry"
    variant = next(td for td in ontology.node_types if td.name == "variant")
    assert "operator_branch" in rk.attr_names(variant), (
        "the restructure lost a declared attribute name from the real ontology"
    )
