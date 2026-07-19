"""EntitiesConfig — the 9th surface, the entity canonical-id registry (D-B, mirrors PlacesConfig).

The registry is the stable id space that closes the id-namespace split: RESOLVE resolves surface forms
onto these ``entity_id``s (consumed in Phase 3), and the lens/observables/oracle share them.
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.schemas import CONFIG_SECTIONS, EntitiesConfig
from chanakya.settings import config_dir


def test_entities_registered_as_section() -> None:
    assert CONFIG_SECTIONS.get("entities") is EntitiesConfig


def test_entities_seed_from_yaml() -> None:
    entities = ConfigStore.seed_from(config_dir()).snapshot().entities
    by_id = entities.as_map()
    # the canonical ids the oracle / lens / observables reference must exist as registry entries
    for eid in ("comp_ht233", "unit_paad", "mfr_casic", "mfr_taian", "comp_tel_chassis"):
        assert eid in by_id, eid
    ht233 = by_id["comp_ht233"]
    assert ht233.type == "component"
    assert ht233.aliases  # the fragments the RCA saw (9 name variants) collapse to this one entry


def test_distinct_from_traps_preserved() -> None:
    by_id = ConfigStore.seed_from(config_dir()).snapshot().entities.as_map()

    def barred(a: str, b: str) -> bool:
        return b in by_id[a].distinct_from or a in by_id[b].distinct_from

    # HQ-9/P stays distinct from HQ-9BE and FT-2000 (the earned distinct-from traps)
    assert barred("var_hq9p", "var_hq9be")
    assert barred("var_hq9p", "alias_ft2000")
    # Pakistan Army Air Defence must NOT co-merge with the PAF operator
    assert barred("unit_paad", "unit_hq9b")


def test_hot_write_bumps_version() -> None:
    store = ConfigStore.seed_from(config_dir())
    v0 = store.version
    v1 = store.set_section("entities", {"entities": []})
    assert v1 == v0 + 1
    assert store.snapshot().entities.entities == []
