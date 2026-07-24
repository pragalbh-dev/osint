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


def test_unit_service_branch_unaffected() -> None:
    """The pre-existing neighbour entry is untouched: still supporting, still durable (not perishable)."""
    cfg = _cfg()
    assert cfg.attribute_roles("unit").get("service_branch", {}).get("role") == "supporting"
    assert cfg.attribute_perishable("unit", "service_branch") is False


def test_variant_operator_branch_still_critical_and_untouched() -> None:
    """This pass must not alter the existing (already-critical) variant.operator_branch declaration."""
    cfg = _cfg()
    assert "operator_branch" in cfg.critical_role_attrs("variant")
    assert "operator_branch" not in cfg.supporting_role_attrs("variant")
