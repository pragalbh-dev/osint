"""The shipped ``config/resolution.yaml`` ``attribute_roles`` block (D5/D6) — the two attributes touched
by the RESOLUTION-REDESIGN additive extraction-schema pass: the new ``unit.alert_posture`` (supporting +
perishable) and the pre-existing, untouched ``variant.operator_branch`` (critical).

Corpus-independent: reads only the declared config schema (``ResolveConfig.attribute_roles`` /
``attribute_perishable`` / ``supporting_role_attrs`` / ``critical_role_attrs``), never a corpus document
or the answer key. Mirrors ``tests/config/test_entities_config.py`` / ``test_places_config.py`` — the
established pattern for asserting against the real, seeded config directory rather than a synthetic
``mk_config`` fixture (which is what ``tests/resolve/test_attribute_roles.py`` pins the MECHANISM with).
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.settings import config_dir


def _cfg() -> ResolveConfig:
    """The shipped config. There is no stage flag left to pin it either side of."""
    return ResolveConfig.from_bundle(ConfigStore.seed_from(config_dir()).snapshot())


def test_unit_alert_posture_declared_supporting_and_perishable() -> None:
    cfg = _cfg()
    spec = cfg.attribute_roles("unit").get("alert_posture")
    assert spec is not None, "unit.alert_posture must be declared in config/resolution.yaml"
    assert spec.get("role") == "supporting"
    assert cfg.attribute_perishable("unit", "alert_posture") is True
    assert "alert_posture" in cfg.supporting_role_attrs("unit")
    # a supporting attribute is never a hard wall
    assert "alert_posture" not in cfg.critical_role_attrs("unit")


def test_the_two_operator_scoped_slots_are_critical() -> None:
    """``unit.service_branch`` and ``trading_org.origin_country`` are WALLS — and normalisation is why.

    Both were ``supporting`` (i.e. inert) for one stated reason: the corpus writes them unnormalised
    ('Air Force' / 'PAF' / 'Pakistan Air Force'; 'CHINA' vs 'China'), and an exact-match wall on those
    "SHATTERS legitimate merges". ``value_normalization`` removes that objection and now runs
    unconditionally, so a genuinely different service branch is a different unit and a genuinely different
    country of origin is a different company.

    ``origin_country`` is asserted here because it was the slot left behind: its normalisation rows shipped
    while the promotion did not, so the prerequisite existed and the wall did not. For an operator-scoped
    order of battle two same-named organisations in two countries is the costliest over-merge there is.
    """
    cfg = _cfg()
    assert "service_branch" in cfg.critical_role_attrs("unit")
    assert cfg.attribute_perishable("unit", "service_branch") is False
    assert "origin_country" in cfg.critical_role_attrs("trading_org")
    # …and the normalisation prerequisite the promotions rest on is declared for BOTH slots.
    normalization = dict(cfg.earned_identity.value_normalization)
    assert "service_branch" in normalization and "origin_country" in normalization, (
        "a slot was promoted to a wall without the value-normalisation classes that make the wall safe — "
        "that is the exact-match shattering the finding in config/resolution.yaml warns about"
    )
    assert "service_branch" in cfg.earned_identity.normalization_required_attrs
    assert "origin_country" in cfg.earned_identity.normalization_required_attrs


def test_no_row_carries_a_retired_stage_marker() -> None:
    """``requires:`` / ``earned_role:`` are gone, and a row that re-grows one fails to LOAD.

    The markers were the stage flag at row granularity. With the machinery unconditional they can only mean
    "this row is for the other behaviour", and a silently ignored ``earned_role: critical`` would quietly
    demote a wall its author meant to declare — so the reader raises instead of ignoring. Asserted through the
    loader, so it covers the shipped file and any future edit to it.
    """
    from chanakya.resolve.rconfig import AttributeRoleError, _validate_attribute_roles

    _validate_attribute_roles(  # the shipped block loads (this call is what ResolveConfig makes)
        ConfigStore.seed_from(config_dir()).snapshot().resolution.attribute_roles
    )
    for marker in ({"requires": "earned_identity"}, {"earned_role": "critical"}):
        try:
            _validate_attribute_roles({"unit": {"service_branch": {"role": "supporting", **marker}}})
        except AttributeRoleError:
            continue
        raise AssertionError(f"a row carrying {marker} loaded silently instead of failing loudly")


def test_variant_operator_branch_still_critical_and_untouched() -> None:
    """This pass must not alter the existing (already-critical) variant.operator_branch declaration."""
    cfg = _cfg()
    assert "operator_branch" in cfg.critical_role_attrs("variant")
    assert "operator_branch" not in cfg.supporting_role_attrs("variant")
