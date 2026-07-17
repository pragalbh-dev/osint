"""Emit the golden view JSON to stdout — run by G2 in subprocesses with differing PYTHONHASHSEED.

This catches nondeterminism that a single in-process run cannot: hash-seed-dependent set/dict
iteration order leaking into the output.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # backend/ on path for `tests.*`

from chanakya.view import view_to_json  # noqa: E402
from tests.fixtures import loaders  # noqa: E402

if __name__ == "__main__":
    sys.stdout.write(view_to_json(loaders.golden_view()))
