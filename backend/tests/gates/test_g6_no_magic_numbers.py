"""G6 — no magic numbers. Scoring/threshold/half-life literals are absent from the scoring cores;
all read from config (master §1 #3 config-driven, §5; principle 9).

Scans ``credibility/``, ``resolve/``, ``materiality/``, ``observe/`` for numeric literals other than a
tiny structural allowlist (0, 1, -1). A hardcoded weight/threshold/half-life fails here, not review.
The F0 stubs contain no scoring numbers; SCORE/RESOLVE/MONITOR keep it that way by reading config.
"""

from __future__ import annotations

import pytest

from tests.gates._srcscan import numeric_literals, package_py_files

# Structural constants that are never "scoring numbers".
_ALLOW = {0.0, 1.0, -1.0}
_SCORING_PACKAGES = ["credibility", "resolve", "materiality", "observe"]


@pytest.mark.parametrize("subpackage", _SCORING_PACKAGES)
def test_no_scoring_literals_in_code(subpackage: str) -> None:
    offenders: list[str] = []
    for path in package_py_files(subpackage):
        for lineno, value in numeric_literals(path, allow=_ALLOW):
            offenders.append(f"{path.relative_to(path.parents[2])}:{lineno} -> {value!r}")
    assert not offenders, (
        "magic number(s) found in scoring code — move to config (G6): " + "; ".join(offenders)
    )
