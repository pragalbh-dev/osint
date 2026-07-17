"""Unit tests for the live config store: seed, snapshot immutability, versioned hot writes,
and — the key hot-config property — a write reflected in the next rebuild with no restart.
"""

from __future__ import annotations

from chanakya.config import ConfigStore
from chanakya.view import rebuild
from tests.fixtures import loaders


def test_seed_from_yaml_loads_all_sections() -> None:
    store = loaders.golden_config_store()
    bundle = store.snapshot()
    assert store.version == 1
    assert bundle.credibility.thresholds == {"confirmed": 0.80, "probable": 0.50}
    assert bundle.resolution.merge_weights["relational"] == 0.40
    assert {s.subject_id for s in bundle.subjects.subjects} == {"lens-acme", "lens-acme-1hop"}
    assert bundle.sources.as_map()["src-imagery"].bias_vector == "commercial"


def test_seed_from_missing_dir_is_tolerant(tmp_path) -> None:
    store = ConfigStore.seed_from(tmp_path)  # empty dir → valid empty bundle
    assert store.version == 1
    assert store.snapshot().credibility.thresholds == {}


def test_snapshot_is_isolated_from_the_store() -> None:
    store = loaders.golden_config_store()
    snap = store.snapshot()
    snap.credibility.thresholds["confirmed"] = 0.99  # mutate the copy
    assert store.snapshot().credibility.thresholds["confirmed"] == 0.80  # store unchanged


def test_hot_write_bumps_version_and_reflects_in_rebuild() -> None:
    store = loaders.golden_config_store()
    ev, dl = loaders.golden_evidence_log(), loaders.golden_decision_log()

    v1 = rebuild(ev, dl, store.snapshot())
    assert v1.meta["config_version"] == 1

    new_version = store.update_credibility({"thresholds": {"confirmed": 0.90}})
    assert new_version == 2

    v2 = rebuild(loaders.golden_evidence_log(), loaders.golden_decision_log(), store.snapshot())
    assert v2.meta["config_version"] == 2  # rebuild saw the new config — no restart
    assert store.snapshot().credibility.thresholds["confirmed"] == 0.90
    assert store.snapshot().credibility.thresholds["probable"] == 0.50  # shallow-merge kept the rest


def test_set_section_replaces_and_versions() -> None:
    store = loaders.golden_config_store()
    v = store.set_section("observables", {"observables": []})
    assert v == 2
    assert store.snapshot().observables.observables == []
