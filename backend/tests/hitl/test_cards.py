"""The 3 ★ card payloads + the integrity caller + the 8-control-point catalogue."""

from __future__ import annotations

from chanakya.hitl import (
    CONTROL_POINTS,
    CONTROL_POINTS_BY_KEY,
    build_alert_disposition_item,
    build_integrity_flag_item,
    build_merge_item,
    build_status_override_item,
)


def test_merge_card_renders_handed_signals_and_offers_accept_reject_split() -> None:
    item = build_merge_item(
        item_id="m1",
        candidate_a={"id": "var_fd2000", "name": "FD-2000"},
        candidate_b={"id": "var_ft2000", "name": "FT-2000"},
        signals=[{"signal": "name-attr", "weight": 0.3, "value": 0.9},
                 {"signal": "shared-neighbourhood", "weight": 0.4, "value": 0.2}],
        merge_score=0.61,
        band="needs-you",
    )
    assert item.type == "merge" and item.pinned is True
    assert item.options == ["accept", "reject", "split"]
    assert item.payload["band"] == "needs-you" and item.payload["merge_score"] == 0.61
    # accept grows the alias table; reject records distinct-from; split reverses a prior merge
    assert item.effects["accept"]["grow_alias"]["same_as"] == ["var_fd2000", "var_ft2000"]
    assert item.effects["reject"]["record_distinct"]["pair"] == ["var_fd2000", "var_ft2000"]
    assert "split_merge" in item.effects["split"]


def test_status_override_card_offers_promote_demote_reject_with_set_status_effects() -> None:
    item = build_status_override_item(item_id="s1", subject_ref="e:x:rel:y", current_status="confirmed")
    assert item.type == "status-override" and item.pinned is True
    assert item.options == ["promote", "demote", "reject"]
    assert item.effects["promote"] == {"set_status": {"e:x:rel:y": "confirmed"}}
    assert item.effects["demote"] == {"set_status": {"e:x:rel:y": "probable"}}
    # reject == forced demote for now (decision 2026-07-18)
    assert item.effects["reject"] == {"set_status": {"e:x:rel:y": "probable"}}


def test_alert_card_shows_before_after_and_offers_real_noise_needsmore() -> None:
    item = build_alert_disposition_item(
        item_id="a1", observable_id="obs-relocation", subject_ref="unit_paad",
        before={"based_at": "Rawalpindi"}, after={"based_at": "Rahwali"},
    )
    assert item.type == "alert-disposition" and item.pinned is True
    assert item.options == ["real", "noise", "needs-more"]
    assert item.payload["before"] == {"based_at": "Rawalpindi"}
    assert item.effects["real"]["tune_tripwire"]["disposition"] == "real"


def test_integrity_flag_carries_origin_and_co_referring_set() -> None:
    item = build_integrity_flag_item(
        item_id="ig1", primary_origin_id="origin-fake",
        affected_element="e:unit_x:based-at:site_y", co_referring_claims=["co1", "co2"],
    )
    assert item.type == "integrity-flag" and item.options == ["flag"]
    eff = item.effects["flag"]
    assert eff["add_integrity_flag"]["element_id"] == "e:unit_x:based-at:site_y"
    assert eff["flag_origin"]["primary_origin_id"] == "origin-fake"
    assert eff["flag_origin"]["co_referring_claims"] == ["co1", "co2"]


def test_all_eight_control_points_exist_in_one_service() -> None:
    keys = {cp.key for cp in CONTROL_POINTS}
    assert keys == {
        "credibility-config", "merge", "ontology-extension", "status-override",
        "observable-definition", "alert-disposition", "assessment-review", "integrity-flag",
    }
    # exactly three are wired deep ★ ...
    star = {cp.key for cp in CONTROL_POINTS if cp.star}
    assert star == {"merge", "status-override", "alert-disposition"}
    wired = {cp.key for cp in CONTROL_POINTS if cp.depth == "wired-deep"}
    assert wired == star
    # ... plus the built (non-★) integrity flag; the rest are config/roadmap only
    assert CONTROL_POINTS_BY_KEY["integrity-flag"].depth == "built"
    assert {cp.depth for cp in CONTROL_POINTS} == {"wired-deep", "built", "config", "roadmap"}
