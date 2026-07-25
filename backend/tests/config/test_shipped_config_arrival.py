"""The shipped ``config/*.yaml`` still loads, and still rebuilds — a cheap arrival guard.

Salvaged from ``tests/gates/test_s2_flag_off_equivalence.py``, which is deleted along with the stage flag it
pinned. That file's job was "with the flag off the graph is byte-identical to the stage before", i.e. it
asserted **backward compatibility** — the thing the flags existed to preserve and the thing their deletion
gives up on purpose. This one assertion in it was not about the flag at all: the config loader *rejects*
unknown shapes at its typed fields, so a malformed ontology or resolution edit surfaces as a boot failure
rather than as a readable test failure. Loud validation must not become a boot break.
"""

from __future__ import annotations

from chanakya.resolve.rconfig import ResolveConfig
from tests import _rk_layer as rk


def test_the_shipped_config_loads_and_rebuilds() -> None:
    bundle = rk.shipped_bundle()

    assert bundle.ontology.node_types and bundle.ontology.edge_types, (
        "the shipped ontology loaded empty — a config edit broke the file's shape"
    )
    view = rk.build_view(rk.fixture_config(), [
        rk.entity_claim("n1", bundle.ontology.node_types[0].name, name="Alpha"),
    ])
    assert view.nodes, "rebuild over the shipped ontology produced no nodes"


def test_the_shipped_resolution_config_compiles_its_identity_tunables() -> None:
    """Every knob the identity machinery reads is *declared*, now that nothing gates it.

    With the stage flags deleted, an undeclared knob is no longer "the stage is off" — it is a mechanism with
    nothing to apply, silently. So the shipped bundle is asserted to declare the four that decide whether a
    merge is earned: the two caps that bind the fusion path, the relationship wall's predicates, and the
    normalisation classes the walls are prerequisite on.
    """
    cfg = ResolveConfig.from_bundle(rk.shipped_bundle())
    earned = cfg.earned_identity

    assert earned.name_ceiling, "no name_ceiling declared — the name cap has nothing to apply"
    assert earned.colocation_ceiling, "no colocation_ceiling declared — the co-location cap is inert"
    assert earned.wall_predicates, "no wall_predicates declared — the relationship wall is inert"
    assert earned.value_normalization, (
        "no value_normalization declared — every wall on a normalization-required slot then takes the third "
        "state, so the walls are inert in the direction that matters"
    )
