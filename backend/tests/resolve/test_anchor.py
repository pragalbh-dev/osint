"""Unit tests for the shared view-level anchor resolver (AR-2).

The lens and the observable watch-scope both route through :func:`chanakya.resolve.resolve_anchors`, so
its ladder (literal id → registry alias → alias class) and its honest-miss reporting are tested once here.
"""

from __future__ import annotations

from chanakya.resolve import AnchorResolution, resolve_anchors
from chanakya.resolve.anchor import ALIAS_INDEX, LITERAL, REGISTRY_ALIAS
from chanakya.schemas import (
    ConfigBundle,
    EntitiesConfig,
    EntityEntry,
    GraphView,
    NodeView,
    ResolutionConfig,
)


def _view() -> GraphView:
    return GraphView(
        nodes=[
            NodeView(id="unit_paad", type="unit", name="Pakistan Army Air Defence"),
            # Registry id is ``site_karachi`` but the node landed under a minted id carrying the name.
            NodeView(id="ent:basing_site:Malir", type="basing_site", name="Malir Cantonment"),
            # A same-named node of the WRONG type — must NOT capture a basing_site anchor (type gate).
            NodeView(id="unit_malir", type="unit", name="Malir Cantonment"),
            NodeView(id="var_hq9p", type="variant", name="HQ-9/P"),
        ]
    )


def _config() -> ConfigBundle:
    return ConfigBundle(
        entities=EntitiesConfig(
            entities=[
                EntityEntry(
                    entity_id="site_karachi",
                    type="basing_site",
                    canonical_name="Karachi Army Air Defence site",
                    aliases=["Malir Cantonment", "Malir"],
                ),
            ]
        ),
        resolution=ResolutionConfig(alias_table={"HQ-9/P": ["FD-2000"]}),
    )


def test_tier1_literal_id() -> None:
    (r,) = resolve_anchors(["unit_paad"], _view(), _config())
    assert r == AnchorResolution("unit_paad", "unit_paad", LITERAL)


def test_tier2_registry_alias_is_type_gated() -> None:
    (r,) = resolve_anchors(["site_karachi"], _view(), _config())
    # Binds the basing_site node by alias, NOT the same-named unit — the type gate holds.
    assert r.node_id == "ent:basing_site:Malir"
    assert r.via == REGISTRY_ALIAS


def test_tier3_alias_index_class() -> None:
    # "FD-2000" is only alias-equivalent to "HQ-9/P" via the seeded alias table (no literal, no registry).
    (r,) = resolve_anchors(["FD-2000"], _view(), _config())
    assert r.node_id == "var_hq9p"
    assert r.via == ALIAS_INDEX


def test_miss_is_reported_not_dropped() -> None:
    (r,) = resolve_anchors(["site_karrachi_typo"], _view(), _config())
    assert r == AnchorResolution("site_karrachi_typo", None, None)


def test_config_none_degrades_to_literal_only() -> None:
    # Without config, tier 2/3 are inert: the registry-id anchor no longer binds, only literal ids do.
    lit, reg = resolve_anchors(["unit_paad", "site_karachi"], _view(), None)
    assert lit.via == LITERAL and lit.node_id == "unit_paad"
    assert reg.node_id is None and reg.via is None
