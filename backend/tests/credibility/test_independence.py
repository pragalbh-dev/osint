"""Three-axis independence grouping — the anti-false-corroboration machine (spine/04 §3.5)."""

from __future__ import annotations

from chanakya.credibility.independence import group_by_independence
from tests.credibility.builders import bundle, claim, source


def _group_ids(groups: list) -> list[list[str]]:
    return [sorted(g.claim_ids) for g in groups]


def test_two_cross_independent_claims_are_two_groups() -> None:
    cfg = bundle()
    claims = {
        "a": claim("a", "sa"),  # imint source
        "b": claim("b", "sb"),  # text source
    }
    sources = {"sa": source("sa", "imint"), "sb": source("sb", "text")}
    groups = group_by_independence(["a", "b"], claims, sources, cfg)
    assert _group_ids(groups) == [["a"], ["b"]]  # different origin + discipline + interest → 2 looks


def test_shared_origin_collapses_to_one_group() -> None:
    # Two reshares of one origin → one group (echo collapse; no false corroboration).
    cfg = bundle()
    claims = {"a": claim("a", "sa"), "b": claim("b", "sb")}
    sources = {
        "sa": source("sa", "text", origin="parade_img"),
        "sb": source("sb", "text", origin="parade_img"),
    }
    groups = group_by_independence(["a", "b"], claims, sources, cfg)
    assert len(groups) == 1 and _group_ids(groups) == [["a", "b"]]


def test_shared_image_hash_is_one_origin() -> None:
    cfg = bundle()
    claims = {
        "a": claim("a", "sa", attributes={"sha256": "IMG"}),
        "b": claim("b", "sb", attributes={"sha256": "IMG"}),
    }
    sources = {"sa": source("sa", "text"), "sb": source("sb", "text2")}
    assert len(group_by_independence(["a", "b"], claims, sources, cfg)) == 1


def test_aggregator_inherits_upstream_origin() -> None:
    # SIPRI (aggregator_of [press]) + that press = one origin, not two independent looks.
    cfg = bundle()
    claims = {"a": claim("a", "sipri"), "b": claim("b", "press")}
    sources = {"sipri": source("sipri", "text", aggregator=["press"]), "press": source("press", "text2")}
    assert len(group_by_independence(["a", "b"], claims, sources, cfg)) == 1


def test_aligned_interest_is_false_corroboration() -> None:
    # Operator-state + exporter-state are aligned parties → one group, not cross-interest corroboration.
    cfg = bundle()
    claims = {"a": claim("a", "sa"), "b": claim("b", "sb")}
    sources = {
        "sa": source("sa", "imint", bias="operator-state"),
        "sb": source("sb", "text", bias="exporter-state"),
    }
    assert len(group_by_independence(["a", "b"], claims, sources, cfg)) == 1


def test_adversary_denial_is_excluded_from_grouping() -> None:
    # A fake second-source never enters a group → never corroborates.
    cfg = bundle()
    claims = {"a": claim("a", "sa"), "x": claim("x", "sx")}
    sources = {"sa": source("sa", "text"), "sx": source("sx", "text2", adversary=True)}
    groups = group_by_independence(["a", "x"], claims, sources, cfg)
    assert _group_ids(groups) == [["a"]]  # x is gone entirely


def test_inference_shares_its_premises_group() -> None:
    # D (inference, premises=[A]) must not corroborate its own premise A → same group.
    cfg = bundle()
    claims = {
        "A": claim("A", "sa", predicate="based-at"),
        "D": claim("D", "sd", predicate="based-at", kind="inference", premises=["A"]),
    }
    sources = {"sa": source("sa", "imint"), "sd": source("sd", "text")}
    groups = group_by_independence(["A", "D"], claims, sources, cfg)
    assert len(groups) == 1 and _group_ids(groups) == [["A", "D"]]


def test_same_discipline_pair_is_half_weight() -> None:
    # Two independent-but-same-class (both textual) looks: separate groups, the second at half weight.
    cfg = bundle()
    claims = {"a": claim("a", "sa"), "b": claim("b", "sb")}
    sources = {"sa": source("sa", "text"), "sb": source("sb", "text2")}
    groups = group_by_independence(["a", "b"], claims, sources, cfg)
    assert len(groups) == 2
    assert sorted(g.weight for g in groups) == [0.5, 1.0]
