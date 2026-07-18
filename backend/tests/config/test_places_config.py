"""PlacesConfig — the 8th config surface (F0-amendment: place gazetteer into the live store).

The gazetteer is now seeded + hot-writable like every other surface, so RESOLVE reads it through the
config store (not a second file path) and an analyst can extend it with no restart.
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.schemas import CONFIG_SECTIONS, PlacesConfig
from chanakya.settings import config_dir


def test_places_registered_as_section() -> None:
    assert CONFIG_SECTIONS.get("places") is PlacesConfig


def test_places_seeds_from_yaml() -> None:
    places = ConfigStore.seed_from(config_dir()).snapshot().places
    by_id = places.as_map()

    # the anchors RESOLVE needs are present
    assert "pl_nurkhan" in by_id
    nur = by_id["pl_nurkhan"]
    assert nur.icao == "OPRN"
    assert nur.canonical_dd is not None and len(nur.canonical_dd) == 2

    # the withheld "Chaklala" alias must NOT be seeded (it is the earned-merge demo)
    assert not any("chaklala" in a.lower() for a in nur.aliases)

    # the two-ports distinct-from trap is present and mutual
    assert "pl_karachi_port" in by_id["pl_port_qasim"].distinct_from
    assert "pl_port_qasim" in by_id["pl_karachi_port"].distinct_from

    # per-precision-class proximity radii loaded
    assert places.proximity_radius_m.get("terminal")


def test_places_hot_write_bumps_version() -> None:
    store = ConfigStore.seed_from(config_dir())
    v0 = store.version
    v1 = store.set_section("places", {"places": [], "proximity_radius_m": {}})
    assert v1 == v0 + 1
    assert store.snapshot().places.places == []
