"""AR-2 (anchor resolution + honest-empty diagnostics) and AR-3 (materiality filter) for ``apply_lens``.

These cover the two defects the corrected Phase-4 plan scoped: the lens now *resolves* its anchors (and
says so in ``meta``, including when it finds nothing), and the materiality filter reads the keys the
shipped config actually declares.
"""

from __future__ import annotations

from chanakya.schemas import (
    ConfigBundle,
    EdgeView,
    EntitiesConfig,
    EntityEntry,
    GraphView,
    NodeView,
    SubjectLens,
)
from chanakya.view import apply_lens


def _view() -> GraphView:
    return GraphView(
        nodes=[
            NodeView(id="unit_paad", type="unit", name="Pakistan Army Air Defence"),
            NodeView(id="var_hq9p", type="variant", name="HQ-9/P"),
            NodeView(id="comp_ht233", type="component", name="HT-233"),
            NodeView(id="radar_unknown", type="unknown", name="HT-233 radar"),  # material but untyped
            NodeView(id="blog_rumor", type="rumor", name="unsourced blog claim"),  # genuine off-type chaff
        ],
        edges=[
            EdgeView(id="e1", type="fields", source="unit_paad", target="var_hq9p"),
            EdgeView(id="e2", type="has-component", source="var_hq9p", target="comp_ht233"),
            EdgeView(id="e3", type="observed", source="comp_ht233", target="radar_unknown"),
            EdgeView(id="e4", type="mentions", source="comp_ht233", target="blog_rumor"),
        ],
    )


# ── AR-2: honest-empty + meta diagnostics ────────────────────────────────────────────────────────

def test_meta_carries_anchor_diagnostics() -> None:
    lens = SubjectLens(subject_id="s", anchors=["unit_paad"], max_hops=3)
    out = apply_lens(_view(), lens)
    assert out.meta["anchors_requested"] == ["unit_paad"]
    assert out.meta["anchors_resolved"] == {"unit_paad": "unit_paad"}
    assert out.meta["anchors_missing"] == []
    assert out.meta["anchor_resolution"] == {"unit_paad": "literal"}


def test_all_miss_returns_diagnosed_empty_not_bare_empty() -> None:
    lens = SubjectLens(subject_id="s", anchors=["unit_paaad_typo"], max_hops=3)
    out = apply_lens(_view(), lens)
    assert out.nodes == []  # empty view …
    assert out.meta["anchors_missing"] == ["unit_paaad_typo"]  # … but it SAYS why (the non-negotiable)
    assert out.meta["anchors_resolved"] == {}


def test_registry_anchor_resolves_to_differently_id_node() -> None:
    view = GraphView(
        nodes=[NodeView(id="ent:unit:PAAD", type="unit", name="Pakistan Army Air Defence")],
        edges=[],
    )
    config = ConfigBundle(
        entities=EntitiesConfig(
            entities=[
                EntityEntry(
                    entity_id="unit_paad",
                    type="unit",
                    canonical_name="Pakistan Army Air Defence",
                )
            ]
        )
    )
    lens = SubjectLens(subject_id="s", anchors=["unit_paad"], max_hops=1)
    out = apply_lens(view, lens, config=config)
    assert {n.id for n in out.nodes} == {"ent:unit:PAAD"}  # seeded traversal from the resolved node
    assert out.meta["anchor_resolution"] == {"unit_paad": "registry_alias"}


# ── AR-3: materiality filter ─────────────────────────────────────────────────────────────────────

def test_node_types_allow_drops_offtype_but_keeps_indeterminate() -> None:
    lens = SubjectLens(
        subject_id="s",
        anchors=["unit_paad"],
        max_hops=3,
        materiality_filter={"node_types_allow": ["unit", "variant", "component"]},
    )
    ids = {n.id for n in apply_lens(_view(), lens).nodes}
    assert "blog_rumor" not in ids  # off-type chaff dropped
    assert "radar_unknown" in ids  # type-indeterminate kept (never_drop_indeterminate defaults true)
    assert {"unit_paad", "var_hq9p", "comp_ht233"} <= ids


def test_never_drop_indeterminate_false_drops_unknown_type() -> None:
    lens = SubjectLens(
        subject_id="s",
        anchors=["unit_paad"],
        max_hops=3,
        materiality_filter={
            "node_types_allow": ["unit", "variant", "component"],
            "never_drop_indeterminate": False,
        },
    )
    ids = {n.id for n in apply_lens(_view(), lens).nodes}
    assert "radar_unknown" not in ids  # now the indeterminate node is dropped too
    assert "blog_rumor" not in ids


def test_unrecognised_filter_keys_surfaced_in_meta() -> None:
    lens = SubjectLens(
        subject_id="s",
        anchors=["unit_paad"],
        max_hops=3,
        # exclude_off_subject is the oracle-only key D-P4.9 deletes rather than implements.
        materiality_filter={"node_types_allow": ["unit"], "exclude_off_subject": True},
    )
    out = apply_lens(_view(), lens)
    assert out.meta["unrecognised_filter_keys"] == ["exclude_off_subject"]
