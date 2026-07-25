"""G2 — rebuild-determinism. Same (logs, config) → byte-identical JSON (master §1 #1, §5).

Three checks: two in-process rebuilds match; the output matches the committed golden file (so a drift
is caught in review); and two subprocess runs under *different* ``PYTHONHASHSEED`` match (so no
hash-seed-dependent set/dict iteration leaks into the output).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from chanakya.view import view_to_json
from tests.fixtures import loaders

_SUBPROC = Path(__file__).parent / "_determinism_subproc.py"
_BACKEND = Path(__file__).resolve().parents[2]


def test_two_rebuilds_are_byte_identical() -> None:
    assert view_to_json(loaders.golden_view()) == view_to_json(loaders.golden_view())


def test_matches_committed_golden_file() -> None:
    # The committed expected_view.json is written with a trailing newline.
    assert view_to_json(loaders.golden_view()) + "\n" == loaders.expected_view_json()


def _run_with_seed(seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run(
        [sys.executable, str(_SUBPROC)], env=env, cwd=str(_BACKEND),
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def test_deterministic_across_hash_seeds() -> None:
    assert _run_with_seed("0") == _run_with_seed("1")
