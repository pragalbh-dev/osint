"""G7 — confirmed-gate. Cannot reach ``confirmed`` without sufficiency-satisfied AND ≥2 independent
groups AND ``assertion_confidence ≥ threshold`` AND clean gates AND no unresolved contradiction (§5).

F0 owns the **checker** (the durable invariant) and seeds positive/negative cases; SCORE later ALSO
runs this checker over real rebuild output (and may add cases, never weaken it). The checker is a pure
property that must hold for *every* confirmed element in *any* view.
"""

from __future__ import annotations

from chanakya.schemas import EdgeView
from tests.fixtures import loaders

# Gates that cap an assertion at *probable* — a confirmed element must carry none (spine/04 §3.4).
_CAP_FLAGS = {"adversary-denial", "adversary_denial", "decoy-risk", "decoy_risk"}


def is_valid_confirmed(el: EdgeView, confirmed_threshold: float) -> bool:
    """The invariant: if an element is ``confirmed`` it must satisfy every confirmed condition."""
    if el.status != "confirmed":
        return True  # only constrains confirmed elements
    conf = el.confidence.assertion_confidence if el.confidence else None
    if conf is None or conf < confirmed_threshold:
        return False
    groups = el.confidence.independence_groups if el.confidence else []
    if len({g.group_id for g in groups}) < 2:
        return False
    if el.sufficiency is None or not el.sufficiency.satisfied:
        return False
    if el.attrs.get("contradiction"):
        return False
    flags = set(el.confidence.integrity_flags if el.confidence else [])
    if flags & _CAP_FLAGS:
        return False
    return True


def test_checker_matches_seeded_cases() -> None:
    threshold = loaders.golden_config_store().snapshot().credibility.thresholds["confirmed"]
    for case in loaders.per_stage("status_cases")["cases"]:
        el = EdgeView.model_validate(case["element"])
        assert is_valid_confirmed(el, threshold) == case["expected_valid_confirmed"], case["name"]


def test_golden_view_has_no_invalid_confirmed() -> None:
    threshold = loaders.golden_config_store().snapshot().credibility.thresholds["confirmed"]
    view = loaders.golden_view()
    for e in view.edges:
        assert is_valid_confirmed(e, threshold), e.id
    # F0's stub machine never fabricates a confirmed status.
    assert all(e.status != "confirmed" for e in view.edges)
