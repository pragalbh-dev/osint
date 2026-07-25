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


def _bundle(*, earned: bool = False):
    """The shipped bundle, optionally with the RK-COREF stage flag on (rows may be gated on it)."""
    bundle = ConfigStore.seed_from(config_dir()).snapshot()
    if earned:
        block = {**(getattr(bundle.resolution, "earned_identity", None) or {}), "enabled": True}
        resolution = bundle.resolution.model_copy(update={"earned_identity": block})
        return bundle.model_copy(update={"resolution": resolution})
    return bundle


def _cfg() -> ResolveConfig:
    return ResolveConfig.from_bundle(_bundle())


def test_unit_alert_posture_declared_supporting_and_perishable() -> None:
    cfg = _cfg()
    spec = cfg.attribute_roles("unit").get("alert_posture")
    assert spec is not None, "unit.alert_posture must be declared in config/resolution.yaml"
    assert spec.get("role") == "supporting"
    assert cfg.attribute_perishable("unit", "alert_posture") is True
    assert "alert_posture" in cfg.supporting_role_attrs("unit")
    # a supporting attribute is never a hard wall
    assert "alert_posture" not in cfg.critical_role_attrs("unit")


def test_unit_service_branch_is_promoted_to_critical_by_earned_identity() -> None:
    """RK-COREF (S3) promotes it — and C7's value normalisation is the prerequisite that made that legal.

    It was ``supporting`` (i.e. inert) for one stated reason: the corpus writes the branch unnormalised
    ('Air Force' / 'PAF' / 'Pakistan Air Force'), and an exact-match wall on those "SHATTERS legitimate
    merges". ``value_normalization`` removes that objection, so a genuinely different service branch is now a
    genuinely different unit. The row carries ``requires: earned_identity``, so the promotion rides the stage
    flag: **flag off it still reads exactly as it did**, which is what this asserts on both sides.
    """
    off = _cfg()
    assert "service_branch" not in off.critical_role_attrs("unit"), (
        "the promotion is live with the stage flag off — flag-off behaviour would not be flag-off"
    )
    # The row PREDATES S3, so flag-off it must read exactly as it always did — still declared, still
    # supporting, still durable. An `earned_role` override is used precisely so the row is not dropped:
    # dropping it would remove the attribute from the agreement ratio and move flag-off scoring.
    assert "service_branch" in off.supporting_role_attrs("unit")
    assert off.attribute_perishable("unit", "service_branch") is False

    on = ResolveConfig.from_bundle(_bundle(earned=True))
    assert "service_branch" in on.critical_role_attrs("unit"), (
        "with the stage flag on the branch is still only `supporting`, so C7's normalisation bought nothing "
        "and the wall D5 describes remains unreachable"
    )


def test_variant_operator_branch_still_critical_and_untouched() -> None:
    """This pass must not alter the existing (already-critical) variant.operator_branch declaration."""
    cfg = _cfg()
    assert "operator_branch" in cfg.critical_role_attrs("variant")
    assert "operator_branch" not in cfg.supporting_role_attrs("variant")
