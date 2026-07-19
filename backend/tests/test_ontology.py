"""EdgeLaneIndex — the domain/range re-lane + the extraction enum (D-A, DECISIONS §6 "EVAL").

These encode the RCA's edge-vocabulary symptoms as passing assertions: the collisions the live pipeline
hit (``equips`` firing Variant→Unit, the hero landing on ``component-of``, ``supplies-component`` never
firing) become deterministic re-lanes keyed on endpoint types.
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.ontology import EdgeLaneIndex
from chanakya.settings import config_dir

EXTRACTOR_ENUM = {
    "based-at", "inducted-into", "imported-by", "exported-by", "equips",
    "supplies-component", "manufactures", "design-authority-for", "component-of", "replenishes",
}
NON_EXTRACTOR = {
    "same-as", "distinct-from", "substitutable-by", "evidenced-by",
    "corroborates", "contradicts", "supersedes", "derived-from", "sustained-by",
}


def _index() -> EdgeLaneIndex:
    return EdgeLaneIndex(ConfigStore.seed_from(config_dir()).snapshot().ontology)


def test_no_endpoint_collisions() -> None:
    # every extractor edge must be uniquely determined by (from -> to); a collision is a config bug.
    assert _index().collisions == {}


def test_extraction_enum_is_relationship_edges_only() -> None:
    enum = set(_index().extractor_edges())
    assert enum == EXTRACTOR_ENUM
    assert enum.isdisjoint(NON_EXTRACTOR)  # resolution/evidence/derived edges are never LLM-asserted


def test_canonical_edge_by_endpoints() -> None:
    idx = _index()
    assert idx.canonical_edge("component", "variant") == "equips"           # the hero relation
    assert idx.canonical_edge("variant", "unit") == "inducted-into"
    assert idx.canonical_edge("manufacturer", "component") == "supplies-component"
    assert idx.canonical_edge("manufacturer", "variant") == "manufactures"  # tightened → no collision
    assert idx.canonical_edge("unit", "basing_site") == "based-at"
    assert idx.canonical_edge("component", "component") == "component-of"


def test_relane_fixes_the_rca_collisions() -> None:
    idx = _index()
    # "HQ-9/P equips the PAF" — LLM picks a valid-but-wrong-direction verb; endpoints re-lane it.
    r = idx.relane("equips", "variant", "unit")
    assert r.edge == "inducted-into" and r.action == "relaned"
    # HT-233 --component-of--> HQ-9/P — the hero, mis-laned by the LLM; endpoints restore `equips`.
    r = idx.relane("component-of", "component", "variant")
    assert r.edge == "equips" and r.action == "relaned"
    # Taian --manufactures--> chassis — near-synonym; endpoints force the deep-tier edge.
    r = idx.relane("manufactures", "manufacturer", "component")
    assert r.edge == "supplies-component" and r.action == "relaned"


def test_relane_keeps_already_correct() -> None:
    r = _index().relane("equips", "component", "variant")
    assert r.action == "kept" and r.edge == "equips" and not r.reversed


def test_relane_handles_backwards_written_fact() -> None:
    # "PAF equips HQ-9/P" written unit->variant: no forward edge, but the swap names inducted-into.
    r = _index().relane("equips", "unit", "variant")
    assert r.edge == "inducted-into" and r.action == "relaned" and r.reversed is True


def test_relane_rejects_offontology_endpoints() -> None:
    r = _index().relane("equips", "source", "known_gap")
    assert r.edge is None and r.action == "rejected" and not r.ok
