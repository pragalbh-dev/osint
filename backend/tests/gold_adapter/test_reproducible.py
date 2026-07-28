"""The committed ``.bakeoff.json`` files must be REGENERABLE, not trusted.

A reviewer has to be able to rebuild them from the labeled gold and get the same bytes; otherwise the
scored denominators are an artefact somebody hand-made once. Two properties are asserted: the CLI is
deterministic (same input, same bytes) and its output equals what is committed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval.gold.adapter import main

from .conftest import GOLD_DIR, REPO_ROOT

COMMITTED = (GOLD_DIR / "claim-gold.bakeoff.json", GOLD_DIR / "sub-oracle.bakeoff.json")

pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in COMMITTED),
    reason="the adapted gold is not present in this checkout",
)


def _regenerate(out_dir: Path) -> int:
    return main([
        "--gold", str(GOLD_DIR / "claim-gold.json"),
        "--sub-oracle", str(GOLD_DIR / "sub-oracle.json"),
        "--out-dir", str(out_dir),
        "--repo-root", str(REPO_ROOT),
    ])


def test_the_committed_files_regenerate_byte_for_byte(tmp_path: Path, capsys: Any) -> None:
    assert _regenerate(tmp_path) == 0
    capsys.readouterr()
    for committed in COMMITTED:
        fresh = tmp_path / committed.name
        assert fresh.read_bytes() == committed.read_bytes(), (
            f"{committed.name} is not reproducible from the adapter — regenerate it with "
            "`cd backend && python -m eval.gold` and commit the result"
        )


def test_regeneration_is_deterministic(tmp_path: Path, capsys: Any) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    _regenerate(first)
    _regenerate(second)
    capsys.readouterr()
    for name in (p.name for p in COMMITTED):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_the_derived_files_say_they_are_derived(tmp_path: Path, capsys: Any) -> None:
    """Provenance on the artefact itself, including the digest of the labels it came from."""
    _regenerate(tmp_path)
    capsys.readouterr()
    for name in (p.name for p in COMMITTED):
        produced = json.loads((tmp_path / name).read_text(encoding="utf-8"))["produced_by"]
        assert produced["adapter"] == "eval.gold.adapter"
        assert produced["from_schema"].startswith("rk-spike-")
        assert len(produced["from_digest_sha256"]) == 64
        assert "regenerate" in produced["note"].lower()


def test_the_digest_tracks_the_labeled_input(tmp_path: Path, capsys: Any) -> None:
    """Change a label and the digest changes — so a stale derived file is detectable, not invisible."""
    import hashlib

    _regenerate(tmp_path)
    capsys.readouterr()
    recorded = json.loads(
        (tmp_path / "claim-gold.bakeoff.json").read_text(encoding="utf-8")
    )["produced_by"]["from_digest_sha256"]
    actual = hashlib.sha256((GOLD_DIR / "claim-gold.json").read_bytes()).hexdigest()
    assert recorded == actual
